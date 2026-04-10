"""
Structural Advantage — Business Audit Rubric
=============================================

All scoring content lives here. Edit freely; do not edit app.py to change
content. scoring.py consumes this file as plain data.

To change the product's behavior, edit (in order of how often you'll touch it):
    1. MODE                     — switch lead-magnet vs. advisory build
    2. Question text / weights  — inside DIMENSIONS
    3. Copy (risk / opp / rec)  — inside each question
    4. BANDS / thresholds       — scoring tier boundaries
    5. CTA / BRAND              — report framing
"""

# ---------------------------------------------------------------------------
# Version
# Bump on any change to questions, weights, bands, or reverse flags so that
# generated reports can be traced to the rubric that produced them.
# ---------------------------------------------------------------------------
RUBRIC_VERSION = "0.1.0"

# ---------------------------------------------------------------------------
# MODE
# "lead_magnet" -> scores + bands + top 3 risks only.
# "advisory"    -> adds opportunities, written recommendations, 30/60/90 block.
#
# Set via environment variable AUDIT_MODE to avoid editing this file.
# Defaults to "lead_magnet" if not set.
# ---------------------------------------------------------------------------
import os
MODE = os.environ.get("AUDIT_MODE", "lead_magnet")

# ---------------------------------------------------------------------------
# TIERS — feature-gate definitions for paid plans
# "free" features are always available. Each higher tier inherits all
# features from the tier below.
#
# stripe_price_id values are placeholders — replace with real Stripe price
# IDs once you create products in the Stripe Dashboard.
# ---------------------------------------------------------------------------
_FULL_REPORT_FEATURES = {
    "scores",
    "risk_ranking",
    "basic_pdf",
    "quantitative_benchmarks",
    "ai_recommendations",
    "pdf_full",
    "historical_tracking",
    "recommendation_tracker",
}

TIERS = {
    "free": {
        "name": "Free Diagnostic",
        "price_monthly": 0,
        "price_onetime": 0,
        "billing_mode": "free",
        "stripe_price_id": None,
        "features": {
            "scores",
            "risk_ranking",
            "basic_pdf",
        },
    },
    # "report" is the new primary paid tier: a one-time $149 purchase that
    # grants lifetime access to the full report features. This replaces the
    # former $79/mo recurring "pro" subscription.
    "report": {
        "name": "Full Report",
        "price_monthly": 0,
        "price_onetime": 149,
        "billing_mode": "payment",   # Stripe Checkout mode
        "stripe_price_id": os.environ.get("STRIPE_PRICE_REPORT", "price_report_placeholder"),
        "features": _FULL_REPORT_FEATURES,
    },
    # "pro" is kept as an alias for backward compatibility with any existing
    # subscription rows in the DB. Same features as "report". Do not surface
    # it in new upgrade flows.
    "pro": {
        "name": "Professional (legacy)",
        "price_monthly": 79,
        "price_onetime": 0,
        "billing_mode": "subscription",
        "stripe_price_id": os.environ.get("STRIPE_PRICE_PRO", "price_pro_placeholder"),
        "features": _FULL_REPORT_FEATURES,
    },
    "team": {
        "name": "Team",
        "price_monthly": 299,
        "price_onetime": 0,
        "billing_mode": "subscription",
        "stripe_price_id": os.environ.get("STRIPE_PRICE_TEAM", "price_team_placeholder"),
        "features": _FULL_REPORT_FEATURES | {
            "multi_respondent",
            "team_consensus",
            "blind_spots",
            "white_label_pdf",
        },
    },
}


def has_feature(tier, feature):
    """Check if a tier includes a given feature.

    Args:
        tier: "free", "pro", or "team"
        feature: feature string (e.g., "ai_recommendations")

    Returns True if the tier includes the feature.
    """
    tier_def = TIERS.get(tier, TIERS["free"])
    return feature in tier_def["features"]

# ---------------------------------------------------------------------------
# Brand strings
# ---------------------------------------------------------------------------
BRAND = {
    "wordmark": "STRUCTURAL ADVANTAGE",
    "cover_subtitle": {
        "lead_magnet": "Business Structural Audit",
        "advisory":    "Confidential Advisory Audit",
    },
    "prepared_by": "Prepared by Graham Kindermann · GLK Holdings LLC · kindermanngraham@gmail.com",
}

# ---------------------------------------------------------------------------
# CTA blocks per mode
# ---------------------------------------------------------------------------
CTA = {
    "lead_magnet": {
        "headline": "Book a 30-minute structural review with Graham.",
        "primary_label": "Schedule review",
        "primary_url":   "https://calendly.com/gkholdingsllcva/structural-review",
        "secondary_label": "Subscribe to Structural Advantage",
        "secondary_url":   "https://structuraladvantage.substack.com/",
    },
    "advisory": {
        "headline": "Next step: 30/60/90 execution plan review.",
        "primary_label": "Schedule working session",
        "primary_url":   "https://calendly.com/gkholdingsllcva/structural-review",
        "secondary_label": None,
        "secondary_url":   None,
    },
}

# ---------------------------------------------------------------------------
# Score bands
# Half-open intervals [lo, hi). Final band closes at 101 so that a score of
# exactly 100 falls into "Durable". Downstream code keys off the band id,
# never the label string.
# ---------------------------------------------------------------------------
BANDS = [
    ("critical",    0,  41, "Critical"),
    ("fragile",    41,  61, "Fragile"),
    ("functional", 61,  76, "Functional"),
    ("strong",     76,  91, "Strong"),
    ("durable",    91, 101, "Durable"),
]

