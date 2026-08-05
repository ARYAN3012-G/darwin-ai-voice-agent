"""
Q2 Knowledge Base — Seed Knowledge Documents
=============================================
A curated set of domain knowledge documents covering:
  - Health Insurance products, policies, and qualification rules
  - Business Loan products, eligibility, and objection handling
  - FAQ and compliance documents

These records are ingested and indexed by the HybridRetriever at startup.
"""

from __future__ import annotations

from .schema import (
    DocumentCategory,
    DocumentStatus,
    DocumentTaxonomy,
    KnowledgeRecord,
    SourceTracking,
)

# ---------------------------------------------------------------------------
# Helper factory to keep record construction concise
# ---------------------------------------------------------------------------

def _make_record(
    title: str,
    content: str,
    summary: str,
    category: DocumentCategory,
    keywords: list[str],
    intent_tags: list[str],
    product_lines: list[str],
    markets: list[str],
    version: str = "1.0.0",
) -> KnowledgeRecord:
    return KnowledgeRecord(
        title=title,
        content=content,
        summary=summary,
        category=category,
        version=version,
        status=DocumentStatus.ACTIVE,
        taxonomy=DocumentTaxonomy(
            primary_category=category,
            product_lines=product_lines,
            markets=markets,
            keywords=keywords,
            intent_tags=intent_tags,
        ),
        source=SourceTracking(
            source_system="knowledge_seed_v1",
            source_file="knowledge_data.py",
        ),
    )


# ---------------------------------------------------------------------------
# Health Insurance — Products
# ---------------------------------------------------------------------------

_hi_comprehensive = _make_record(
    title="Comprehensive Health Insurance — Product Overview",
    content="""
Comprehensive Health Insurance provides end-to-end medical coverage for individuals and families.

Key Benefits:
- Inpatient hospitalization: up to PHP 1,000,000 per year
- Outpatient consultations: up to 12 visits per year at accredited clinics
- Emergency care: 100% coverage including ambulance services
- Prescription medicine: up to PHP 50,000 per year
- Specialist referrals: covered with valid GP referral
- Mental health support: up to 6 counseling sessions per year

Optional Riders:
- Critical Illness Rider: lump-sum payout upon diagnosis of major illness
- Maternity Rider: covers normal delivery (PHP 30,000) and CS delivery (PHP 50,000)
- Dental & Vision Rider: basic dental cleaning, extraction, and eyewear allowance

Premium Computation:
Base premium is calculated on insured age, sum assured, and selected riders.
Typical annual premium range: PHP 8,000 to PHP 45,000 depending on coverage level.

Waiting Period:
A 30-day waiting period applies from the policy effective date for illness-related claims.
Accidents are covered from Day 1.
""",
    summary="Comprehensive health insurance with inpatient, outpatient, emergency, and optional rider coverage. Annual premiums PHP 8,000–PHP 45,000.",
    category=DocumentCategory.PRODUCT,
    keywords=[
        "health insurance", "comprehensive", "hospitalization", "outpatient",
        "emergency", "prescription", "rider", "critical illness", "maternity",
        "premium", "coverage", "waiting period",
    ],
    intent_tags=["product_inquiry", "coverage_question", "benefit_explanation"],
    product_lines=["Health Insurance"],
    markets=["PH", "global"],
)

_hi_hmo = _make_record(
    title="HMO Health Maintenance Organization — Plan Comparison",
    content="""
HMO (Health Maintenance Organization) plans provide managed care through a network of accredited doctors and hospitals.

Plan Tiers:
1. Basic HMO Plan — Annual Benefit Limit (ABL): PHP 100,000
   - Inpatient room & board: Standard room
   - Outpatient: 3 visits/year
   - No dental coverage
   - Premium: PHP 6,000/year

2. Standard HMO Plan — ABL: PHP 200,000
   - Inpatient: Semi-private room
   - Outpatient: 6 visits/year
   - Basic dental: cleaning only
   - Premium: PHP 12,000/year

3. Executive HMO Plan — ABL: PHP 500,000
   - Inpatient: Private room
   - Outpatient: Unlimited GP visits
   - Dental & Vision included
   - Annual physical examination
   - Premium: PHP 25,000/year

Network Coverage:
Over 1,200 accredited hospitals and 3,500 clinics nationwide (Philippines).

Pre-authorization Requirements:
All scheduled admissions require pre-authorization 24 hours in advance.
Emergency admissions must be notified within 24 hours.
""",
    summary="HMO plans from Basic (PHP 100K ABL) to Executive (PHP 500K ABL) with tiered premiums PHP 6,000–PHP 25,000.",
    category=DocumentCategory.PRODUCT,
    keywords=[
        "HMO", "health maintenance", "annual benefit limit", "ABL", "inpatient",
        "outpatient", "dental", "vision", "network", "pre-authorization", "room and board",
    ],
    intent_tags=["product_inquiry", "plan_comparison", "benefit_explanation"],
    product_lines=["HMO", "Health Insurance"],
    markets=["PH"],
)

