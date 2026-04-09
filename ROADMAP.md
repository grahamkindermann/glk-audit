# Structural Advantage Audit Platform — Build Roadmap

## Product Vision

Transform the free lead-magnet quiz into a $199/mo SaaS diagnostic platform that delivers consulting-grade analysis at software prices. The moat is the rubric (your domain expertise encoded as data) combined with AI-generated recommendations that feel like a $10K engagement.

## Architecture (designed for Streamlit now, portable to React later)

```
glk-audit/
├── app.py                    # Streamlit UI (replaceable)
├── core/
│   ├── rubric.py             # Questions, dimensions, weights, benchmarks
│   ├── scoring.py            # Pure-function scoring engine
│   ├── report.py             # PDF generation (ReportLab)
│   └── recommendations.py   # Claude API → written analysis
├── db/
│   ├── client.py             # Supabase client init
│   ├── models.py             # Audit, User, Company, Respondent schemas
│   └── queries.py            # CRUD operations
├── payments/
│   └── stripe_gate.py        # Stripe Checkout + webhook handler
├── requirements.txt
├── .env                      # API keys (never committed)
├── .gitignore
└── .streamlit/
    └── config.toml
```

Key principle: `core/` has ZERO dependency on Streamlit, Supabase, or Stripe. It's pure Python. When you migrate to React + FastAPI, you keep `core/` and `db/` untouched and replace `app.py` with API routes.

---

## Phase 1 — v1.1 Cleanup (1-2 days)

Fix the bugs and gaps identified during v1 testing. This is prerequisite to everything else.

### Claude Code Prompt

```
Read the file ROADMAP.md for context on the overall product plan.

Fix these 5 issues in glk-audit:

1. Advisory mode CTA missing from PDF. In report.py around line 399, `cta = CTA.get("lead_magnet", {})` is hardcoded. Change it to use the `use_mode` parameter so advisory PDFs get their own CTA. Verify the CTA renders in both sample PDFs.

2. Advisory mode should show written recommendations in the Streamlit results page AND the PDF. The rubric.py comments reference `recommendation` and `opportunity_copy` fields per question — check if they're populated. If not, add placeholder text for every question that has a risk_copy. In app.py, the `if MODE == "advisory"` branches at lines 212 and 221 should render these. In report.py, the advisory PDF path at line 512 should include a "Recommendations" section.

3. Advisory mode should include a 30/60/90 day action plan section. Add a function in scoring.py that takes the top risks and generates a structured 30/60/90 block (30-day = quick wins from top 3 risks, 60-day = systemic fixes, 90-day = strategic initiatives). Render it in both the Streamlit results page and the PDF for advisory mode only.

4. Incomplete-submission guardrail. If 3 or more dimensions score as "Insufficient Data", the results page should show a warning state instead of the full report. Display which dimensions need more answers and a button to go back and complete them. Don't generate a PDF in this state.

5. Add tests for all of the above in test_scoring.py.

After all changes, run `python3 test_scoring.py` and `python3 report.py` to verify. Show me the test output and confirm both sample PDFs regenerated.
```

---

## Phase 2 — Quantitative Inputs + Enriched Rubric (3-5 days)

This is what separates a "quiz" from an "audit." Real numbers make the output credible.

### What to add

Add a new section to the firmographics step AND weave quantitative questions into each dimension:

**Firmographics (expanded):**
- Annual revenue (dropdown bands: <$1M, $1-5M, $5-20M, $20-50M, $50-100M, $100M+)
- EBITDA margin % (number input)
- Full-time headcount (number input)
- Industry vertical (dropdown: SaaS, Professional Services, Manufacturing, Retail/E-comm, Healthcare, Financial Services, Other)
- Years in operation (number input)

**Per-dimension quantitative questions (examples):**
- Personnel: Annual voluntary turnover % | Avg days to fill a role | % of roles with documented job descriptions
- Accounting: Days to close monthly books | AR aging (% over 60 days) | Do you have a 13-week cash flow forecast? (Y/N)
- Software: Number of SaaS tools in use | % of tools with SSO | Annual software spend as % of revenue
- AI: Number of workflows with AI augmentation | Do you have an AI usage policy? (Y/N)
- Sales: Customer acquisition cost ($) | Customer lifetime value ($) | Monthly churn rate %
- Operations: On-time delivery rate % | Customer NPS score | Mean time to resolve customer issues (hours)