# If more than this fraction of a dimension's weight is answered N/A, the
# dimension is marked INSUFFICIENT_DATA_LABEL and excluded from the overall
# weighted average (remaining dimension weights are re-normalized).
INSUFFICIENT_DATA_THRESHOLD = 0.40
INSUFFICIENT_DATA_LABEL = "Insufficient Data"

# ---------------------------------------------------------------------------
# Band narratives (two-sentence executive-summary interpretation keyed off
# band id). Blunt operator voice. Used by report.py only; the Streamlit UI
# shows the band label without narrative.
# ---------------------------------------------------------------------------
BAND_NARRATIVE = {
    "critical": (
        "The business is structurally fragile across multiple dimensions. "
        "Without intervention, the next shock will expose gaps that could threaten continuity."
    ),
    "fragile": (
        "The business is functioning but running hot. "
        "Most of the load is on the owner, and a handful of weak points are carrying disproportionate risk."
    ),
    "functional": (
        "The business has real structural muscle, but the remaining gaps are load-bearing. "
        "Closing two or three of them would move the business into genuinely durable territory."
    ),
    "strong": (
        "The business is well-run across most dimensions. "
        "The remaining gaps are refinements, not emergencies, and the leverage is in compounding what already works."
    ),
    "durable": (
        "The business is structurally sound and operator-independent. "
        "Focus shifts from fixing weaknesses to protecting the advantage and scaling on strength."
    ),
}