# ---------------------------------------------------------------------------
# Health Insurance — Policy & Qualification Rules
# ---------------------------------------------------------------------------

_hi_eligibility = _make_record(
    title="Health Insurance Eligibility and Underwriting Rules",
    content="""
Eligibility Criteria for Health Insurance:

Age Limits:
- Minimum entry age: 1 year (children covered under family plan)
- Maximum entry age: 65 years old
- Renewability: Plans are renewable up to age 75

Pre-existing Conditions Policy:
- Pre-existing conditions diagnosed within 2 years before application require declaration
- Standard exclusion period: 12 months for declared pre-existing conditions
- Conditions undisclosed at application are permanently excluded from coverage
- Diabetes, hypertension, and heart conditions require medical underwriting
- BMI > 40 may result in premium loading of 15–30%

Medical Examination Requirements:
- Age 18–45, sum assured < PHP 500,000: No medical exam required (non-medical limit)
- Age 46–55, any sum assured: Basic medical exam (CBC, urinalysis, ECG)
- Age 56–65, any sum assured: Full medical exam including chest X-ray and stress test
- History of cancer or major surgery: Full medical exam regardless of age

Waiting Periods:
- All illnesses: 30 days from effective date
- Congenital conditions: Excluded
- Pre-existing conditions: 12 months (if declared and approved)

Disqualifying Conditions (non-insurable):
- Active cancer under treatment
- End-stage renal disease
- HIV/AIDS
- Organ transplant recipients (within 5 years)
""",
    summary="Health insurance eligibility: ages 1–65, renewable to 75. Pre-existing conditions require declaration; 12-month exclusion period applies.",
    category=DocumentCategory.QUALIFICATION,
    keywords=[
        "eligibility", "underwriting", "age limit", "pre-existing condition",
        "medical exam", "waiting period", "BMI", "exclusion", "disqualifying",
        "non-medical limit", "renewability",
    ],
    intent_tags=["qualification", "eligibility_check", "underwriting_inquiry"],
    product_lines=["Health Insurance", "HMO"],
    markets=["PH", "global"],
)

_hi_faq = _make_record(
    title="Health Insurance — Frequently Asked Questions",
    content="""
Q: What is the difference between HMO and traditional health insurance?
A: HMO uses a managed network of providers (you must see accredited doctors). Traditional health insurance allows you to choose any licensed physician, giving more flexibility.

Q: Can I add my dependents to my health plan?
A: Yes. You may add a legal spouse and unmarried children up to age 21 (25 if full-time students). Each dependent requires a separate enrollment form.

Q: What happens if I get sick during the 30-day waiting period?
A: Illness-related claims during the waiting period are not covered. Accidents are covered from Day 1 of the policy.

Q: How do I file a claim for outpatient consultations?
A: Present your insurance ID card at any accredited clinic. For reimbursement, submit official receipts, medical records, and the completed claim form within 30 days of treatment.

Q: What is a pre-existing condition?
A: Any illness, injury, or condition that existed before the policy effective date, whether diagnosed, treated, or showing symptoms.

Q: Can I upgrade my plan mid-year?
A: Plan upgrades are allowed at renewal (anniversary date). Mid-year upgrades may be requested with medical underwriting approval.

Q: Is pregnancy covered under health insurance?
A: Pregnancy is typically excluded unless you have the Maternity Rider. Normal delivery: PHP 30,000 benefit. CS delivery: PHP 50,000 benefit.

Q: How do I cancel my policy?
A: Submit a written cancellation request at least 30 days before the next renewal date. Refund (if any) is pro-rated after deducting used benefits.
""",
    summary="FAQ covering HMO vs traditional insurance, dependent enrollment, waiting periods, claims, pre-existing conditions, upgrades, and cancellations.",
    category=DocumentCategory.FAQ,
    keywords=[
        "FAQ", "HMO", "dependent", "waiting period", "claim", "pre-existing",
        "outpatient", "upgrade", "cancellation", "pregnancy", "maternity",
    ],
    intent_tags=["faq", "customer_inquiry", "claim_process", "policy_explanation"],
    product_lines=["Health Insurance", "HMO"],
    markets=["PH", "global"],
)

