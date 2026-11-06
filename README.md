# The Structural Audit

A B2B operational diagnostic of the business itself, across six dimensions. Companion to the Structural Advantage Index. The Index reads the founder. This reads the company.

## What is in this folder

```
structural-audit/
  app.py                 Streamlit app. Entry point.
  rubric.py              All content, weights, bands, benchmarks. Edit here to change questions.
  test_app.py            End-to-end test suite. Run before every push.
  assets/favicon.png     Tab icon (the gold diamond mark).
  requirements.txt       Minimal deps. Streamlit and requests.
  .streamlit/config.toml Theme and server config.
  README.md              This file.
```

No auth, no Stripe, no database, no missing imports. It runs as-is.

## Configuration (all optional, all silent no-ops when absent)

Set these in Streamlit Cloud secrets, environment variables, or a local `.env`
file (gitignored):

```
POSTHOG_PROJECT_TOKEN  = "..."   # funnel analytics
POSTHOG_HOST           = "https://us.i.posthog.com"
```

Funnel events fired (once per session each): `audit_started`,
`context_completed`, `dimension_completed` (per dimension, with a `skipped`
flag), `results_viewed`, `audit_resumed`. Review the funnel monthly; if any dimension bleeds more than
20 percent of takers, tighten its question count.

## Testing

Run the suite before every push:

```
python3 test_app.py
```

It drives the full fifty-question flow end to end (intro, context, all six
dimensions, results), checks scoring bounds on best and worst answer sets,
confirms there is no email step, and round-trips the save/resume codes.

## Run it locally

```
cd structural-audit
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

It will open on http://localhost:8501.

## Deploy to Streamlit Cloud

Two paths. Pick the one that fits how your current `structural-audit.streamlit.app` is wired.

### Path A . Replace the existing app via GitHub

If your existing Streamlit Cloud app is connected to a GitHub repository, the clean fix is to push this code to the same repo.

1. Clone the connected repo locally.
2. Replace its contents with the contents of this folder. Keep git history intact, just delete the old files and drop these in.
3. Commit and push to the default branch.
4. Streamlit Cloud will detect the push and redeploy within about sixty seconds.

If the existing app was connected to a private or stale repo, consider deleting the app and starting clean with Path B. The old code has missing imports and will not boot anyway.

### Path B . Start a new Streamlit Cloud app

1. Create a new GitHub repo. Call it `structural-audit` or similar.
2. Copy the contents of this folder to the repo root. Commit and push.
3. Go to share.streamlit.io and sign in.
4. Click **New app**.
5. Select the repo, the main branch, and `app.py` as the entry point.
6. Under **Advanced settings**, set the Python version to 3.11.
7. Click **Deploy**. First boot takes about a minute.
8. Once it is live, you can claim the subdomain. In the app settings, set the custom subdomain to `structural-audit` so it lives at `structural-audit.streamlit.app`. If the existing app still owns that subdomain, you will need to delete the old app first.

**Before turning on `AUDIT_REDIRECT_LEGACY`:** the redirect now preserves `location.search`. It did not before, and a saved audit lives entirely in `?code=`, so enabling it would have discarded every shared link.

## Link previews

They do not work, and hosting is not the reason. Streamlit is a JavaScript SPA: `curl https://audit.grahamkindermann.com` returns the shell and "You need to enable JavaScript to run this app." No scraper — LinkedIn, X, Slack, iMessage — ever sees the OG tags, on Community Cloud or on Render. `static/og-audit.png` is correct and is never fetched.

The fix is a small Cloudflare Worker in front of the domain that serves a static HTML shell with the meta tags to bot user-agents and proxies everything else. See `cloudflare-worker-og.js` in this repo.

## How scoring works

Every question carries a weight. Each answer is normalized to a 0 to 1 score.

For Likert questions, 1 to 5 maps to 0 to 1 linearly. Reverse-scored questions flip.

For yes or no questions, yes is 1.0, **Partly is 0.5** (`YESNO_PARTIAL_SCORE`), and no is 0.0. The middle option exists because these questions are not binary in practice: without it a business at the industry median is forced onto "No" across thirteen questions and scores in the Critical band.

For quantitative questions, the answer is compared to industry benchmarks stored in `rubric.py`. Values below the 25th percentile (for lower-is-better metrics) score 1.0. Values above the 75th percentile score 0.0. In between, the score interpolates linearly through the 50th percentile at 0.5.

Each dimension's score is the weighted average of its answered questions, scaled to 0 to 100. The overall score is the weight-blended average of all scored dimensions.

A dimension needs at least `MINIMUM_ANSWERED_FRACTION` (60 percent) of its question weight **scored** before it gets a score. Unscored covers more than an explicit N/A: a blank, an unparseable entry, a negative number, and any metric with no benchmark for the selected industry all count against it. Below the threshold the dimension is marked Insufficient Data and excluded from the overall — not scored as zero, which is why skipping a dimension nudges the overall up. The results page names any dimension it excluded.

**Risks** are answered items scoring below `RISK_THRESHOLD` (0.4). **Opportunities** are items between `RISK_THRESHOLD` and `OPPORTUNITY_CEILING` (0.75) — partly in place. Note that an opportunity's available gain is always *smaller* than a risk's at equal weight; opportunities are cheaper to close, not worth more.

Both lists are ordered by **lever**: the number of points the overall score would gain if that one answer moved to full marks. Lever accounts for the question's weight, its dimension's answered weight, and the dimension's own weight:

```
lever = (1 - score) * q_weight / dim_answered_weight * 100 * dim_weight / total_scored_dim_weight
```

Ordering by question weight alone (the pre-1.1.0 behaviour) ignored dimension weight, so the lowest-weighted dimension could supply the headline risk, the "biggest lever" callout and the first item of the 90-day plan. If you change the ranking, change the callout with it — `test_risk_ranking_uses_dimension_weight` checks that the item named as the biggest lever really is.

## Editing questions or copy

All content lives in `rubric.py`. Do not edit `app.py` to change text. The schema per question:

```python
{
  "id": "per_01",
  "text": "...",                   # shown to user
  "type": "likert" | "yesno" | "number" | "percent",
  "group": "Owner Dependency",      # section heading within the dimension
  "weight": 2.0,                    # higher = more load on the dimension score
  "allow_na": True,                 # show N/A as an option
  "reverse": False,                 # likert/yesno only: flip the polarity.
                                    # There are currently NONE, deliberately —
                                    # one reversed item among fifty is a
                                    # mis-answer trap, not a validity check.
                                    # test_no_reverse_scored_items enforces it.
  "lower_is_better": True,          # number/percent only: benchmark direction
  "risk_copy": "...",               # surfaced on the risk list
  "opportunity_copy": "...",        # surfaced on the opportunities list
  "recommendation": "...",          # the next-action line
}
```

Quantitative questions need a matching entry in the `BENCHMARKS` dict, keyed by `(industry, question_id)`, with `p25 / p50 / p75` values.

## Positioning

This tool is the B2B counterpart to the Structural Advantage Index at `index.grahamkindermann.com`. All tool links live on owned subdomains; never link a `*.netlify.app` or `*.streamlit.app` host from user-facing copy (`test_no_vendor_or_legacy_hosts` enforces this). The intended user journey is Index first, Audit second. Keep the cross-links current in both directions. The Index links here from its results screen. This app links back to the Index from its intro and its results screen.