# ---------------------------------------------------------------------------
# Dimensions
#
# Dimension weights are raw; scoring.py normalizes them to sum to 6.0 at
# runtime. AI Readiness is deliberately thin (4 questions, weight 0.50).
#
# Question schema:
#   {
#       "id":               "per_01",
#       "text":             "...",
#       "type":             "likert" | "yesno",
#       "weight":           float,
#       "reverse":          bool,   # see scoring.py header for rules
#       "allow_na":         bool,
#       "risk_copy":        "...",  # shown when question surfaces as a risk
#       "opportunity_copy": "...",  # advisory mode only
#       "recommendation":   "...",  # advisory mode only
#   }
#
# "summary" fields per dimension are intentionally left empty for now; they
# will be filled in after the scoring engine is locked.
# ---------------------------------------------------------------------------
DIMENSIONS = [
    {
        "id": "personnel",
        "name": "Personnel & Org",
        "weight": 1.15,
        "summary": "",
        "questions": [
            {
                "id": "per_01",
                "text": "If I were unreachable for 30 days, the business would continue operating at near-normal capacity without me.",
                "type": "likert",
                "weight": 2.0,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Owner dependency at this level caps enterprise value and makes the business nearly unsellable.",
                "opportunity_copy": "Decoupling the business from the owner is the single highest-leverage move available and unlocks both resilience and exit optionality.",
                "recommendation": "Schedule an actual 10-day absence in the next 90 days and treat every escalation as a gap to close.",
            },
            {
                "id": "per_02",
                "text": "More than half of my leadership team would be considered A-players by a top competitor in our industry.",
                "type": "likert",
                "weight": 1.8,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "B-players hire C-players; talent drift compounds quietly until it becomes a full rebuild.",
                "opportunity_copy": "Upgrading one leadership seat per year is the most durable compounding move an operator can make.",
                "recommendation": "Rank your leadership team honestly on a 1–5 scale; anyone at 3 or below gets a 90-day bar or an exit plan.",
            },
            {
                "id": "per_03",
                "text": "Every recurring decision in the business has a single named owner who does not need to check with me.",
                "type": "likert",
                "weight": 1.5,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Decisions routing through the owner create a bottleneck that slows the entire business to the speed of one person.",
                "opportunity_copy": "Assigning one name to every recurring decision is cheap, fast, and immediately compounds through the org.",
                "recommendation": "List ten decisions you've made in the last two weeks that didn't need your input and assign each a permanent owner this week.",
            },
            {
                "id": "per_04",
                "text": "When someone on the team makes a commitment with a date, it is met or renegotiated before the date — not missed silently.",
                "type": "likert",
                "weight": 1.5,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "When deadlines slip silently, the owner becomes the only quality-control mechanism in the business.",
                "opportunity_copy": "This is the single cheapest accountability upgrade available — it costs nothing but attention.",
                "recommendation": "Model it yourself for 30 days by renegotiating, out loud, every date you're about to miss.",
            },
            {
                "id": "per_05",
                "text": "In the last 12 months, I have removed or reassigned at least one underperformer without dragging it out.",
                "type": "yesno",
                "weight": 1.2,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Tolerating underperformance is a tax every A-player on the team pays daily.",
                "opportunity_copy": "One honest underperformance decision resets the standards of the entire team.",
                "recommendation": "Ask yourself: if this person quit tomorrow, would you be relieved? If yes, act on it.",
            },
            {
                "id": "per_06",
                "text": "Every key seat in the business has a documented backup or succession plan.",
                "type": "yesno",
                "weight": 1.0,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "The absence of a succession plan is a silent concentration risk sitting under your entire org chart.",
                "opportunity_copy": "A one-page key-seat map is a cheap insurance policy against the single most predictable business failure mode.",
                "recommendation": "Draft a one-page key-seat map this week listing every critical role and a named backup; the gaps become your Q1 hiring priorities.",
            },
            {
                "id": "per_07",
                "text": "Compensation for our critical roles is at or above the 50th percentile for our market.",
                "type": "likert",
                "weight": 1.0,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Underpaying key roles is the most expensive cost-saving move in a business.",
                "opportunity_copy": "Paying at or above market for critical roles turns retention into a moat.",
                "recommendation": "Benchmark your top three roles this quarter against published ranges and close any gap for anyone you'd fight to keep.",
            },
            {
                "id": "per_q_turnover_pct",
                "text": "Annual voluntary turnover (%)",
                "type": "percent",
                "weight": 1.5,
                "lower_is_better": True,
                "allow_na": True,
                "risk_copy": "High voluntary turnover is a compounding tax on institutional knowledge and hiring costs.",
                "opportunity_copy": "Even a few points of turnover reduction pays for itself in avoided recruiting and ramp costs.",
                "recommendation": "Interview your last three departures for the real reason they left, then fix the pattern.",
            },
            {
                "id": "per_q_days_to_fill",
                "text": "Average days to fill a role",
                "type": "number",
                "weight": 1.0,
                "lower_is_better": True,
                "allow_na": True,
                "risk_copy": "Slow hiring means every open seat is draining the team that remains.",
                "opportunity_copy": "Cutting time-to-fill by even a week compounds across every hire.",
                "recommendation": "Pre-build job descriptions and sourcing channels for your top three roles before you need them.",
            },
        ],
    },
    {
        "id": "finance",
        "name": "Accounting & Finance",
        "weight": 1.25,
        "summary": "",
        "questions": [
            {
                "id": "fin_01",
                "text": "I can state, within 10% accuracy, how many weeks of cash the business has available right now.",
                "type": "likert",
                "weight": 2.0,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "An owner who cannot state weeks of cash on command is flying blind on the single most important number in the business.",
                "opportunity_copy": "A simple weekly cash dashboard is the highest ROI finance hygiene move available.",
                "recommendation": "Build a one-page weekly cash position report and review it every Monday morning for the next 90 days.",
            },
            {
                "id": "fin_02",
                "text": "I know the gross margin of every meaningful product line or service offering we sell.",
                "type": "likert",
                "weight": 1.8,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Without margin visibility by line, you may be scaling your least profitable offering and subsidizing it with your best.",
                "opportunity_copy": "One clean margin-by-line view reveals which offerings to expand, reprice, or kill.",
                "recommendation": "Identify your lowest-margin line and either reprice it, cut its delivery cost, or sunset it within 90 days.",
            },
            {
                "id": "fin_03",
                "text": "I can explain on one page what it costs to acquire a customer and what that customer is worth over their lifetime.",
                "type": "likert",
                "weight": 1.5,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Without CAC and LTV, marketing spend is a guess dressed up as a budget.",
                "opportunity_copy": "A one-page CAC/LTV view turns marketing from a cost center into a controlled investment.",
                "recommendation": "Pick your top two channels and calculate fully-loaded CAC and 24-month LTV this month; put it on one page.",
            },
            {
                "id": "fin_04",
                "text": "Books close within 10 business days of month-end, every month.",
                "type": "yesno",
                "weight": 1.5,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "A slow close means you're running the business on stale numbers, and decisions made on month-old data cost money.",
                "opportunity_copy": "A 10-day close forces cleaner data upstream and faster decisions downstream.",
                "recommendation": "Set a hard 10-day close target and make it a standing KPI for your bookkeeper or controller.",
            },
            {
                "id": "fin_05",
                "text": "A budget vs. actuals review happens on a fixed cadence with a named owner — not just when something looks off.",
                "type": "likert",
                "weight": 1.2,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Without a standing budget review, variances get noticed too late to do anything about them.",
                "opportunity_copy": "A monthly 30-minute budget review is the cheapest early-warning system in finance.",
                "recommendation": "Schedule a monthly budget review on a fixed day with a named owner; keep it to 30 minutes and variance-focused.",
            },
            {
                "id": "fin_06",
                "text": "All federal, state, and local tax filings are current, with no open surprises from any authority.",
                "type": "yesno",
                "weight": 1.2,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Tax surprises scale with the business; unresolved issues at $5M become existential at $15M.",
                "opportunity_copy": "Clean tax posture is table stakes for any future financing, sale, or audit.",
                "recommendation": "Commission a tax posture review from a CPA this quarter and close every open item on a timeline.",
            },
            {
                "id": "fin_07",
                "text": "DSO is tracked monthly and I know whether it is trending up, flat, or down.",
                "type": "likert",
                "weight": 1.0,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Rising DSO is a silent working-capital drain that compounds into a cash crunch.",
                "opportunity_copy": "Tightening DSO by a few days frees meaningful cash without touching sales or costs.",
                "recommendation": "Audit your top five open receivables this week; if any are overdue, collect them personally.",
            },
            {
                "id": "fin_08",
                "text": "My own compensation is set at market replacement cost for my role — not whatever is left over at the end of the month.",
                "type": "yesno",
                "weight": 0.8,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Under-compensating the owner creates a P&L that lies about the health of the business.",
                "opportunity_copy": "This single change reveals whether the business is actually profitable or just subsidized by the owner.",
                "recommendation": "Benchmark your role to a market salary and book that number as owner compensation, even if you don't take it as cash.",
            },
            {
                "id": "fin_q_days_to_close",
                "text": "Days to close monthly books",
                "type": "number",
                "weight": 1.2,
                "lower_is_better": True,
                "allow_na": True,
                "risk_copy": "A slow close means decisions are made on stale numbers.",
                "opportunity_copy": "Every day you cut from the close gives you a day of faster decision-making.",
                "recommendation": "Set a hard close-day target and work backward to identify the bottleneck steps.",
            },
            {
                "id": "fin_q_ar_over_60_pct",
                "text": "Accounts receivable over 60 days (%)",
                "type": "percent",
                "weight": 1.0,
                "lower_is_better": True,
                "allow_na": True,
                "risk_copy": "Aging receivables are a silent working capital drain that compounds into write-offs.",
                "opportunity_copy": "Tightening collections on the oldest invoices often frees meaningful cash with one phone call.",
                "recommendation": "Call your top five overdue accounts this week personally.",
            },
        ],
    },
    {
        "id": "software",
        "name": "Software Stack",
        "weight": 0.85,
        "summary": "",
        "questions": [
            {
                "id": "sw_01",
                "text": "For every critical domain — customers, finances, employees, operations — there is one system of record, and everyone on the team knows which one.",
                "type": "likert",
                "weight": 1.8,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Multiple sources of truth mean there is no truth.",
                "opportunity_copy": "This is the foundation for any future automation, reporting, or AI work.",
                "recommendation": "List your four core domains and name the authoritative system for each; communicate it to the team this week.",
            },
            {
                "id": "sw_02",
                "text": "Core systems are integrated well enough that no one spends meaningful time re-keying data between them.",
                "type": "likert",
                "weight": 1.5,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Re-keying between systems means you are paying people to do work software should do for free.",
                "opportunity_copy": "Eliminating the worst re-keying workflow usually returns hours per week immediately.",
                "recommendation": "Identify the single worst re-keying workflow in the business and fix it with an integration or automation in 30 days.",
            },
            {
                "id": "sw_03",
                "text": "Our CRM or primary customer database is clean enough that I trust the numbers I pull from it without caveats.",
                "type": "likert",
                "weight": 1.2,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "A dirty CRM makes every sales and marketing report untrustworthy, and the team stops using it.",
                "opportunity_copy": "A two-week CRM cleanup often produces months of downstream clarity.",
                "recommendation": "Assign one person to a 10-day CRM data cleanup sprint with specific targets.",
            },
            {
                "id": "sw_04",
                "text": "When someone leaves the company, access to every system is revoked within one business day via a documented process.",
                "type": "yesno",
                "weight": 1.0,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Every departing employee who retains access is a liability sitting on your books.",
                "opportunity_copy": "A documented one-day offboarding checklist takes an afternoon to build and eliminates an entire risk category.",
                "recommendation": "Write a one-page offboarding checklist this week and run it on the next departure.",
            },
            {
                "id": "sw_05",
                "text": "I could produce a complete list of every paid software tool the business pays for in under 15 minutes.",
                "type": "yesno",
                "weight": 0.8,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Not being able to list your stack quickly means you are paying for things you don't use and don't know about.",
                "opportunity_copy": "A 30-minute stack audit typically finds 5–15% of software spend that can be cut immediately.",
                "recommendation": "Pull the last 90 days of credit card and AP statements, build a stack list, and flag anything unused.",
            },
            {
                "id": "sw_06",
                "text": "We have audited software spend in the last 12 months and eliminated or renegotiated at least one line item.",
                "type": "yesno",
                "weight": 0.7,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Autopilot SaaS spend is one of the most predictable leaks in a $2–20M business.",
                "opportunity_copy": "Vendors negotiate when you ask; most owners never ask.",
                "recommendation": "Before your next renewal, ask for a discount in writing; do this for every vendor.",
            },
            {
                "id": "sw_q_num_saas_tools",
                "text": "Number of paid SaaS tools in use",
                "type": "number",
                "weight": 0.8,
                "lower_is_better": False,
                "allow_na": True,
                "risk_copy": "Tool sprawl means you are paying for overlap, confusion, and integration gaps.",
                "opportunity_copy": "Knowing your exact count is the first step to rationalizing the stack.",
                "recommendation": "Build a complete tool inventory this week and flag any with fewer than three active users.",
            },
            {
                "id": "sw_q_software_spend_pct",
                "text": "Annual software spend as % of revenue",
                "type": "percent",
                "weight": 0.8,
                "lower_is_better": False,
                "allow_na": True,
                "risk_copy": "Software spend outside the industry norm — too high or too low — signals either waste or underinvestment.",
                "opportunity_copy": "Benchmarking spend against your vertical reveals where you are over- or under-tooled.",
                "recommendation": "Pull total SaaS spend from AP, divide by revenue, and compare to industry median.",
            },
        ],
    },
    {
        "id": "ai",
        "name": "AI Readiness",
        "weight": 0.50,
        "summary": "",
        "questions": [
            {
                "id": "ai_01",
                "text": "The business has at least one AI-enabled workflow in production today that is saving time or money. Not a pilot — in production.",
                "type": "yesno",
                "weight": 1.8,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Businesses without production AI workflows today will be operating at a structural cost disadvantage within a year.",
                "opportunity_copy": "One well-chosen AI workflow is a cheap, fast, high-leverage entry point.",
                "recommendation": "Pick one repetitive, text-heavy workflow and put an AI tool into production on it within 30 days.",
            },
            {
                "id": "ai_02",
                "text": "I personally use AI tools in my own workflow at least weekly, in ways that materially change the output of my work.",
                "type": "likert",
                "weight": 1.5,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "An owner who doesn't use AI personally cannot credibly lead an AI-enabled team.",
                "opportunity_copy": "Personal AI fluency changes how you evaluate every other decision — hiring, pricing, speed.",
                "recommendation": "Pick one task you do weekly and move it to an AI-assisted workflow this month.",
            },
            {
                "id": "ai_03",
                "text": "People beyond me on the team know how to use AI tools effectively for their own work.",
                "type": "likert",
                "weight": 1.2,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "AI fluency concentrated in the owner creates a bottleneck identical to every other owner-dependency issue.",
                "opportunity_copy": "Peer-taught AI use compounds; top-down training does not.",
                "recommendation": "Start a standing 30-minute weekly AI demo session where team members share workflows.",
            },
            {
                "id": "ai_04",
                "text": "We have a written, simple policy on acceptable AI use covering customer data and confidentiality.",
                "type": "yesno",
                "weight": 1.0,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "The absence of a policy is itself the policy — and it is the wrong one.",
                "opportunity_copy": "Clear rules let the team use AI faster, not slower.",
                "recommendation": "Draft a one-page AI policy this week covering customer data, confidentiality, and approved tools; share it with the team.",
            },
            {
                "id": "ai_q_num_ai_workflows",
                "text": "Number of workflows with AI augmentation in production",
                "type": "number",
                "weight": 1.2,
                "lower_is_better": False,
                "allow_na": True,
                "risk_copy": "Zero production AI workflows means you are falling behind competitors who have them.",
                "opportunity_copy": "Each production AI workflow compounds — it trains the team, generates data, and unlocks the next one.",
                "recommendation": "Pick one high-volume, text-heavy process and deploy an AI tool on it within 30 days.",
            },
        ],
    },
    {
        "id": "sales",
        "name": "Sales & Marketing",
        "weight": 1.00,
        "summary": "",
        "questions": [
            {
                "id": "sal_01",
                "text": "I can describe our ideal customer in one sentence, and my team would describe them the same way.",
                "type": "likert",
                "weight": 1.8,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "ICP drift is the most expensive unnoticed failure in sales.",
                "opportunity_copy": "One-page ICP alignment is free and compounds across every sales, marketing, and product decision.",
                "recommendation": "Write a one-sentence ICP, paste it in Slack, and ask the team to paraphrase it back; the gaps are the finding.",
            },
            {
                "id": "sal_02",
                "text": "Deals above a meaningful size usually require my personal involvement to close.",
                "type": "likert",
                "weight": 1.8,
                "reverse": True,
                "allow_na": True,
                "risk_copy": "Deal-closing owner dependency is a silent ceiling on revenue growth and a major red flag to buyers.",
                "opportunity_copy": "Building a second closer is the single highest-leverage sales move available in an owner-dependent shop.",
                "recommendation": "Identify your most promotable salesperson, shadow-close the next three deals with them, and hand over the fourth.",
            },
            {
                "id": "sal_03",
                "text": "I can open our pipeline right now and see every open opportunity with a stage, dollar value, and a next step.",
                "type": "likert",
                "weight": 1.5,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "A pipeline without stages, dollar values, and next steps is a list of hopes, not a forecast.",
                "opportunity_copy": "One hour of pipeline hygiene per week produces weeks of forecast clarity.",
                "recommendation": "Define your stages in one paragraph each and require every open deal to have a stage, dollar value, and next step by end of week.",
            },
            {
                "id": "sal_04",
                "text": "I track customer churn or retention on a fixed cadence and know the number for the trailing 12 months.",
                "type": "likert",
                "weight": 1.5,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Churn blindness means you may be replacing customers as fast as you win them without realizing it.",
                "opportunity_copy": "A trailing-12-month churn number is the single most useful sales metric after revenue.",
                "recommendation": "Interview your last five churned customers and find the pattern.",
            },
            {
                "id": "sal_05",
                "text": "I know which marketing channels produce our best customers — not just our cheapest leads.",
                "type": "likert",
                "weight": 1.2,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Cheap leads that don't close or don't stay are the most expensive kind.",
                "opportunity_copy": "Reallocating spend toward channels that produce best customers often doubles effective marketing ROI.",
                "recommendation": "Tag your last 50 closed-won customers by source and reallocate next quarter's marketing spend accordingly.",
            },
            {
                "id": "sal_06",
                "text": "Discounts above a set threshold require approval. They are not handed out by reps to close deals.",
                "type": "yesno",
                "weight": 1.0,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Uncontrolled discounting trains customers to negotiate and trains reps to lead with price.",
                "opportunity_copy": "A simple discount approval threshold recovers margin immediately with no product or process change.",
                "recommendation": "Set a discount approval threshold this week; anything above requires written sign-off.",
            },
            {
                "id": "sal_07",
                "text": "A meaningful share of new customers came from referrals or word-of-mouth in the last 12 months.",
                "type": "likert",
                "weight": 0.8,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "A business with no meaningful referral volume is either serving customers poorly or not asking.",
                "opportunity_copy": "Referrals are the highest-margin, highest-trust acquisition channel, and building the engine is cheap and durable.",
                "recommendation": "Build a systematic referral ask into your customer success handoff and measure referrals per quarter.",
            },
            {
                "id": "sal_q_cac",
                "text": "Customer acquisition cost ($)",
                "type": "number",
                "weight": 1.2,
                "lower_is_better": True,
                "allow_na": True,
                "risk_copy": "Not knowing CAC means you cannot tell which growth channels are profitable.",
                "opportunity_copy": "Even a rough CAC number transforms marketing from a cost center into a measurable investment.",
                "recommendation": "Calculate fully-loaded CAC for your top two channels this month.",
            },
            {
                "id": "sal_q_monthly_churn_pct",
                "text": "Monthly customer churn rate (%)",
                "type": "percent",
                "weight": 1.2,
                "lower_is_better": True,
                "allow_na": True,
                "risk_copy": "High churn means you are filling a leaking bucket — growth masks the real problem.",
                "opportunity_copy": "Cutting churn by even half a point compounds into massive LTV improvement.",
                "recommendation": "Interview your last five churned customers and fix the top pattern.",
            },
        ],
    },
    {
        "id": "ops",
        "name": "Operations & Process",
        "weight": 1.10,
        "summary": "",
        "questions": [
            {
                "id": "ops_01",
                "text": "Our core delivery workflows are documented well enough that a new hire could run them with minimal supervision.",
                "type": "likert",
                "weight": 1.8,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Tribal knowledge is a liability disguised as institutional memory.",
                "opportunity_copy": "Documenting your top three workflows cuts new-hire ramp time dramatically and surfaces improvement opportunities in the process.",
                "recommendation": "Pick your three most critical workflows and document each in a single page this month.",
            },
            {
                "id": "ops_02",
                "text": "We meet our commitments to customers — on time and in full — more than 95% of the time.",
                "type": "likert",
                "weight": 1.5,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Unreliable delivery erodes customer trust faster than any marketing campaign can rebuild it.",
                "opportunity_copy": "Fixing delivery reliability compounds: the same customers buy more, churn less, and refer more.",
                "recommendation": "Instrument OTIF measurement for the next 60 days, even roughly — you cannot fix what you don't measure.",
            },
            {
                "id": "ops_03",
                "text": "I can name the single biggest bottleneck in our operation right now, and we are actively working on it.",
                "type": "likert",
                "weight": 1.5,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Operating without a bottleneck hypothesis means every improvement is a guess.",
                "opportunity_copy": "Correctly identifying and fixing the bottleneck is the single highest-ROI operations move available.",
                "recommendation": "Walk your core process end to end and identify where work waits — that's the bottleneck.",
            },
            {
                "id": "ops_04",
                "text": "Rework — redoing work that was delivered incorrectly the first time — is rare and tracked when it happens.",
                "type": "likert",
                "weight": 1.2,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Untracked rework is a cost center hiding inside your labor line.",
                "opportunity_copy": "Cutting rework is almost always cheaper than adding capacity.",
                "recommendation": "Define rework in one sentence for your business and start tracking incidents for 60 days.",
            },
            {
                "id": "ops_05",
                "text": "There is a standing KPI review on a fixed cadence that the team actually attends and uses.",
                "type": "yesno",
                "weight": 1.2,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "KPIs that aren't reviewed aren't KPIs — they're wallpaper.",
                "opportunity_copy": "A 30-minute weekly KPI review is the cheapest management upgrade available in operations.",
                "recommendation": "Schedule a standing weekly KPI review, 30 minutes, same day and time; start next week.",
            },
            {
                "id": "ops_06",
                "text": "No single vendor or supplier represents a concentration risk that would materially damage the business if they disappeared.",
                "type": "yesno",
                "weight": 1.0,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Concentration risk is cheap until it isn't — and then it's the whole business.",
                "opportunity_copy": "Even a partial second source gives you pricing leverage on the primary.",
                "recommendation": "List your top five vendors; for any that would cripple the business if they disappeared, qualify a backup this quarter.",
            },
            {
                "id": "ops_07",
                "text": "Our recurring meetings have agendas, produce decisions with owners, and someone would notice if they were cancelled.",
                "type": "likert",
                "weight": 0.8,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "If a recurring meeting could be cancelled without anyone noticing, it already has been; you're just still paying for it.",
                "opportunity_copy": "Tightening meeting discipline is free and immediately returns hours per week across the team.",
                "recommendation": "Audit your recurring meetings and cut any that cannot name a decision made in the last month.",
            },
            {
                "id": "ops_q_on_time_delivery_pct",
                "text": "On-time, in-full delivery rate (%)",
                "type": "percent",
                "weight": 1.2,
                "lower_is_better": False,
                "allow_na": True,
                "risk_copy": "Every missed delivery erodes the trust that keeps customers renewing.",
                "opportunity_copy": "Tracking OTIF for 60 days reveals the root causes you can actually fix.",
                "recommendation": "Instrument OTIF measurement this month, even roughly — you cannot fix what you don't measure.",
            },
            {
                "id": "ops_q_mttr_hours",
                "text": "Mean time to resolve customer issues (hours)",
                "type": "number",
                "weight": 1.0,
                "lower_is_better": True,
                "allow_na": True,
                "risk_copy": "Long resolution times compound: one slow fix creates three follow-up tickets.",
                "opportunity_copy": "Cutting MTTR often costs nothing — the fix is usually a process bottleneck, not a resource gap.",
                "recommendation": "Pull your last 20 resolved tickets, find the step where they sat longest, and fix that step.",
            },
        ],
    },
]

