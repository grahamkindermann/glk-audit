"""
Structural Advantage: Business Audit Rubric
=============================================

All scoring content lives here. Edit freely; do not edit app.py to change
content. app.py consumes this file as plain data.

To change the product's behavior, edit (in order of how often you'll touch it):
    1. Question text / weights  : inside DIMENSIONS
    2. Copy (risk / opp / rec)  : inside each question
    3. BANDS / thresholds       : scoring tier boundaries
    4. CTA / BRAND              : report framing
"""

# ---------------------------------------------------------------------------
# Version
# Bump on any change to questions, weights, bands, or reverse flags so that
# generated reports can be traced to the rubric that produced them.
# ---------------------------------------------------------------------------
RUBRIC_VERSION = "0.1.0"

# ---------------------------------------------------------------------------
# Brand strings
# ---------------------------------------------------------------------------
BRAND = {
    "wordmark": "STRUCTURAL ADVANTAGE",
    "cover_subtitle": "Business Structural Audit",
    "prepared_by": "Prepared by Graham Kindermann · GLK Holdings LLC · graham@grahamkindermann.com",
}

# ---------------------------------------------------------------------------
# CTA blocks
# ---------------------------------------------------------------------------
CTA = {
    "lead_magnet": {
        "headline": "Ready for the conversation behind the score?",
        "primary_label": "Book a 30-min structural review",
        "primary_url":   "https://calendly.com/gkholdingsllcva/advisory-intro",
        "secondary_label": "Subscribe to Structural Advantage",
        "secondary_url":   "https://structuraladvantage.substack.com/",
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

# Minimum fraction of a dimension's total weight that must be answered for
# the dimension to receive a score. If less than this fraction is answered,
# the dimension is marked INSUFFICIENT_DATA_LABEL and excluded from the
# overall weighted average. E.g. 0.60 means at least 60% must be answered.
MINIMUM_ANSWERED_FRACTION = 0.60
INSUFFICIENT_DATA_LABEL = "Insufficient Data"

# Score thresholds for classifying question results as risks vs opportunities.
# Risks: answered questions scoring below this fraction.
RISK_THRESHOLD = 0.4
# Opportunities: questions scoring at or above RISK_THRESHOLD but below this ceiling.
OPPORTUNITY_CEILING = 0.75

# ---------------------------------------------------------------------------
# Band narratives (two-sentence executive-summary interpretation keyed off
# band id). Blunt operator voice. Used in both the Streamlit UI and PDF
# reports. Written in second person to match the interactive tool's voice.
# ---------------------------------------------------------------------------
BAND_NARRATIVE = {
    "critical": (
        "Your business is structurally exposed across multiple dimensions. "
        "Without intervention, the next shock will expose gaps that could threaten continuity."
    ),
    "fragile": (
        "Your business is functioning but running hot. "
        "Most of the load is on you, and a handful of weak points are carrying disproportionate risk."
    ),
    "functional": (
        "Your business has real structural muscle, but the remaining gaps are load-bearing. "
        "Closing two or three of them would move you into durable territory."
    ),
    "strong": (
        "Your business is well-run across most dimensions. "
        "The remaining gaps are refinements, not emergencies, and the leverage is in compounding what already works."
    ),
    "durable": (
        "Your business is structurally sound and operator-independent. "
        "Focus shifts from fixing weaknesses to protecting the advantage and scaling on strength."
    ),
}

# ---------------------------------------------------------------------------
# Dimensions
#
# Dimension weights are raw; app.py uses them as-is in a weighted average
# at runtime. AI Readiness is deliberately thin (5 questions, weight 0.50).
#
# Question schema:
#   {
#       "id":               "per_01",
#       "text":             "...",
#       "type":             "likert" | "yesno",
#       "weight":           float,
#       "reverse":          bool,   # see app.py score_question() for rules
#       "allow_na":         bool,
#       "risk_copy":        "...",  # shown when question surfaces as a risk
#       "opportunity_copy": "...",
#       "recommendation":   "...",
#   }
# ---------------------------------------------------------------------------
DIMENSIONS = [
    {
        "id": "personnel",
        "name": "Personnel & Org",
        "weight": 1.15,
        "summary": "How dependent is the business on the owner, and how deep is the leadership bench? This dimension measures whether the org can operate, decide, and execute without a single point of failure.",
        "questions": [
            {
                "id": "per_01",
                "group": "Owner Dependency & Leadership",
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
                "group": "Owner Dependency & Leadership",
                "text": "More than half of my leadership team would be considered A-players by a top competitor in our industry.",
                "type": "likert",
                "weight": 1.8,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "B-players hire C-players; talent drift compounds quietly until it becomes a full rebuild.",
                "opportunity_copy": "Upgrading one leadership seat per year is the most durable compounding move an operator can make.",
                "recommendation": "Rank your leadership team honestly on a 1 to 5 scale; anyone at 3 or below gets a 90-day bar or an exit plan.",
            },
            {
                "id": "per_03",
                "group": "Owner Dependency & Leadership",
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
                "group": "Team Quality & Retention",
                "text": "When someone on the team makes a commitment with a date, it is met or renegotiated before the date, not missed silently.",
                "type": "likert",
                "weight": 1.5,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "When deadlines slip silently, the owner becomes the only quality-control mechanism in the business.",
                "opportunity_copy": "This is the single cheapest accountability upgrade available. It costs nothing but attention.",
                "recommendation": "Model it yourself for 30 days by renegotiating, out loud, every date you're about to miss.",
            },
            {
                "id": "per_05",
                "group": "Team Quality & Retention",
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
                "group": "Team Quality & Retention",
                "text": "Every key seat in the business has a documented backup or succession plan.",
                "type": "yesno",
                "weight": 1.0,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "The absence of a succession plan is a silent concentration risk sitting under your entire org chart.",
                "opportunity_copy": "A one-page key-seat map is a cheap insurance policy against the single most predictable business failure mode.",
                "recommendation": "Draft a one-page key-seat map this week listing every critical role and a named backup; the gaps become your next-quarter hiring priorities.",
            },
            {
                "id": "per_07",
                "group": "Team Quality & Retention",
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
                "group": "Workforce Metrics",
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
                "group": "Workforce Metrics",
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
        "summary": "Can you see what's happening financially in real time, or are you flying blind between monthly closes? This dimension assesses whether your financial controls, reporting, and cash management are built to scale.",
        "questions": [
            {
                "id": "fin_01",
                "group": "Financial Visibility",
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
                "group": "Financial Visibility",
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
                "group": "Financial Visibility",
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
                "group": "Discipline & Controls",
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
                "group": "Discipline & Controls",
                "text": "A budget vs. actuals review happens on a fixed cadence with a named owner, not just when something looks off.",
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
                "group": "Discipline & Controls",
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
                "group": "Discipline & Controls",
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
                "group": "Discipline & Controls",
                "text": "My own compensation is set at market replacement cost for my role, not whatever is left over at the end of the month.",
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
                "group": "Operational Metrics",
                "text": "Days to close monthly books",
                "type": "number",
                "weight": 1.2,
                "lower_is_better": True,
                "allow_na": True,
                "risk_copy": "A close cycle longer than industry median means every monthly decision starts with stale data.",
                "opportunity_copy": "A close near industry median still has room to improve. Shaving even two days off compounds into faster action across the business.",
                "recommendation": "Map the close calendar step by step, find the single longest wait, and fix that one bottleneck.",
            },
            {
                "id": "fin_q_ar_over_60_pct",
                "group": "Operational Metrics",
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
        "summary": "Is your tech stack helping you scale or holding you back? This dimension evaluates whether your systems are integrated, documented, and built for growth rather than patched together.",
        "questions": [
            {
                "id": "sw_01",
                "group": "Systems of Record",
                "text": "For every critical domain (customers, finances, employees, operations) there is one system of record, and everyone on the team knows which one.",
                "type": "likert",
                "weight": 1.8,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Multiple sources of truth mean there is no truth.",
                "opportunity_copy": "One clean system-of-record per domain cuts reporting time in half and makes every automation project immediately cheaper.",
                "recommendation": "List your four core domains and name the authoritative system for each; communicate it to the team this week.",
            },
            {
                "id": "sw_02",
                "group": "Systems of Record",
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
                "group": "Systems of Record",
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
                "group": "Governance & Hygiene",
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
                "group": "Governance & Hygiene",
                "text": "I could produce a complete list of every paid software tool the business pays for in under 15 minutes.",
                "type": "yesno",
                "weight": 0.8,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Not being able to list your stack quickly means you are paying for things you don't use and don't know about.",
                "opportunity_copy": "A 30-minute stack audit typically finds 5 to 15% of software spend that can be cut immediately.",
                "recommendation": "Pull the last 90 days of credit card and AP statements, build a stack list, and flag anything unused.",
            },
            {
                "id": "sw_06",
                "group": "Governance & Hygiene",
                "text": "We have audited software spend in the last 12 months and eliminated or renegotiated at least one line item.",
                "type": "yesno",
                "weight": 0.7,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Autopilot SaaS spend is one of the most predictable leaks in a two to twenty million dollar business.",
                "opportunity_copy": "Vendors negotiate when you ask; most owners never ask.",
                "recommendation": "Before your next renewal, ask for a discount in writing; do this for every vendor.",
            },
            {
                "id": "sw_q_num_saas_tools",
                "group": "Spend Metrics",
                "text": "Number of paid SaaS tools in use",
                "type": "number",
                "weight": 0.8,
                "lower_is_better": True,
                "allow_na": True,
                "risk_copy": "Tool sprawl means you are paying for overlap, confusion, and integration gaps.",
                "opportunity_copy": "A leaner stack is cheaper, easier to integrate, and faster to onboard new hires onto.",
                "recommendation": "Build a complete tool inventory this week and flag any with fewer than three active users.",
            },
            {
                "id": "sw_q_software_spend_pct",
                "group": "Spend Metrics",
                "text": "Annual software spend as % of revenue",
                "type": "percent",
                "weight": 0.8,
                "lower_is_better": True,
                "allow_na": True,
                "risk_copy": "Software spend well above industry norm is a drag on margin that compounds every month.",
                "opportunity_copy": "Benchmarking spend against your vertical reveals where you are over-tooled and where renegotiation pays off.",
                "recommendation": "Pull total SaaS spend from AP, divide by revenue, and compare to industry median.",
            },
        ],
    },
    {
        "id": "ai",
        "name": "AI Readiness",
        "weight": 0.50,
        "summary": "AI readiness is a structural advantage. This dimension measures whether the business has production AI workflows, whether the team can use them without the owner, and whether a policy exists to govern their use. Companies that score low here are already operating at a cost and speed disadvantage.",
        "questions": [
            {
                "id": "ai_01",
                "group": "Adoption & Usage",
                "text": "The business has at least one AI-enabled workflow in production today that is saving time or money. Not a pilot, in production.",
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
                "group": "Adoption & Usage",
                "text": "I personally use AI tools in my own workflow at least weekly, in ways that materially change the output of my work.",
                "type": "likert",
                "weight": 1.5,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "An owner who doesn't use AI personally cannot credibly lead an AI-enabled team.",
                "opportunity_copy": "Personal AI fluency changes how you evaluate every other decision — from hiring to pricing to speed.",
                "recommendation": "Pick one task you do weekly and move it to an AI-assisted workflow this month.",
            },
            {
                "id": "ai_03",
                "group": "Adoption & Usage",
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
                "group": "Policy & Scale",
                "text": "We have a written, simple policy on acceptable AI use covering customer data and confidentiality.",
                "type": "yesno",
                "weight": 1.0,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "The absence of a policy is itself the policy, and it is the wrong one.",
                "opportunity_copy": "Clear rules let the team use AI faster, not slower.",
                "recommendation": "Draft a one-page AI policy this week covering customer data, confidentiality, and approved tools; share it with the team.",
            },
            {
                "id": "ai_q_num_ai_workflows",
                "group": "Policy & Scale",
                "text": "Number of workflows with AI augmentation in production",
                "type": "number",
                "weight": 1.2,
                "lower_is_better": False,
                "allow_na": True,
                "risk_copy": "Zero production AI workflows means you are falling behind competitors who have them.",
                "opportunity_copy": "Each production AI workflow compounds: it trains the team, generates data, and unlocks the next one.",
                "recommendation": "Pick one high-volume, text-heavy process and deploy an AI tool on it within 30 days.",
            },
        ],
    },
    {
        "id": "sales",
        "name": "Sales & Marketing",
        "weight": 1.00,
        "summary": "Revenue is oxygen. This dimension measures whether your pipeline, positioning, and customer acquisition are repeatable systems or dependent on the founder's personal network and hustle.",
        "questions": [
            {
                "id": "sal_01",
                "group": "Pipeline & Targeting",
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
                "group": "Pipeline & Targeting",
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
                "group": "Pipeline & Targeting",
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
                "group": "Retention & Economics",
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
                "group": "Retention & Economics",
                "text": "I know which marketing channels produce our best customers, not just our cheapest leads.",
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
                "group": "Retention & Economics",
                "text": "Discounts above a set threshold require approval and are not handed out by reps to close deals.",
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
                "group": "Retention & Economics",
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
                "group": "Unit Economics",
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
                "group": "Unit Economics",
                "text": "Monthly customer churn rate (%)",
                "type": "percent",
                "weight": 1.2,
                "lower_is_better": True,
                "allow_na": True,
                "risk_copy": "A monthly churn rate above industry median means replacing a meaningful share of the customer base every year just to stay flat.",
                "opportunity_copy": "Churn near industry norms still has room to improve. Cutting it by even half a point per month compounds into significant LTV improvement over a year.",
                "recommendation": "Segment your last 10 churned customers by reason and fix the single most common one.",
            },
        ],
    },
    {
        "id": "ops",
        "name": "Operations & Process",
        "weight": 1.10,
        "summary": "Operations is where margin lives. This dimension assesses whether your core workflows are documented, measured, and improvable, or whether institutional knowledge walks out the door when someone quits.",
        "questions": [
            {
                "id": "ops_01",
                "group": "Delivery & Process",
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
                "group": "Delivery & Process",
                "text": "We meet our commitments to customers (on time and in full) more than 95% of the time.",
                "type": "likert",
                "weight": 1.5,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Unreliable delivery erodes customer trust faster than any marketing campaign can rebuild it.",
                "opportunity_copy": "Fixing delivery reliability compounds: the same customers buy more, churn less, and refer more.",
                "recommendation": "Instrument OTIF measurement for the next 60 days, even roughly; you cannot fix what you don't measure.",
            },
            {
                "id": "ops_03",
                "group": "Delivery & Process",
                "text": "I can name the single biggest bottleneck in our operation right now, and we are actively working on it.",
                "type": "likert",
                "weight": 1.5,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Operating without a bottleneck hypothesis means every improvement is a guess.",
                "opportunity_copy": "Correctly identifying and fixing the bottleneck is the single highest-ROI operations move available.",
                "recommendation": "Walk your core process end to end and identify where work waits; that is the bottleneck.",
            },
            {
                "id": "ops_04",
                "group": "Delivery & Process",
                "text": "Rework (redoing work that was delivered incorrectly the first time) is rare and tracked when it happens.",
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
                "group": "Governance & Risk",
                "text": "There is a standing KPI review on a fixed cadence that the team actually attends and uses.",
                "type": "yesno",
                "weight": 1.2,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "KPIs that aren't reviewed aren't KPIs, they're wallpaper.",
                "opportunity_copy": "A 30-minute weekly KPI review is the cheapest management upgrade available in operations.",
                "recommendation": "Schedule a standing weekly KPI review, 30 minutes, same day and time; start next week.",
            },
            {
                "id": "ops_06",
                "group": "Governance & Risk",
                "text": "No single vendor or supplier represents a concentration risk that would materially damage the business if they disappeared.",
                "type": "yesno",
                "weight": 1.0,
                "reverse": False,
                "allow_na": True,
                "risk_copy": "Concentration risk is cheap until it isn't, and then it's the whole business.",
                "opportunity_copy": "Even a partial second source gives you pricing leverage on the primary.",
                "recommendation": "List your top five vendors; for any that would cripple the business if they disappeared, qualify a backup this quarter.",
            },
            {
                "id": "ops_07",
                "group": "Governance & Risk",
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
                "group": "Performance Metrics",
                "text": "On-time, in-full delivery rate (%)",
                "type": "percent",
                "weight": 1.2,
                "lower_is_better": False,
                "allow_na": True,
                "risk_copy": "Your OTIF rate is below the industry median. At this level, delivery misses are a recurring drag on retention and referrals.",
                "opportunity_copy": "Your OTIF rate is close to industry norms. A focused push toward the 75th percentile would create a measurable retention advantage.",
                "recommendation": "Pull your last 20 missed deliveries, categorize the root causes, and fix the top pattern.",
            },
            {
                "id": "ops_q_mttr_hours",
                "group": "Performance Metrics",
                "text": "Mean time to resolve customer issues (hours)",
                "type": "number",
                "weight": 1.0,
                "lower_is_better": True,
                "allow_na": True,
                "risk_copy": "Long resolution times compound: one slow fix creates three follow-up tickets.",
                "opportunity_copy": "Cutting MTTR often costs nothing: the fix is usually a process bottleneck, not a resource gap.",
                "recommendation": "Pull your last 20 resolved tickets, find the step where they sat longest, and fix that step.",
            },
        ],
    },
]

# ---------------------------------------------------------------------------
# Industry Benchmarks
#
# Keyed by (industry, question_id). Each entry has p25/p50/p75 values.
# Used by app.py to compute percentile-based scores for quantitative
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
    "Construction / Trades", "Real Estate", "Logistics / Distribution",
    "Hospitality / Food Service", "Education / Training", "Other",
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

    # --- Cross-industry defaults for new industries ---
    # These use approximate medians across all sectors above.
    # Personnel
    ("Construction / Trades", "per_q_turnover_pct"):  {"p25": 12, "p50": 20, "p75": 32},
    ("Real Estate", "per_q_turnover_pct"):            {"p25": 8,  "p50": 15, "p75": 25},
    ("Logistics / Distribution", "per_q_turnover_pct"):{"p25":12, "p50": 22, "p75": 35},
    ("Hospitality / Food Service", "per_q_turnover_pct"):{"p25":18,"p50": 30, "p75": 50},
    ("Education / Training", "per_q_turnover_pct"):   {"p25": 8,  "p50": 14, "p75": 24},
    ("Other", "per_q_turnover_pct"):                  {"p25": 10, "p50": 18, "p75": 28},

    ("Construction / Trades", "per_q_days_to_fill"):  {"p25": 20, "p50": 35, "p75": 55},
    ("Real Estate", "per_q_days_to_fill"):            {"p25": 20, "p50": 38, "p75": 60},
    ("Logistics / Distribution", "per_q_days_to_fill"):{"p25":15, "p50": 30, "p75": 50},
    ("Hospitality / Food Service", "per_q_days_to_fill"):{"p25":10,"p50": 22, "p75": 40},
    ("Education / Training", "per_q_days_to_fill"):   {"p25": 25, "p50": 42, "p75": 65},
    ("Other", "per_q_days_to_fill"):                  {"p25": 22, "p50": 38, "p75": 60},

    # Accounting & Finance
    ("Construction / Trades", "fin_q_days_to_close"):  {"p25": 7,  "p50": 12, "p75": 20},
    ("Real Estate", "fin_q_days_to_close"):            {"p25": 5,  "p50": 10, "p75": 18},
    ("Logistics / Distribution", "fin_q_days_to_close"):{"p25": 6, "p50": 10, "p75": 18},
    ("Hospitality / Food Service", "fin_q_days_to_close"):{"p25":5,"p50": 8,  "p75": 15},
    ("Education / Training", "fin_q_days_to_close"):   {"p25": 5,  "p50": 10, "p75": 18},
    ("Other", "fin_q_days_to_close"):                  {"p25": 6,  "p50": 10, "p75": 17},

    ("Construction / Trades", "fin_q_ar_over_60_pct"):  {"p25": 8, "p50": 15, "p75": 28},
    ("Real Estate", "fin_q_ar_over_60_pct"):            {"p25": 5, "p50": 10, "p75": 20},
    ("Logistics / Distribution", "fin_q_ar_over_60_pct"):{"p25":5, "p50": 12, "p75": 22},
    ("Hospitality / Food Service", "fin_q_ar_over_60_pct"):{"p25":2,"p50": 5, "p75": 12},
    ("Education / Training", "fin_q_ar_over_60_pct"):   {"p25": 3, "p50": 8,  "p75": 16},
    ("Other", "fin_q_ar_over_60_pct"):                  {"p25": 4, "p50": 10, "p75": 20},

    # Software Stack
    ("Construction / Trades", "sw_q_num_saas_tools"):  {"p25": 6,  "p50": 12, "p75": 25},
    ("Real Estate", "sw_q_num_saas_tools"):            {"p25": 8,  "p50": 18, "p75": 35},
    ("Logistics / Distribution", "sw_q_num_saas_tools"):{"p25": 8, "p50": 18, "p75": 35},
    ("Hospitality / Food Service", "sw_q_num_saas_tools"):{"p25":6,"p50": 12, "p75": 25},
    ("Education / Training", "sw_q_num_saas_tools"):   {"p25": 8,  "p50": 18, "p75": 35},
    ("Other", "sw_q_num_saas_tools"):                  {"p25": 10, "p50": 20, "p75": 38},

    ("Construction / Trades", "sw_q_software_spend_pct"):  {"p25": 1, "p50": 3,  "p75": 6},
    ("Real Estate", "sw_q_software_spend_pct"):            {"p25": 2, "p50": 5,  "p75": 10},
    ("Logistics / Distribution", "sw_q_software_spend_pct"):{"p25":2,"p50": 4,  "p75": 8},
    ("Hospitality / Food Service", "sw_q_software_spend_pct"):{"p25":1,"p50":3, "p75": 6},
    ("Education / Training", "sw_q_software_spend_pct"):   {"p25": 2, "p50": 5, "p75": 10},
    ("Other", "sw_q_software_spend_pct"):                  {"p25": 2, "p50": 5, "p75": 10},

    # AI Readiness
    ("Construction / Trades", "ai_q_num_ai_workflows"):  {"p25": 0, "p50": 1,  "p75": 3},
    ("Real Estate", "ai_q_num_ai_workflows"):            {"p25": 0, "p50": 2,  "p75": 5},
    ("Logistics / Distribution", "ai_q_num_ai_workflows"):{"p25":0, "p50": 2,  "p75": 5},
    ("Hospitality / Food Service", "ai_q_num_ai_workflows"):{"p25":0,"p50":1,  "p75": 3},
    ("Education / Training", "ai_q_num_ai_workflows"):   {"p25": 0, "p50": 2,  "p75": 4},
    ("Other", "ai_q_num_ai_workflows"):                  {"p25": 1, "p50": 3,  "p75": 6},

    # Sales & Marketing
    ("Construction / Trades", "sal_q_cac"):            {"p25": 200,"p50": 500, "p75": 1200},
    ("Real Estate", "sal_q_cac"):                      {"p25": 300,"p50": 700, "p75": 1800},
    ("Logistics / Distribution", "sal_q_cac"):         {"p25": 150,"p50": 400, "p75": 1000},
    ("Hospitality / Food Service", "sal_q_cac"):       {"p25": 30, "p50": 80,  "p75": 200},
    ("Education / Training", "sal_q_cac"):             {"p25": 200,"p50": 500, "p75": 1200},
    ("Other", "sal_q_cac"):                            {"p25": 200,"p50": 550, "p75": 1400},

    ("Construction / Trades", "sal_q_monthly_churn_pct"):  {"p25": 0.5,"p50":1.5,"p75":3.0},
    ("Real Estate", "sal_q_monthly_churn_pct"):            {"p25": 0.5,"p50":1.5,"p75":3.0},
    ("Logistics / Distribution", "sal_q_monthly_churn_pct"):{"p25":0.5,"p50":1.0,"p75":2.5},
    ("Hospitality / Food Service", "sal_q_monthly_churn_pct"):{"p25":2.0,"p50":4.0,"p75":7.0},
    ("Education / Training", "sal_q_monthly_churn_pct"):   {"p25": 1.0,"p50":2.0,"p75":4.0},
    ("Other", "sal_q_monthly_churn_pct"):                  {"p25": 1.0,"p50":2.5,"p75":4.5},

    # Operations
    ("Construction / Trades", "ops_q_on_time_delivery_pct"):  {"p25": 85,"p50": 92, "p75": 97},
    ("Real Estate", "ops_q_on_time_delivery_pct"):            {"p25": 88,"p50": 94, "p75": 98},
    ("Logistics / Distribution", "ops_q_on_time_delivery_pct"):{"p25":90,"p50":95, "p75":98},
    ("Hospitality / Food Service", "ops_q_on_time_delivery_pct"):{"p25":85,"p50":92,"p75":97},
    ("Education / Training", "ops_q_on_time_delivery_pct"):   {"p25": 90,"p50": 95, "p75": 98},
    ("Other", "ops_q_on_time_delivery_pct"):                  {"p25": 89,"p50": 94, "p75": 98},

    ("Construction / Trades", "ops_q_mttr_hours"):    {"p25": 4,  "p50": 16, "p75": 48},
    ("Real Estate", "ops_q_mttr_hours"):              {"p25": 4,  "p50": 12, "p75": 36},
    ("Logistics / Distribution", "ops_q_mttr_hours"): {"p25": 2,  "p50": 8,  "p75": 24},
    ("Hospitality / Food Service", "ops_q_mttr_hours"):{"p25": 1, "p50": 4,  "p75": 12},
    ("Education / Training", "ops_q_mttr_hours"):     {"p25": 4,  "p50": 12, "p75": 36},
    ("Other", "ops_q_mttr_hours"):                    {"p25": 3,  "p50": 10, "p75": 30},
}
