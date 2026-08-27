/**
 * Link-preview shim for audit.grahamkindermann.com
 * ================================================
 *
 * The problem this solves, verified 2026-08-26:
 * Streamlit is a JavaScript SPA. Fetching the app returns only its shell plus
 * "You need to enable JavaScript to run this app." No scraper — LinkedIn, X,
 * Slack, iMessage, WhatsApp, Discord — ever executes the JS that injects the
 * OG tags, so every share of the audit renders as a bare URL with no title,
 * no description and no image. This is true on Streamlit Community Cloud AND
 * on Render; it is a property of the framework, not the host.
 *
 * This Worker sits in front of the domain, answers bot requests with a static
 * HTML document carrying the meta tags, and proxies every human request to
 * the app untouched. Humans never see this document; bots never see the app.
 *
 * Deploy (Cloudflare dashboard, same account as the Pages site):
 *   1. Workers & Pages -> Create -> Worker. Paste this file. Deploy.
 *   2. Settings -> Domains & Routes -> Add route:
 *        audit.grahamkindermann.com/*      (zone: grahamkindermann.com)
 *   3. Leave the existing CNAME/proxy for the app in place; this Worker runs
 *      in front of it and calls it via ORIGIN below.
 *   4. Verify:
 *        curl -A "facebookexternalhit/1.1" https://audit.grahamkindermann.com/ | head -40
 *        curl -A "Mozilla/5.0" -sI https://audit.grahamkindermann.com/ | head -5
 *      The first must show <meta property="og:title">; the second must be the
 *      normal app response.
 *   5. Re-scrape with LinkedIn Post Inspector and the X card validator; both
 *      cache aggressively.
 *
 * The same pattern works unchanged for index. and household. — change ORIGIN
 * and the META block.
 */

const ORIGIN = "https://structural-audit.streamlit.app";
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

    // Only the document root gets the shim. Static assets, the websocket and
    // every /_stcore/ call must pass through untouched or the app will not run.
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

    // Everything else proxies to the app, preserving method, body, headers,
    // query string and websocket upgrades.
    const target = new URL(url.pathname + url.search, ORIGIN);
    const proxied = new Request(target, request);
    proxied.headers.set("host", new URL(ORIGIN).host);
    return fetch(proxied);
  },
};