# ---------------------------------------------------------------------------
# Firmographics (intake screen, not scored)
# Stored in the JSON export and printed on the PDF cover.
# ---------------------------------------------------------------------------
FIRMOGRAPHICS = [
    {"id": "company_name", "label": "Company name",                          "type": "text"},
    {"id": "revenue_band", "label": "Annual revenue",                        "type": "select",
     "options": ["<$1M", "$1–5M", "$5–20M", "$20–50M", "$50–100M", "$100M+"]},
    {"id": "ebitda_margin", "label": "EBITDA margin (%)",                    "type": "int"},
    {"id": "employees",    "label": "Full-time headcount",                   "type": "int"},
    {"id": "industry",     "label": "Industry",                              "type": "select",
     "options": ["SaaS", "Professional Services", "Manufacturing",
                 "Retail / E-commerce", "Healthcare", "Financial Services", "Other"]},
    {"id": "years",        "label": "Years in operation",                    "type": "int"},
    {"id": "owner_hours",  "label": "Owner's weekly hours in the business",  "type": "int"},
]

# ---------------------------------------------------------------------------
# Industry Benchmarks
#
# Keyed by (industry, question_id). Each entry has p25/p50/p75 values.
# Used by scoring.py to compute percentile-based scores for quantitative
# questions. Values are reasonable estimates for v0.2; refine with real
# data as it accumulates.
#
# Convention: lower-is-better metrics (days_to_close, churn, etc.) have
# p25 as the *best* value and p75 as the *worst*. The scoring engine
# handles directionality via the "lower_is_better" flag on each question.
# ---------------------------------------------------------------------------
INDUSTRY_LIST = [
    "SaaS", "Professional Services", "Manufacturing",
    "Retail / E-commerce", "Healthcare", "Financial Services",
]