_hi_objections = _make_record(
    title="Health Insurance — Common Objections and Recommended Responses",
    content="""
Objection: "It's too expensive. I can't afford the premium."
Response: "I completely understand your concern about cost. Let me show you our tiered plans — our Basic HMO starts at PHP 6,000 per year, which works out to just PHP 500 per month. Compare this to a single hospital admission that can cost PHP 50,000–PHP 200,000 without coverage. Would you like me to calculate how much a customized plan would cost based on your specific needs?"

Objection: "I'm healthy now. I don't need insurance."
Response: "That's a great position to be in! In fact, the best time to get health insurance is when you're healthy — premiums are lower, pre-existing conditions haven't developed yet, and you avoid the waiting periods. Many of our clients regret not getting covered sooner when an unexpected illness occurred."

Objection: "My company already provides HMO. Why do I need additional coverage?"
Response: "Company HMO typically has limited coverage — usually PHP 100,000 to PHP 200,000 which may not be enough for serious illness. It also doesn't follow you if you resign or are laid off. A personal health plan provides continuity of coverage regardless of your employment status."

Objection: "I had a pre-existing condition. They'll probably reject me."
Response: "Not necessarily. We have special programs for applicants with pre-existing conditions. Some conditions are approved with a 12-month exclusion period or a small premium loading. Let me walk you through our process — there's no commitment required just to apply."

Objection: "I need to think about it."
Response: "Of course, this is an important decision. May I ask what specific concern is making you hesitate? Is it the cost, the coverage, or something else? I'd love to address any questions before you decide."

Objection: "Can you just send me a brochure?"
Response: "Absolutely, I'll send that right away. May I also schedule a quick follow-up call in 2 days to answer any questions after you've reviewed it? This way you'll have all the information you need to make the best decision."
""",
    summary="Six common health insurance objections with recommended agent responses covering cost, health status, existing company HMO, pre-existing conditions, hesitation, and information requests.",
    category=DocumentCategory.OBJECTION,
    keywords=[
        "objection", "too expensive", "healthy", "company HMO", "pre-existing",
        "think about it", "brochure", "rejection", "response", "handling",
    ],
    intent_tags=["objection_handling", "sales", "agent_guide"],
    product_lines=["Health Insurance", "HMO"],
    markets=["PH", "global"],
)

# ---------------------------------------------------------------------------
# Business Loans — Products
# ---------------------------------------------------------------------------

_loan_sme = _make_record(
    title="SME Business Loan — Product Features and Terms",
    content="""
SME Business Loan provides flexible financing for small-to-medium enterprises.

Loan Parameters:
- Loan Amount: PHP 500,000 to PHP 10,000,000
- Loan Tenor: 12 months to 60 months (1 to 5 years)
- Interest Rate: 1.25% to 1.75% per month (declining balance method)
- Processing Fee: 1.5% of loan amount (deducted upfront)
- Annual Penalty Rate: 3% per annum on overdue principal

Eligible Business Types:
- Sole proprietorships, partnerships, and corporations
- Retail, trading, manufacturing, and service businesses
- Minimum operating history: 2 years

Required Documentation:
- Duly accomplished loan application form
- Latest 2 years audited financial statements (or 3 years BIR-filed ITR for sole props)
- Bank statements: last 6 months (all business accounts)
- Government-issued IDs (2 valid IDs) of all owners/signatories
- DTI/SEC/CDA registration certificate
- Mayor's Permit / Business Permit (current year)
- Collateral documents (for secured loans):
  - Land title (Transfer Certificate of Title — TCT) or Condominium Certificate of Title (CCT)
  - Latest real property tax declaration and tax clearance
  - Latest tax payment receipt

Collateral Requirements:
- Loans above PHP 2,000,000 typically require real estate collateral
- Appraised value must be at least 125% of loan amount
- Collateral may be existing or newly purchased property

Unsecured Loans:
- Available up to PHP 2,000,000 for businesses with strong financials
- Requires average monthly sales of at least PHP 200,000
- No active adverse credit history in the last 3 years
""",
    summary="SME Business Loans PHP 500K–PHP 10M, 1–5 year tenor, 1.25–1.75% monthly declining interest. Requires 2 years operating history and supporting financial documents.",
    category=DocumentCategory.PRODUCT,
    keywords=[
        "SME", "business loan", "loan amount", "tenor", "interest rate",
        "processing fee", "collateral", "unsecured", "financial statements",
        "bank statements", "DTI", "SEC", "mayor's permit",
    ],
    intent_tags=["product_inquiry", "loan_features", "document_requirements"],
    product_lines=["Business Loans", "SME Loans"],
    markets=["PH"],
)

