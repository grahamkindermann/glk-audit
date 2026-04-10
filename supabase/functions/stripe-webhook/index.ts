// Supabase Edge Function: stripe-webhook
// Handles Stripe subscription lifecycle events and updates the subscriptions table.
//
// Required env vars (set in Supabase Dashboard → Edge Functions → Secrets):
//   STRIPE_SECRET_KEY    — sk_live_...
//   STRIPE_WEBHOOK_SECRET — whsec_...
//
// Deploy with:
//   supabase functions deploy stripe-webhook --project-ref fucitxhzxtvrpfxlkhox

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import Stripe from "https://esm.sh/stripe@14?target=deno";

const stripe = new Stripe(Deno.env.get("STRIPE_SECRET_KEY")!, {
  apiVersion: "2023-10-16",
  httpClient: Stripe.createFetchHttpClient(),
});

const WEBHOOK_SECRET = Deno.env.get("STRIPE_WEBHOOK_SECRET")!;

// Supabase client with service_role key (bypasses RLS)
const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
const supabaseServiceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const supabase = createClient(supabaseUrl, supabaseServiceKey);

// Map Stripe price IDs to tier names (used by the subscription path only;
// one-time purchases resolve tier via the purchases table + product_type).
const PRICE_TO_TIER: Record<string, string> = {
  [Deno.env.get("STRIPE_PRICE_REPORT") || ""]: "report",
  [Deno.env.get("STRIPE_PRICE_PRO") || ""]: "pro",
  [Deno.env.get("STRIPE_PRICE_TEAM") || ""]: "team",
};

function tierFromPriceId(priceId: string | null): string {
  if (!priceId) return "free";
  return PRICE_TO_TIER[priceId] || "pro";
}

serve(async (req) => {
  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  const body = await req.text();
  const sig = req.headers.get("stripe-signature");

  if (!sig) {
    return new Response("Missing stripe-signature header", { status: 400 });
  }

  // Verify webhook signature
  let event: Stripe.Event;
  try {
    event = await stripe.webhooks.constructEventAsync(body, sig, WEBHOOK_SECRET);
  } catch (err) {
    console.error("Webhook signature verification failed:", err.message);
    return new Response(`Webhook Error: ${err.message}`, { status: 400 });
  }

  console.log(`Received event: ${event.type}`);

  // -----------------------------------------------------------------------
  // checkout.session.completed — branch on session mode
  //   "payment"      -> one-time purchase, insert into `purchases`
  //   "subscription" -> recurring subscription, upsert into `subscriptions`
  // -----------------------------------------------------------------------
  if (event.type === "checkout.session.completed") {
    const session = event.data.object as Stripe.Checkout.Session;
    const userId = session.metadata?.user_id;
    const stripeCustomerId = session.customer as string;

    if (!userId) {
      console.error("No user_id in checkout session metadata");
      return new Response("OK", { status: 200 });
    }

    if (session.mode === "payment") {
      // One-time purchase flow (e.g., $149 Full Report)
      // Retrieve the full session with line items expanded to get the price ID.
      const fullSession = await stripe.checkout.Sessions.retrieve(session.id, {
        expand: ["line_items"],
      });
      const priceId = fullSession.line_items?.data[0]?.price?.id || null;
      const amountTotal = session.amount_total || 0;
      const currency = session.currency || "usd";
      const paymentIntentId = session.payment_intent as string | null;

      const { error } = await supabase.from("purchases").upsert(
        {
          user_id: userId,
          stripe_customer_id: stripeCustomerId,
          stripe_payment_intent_id: paymentIntentId,
          stripe_checkout_session_id: session.id,
          stripe_price_id: priceId,
          product_type: "full_report",
          amount_cents: amountTotal,
          currency,
          status: "completed",
        },
        { onConflict: "stripe_checkout_session_id" }
      );

      if (error) {
        console.error("Supabase purchases upsert error:", error);
        return new Response("DB error", { status: 500 });
      }

      console.log(`Purchase recorded: user=${userId} product=full_report amount=${amountTotal}`);
    } else if (session.mode === "subscription") {
      // Legacy recurring-subscription flow
      const stripeSubscriptionId = session.subscription as string;
      const subscription = await stripe.subscriptions.retrieve(stripeSubscriptionId);
      const priceId = subscription.items.data[0]?.price?.id || null;
      const tier = tierFromPriceId(priceId);

      const { error } = await supabase.from("subscriptions").upsert(
        {
          user_id: userId,
          tier,
          status: "active",
          stripe_customer_id: stripeCustomerId,
          stripe_subscription_id: stripeSubscriptionId,
          stripe_price_id: priceId,
          current_period_start: new Date(subscription.current_period_start * 1000).toISOString(),
          current_period_end: new Date(subscription.current_period_end * 1000).toISOString(),
          updated_at: new Date().toISOString(),
        },
        { onConflict: "stripe_subscription_id" }
      );

      if (error) {
        console.error("Supabase subscriptions upsert error:", error);
        return new Response("DB error", { status: 500 });
      }

      console.log(`Subscription created: user=${userId} tier=${tier}`);
    }
  }

  // -----------------------------------------------------------------------
  // customer.subscription.updated — plan change, renewal, payment issue
  // -----------------------------------------------------------------------
  if (event.type === "customer.subscription.updated") {
    const subscription = event.data.object as Stripe.Subscription;
    const stripeSubscriptionId = subscription.id;
    const priceId = subscription.items.data[0]?.price?.id || null;
    const tier = tierFromPriceId(priceId);
    const status = subscription.status === "active" ? "active"
      : subscription.status === "past_due" ? "past_due"
      : subscription.status === "trialing" ? "trialing"
      : "canceled";

    const { error } = await supabase
      .from("subscriptions")
      .update({
        tier,
        status,
        stripe_price_id: priceId,
        current_period_start: new Date(subscription.current_period_start * 1000).toISOString(),
        current_period_end: new Date(subscription.current_period_end * 1000).toISOString(),
        updated_at: new Date().toISOString(),
      })
      .eq("stripe_subscription_id", stripeSubscriptionId);

    if (error) {
      console.error("Supabase update error:", error);
      return new Response("DB error", { status: 500 });
    }

    console.log(`Subscription updated: sub=${stripeSubscriptionId} tier=${tier} status=${status}`);
  }

  // -----------------------------------------------------------------------
  // customer.subscription.deleted — cancellation
  // -----------------------------------------------------------------------
  if (event.type === "customer.subscription.deleted") {
    const subscription = event.data.object as Stripe.Subscription;
    const stripeSubscriptionId = subscription.id;

    const { error } = await supabase
      .from("subscriptions")
      .update({
        status: "canceled",
        updated_at: new Date().toISOString(),
      })
      .eq("stripe_subscription_id", stripeSubscriptionId);

    if (error) {
      console.error("Supabase delete error:", error);
      return new Response("DB error", { status: 500 });
    }

    console.log(`Subscription canceled: sub=${stripeSubscriptionId}`);
  }

  return new Response(JSON.stringify({ received: true }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
});