**Industry benchmarks:** For each quantitative input, store a benchmark range per industry vertical. The scoring engine compares the company's actual number against the benchmark and generates a percentile or gap score.

### Claude Code Prompt

```
Read ROADMAP.md for full context. We're on Phase 2 — adding quantitative inputs and industry benchmarks.

1. RESTRUCTURE: Move rubric.py, scoring.py, report.py into a new `core/` directory. Update all imports in app.py. Keep the flat files as symlinks or delete them and update .gitignore. Run tests to verify nothing broke.

2. EXPAND FIRMOGRAPHICS in core/rubric.py: Add these fields to the FIRMOGRAPHICS list:
   - annual_revenue: select with bands ["<$1M", "$1-5M", "$5-20M", "$20-50M", "$50-100M", "$100M+"]
   - ebitda_margin: int (percentage, 0-100)
   - headcount: int
   - industry: select ["SaaS", "Professional Services", "Manufacturing", "Retail / E-commerce", "Healthcare", "Financial Services", "Other"]
   - years_in_operation: int

3. ADD QUANTITATIVE QUESTIONS: Add 2-3 quantitative questions per dimension. These should have type "number" or "percent" (new types). Examples:
   - Personnel: annual_voluntary_turnover_pct, avg_days_to_fill_role
   - Accounting: days_to_close_books, ar_over_60_days_pct
   - Software: num_saas_tools, annual_software_spend_pct_revenue
   - AI: num_ai_augmented_workflows
   - Sales: customer_acquisition_cost, monthly_churn_rate_pct
   - Operations: on_time_delivery_pct, mean_time_to_resolve_hours

4. ADD BENCHMARKS: Create a BENCHMARKS dict in rubric.py keyed by (industry, question_id). Each entry has {p25, p50, p75} values. For MVP, use reasonable estimates — we'll refine with real data later. Example:
   ```python
   BENCHMARKS = {
       ("SaaS", "monthly_churn_rate_pct"): {"p25": 1.5, "p50": 3.0, "p75": 5.0},
       ("Professional Services", "days_to_close_books"): {"p25": 5, "p50": 10, "p75": 20},
   }
   ```

5. UPDATE SCORING ENGINE: In core/scoring.py, handle the new "number" and "percent" question types. For quantitative questions with benchmarks, compute a percentile-based score (0-100) comparing the company's value to the industry benchmark. Blend quantitative scores with Likert scores for the dimension total using a 40/60 weight (40% quantitative, 60% qualitative) — but only if quantitative questions were answered.

6. UPDATE UI: In app.py, render number inputs (st.number_input) for the new question types. Show the benchmark range as a caption below each quantitative input: "Industry median: 10 days | Top quartile: 5 days".

7. UPDATE PDF: In core/report.py, add a "How You Compare" section that shows a table of quantitative inputs vs. industry benchmarks with color coding (green = above p75, yellow = p25-p75, red = below p25).

8. UPDATE TESTS: Add test cases for quantitative scoring, benchmark lookups, and blended dimension scores.

Run all tests and regenerate sample PDFs when done.
```

---

## Phase 3 — AI-Generated Recommendations (3-5 days)

This is the killer feature. Instead of canned risk_copy strings, use Claude to write a 2-3 page consulting memo tailored to the company's specific answers.

### How it works

1. After scoring, collect: firmographics, all answers, dimension scores, top risks, top opportunities, quantitative inputs vs benchmarks.
2. Send this context to Claude API with a carefully crafted system prompt that positions it as a PE-style operating advisor.
3. Claude generates: (a) executive summary paragraph, (b) per-dimension analysis with specific recommendations, (c) prioritized 30/60/90 action plan, (d) estimated ROI for top 3 recommendations.
4. Cache the result in session state (and later, in the database) so regenerating the PDF doesn't re-call the API.
5. Display in Streamlit and embed in the PDF.

