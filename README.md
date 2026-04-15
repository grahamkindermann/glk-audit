# The Structural Audit

A B2B operational diagnostic of the business itself, across six dimensions. Companion to the Structural Advantage Index. The Index reads the founder. This reads the company.

## What is in this folder

```
structural-audit/
  app.py                 Streamlit app. Entry point.
  rubric.py              All content, weights, bands, benchmarks. Edit here to change questions.
  requirements.txt       Minimal deps. Just streamlit.
  .streamlit/config.toml Theme and server config.
  README.md              This file.
```

No auth, no Stripe, no database, no missing imports. It runs as-is.

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

## How scoring works

Every question carries a weight. Each answer is normalized to a 0 to 1 score.

For Likert questions, 1 to 5 maps to 0 to 1 linearly. Reverse-scored questions flip.

For yes or no questions, yes is 1.0 and no is 0.0 (unless reversed).

For quantitative questions, the answer is compared to industry benchmarks stored in `rubric.py`. Values below the 25th percentile (for lower-is-better metrics) score 1.0. Values above the 75th percentile score 0.0. In between, the score interpolates linearly through the 50th percentile at 0.5.

Each dimension's score is the weighted average of its answered questions, scaled to 0 to 100. The overall score is the weight-blended average of all scored dimensions.

If more than 40 percent of a dimension's question weight is answered as N/A, the dimension is marked Insufficient Data and excluded from the overall score.

Risks are the answered questions with the highest weighted gap from perfect. Opportunities are the partially in-place items where a focused quarter would move the score most.

## Editing questions or copy

All content lives in `rubric.py`. Do not edit `app.py` to change text. The schema per question:

```python
{
  "id": "per_01",
  "text": "...",                   # shown to user
  "type": "likert" | "yesno" | "number" | "percent",
  "weight": 2.0,                    # higher = more load on the dimension score
  "reverse": False,                 # flip the polarity
  "allow_na": True,                 # show N/A as an option
  "risk_copy": "...",               # surfaced on the risk list
  "opportunity_copy": "...",        # surfaced on the opportunities list
  "recommendation": "...",          # the next-action line
}
```

Quantitative questions need a matching entry in the `BENCHMARKS` dict, keyed by `(industry, question_id)`, with `p25 / p50 / p75` values.

## Positioning

This tool is the B2B counterpart to the B2C Structural Advantage Index at `structuraladvantagediagnostic.netlify.app`. The intended user journey is Index first, Audit second. Keep the cross-links current in both directions. The Index links here from its results screen. This app links back to the Index from its intro and its results screen.

If you ever want to sell a paid deep audit, do not bolt it onto this free tool. Run the paid engagement on email, starting with a read-out call. Keep this tool free and comprehensive as the trust-builder.
