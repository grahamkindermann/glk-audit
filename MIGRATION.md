# Migration: structural-audit.streamlit.app → audit.grahamkindermann.com

Everything code-side is already in this repo (July 10). What remains is ~20 minutes
of dashboard work that requires your accounts. Follow in order.

## What changed in the repo (already done)
- `app.py`: canonical URL + og:image + twitter summary_large_image meta (both the
  body block and the JS head injector), `<link rel=canonical>`, and an env-gated
  legacy redirect (`AUDIT_REDIRECT_LEGACY=1` bounces *.streamlit.app → custom domain).
- `static/og-audit.png`: 1200×630 branded share image, served at
  `/app/static/og-audit.png` (static serving enabled in `.streamlit/config.toml`).
- `Dockerfile`, `.dockerignore`, `render.yaml`: always-on container deploy.

## Step 1 — Push
```bash
git push origin main
```
(Streamlit Cloud will auto-redeploy; harmless — the new meta defaults to the
custom-domain canonical, which is what you want scrapers to see going forward.)

## Step 2 — Render (~10 min)
1. render.com → New + → **Blueprint** → select `grahamkindermann/glk-audit`.
2. It reads `render.yaml`. Confirm plan **Starter** (always-on, ~$7/mo).
3. In the service → Environment, set values for
   `POSTHOG_PROJECT_TOKEN`, `POSTHOG_HOST` (copy from Streamlit Cloud
   → App settings → Secrets).
4. Deploy; wait for healthy. Test the `onrender.com` URL end-to-end
   (landing → a few questions → save code → gate → results).

## Step 3 — DNS (~2 min, Cloudflare)
Cloudflare dashboard → grahamkindermann.com → DNS:
- Add `CNAME  audit  glk-structural-audit.onrender.com` (or the target Render
  shows under Custom Domains), **DNS only (grey cloud)** first.
- In Render → Settings → Custom Domains → add `audit.grahamkindermann.com`,
  wait for the certificate to issue, verify https loads.
- Optional: flip to proxied (orange cloud) afterwards if you want Cloudflare
  in front; verify websockets still connect (the app goes blank if not).

## Step 4 — Verify the share card
- https://audit.grahamkindermann.com/app/static/og-audit.png loads.
- Paste the domain into LinkedIn Post Inspector / opengraph.xyz — image + title
  + description should render. (This never worked on Community Cloud: non-JS
  scrapers only saw the shell. On Render they see real HTML.)

## Step 5 — Flip the published links (same day)
- Site: tools.html, advisory.html, index.html cards → audit.grahamkindermann.com
  (keep the UTM params). The v38 folder Claude prepared already has this change.
- Index tool result page ("Structural Audit" cross-link) and Household result page.
- Substack: About page link + the post-footer boilerplate going forward.

## Step 6 — Legacy redirect
On **Streamlit Cloud** → App settings → Secrets, add:
```toml
AUDIT_REDIRECT_LEGACY = "1"
```
Reboot the app. Old links now bounce to the custom domain. Keep the Streamlit
app alive 6–12 months, then retire it.

## Rollback
Point the site links back to structural-audit.streamlit.app and set
`AUDIT_REDIRECT_LEGACY = "0"`. Nothing else to undo.