### Claude Code Prompt

```
Read ROADMAP.md for full context. We're on Phase 3 — AI-generated recommendations using the Claude API (Anthropic SDK).

1. ADD DEPENDENCY: Add `anthropic` to requirements.txt.

2. CREATE core/recommendations.py with these functions:

   a. `generate_recommendations(result, firmographics, answers)` — the main entry point.
      - Constructs a prompt with all audit data
      - Calls Claude API (claude-sonnet-4-20250514, temperature=0.3)
      - Returns a structured dict with: executive_summary, dimension_analyses (list), action_plan_30_60_90, top_3_roi_estimates
      - Uses structured output (JSON mode) so we can reliably parse the response

   b. The SYSTEM PROMPT should be approximately:
      "You are a senior operating advisor at a private equity firm. You have just reviewed a comprehensive business audit for a {industry} company with {headcount} employees and {revenue} in annual revenue. Your job is to write a specific, actionable diagnostic memo — not generic advice. Reference the company's actual scores and answers. Be direct about what's broken and what the fix costs. Every recommendation should have a concrete next step, not a vague suggestion."

   c. The USER PROMPT should include:
      - Company profile (firmographics)
      - Overall score and band
      - Per-dimension scores with band labels
      - Top risks with their question text and the company's answer
      - Top opportunities
      - Quantitative inputs vs. benchmarks (where available)
      - Instruction to output JSON matching a specific schema

   d. Handle API errors gracefully — if the call fails, fall back to the existing canned risk_copy/opportunity_copy strings. Never block the results page because of an API failure.

3. CREATE .env.example with:
   ```
   ANTHROPIC_API_KEY=your-key-here
   ```
   Add .env to .gitignore (it should already be there; verify).

4. UPDATE app.py:
   - After computing `result = run_audit(answers)`, call `generate_recommendations(result, firm, answers)`.
   - Store the AI output in `st.session_state.ai_recommendations` so it persists across reruns.
   - On the results page, render the AI executive summary, dimension analyses, and action plan in styled markdown sections.
   - Add a "Regenerate analysis" button that clears the cached recommendations and reruns.
   - Gate this behind an environment variable: if ANTHROPIC_API_KEY is not set, skip the AI call and use canned copy (this lets the free tier still work).

5. UPDATE core/report.py:
   - Accept an optional `ai_recommendations` parameter in build_pdf().
   - If present, replace the canned risk_copy sections with the AI-generated dimension analyses.
   - Add the 30/60/90 action plan as a new section.
   - Add ROI estimates table.
   - The AI content should be clearly formatted — use the same visual language as the rest of the PDF (navy headers, serif body, proper spacing).

6. For local testing, add ANTHROPIC_API_KEY to .env (I'll provide my key separately — do NOT commit it).

7. Add basic tests: mock the API call, verify the prompt construction, verify graceful fallback on API failure.

Run tests and regenerate samples when done. For the sample PDFs, use canned copy (no API call) since we won't have a key in CI.
```

---

## Phase 4 — Auth + Persistence with Supabase (3-5 days)

This turns the tool from stateless to stateful. Users can log in, save audits, and come back later.

### Claude Code Prompt