BENCHMARKS = {
    # --- Personnel ---
    ("SaaS", "per_q_turnover_pct"):               {"p25": 8,  "p50": 15, "p75": 25},
    ("Professional Services", "per_q_turnover_pct"):{"p25": 10, "p50": 18, "p75": 28},
    ("Manufacturing", "per_q_turnover_pct"):        {"p25": 8,  "p50": 14, "p75": 22},
    ("Retail / E-commerce", "per_q_turnover_pct"):  {"p25": 15, "p50": 25, "p75": 40},
    ("Healthcare", "per_q_turnover_pct"):           {"p25": 12, "p50": 20, "p75": 30},
    ("Financial Services", "per_q_turnover_pct"):   {"p25": 8,  "p50": 14, "p75": 22},

    ("SaaS", "per_q_days_to_fill"):               {"p25": 25, "p50": 40, "p75": 60},
    ("Professional Services", "per_q_days_to_fill"):{"p25": 20, "p50": 35, "p75": 55},
    ("Manufacturing", "per_q_days_to_fill"):        {"p25": 25, "p50": 45, "p75": 70},
    ("Retail / E-commerce", "per_q_days_to_fill"):  {"p25": 15, "p50": 30, "p75": 50},
    ("Healthcare", "per_q_days_to_fill"):           {"p25": 30, "p50": 50, "p75": 75},
    ("Financial Services", "per_q_days_to_fill"):   {"p25": 25, "p50": 42, "p75": 65},

    # --- Accounting & Finance ---
    ("SaaS", "fin_q_days_to_close"):               {"p25": 5,  "p50": 8,  "p75": 15},
    ("Professional Services", "fin_q_days_to_close"):{"p25": 5, "p50": 10, "p75": 18},
    ("Manufacturing", "fin_q_days_to_close"):        {"p25": 7, "p50": 12, "p75": 20},
    ("Retail / E-commerce", "fin_q_days_to_close"):  {"p25": 5, "p50": 8,  "p75": 14},
    ("Healthcare", "fin_q_days_to_close"):           {"p25": 7, "p50": 12, "p75": 20},
    ("Financial Services", "fin_q_days_to_close"):   {"p25": 5, "p50": 8,  "p75": 15},

    ("SaaS", "fin_q_ar_over_60_pct"):              {"p25": 3,  "p50": 8,  "p75": 18},
    ("Professional Services", "fin_q_ar_over_60_pct"):{"p25": 5,"p50": 12, "p75": 22},
    ("Manufacturing", "fin_q_ar_over_60_pct"):       {"p25": 5, "p50": 10, "p75": 20},
    ("Retail / E-commerce", "fin_q_ar_over_60_pct"): {"p25": 2, "p50": 5,  "p75": 12},
    ("Healthcare", "fin_q_ar_over_60_pct"):          {"p25": 8, "p50": 18, "p75": 30},
    ("Financial Services", "fin_q_ar_over_60_pct"):  {"p25": 3, "p50": 8,  "p75": 16},

    # --- Software Stack ---
    ("SaaS", "sw_q_num_saas_tools"):               {"p25": 15, "p50": 30, "p75": 55},
    ("Professional Services", "sw_q_num_saas_tools"):{"p25": 10,"p50": 20, "p75": 40},
    ("Manufacturing", "sw_q_num_saas_tools"):        {"p25": 8, "p50": 15, "p75": 30},
    ("Retail / E-commerce", "sw_q_num_saas_tools"):  {"p25": 12,"p50": 25, "p75": 45},
    ("Healthcare", "sw_q_num_saas_tools"):           {"p25": 10,"p50": 20, "p75": 35},
    ("Financial Services", "sw_q_num_saas_tools"):   {"p25": 12,"p50": 25, "p75": 45},

    ("SaaS", "sw_q_software_spend_pct"):           {"p25": 5,  "p50": 10, "p75": 18},
    ("Professional Services", "sw_q_software_spend_pct"):{"p25":3,"p50": 6,"p75": 12},
    ("Manufacturing", "sw_q_software_spend_pct"):    {"p25": 1, "p50": 3,  "p75": 6},
    ("Retail / E-commerce", "sw_q_software_spend_pct"):{"p25": 2,"p50": 5, "p75": 10},
    ("Healthcare", "sw_q_software_spend_pct"):       {"p25": 2, "p50": 5,  "p75": 10},
    ("Financial Services", "sw_q_software_spend_pct"):{"p25": 3,"p50": 7,  "p75": 14},

    # --- AI Readiness ---
    ("SaaS", "ai_q_num_ai_workflows"):             {"p25": 2,  "p50": 5,  "p75": 10},
    ("Professional Services", "ai_q_num_ai_workflows"):{"p25":1,"p50": 3,  "p75": 6},
    ("Manufacturing", "ai_q_num_ai_workflows"):      {"p25": 0, "p50": 1,  "p75": 3},
    ("Retail / E-commerce", "ai_q_num_ai_workflows"):{"p25": 1, "p50": 3,  "p75": 7},
    ("Healthcare", "ai_q_num_ai_workflows"):         {"p25": 0, "p50": 2,  "p75": 4},
    ("Financial Services", "ai_q_num_ai_workflows"): {"p25": 1, "p50": 3,  "p75": 7},

    # --- Sales & Marketing ---
    ("SaaS", "sal_q_cac"):                         {"p25": 200,"p50": 500, "p75": 1200},
    ("Professional Services", "sal_q_cac"):         {"p25": 300,"p50": 800, "p75": 2000},
    ("Manufacturing", "sal_q_cac"):                  {"p25": 150,"p50": 400,"p75": 1000},
    ("Retail / E-commerce", "sal_q_cac"):            {"p25": 20, "p50": 60, "p75": 150},
    ("Healthcare", "sal_q_cac"):                     {"p25": 400,"p50":1000,"p75": 2500},
    ("Financial Services", "sal_q_cac"):             {"p25": 300,"p50": 700,"p75": 1800},

    ("SaaS", "sal_q_monthly_churn_pct"):           {"p25": 1.5,"p50": 3.0,"p75": 5.0},
    ("Professional Services", "sal_q_monthly_churn_pct"):{"p25":0.5,"p50":1.5,"p75":3.0},
    ("Manufacturing", "sal_q_monthly_churn_pct"):    {"p25": 0.5,"p50":1.0,"p75": 2.5},
    ("Retail / E-commerce", "sal_q_monthly_churn_pct"):{"p25":2.0,"p50":4.0,"p75":7.0},
    ("Healthcare", "sal_q_monthly_churn_pct"):       {"p25": 0.5,"p50":1.5,"p75": 3.0},
    ("Financial Services", "sal_q_monthly_churn_pct"):{"p25":0.5,"p50":1.5,"p75":3.0},

    # --- Operations ---
    ("SaaS", "ops_q_on_time_delivery_pct"):        {"p25": 92, "p50": 96, "p75": 99},
    ("Professional Services", "ops_q_on_time_delivery_pct"):{"p25":88,"p50":94,"p75":98},
    ("Manufacturing", "ops_q_on_time_delivery_pct"): {"p25": 90,"p50": 95, "p75": 98},
    ("Retail / E-commerce", "ops_q_on_time_delivery_pct"):{"p25":90,"p50":95,"p75":99},
    ("Healthcare", "ops_q_on_time_delivery_pct"):    {"p25": 88,"p50": 93, "p75": 97},
    ("Financial Services", "ops_q_on_time_delivery_pct"):{"p25":92,"p50":96,"p75":99},

    ("SaaS", "ops_q_mttr_hours"):                  {"p25": 2,  "p50": 8,  "p75": 24},
    ("Professional Services", "ops_q_mttr_hours"):  {"p25": 4,  "p50": 12, "p75": 36},
    ("Manufacturing", "ops_q_mttr_hours"):           {"p25": 4,  "p50": 16, "p75": 48},
    ("Retail / E-commerce", "ops_q_mttr_hours"):     {"p25": 2,  "p50": 8,  "p75": 24},
    ("Healthcare", "ops_q_mttr_hours"):              {"p25": 4,  "p50": 12, "p75": 36},
    ("Financial Services", "ops_q_mttr_hours"):      {"p25": 2,  "p50": 8,  "p75": 24},
}