_loan_qualification = _make_record(
    title="Business Loan Qualification Criteria and Credit Assessment",
    content="""
Credit Assessment Framework for Business Loans:

5-C Framework:
1. Character: Credit history, payment behavior, business reputation
2. Capacity: Ability to repay — Debt Service Coverage Ratio (DSCR) >= 1.2
3. Capital: Net worth and equity of the business (minimum 30% equity ratio)
4. Collateral: Security offered to mitigate credit risk
5. Conditions: Purpose of loan and economic/industry conditions

Key Financial Ratios Evaluated:
- Debt Service Coverage Ratio (DSCR): Net Operating Income / Total Debt Service >= 1.2
- Current Ratio: Current Assets / Current Liabilities >= 1.0
- Net Profit Margin: >= 5% for the latest fiscal year
- Leverage Ratio: Total Debt / Total Equity <= 2.5

Disqualifying Criteria:
- Delinquent accounts or defaults in the last 5 years (any lending institution)
- Business with negative net worth
- Business operating for less than 2 years
- Industry on the negative list (gambling, illegal activities, etc.)
- Court-filed cases involving fraud or financial crimes

Ideal Borrower Profile:
- Business age: 3+ years
- Monthly revenue: PHP 300,000+
- DSCR >= 1.5 (strong repayment capacity)
- Clean credit history (no past-due in last 3 years)
- Existing relationship with the bank/lender preferred

Loan Amount Benchmarks:
- Maximum loan = 10x average monthly net income (last 12 months)
- Alternative: Maximum loan = 70% of appraised collateral value (whichever is lower)
""",
    summary="Business loan qualification using the 5-C framework: Character, Capacity (DSCR ≥ 1.2), Capital, Collateral, Conditions. Disqualifiers include defaults in past 5 years.",
    category=DocumentCategory.QUALIFICATION,
    keywords=[
        "5C", "character", "capacity", "DSCR", "debt service coverage",
        "capital", "collateral", "conditions", "credit assessment",
        "disqualifying", "net worth", "leverage ratio", "current ratio",
    ],
    intent_tags=["qualification", "credit_assessment", "eligibility_check"],
    product_lines=["Business Loans", "SME Loans"],
    markets=["PH"],
)

_loan_faq = _make_record(
    title="Business Loan — Frequently Asked Questions",
    content="""
Q: How long does the business loan application process take?
A: Initial assessment takes 3–5 business days after complete document submission. Full approval and release: 10–15 business days.

Q: What is the minimum and maximum loan I can apply for?
A: Minimum is PHP 500,000. Maximum is PHP 10,000,000 for SME loans (higher amounts go through corporate banking).

Q: Can a startup apply for a business loan?
A: Startups (less than 2 years operating) generally do not qualify for standard SME loans. We have a Startup Loan Program for businesses 1–2 years old with strong business plan and sponsors.

Q: Is collateral always required?
A: No. Unsecured loans up to PHP 2,000,000 are available for businesses with strong financials and clean credit history.

Q: What interest rate should I expect?
A: Interest rates range from 1.25% to 1.75% per month on a declining balance basis, depending on your credit profile and loan tenor.

Q: Can I prepay my loan early?
A: Yes. Prepayment is allowed with no penalty after the 6th month of the loan. Early prepayment before month 6 carries a 2% prepayment fee on outstanding principal.

Q: What happens if I miss a payment?
A: A late payment fee of 3% per annum is charged on overdue principal. Three consecutive missed payments may trigger loan restructuring or legal action.

Q: Can I apply jointly with my business partner?
A: Yes. Joint applications are accepted with all co-borrowers signing the loan agreement. All co-borrowers' credit histories will be evaluated.
""",
    summary="Business loan FAQ: application timeline (10–15 days), loan range PHP 500K–PHP 10M, startup eligibility, collateral requirements, interest rates, prepayment, missed payments.",
    category=DocumentCategory.FAQ,
    keywords=[
        "FAQ", "loan application", "timeline", "minimum loan", "startup",
        "collateral", "interest rate", "prepayment", "missed payment",
        "co-borrower", "joint application",
    ],
    intent_tags=["faq", "customer_inquiry", "loan_process", "eligibility"],
    product_lines=["Business Loans", "SME Loans"],
    markets=["PH"],
)