```
Read ROADMAP.md for full context. We're on Phase 4 — adding authentication and data persistence with Supabase.

1. ADD DEPENDENCIES: Add `supabase` to requirements.txt.

2. CREATE db/client.py:
   - Initialize the Supabase client from environment variables (SUPABASE_URL, SUPABASE_KEY).
   - Export a `get_client()` function that returns a singleton.
   - If env vars are not set, return None (graceful degradation — app still works without a database, just no persistence).

3. CREATE db/models.py with these table schemas (we'll create them in Supabase dashboard):

   - `users` — id (uuid, from Supabase auth), email, name, created_at
   - `companies` — id (uuid), user_id (FK), name, industry, headcount, revenue_band, created_at
   - `audits` — id (uuid), company_id (FK), user_id (FK), mode (lead_magnet/advisory), answers (jsonb), firmographics (jsonb), result (jsonb), ai_recommendations (jsonb), overall_score (float), overall_band (text), created_at
   - `respondents` — id (uuid), audit_id (FK), email, name, role, answers (jsonb), completed_at (nullable)

4. CREATE db/queries.py with CRUD functions:
   - save_audit(user_id, company_id, audit_data) → audit_id
   - get_audits_for_company(company_id) → list of audits (for historical tracking)
   - get_audit(audit_id) → single audit with all data
   - save_respondent_answers(audit_id, respondent_data)
   - get_respondents_for_audit(audit_id) → list

5. UPDATE app.py:
   - Add a login/signup screen as Step 0 using Supabase Auth (st.session_state for auth token).
   - Use st_supabase_connector or manual OAuth flow with st.query_params.
   - After auth, show a "company selector" — user can pick an existing company or create one.
   - After completing an audit, auto-save to Supabase.
   - Add a "My Audits" sidebar section showing past audits with dates and scores.

6. Create SQL migration file (db/migrations/001_initial.sql) with the CREATE TABLE statements so I can run them in Supabase SQL editor.

7. Add .env.example entries for SUPABASE_URL and SUPABASE_KEY.

8. Graceful degradation: if Supabase is not configured, the app should work exactly as it does today — no login, no persistence, just the quiz. This lets the free lead-magnet version keep running on the public URL.
```

---

## Phase 5 — Historical Tracking + Dashboard (2-3 days) ✅ SHIPPED

### Claude Code Prompt

```
Read ROADMAP.md for full context. We're on Phase 5 — historical tracking and trend dashboards.

1. ADD a "Dashboard" view to app.py (new step after login, before starting a new audit):
   - Show a company health scorecard: latest overall score, per-dimension scores, band labels.
   - Trend chart (line chart using st.line_chart or Altair): overall score over time, one line per dimension.
   - "Score delta" badges: "Operations: +12 since last audit" with green/red arrows.
   - "Last audited" timestamp and a "Run new audit" button.

2. ENHANCE the results page:
   - If this isn't the first audit, show a "vs. last audit" comparison column in the dimension table.
   - Highlight dimensions that improved vs. declined.
   - In the PDF, add a "Progress Since Last Audit" section with delta scores.

3. ADD a "Recommendation tracker":
   - After each audit, the AI recommendations are saved.
   - On the dashboard, show a checklist of past recommendations with status: Not started / In progress / Done.
   - User can update status manually (simple checkbox + dropdown).
   - Next audit, the AI prompt includes which recommendations were implemented — so it can comment on progress.

4. Use Supabase queries from db/queries.py. Add any new query functions needed.
```

---

## Phase 6 — Multi-Respondent Surveys (3-5 days)

This is the PE-firm feature. CEO and CFO take the same audit independently; the platform shows where they agree and where they diverge.

### Claude Code Prompt

```
Read ROADMAP.md for full context. We're on Phase 6 — multi-respondent team surveys.

1. ADD an "Invite Team" flow:
   - After a company admin creates a new audit, they can invite team members by email.
   - Each invitee gets a unique link (audit_id + respondent token in URL params).
   - Invitees see the same quiz but their answers are stored separately in the `respondents` table.
   - Invitees do NOT need to create an account — the link is their auth (read-only, scoped to this audit).

2. ADD a "Team Consensus" view (only visible to the admin who created the audit):
   - For each question, show the distribution of answers across respondents.
   - Highlight "divergence" — questions where respondents disagree significantly (e.g., one person says Strongly Agree, another says Strongly Disagree). Flag these as blind spots.
   - Show per-respondent dimension scores side by side (table: rows = dimensions, columns = respondents).
   - Overall consensus score: % of questions where all respondents are within 1 point of each other.

3. ENHANCE AI recommendations:
   - When multi-respondent data exists, include the divergence analysis in the AI prompt.
   - The AI should call out specific blind spots: "Your CEO rated personnel processes as Strong (4.2) while your Operations Manager rated them Critical (1.8). This 2.4-point gap on question per_03 suggests leadership may not have visibility into day-to-day hiring friction."

4. ENHANCE PDF:
   - Add a "Team Survey Results" section with the consensus heatmap.
   - Add a "Blind Spots" callout box for high-divergence items.

5. Add tests for divergence calculation, consensus scoring, and invite-link generation.
```

