/**
 * Link-preview shim for audit.grahamkindermann.com
 * ================================================
 *
 * The problem this solves, verified 2026-08-26:
 * Streamlit is a JavaScript SPA. Fetching the app returns only its shell plus
 * "You need to enable JavaScript to run this app." No scraper — LinkedIn, X,
 * Slack, iMessage, WhatsApp, Discord — ever executes the JS that injects the
 * OG tags, so every share of the audit renders as a bare URL with no title,
 * no description and no image. It is a property of the framework, not the host.
 *
 * This Worker answers bot requests at the document root with a static HTML
 * document carrying the meta tags. EVERY other request is passed through
 * untouched by returning `fetch(request)` — no URL rewriting, no header
 * surgery, no second origin. Cloudflare resolves it against the zone's own
 * DNS record for this hostname, which is the CNAME to Render.
 *
 * That passthrough is deliberate and it is the whole safety argument:
 *   - There is no hardcoded origin hostname to go stale. An earlier draft of
 *     this file hardcoded the LEGACY Streamlit Cloud host, which would have
 *     silently served the old, unmaintained app to every human visitor.
 *   - Streamlit's websocket (/_stcore/stream) upgrades through Cloudflare
 *     natively. Reconstructing the request is what breaks WS upgrades.
 *
 * PRE-REQUISITE — this Worker does nothing until the DNS record is proxied:
 *   DNS -> audit.grahamkindermann.com must be **Proxied** (orange cloud).
 *   It ships as "DNS only", and Worker routes never fire on a grey-cloud
 *   record. Zone SSL/TLS mode must be Full or Full (strict) — verified Full
 *   on 2026-08-27. On Flexible, Cloudflare would talk HTTP to Render, Render
 *   would redirect to HTTPS, and the tool would enter a redirect loop.
 *
 * Deploy:
 *   1. Workers & Pages -> Create -> Worker. Paste this file. Deploy.
 *   2. Settings -> Domains & Routes -> Add route:
 *        audit.grahamkindermann.com/*      (zone: grahamkindermann.com)
 *   3. DNS -> edit the audit CNAME -> Proxy status: Proxied. Save.
 *   4. Verify, in this order, and roll back at the first failure:
 *        curl -sI https://audit.grahamkindermann.com/_stcore/health
 *        curl -A "Mozilla/5.0" -s https://audit.grahamkindermann.com/ | head -5
 *        curl -A "facebookexternalhit/1.1" https://audit.grahamkindermann.com/ | head -40
 *        then load the tool in a browser and answer one question — if the
 *        websocket is down, the app renders and then hangs, which a curl
 *        cannot tell you.
 *      Rollback is one click: set the DNS record back to DNS only.
 *   5. Re-scrape with LinkedIn Post Inspector and the X card validator; both
 *      cache aggressively.
 *
 * The same pattern works unchanged for index. and household. — change the
 * META block. Both are on Netlify and both are currently DNS-only too.
 */

const CANONICAL = "https://audit.grahamkindermann.com";

const META = {
  title: "The Structural Audit: A diagnostic of the company, not the founder",
  description:
    "Fifty questions across six dimensions. Weighted scoring, industry benchmarks, " +
    "risk-ranked output. An honest tool for operators.",
  image: `${CANONICAL}/app/static/og-audit.png`,
  siteName: "Structural Advantage",
};

// Deliberately broad. A false positive costs a bot a static page; a false
// negative costs a broken preview, which is the thing being fixed.
const BOT = new RegExp(
  [
    "facebookexternalhit", "facebookcatalog", "linkedinbot", "twitterbot",
    "slackbot", "slack-imgproxy", "discordbot", "whatsapp", "telegrambot",
    "skypeuripreview", "applebot", "bingbot", "googlebot", "google-inspectiontool",
    "duckduckbot", "baiduspider", "yandex", "embedly", "quora link preview",
    "outbrain", "pinterest", "redditbot", "vkshare", "flipboard", "tumblr",
    "bitlybot", "nuzzel", "iframely", "mastodon", "bluesky", "opengraph",
    "developers.google.com/+/web/snippet", "sogou", "exabot", "ia_archiver",
  ].join("|"),
  "i"
);

const esc = (s) =>
  String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
           .replace(/>/g, "&gt;").replace(/"/g, "&quot;");

function shell() {
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>${esc(META.title)}</title>
<link rel="canonical" href="${CANONICAL}/">
<meta name="description" content="${esc(META.description)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="${esc(META.siteName)}">
<meta property="og:title" content="${esc(META.title)}">
<meta property="og:description" content="${esc(META.description)}">
<meta property="og:url" content="${CANONICAL}/">
<meta property="og:image" content="${META.image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="The Structural Audit — a diagnostic of the company, not the founder">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${esc(META.title)}">
<meta name="twitter:description" content="${esc(META.description)}">
<meta name="twitter:image" content="${META.image}">
<meta http-equiv="refresh" content="0; url=${CANONICAL}/">
</head>
<body>
<h1>${esc(META.title)}</h1>
<p>${esc(META.description)}</p>
<p><a href="${CANONICAL}/">Open the Structural Audit</a></p>
</body>
</html>`;
}

export default {
  async fetch(request) {
    const ua = request.headers.get("user-agent") || "";
    const url = new URL(request.url);

    // Only the document root gets the shim, and only for a scraper. Static
    // assets, the websocket and every /_stcore/ call must reach the app.
    const isRoot = url.pathname === "/" || url.pathname === "";

    if (isRoot && BOT.test(ua)) {
      return new Response(shell(), {
        headers: {
          "content-type": "text/html; charset=utf-8",
          // Short cache: the shell is cheap to regenerate and the scrapers
          // cache on their own side anyway.
          "cache-control": "public, max-age=300",
          "x-og-shim": "bot",
        },
      });
    }

    // Everything else: untouched passthrough to the zone's origin.
    return fetch(request);
  },
};