_loan_objections = _make_record(
    title="Business Loan — Common Objections and Agent Responses",
    content="""
Objection: "The interest rate is too high."
Response: "I understand your concern. Our rate of 1.25% to 1.75% per month is competitive within the market. More importantly, it's calculated on a declining balance — meaning each month your interest decreases as you pay down principal. Would you like me to generate an amortization schedule so you can see the exact monthly cost against the business income you're expecting?"

Objection: "The documentary requirements are too many."
Response: "I hear you — it can feel overwhelming. But these documents protect you too, ensuring your loan is properly structured and compliant. Let me help you create a document checklist and identify which ones you may already have on hand. Many clients find it takes less than a week to compile everything."

Objection: "My business has only been running for 18 months."
Response: "Thank you for being upfront about that. While our standard SME loan requires 2 years of operating history, we do have a Startup Business Loan program for businesses between 1 and 2 years old. Requirements include a business plan, 6-month bank statements, and a guarantor. Would you like me to explain the details?"

Objection: "I had a late payment on my credit card 2 years ago. Will that disqualify me?"
Response: "A single late credit card payment 2 years ago is unlikely to disqualify you — we look at the overall pattern of your credit behavior. What matters more is whether you have any active delinquencies or defaults. I'd recommend we proceed with the pre-qualification assessment to get a clearer picture."

Objection: "I don't have collateral."
Response: "That's not a blocker. For loan amounts up to PHP 2,000,000, we offer unsecured business loans based on your cash flow and credit profile. You don't need to pledge any property. Shall we review your average monthly revenue to see what you'd qualify for?"
""",
    summary="Five common business loan objections with agent responses covering high interest, documents, startup age, credit history, and no collateral.",
    category=DocumentCategory.OBJECTION,
    keywords=[
        "objection", "interest rate", "documentary requirements", "startup",
        "credit history", "collateral", "declining balance", "unsecured",
        "pre-qualification", "response", "handling",
    ],
    intent_tags=["objection_handling", "sales", "agent_guide"],
    product_lines=["Business Loans", "SME Loans"],
    markets=["PH"],
)

_compliance = _make_record(
    title="Agent Compliance and Disclosure Requirements",
    content="""
Mandatory Disclosures Before Closing Any Sale:

For Health Insurance:
1. Policy Exclusions: Agent must verbally state the three most material exclusions (pre-existing conditions, waiting period, out-of-network charges).
2. Premium Payment: Confirm annual, semi-annual, or monthly payment schedule and grace period (30 days).
3. Free Look Period: Customer has 15 days from policy receipt to return for full refund.
4. Cancellation Terms: Pro-rated refund after free look period, minus used benefits.
5. Claims Procedure: Explain how to file a claim (hotline number, online portal, branch).

For Business Loans:
1. Effective Interest Rate (EIR): Must be disclosed in writing. EIR is different from nominal rate.
2. Total Cost of Credit: Total interest, fees, and charges over the full loan term.
3. Right to Prepayment: Inform borrower of prepayment rights and any applicable fees.
4. Penalty Terms: Clearly explain late payment fees (3% p.a.) and consequences of default.
5. Collateral Rights: Explain lender's right to foreclose in case of prolonged default.

Escalation Requirements:
- Escalate to supervisor if customer requests complaint filing.
- Escalate immediately if customer expresses threat of harm to self or others.
- Escalate if customer mentions legal counsel or regulatory complaint.
- Never promise something outside your authority to deliver.

Do Not Do (Prohibited Actions):
- Misrepresent product benefits or downplay exclusions.
- Pressure customers using false urgency or misleading scarcity tactics.
- Collect personal information beyond what is required for application.
- Record any call without customer's explicit consent (where required by law).
""",
    summary="Mandatory compliance disclosures for agents covering health insurance (free look, exclusions, claims) and business loans (EIR, total cost, prepayment, penalties, collateral). Escalation triggers included.",
    category=DocumentCategory.COMPLIANCE,
    keywords=[
        "compliance", "disclosure", "exclusion", "free look", "EIR",
        "effective interest rate", "total cost of credit", "escalation",
        "penalty", "cancellation", "collateral", "agent rules",
    ],
    intent_tags=["compliance", "agent_guide", "escalation", "disclosure"],
    product_lines=["Health Insurance", "Business Loans"],
    markets=["PH", "global"],
)

# ---------------------------------------------------------------------------
# Exported collection
# ---------------------------------------------------------------------------

KNOWLEDGE_DOCUMENTS: list[KnowledgeRecord] = [
    _hi_comprehensive,
    _hi_hmo,
    _hi_eligibility,
    _hi_faq,
    _hi_objections,
    _loan_sme,
    _loan_qualification,
    _loan_faq,
    _loan_objections,
    _compliance,
]