---

## Phase 7 — Stripe Paywall (2-3 days)

### Claude Code Prompt

```
Read ROADMAP.md for full context. We're on Phase 7 — Stripe integration for paid tiers.

1. ADD DEPENDENCY: `stripe` to requirements.txt.

2. CREATE payments/stripe_gate.py:
   - Initialize Stripe from STRIPE_SECRET_KEY env var.
   - create_checkout_session(user_id, price_id) → returns Stripe Checkout URL.
   - verify_subscription(user_id) → checks if user has active subscription.
   - handle_webhook(payload, sig) → processes subscription events.

3. DEFINE TIERS in core/rubric.py:
   ```python
   TIERS = {
       "free": {
           "name": "Lead Magnet",
           "price": 0,
           "features": ["scores", "risk_ranking", "basic_pdf"],
       },
       "pro": {
           "name": "Professional",
           "price_monthly": 99,
           "stripe_price_id": "price_xxx",
           "features": ["scores", "risk_ranking", "quantitative", "benchmarks", "ai_recommendations", "pdf_full", "historical_tracking"],
       },
       "team": {
           "name": "Team",
           "price_monthly": 299,
           "stripe_price_id": "price_yyy",
           "features": ["everything_in_pro", "multi_respondent", "team_consensus", "blind_spots", "white_label_pdf"],
       },
   }
   ```

4. UPDATE app.py:
   - After auth, check subscription tier.
   - Free users see scores + basic risks + CTA to upgrade.
   - Pro users see full AI analysis + benchmarks + tracking.
   - Team users see multi-respondent features.
   - Gate features with a simple `has_feature(user, "ai_recommendations")` check.
   - Show upgrade prompts at the exact moment a free user would benefit (e.g., "Unlock AI-powered recommendations for this audit → $99/mo").

5. Add .env.example entries for STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET.

6. Graceful degradation: if Stripe is not configured, all features are unlocked (for local dev and the free lead-magnet instance).
```

---

## Build Order & Timeline

| Phase | What | Calendar time | Depends on |
|-------|------|--------------|------------|
| 1 | v1.1 cleanup | Days 1-2 | Nothing (start here) |
| 2 | Quantitative inputs + benchmarks | Days 3-7 | Phase 1 |
| 3 | AI recommendations | Days 8-12 | Phase 2 |
| 4 | Auth + persistence | Days 13-17 | Phase 2 |
| 5 | Historical tracking | Days 18-20 | Phase 4 |
| 6 | Multi-respondent | Days 21-25 | Phase 4 |
| 7 | Stripe paywall | Days 26-28 | Phase 4 |

Phases 3 and 4 can run in parallel if you want to move faster. Phase 3 (AI) is the most impactful single feature for conversion. Phase 4 (auth) is the most impactful for retention.

## Revenue Model

- Free tier: Current lead-magnet quiz (unchanged, lives at structural-audit.streamlit.app)
- Pro ($99/mo): AI recommendations + quantitative benchmarks + historical tracking
- Team ($299/mo): Multi-respondent + consensus analysis + blind spots

Target: 50 Pro subscribers = $4,950/mo ARR within 6 months of launch.
Each subscriber is also a warm lead for $10K+ advisory engagements.

## What Makes This "Top Finance Tool" Grade

1. **Quantitative rigor** — real numbers, not just vibes. Industry benchmarks give the scores external validity.
2. **AI that sounds like a $500/hr consultant** — not generic advice, but specific recommendations that reference the company's actual data.
3. **Longitudinal tracking** — run it quarterly, see the trendline, prove ROI on changes you made.
4. **Multi-perspective** — team surveys expose blind spots that no single-respondent tool can find.
5. **Actionable output** — 30/60/90 plans, ROI estimates, recommendation tracking. Not just a diagnosis but a treatment plan.
