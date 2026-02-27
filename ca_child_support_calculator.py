"""
California Child Support Calculator
Based on California Family Code §§ 4050-4076

Implements the statewide uniform guideline formula:
    CS = K[HN - (H%)(TN)]

Where:
    CS  = Child support amount
    K   = Amount of both parents' income allocated for child support
    HN  = High earner's net monthly disposable income
    H%  = Approximate percentage of time the high earner has primary
          physical responsibility for the children
    TN  = Total net monthly disposable income of both parents

References:
    - CA Family Code § 4055: Guideline formula
    - CA Family Code § 4058: Annual gross income
    - CA Family Code § 4059: Annual net disposable income deductions
    - CA Family Code § 4060: Net disposable income computation
    - CA Family Code § 4062: Additional child support (add-ons)
    - CA Family Code § 4070-4073: Hardship deductions
"""

import math

# ---------------------------------------------------------------------------
# Tax Tables (2025 Tax Year)
# ---------------------------------------------------------------------------

# Federal income tax brackets - Single
FEDERAL_BRACKETS_SINGLE = [
    (11_925, 0.10),
    (48_475, 0.12),
    (103_350, 0.22),
    (197_300, 0.24),
    (250_525, 0.32),
    (626_350, 0.35),
    (float("inf"), 0.37),
]

# Federal income tax brackets - Married Filing Jointly
FEDERAL_BRACKETS_MFJ = [
    (23_850, 0.10),
    (96_950, 0.12),
    (206_700, 0.22),
    (394_600, 0.24),
    (501_050, 0.32),
    (751_600, 0.35),
    (float("inf"), 0.37),
]

# Federal income tax brackets - Head of Household
FEDERAL_BRACKETS_HOH = [
    (17_000, 0.10),
    (64_850, 0.12),
    (103_350, 0.22),
    (197_300, 0.24),
    (250_500, 0.32),
    (626_350, 0.35),
    (float("inf"), 0.37),
]

# Federal standard deductions (2025)
FEDERAL_STD_DEDUCTION = {
    "Single": 15_000,
    "Married Filing Jointly": 30_000,
    "Head of Household": 22_500,
}

# California state income tax brackets - Single / Married Filing Separately
CA_BRACKETS_SINGLE = [
    (10_756, 0.01),
    (25_499, 0.02),
    (40_245, 0.04),
    (55_866, 0.06),
    (70_606, 0.08),
    (360_659, 0.093),
    (432_787, 0.103),
    (721_314, 0.113),
    (1_000_000, 0.123),
    (float("inf"), 0.133),  # includes 1% Mental Health Services Tax
]

# California state income tax brackets - Married Filing Jointly
CA_BRACKETS_MFJ = [
    (21_512, 0.01),
    (50_998, 0.02),
    (80_490, 0.04),
    (111_732, 0.06),
    (141_212, 0.08),
    (721_318, 0.093),
    (865_574, 0.103),
    (1_000_000, 0.113),
    (1_442_628, 0.123),
    (float("inf"), 0.133),
]

# California state income tax brackets - Head of Household
CA_BRACKETS_HOH = [
    (21_527, 0.01),
    (51_000, 0.02),
    (65_744, 0.04),
    (81_364, 0.06),
    (96_107, 0.08),
    (490_493, 0.093),
    (588_593, 0.103),
    (980_987, 0.113),
    (1_000_000, 0.123),
    (float("inf"), 0.133),
]

# California standard deduction (2025)
CA_STD_DEDUCTION = {
    "Single": 5_540,
    "Married Filing Jointly": 11_080,
    "Head of Household": 11_080,
}

# California exemption credit (2025)
CA_EXEMPTION_CREDIT = 144  # per exemption

# FICA rates (2025)
SS_RATE = 0.062
SS_WAGE_BASE = 176_100
MEDICARE_RATE = 0.0145
MEDICARE_ADDITIONAL_RATE = 0.009  # on wages over $200k (single)
MEDICARE_ADDITIONAL_THRESHOLD_SINGLE = 200_000
MEDICARE_ADDITIONAL_THRESHOLD_MFJ = 250_000

# California State Disability Insurance (2025)
CA_SDI_RATE = 0.012  # 1.2%, no wage cap since 2024

# K-factor fractions by number of children (CA Family Code § 4055(b)(1))
K_FRACTIONS = {
    1: 0.20,
    2: 0.275,
    3: 0.34,
    4: 0.355,
    5: 0.37,
}

# For 6+ children: add 0.005 per additional child (approximate)
def get_k_fraction(num_children: int) -> float:
    """Get the K-factor fraction based on number of children per § 4055(b)(1)."""
    if num_children <= 0:
        return 0.0
    if num_children <= 5:
        return K_FRACTIONS[num_children]
    # 6+ children: court discretion, approximate continued increase
    return 0.37 + (num_children - 5) * 0.005


# ---------------------------------------------------------------------------
# Tax & Deduction Calculators
# ---------------------------------------------------------------------------

def calc_progressive_tax(annual_income: float, brackets: list) -> float:
    """Calculate tax using progressive brackets."""
    tax = 0.0
    prev_limit = 0
    for limit, rate in brackets:
        if annual_income <= prev_limit:
            break
        taxable = min(annual_income, limit) - prev_limit
        tax += taxable * rate
        prev_limit = limit
    return tax


def calc_federal_tax(annual_gross: float, filing_status: str,
                     num_dependents: int = 0) -> float:
    """Estimate annual federal income tax."""
    brackets_map = {
        "Single": FEDERAL_BRACKETS_SINGLE,
        "Married Filing Jointly": FEDERAL_BRACKETS_MFJ,
        "Head of Household": FEDERAL_BRACKETS_HOH,
    }
    brackets = brackets_map[filing_status]
    std_deduction = FEDERAL_STD_DEDUCTION[filing_status]

    taxable_income = max(0, annual_gross - std_deduction)
    tax = calc_progressive_tax(taxable_income, brackets)

    # Child tax credit ($2,000 per qualifying child under 17)
    child_credit = min(tax, num_dependents * 2_000)
    tax -= child_credit

    return max(0, tax)


def calc_ca_state_tax(annual_gross: float, filing_status: str,
                      num_exemptions: int = 1) -> float:
    """Estimate annual California state income tax."""
    brackets_map = {
        "Single": CA_BRACKETS_SINGLE,
        "Married Filing Jointly": CA_BRACKETS_MFJ,
        "Head of Household": CA_BRACKETS_HOH,
    }
    brackets = brackets_map[filing_status]
    std_deduction = CA_STD_DEDUCTION[filing_status]

    taxable_income = max(0, annual_gross - std_deduction)
    tax = calc_progressive_tax(taxable_income, brackets)

    # Apply exemption credits
    tax -= num_exemptions * CA_EXEMPTION_CREDIT

    return max(0, tax)


def calc_fica(annual_gross: float, filing_status: str) -> float:
    """Calculate annual FICA (Social Security + Medicare) taxes."""
    ss_tax = min(annual_gross, SS_WAGE_BASE) * SS_RATE
    medicare_tax = annual_gross * MEDICARE_RATE

    # Additional Medicare tax
    threshold = (MEDICARE_ADDITIONAL_THRESHOLD_MFJ
                 if filing_status == "Married Filing Jointly"
                 else MEDICARE_ADDITIONAL_THRESHOLD_SINGLE)
    if annual_gross > threshold:
        medicare_tax += (annual_gross - threshold) * MEDICARE_ADDITIONAL_RATE

    return ss_tax + medicare_tax


def calc_ca_sdi(annual_gross: float) -> float:
    """Calculate California State Disability Insurance."""
    return annual_gross * CA_SDI_RATE


def calc_net_monthly_disposable_income(
    monthly_gross: float,
    filing_status: str,
    num_tax_exemptions: int,
    num_dependents_for_credits: int,
    monthly_health_insurance: float = 0,
    monthly_mandatory_retirement: float = 0,
    monthly_union_dues: float = 0,
    monthly_hardship_deduction: float = 0,
    monthly_other_child_support: float = 0,
    use_custom_taxes: bool = False,
    custom_monthly_federal_tax: float = 0,
    custom_monthly_state_tax: float = 0,
    custom_monthly_fica: float = 0,
    custom_monthly_sdi: float = 0,
) -> dict:
    """
    Calculate Net Monthly Disposable Income per CA Family Code § 4059-4060.

    Returns a dict with a breakdown of all deductions and the final NMDI.
    """
    annual_gross = monthly_gross * 12

    if use_custom_taxes:
        federal_tax = custom_monthly_federal_tax
        state_tax = custom_monthly_state_tax
        fica = custom_monthly_fica
        sdi = custom_monthly_sdi
    else:
        federal_tax = calc_federal_tax(
            annual_gross, filing_status, num_dependents_for_credits
        ) / 12
        state_tax = calc_ca_state_tax(
            annual_gross, filing_status, num_tax_exemptions
        ) / 12
        fica = calc_fica(annual_gross, filing_status) / 12
        sdi = calc_ca_sdi(annual_gross) / 12

    total_deductions = (
        federal_tax
        + state_tax
        + fica
        + sdi
        + monthly_health_insurance
        + monthly_mandatory_retirement
        + monthly_union_dues
        + monthly_hardship_deduction
        + monthly_other_child_support
    )

    nmdi = monthly_gross - total_deductions

    return {
        "monthly_gross": monthly_gross,
        "federal_tax": federal_tax,
        "state_tax": state_tax,
        "fica": fica,
        "sdi": sdi,
        "health_insurance": monthly_health_insurance,
        "mandatory_retirement": monthly_mandatory_retirement,
        "union_dues": monthly_union_dues,
        "hardship_deduction": monthly_hardship_deduction,
        "other_child_support": monthly_other_child_support,
        "total_deductions": total_deductions,
        "net_monthly_disposable_income": nmdi,
    }


# ---------------------------------------------------------------------------
# Child Support Formula (CA Family Code § 4055)
# ---------------------------------------------------------------------------

def calc_child_support(
    parent_a_nmdi: float,
    parent_b_nmdi: float,
    num_children: int,
    parent_a_timeshare_pct: float,  # percentage of time Parent A has children (0-100)
) -> dict:
    """
    Calculate guideline child support using CA Family Code § 4055.

    CS = K[HN - (H%)(TN)]

    Parameters:
        parent_a_nmdi: Parent A's net monthly disposable income
        parent_b_nmdi: Parent B's net monthly disposable income
        num_children: Number of children
        parent_a_timeshare_pct: % of time Parent A has the children (0-100)

    Returns:
        Dict with full calculation breakdown
    """
    tn = parent_a_nmdi + parent_b_nmdi  # Total Net

    # Determine high earner
    if parent_a_nmdi >= parent_b_nmdi:
        hn = parent_a_nmdi
        high_earner = "Parent A (higher earner)"
        # H% = time the HIGH earner has the children
        h_pct = parent_a_timeshare_pct / 100.0
    else:
        hn = parent_b_nmdi
        high_earner = "Parent B (higher earner)"
        h_pct = (100 - parent_a_timeshare_pct) / 100.0

    # Calculate K factor per § 4055(b)
    fraction = get_k_fraction(num_children)

    if h_pct <= 0.50:
        k = (1 + h_pct) * fraction
    else:
        k = (2 - h_pct) * fraction

    # Guideline child support
    cs = k * (hn - (h_pct * tn))

    # Determine who pays whom
    if parent_a_nmdi >= parent_b_nmdi:
        # Parent A is the high earner
        if cs >= 0:
            payer = "Parent A"
            payee = "Parent B"
        else:
            payer = "Parent B"
            payee = "Parent A"
            cs = abs(cs)
    else:
        # Parent B is the high earner
        if cs >= 0:
            payer = "Parent B"
            payee = "Parent A"
        else:
            payer = "Parent A"
            payee = "Parent B"
            cs = abs(cs)

    return {
        "child_support": round(cs, 2),
        "payer": payer,
        "payee": payee,
        "high_earner": high_earner,
        "tn": tn,
        "hn": hn,
        "h_pct": h_pct,
        "k_factor": k,
        "fraction": fraction,
        "num_children": num_children,
    }


def calc_addons(
    parent_a_nmdi: float,
    parent_b_nmdi: float,
    childcare_costs: float = 0,
    uninsured_healthcare: float = 0,
    education_costs: float = 0,
    travel_costs: float = 0,
) -> dict:
    """
    Calculate add-on expenses per CA Family Code § 4062.

    Add-ons are split in proportion to each parent's share of total net income.
    """
    total_addons = (
        childcare_costs + uninsured_healthcare + education_costs + travel_costs
    )

    tn = parent_a_nmdi + parent_b_nmdi
    if tn > 0:
        parent_a_share_pct = parent_a_nmdi / tn
        parent_b_share_pct = parent_b_nmdi / tn
    else:
        parent_a_share_pct = 0.50
        parent_b_share_pct = 0.50

    return {
        "childcare_costs": childcare_costs,
        "uninsured_healthcare": uninsured_healthcare,
        "education_costs": education_costs,
        "travel_costs": travel_costs,
        "total_addons": total_addons,
        "parent_a_share_pct": parent_a_share_pct,
        "parent_b_share_pct": parent_b_share_pct,
        "parent_a_addon_amount": total_addons * parent_a_share_pct,
        "parent_b_addon_amount": total_addons * parent_b_share_pct,
    }


# ---------------------------------------------------------------------------
# Streamlit UI (imported lazily so the core logic can be tested standalone)
# ---------------------------------------------------------------------------

def format_currency(amount: float) -> str:
    """Format a number as currency."""
    if amount < 0:
        return f"-${abs(amount):,.2f}"
    return f"${amount:,.2f}"


def format_pct(pct: float) -> str:
    """Format a decimal as a percentage."""
    return f"{pct * 100:.1f}%"


def render_income_section(parent_label: str, key_prefix: str) -> dict:
    """Render the income input section for one parent."""
    import streamlit as st
    st.subheader(f"{parent_label}")

    monthly_gross = st.number_input(
        "Monthly Gross Income",
        min_value=0.0,
        max_value=500_000.0,
        value=0.0,
        step=100.0,
        key=f"{key_prefix}_gross",
        help="Total monthly income from all sources before taxes "
             "(employment, self-employment, rental, investments, etc.) "
             "per CA Family Code § 4058",
    )

    filing_status = st.selectbox(
        "Tax Filing Status",
        ["Single", "Head of Household", "Married Filing Jointly"],
        key=f"{key_prefix}_filing",
        help="Federal and state tax filing status",
    )

    col1, col2 = st.columns(2)
    with col1:
        num_tax_exemptions = st.number_input(
            "CA Tax Exemptions",
            min_value=1,
            max_value=20,
            value=1,
            key=f"{key_prefix}_exemptions",
            help="Number of California tax exemptions claimed",
        )
    with col2:
        num_dependents = st.number_input(
            "Federal Dependent Credits",
            min_value=0,
            max_value=20,
            value=0,
            key=f"{key_prefix}_dependents",
            help="Number of dependents for federal child tax credit",
        )

    use_custom = st.checkbox(
        "Enter actual tax withholdings instead of estimates",
        key=f"{key_prefix}_custom_taxes",
        help="Check this to enter your actual monthly tax withholdings "
             "rather than using the calculator's estimates",
    )

    custom_federal = 0.0
    custom_state = 0.0
    custom_fica = 0.0
    custom_sdi = 0.0

    if use_custom:
        col1, col2 = st.columns(2)
        with col1:
            custom_federal = st.number_input(
                "Monthly Federal Tax",
                min_value=0.0, value=0.0, step=50.0,
                key=f"{key_prefix}_fed_tax",
            )
            custom_fica = st.number_input(
                "Monthly FICA (SS + Medicare)",
                min_value=0.0, value=0.0, step=50.0,
                key=f"{key_prefix}_fica",
            )
        with col2:
            custom_state = st.number_input(
                "Monthly CA State Tax",
                min_value=0.0, value=0.0, step=50.0,
                key=f"{key_prefix}_state_tax",
            )
            custom_sdi = st.number_input(
                "Monthly CA SDI",
                min_value=0.0, value=0.0, step=10.0,
                key=f"{key_prefix}_sdi",
            )

    with st.expander("Additional Deductions (§ 4059)"):
        health_insurance = st.number_input(
            "Monthly Health Insurance (parent only)",
            min_value=0.0, value=0.0, step=25.0,
            key=f"{key_prefix}_health",
            help="Health insurance premiums for the parent (not children)",
        )
        mandatory_retirement = st.number_input(
            "Monthly Mandatory Retirement Contributions",
            min_value=0.0, value=0.0, step=25.0,
            key=f"{key_prefix}_retirement",
            help="Required retirement contributions (not voluntary 401k)",
        )
        union_dues = st.number_input(
            "Monthly Union Dues",
            min_value=0.0, value=0.0, step=10.0,
            key=f"{key_prefix}_union",
            help="Mandatory union dues",
        )
        hardship = st.number_input(
            "Monthly Hardship Deduction (§ 4070-4073)",
            min_value=0.0, value=0.0, step=25.0,
            key=f"{key_prefix}_hardship",
            help="Extraordinary health expenses, uninsured catastrophic "
                 "losses, or minimum basic living expenses for children "
                 "from other relationships",
        )
        other_cs = st.number_input(
            "Monthly Child Support for Other Children",
            min_value=0.0, value=0.0, step=25.0,
            key=f"{key_prefix}_other_cs",
            help="Court-ordered child support paid for children from "
                 "other relationships",
        )

    return {
        "monthly_gross": monthly_gross,
        "filing_status": filing_status,
        "num_tax_exemptions": num_tax_exemptions,
        "num_dependents": num_dependents,
        "use_custom_taxes": use_custom,
        "custom_monthly_federal_tax": custom_federal,
        "custom_monthly_state_tax": custom_state,
        "custom_monthly_fica": custom_fica,
        "custom_monthly_sdi": custom_sdi,
        "monthly_health_insurance": health_insurance,
        "monthly_mandatory_retirement": mandatory_retirement,
        "monthly_union_dues": union_dues,
        "monthly_hardship_deduction": hardship,
        "monthly_other_child_support": other_cs,
    }


def render_nmdi_breakdown(label: str, breakdown: dict):
    """Display a breakdown table of net monthly disposable income."""
    import streamlit as st
    st.markdown(f"**{label} - Income Breakdown**")

    data = [
        ("Monthly Gross Income", breakdown["monthly_gross"]),
        ("Federal Income Tax", -breakdown["federal_tax"]),
        ("CA State Income Tax", -breakdown["state_tax"]),
        ("FICA (Social Security + Medicare)", -breakdown["fica"]),
        ("CA State Disability Insurance", -breakdown["sdi"]),
        ("Health Insurance", -breakdown["health_insurance"]),
        ("Mandatory Retirement", -breakdown["mandatory_retirement"]),
        ("Union Dues", -breakdown["union_dues"]),
        ("Hardship Deduction", -breakdown["hardship_deduction"]),
        ("Other Child Support", -breakdown["other_child_support"]),
    ]

    for label_text, amount in data:
        if amount != 0:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text(label_text)
            with col2:
                st.text(format_currency(amount))

    st.divider()
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("**Net Monthly Disposable Income**")
    with col2:
        st.markdown(f"**{format_currency(breakdown['net_monthly_disposable_income'])}**")


def main():
    import streamlit as st
    st.set_page_config(
        page_title="California Child Support Calculator",
        page_icon="⚖️",
        layout="wide",
    )

    st.title("⚖️ California Child Support Calculator")
    st.caption(
        "Based on California Family Code §§ 4050-4076 — "
        "Statewide Uniform Guideline"
    )

    st.warning(
        "**Disclaimer:** This calculator provides estimates based on the "
        "California guideline child support formula. It is for informational "
        "purposes only and does not constitute legal advice. Actual court "
        "orders may differ based on judicial discretion, deviations under "
        "§ 4057, and other factors. Consult a family law attorney for "
        "specific legal guidance."
    )

    # ---- Sidebar: Key Parameters ----
    with st.sidebar:
        st.header("⚙️ Case Parameters")

        num_children = st.number_input(
            "Number of Children",
            min_value=1,
            max_value=20,
            value=1,
            help="Number of children for this support order",
        )

        st.divider()

        st.subheader("Timeshare")
        st.caption(
            "Enter the percentage of time each parent has primary "
            "physical responsibility for the children."
        )

        parent_a_timeshare = st.slider(
            "Parent A's Timeshare %",
            min_value=0,
            max_value=100,
            value=20,
            step=1,
            help="Percentage of time Parent A has the children. "
                 "Parent B gets the remaining time.",
        )
        parent_b_timeshare = 100 - parent_a_timeshare
        st.info(f"Parent B's Timeshare: **{parent_b_timeshare}%**")

        st.divider()

        st.subheader("Add-On Expenses (§ 4062)")
        st.caption(
            "Monthly expenses shared proportionally to income."
        )

        childcare = st.number_input(
            "Childcare Costs",
            min_value=0.0, value=0.0, step=50.0,
            help="Monthly childcare costs related to employment or education",
        )
        healthcare = st.number_input(
            "Uninsured Healthcare Costs",
            min_value=0.0, value=0.0, step=25.0,
            help="Monthly uninsured health-care costs for the children",
        )
        education = st.number_input(
            "Educational Expenses",
            min_value=0.0, value=0.0, step=25.0,
            help="Monthly costs for children's special educational needs",
        )
        travel = st.number_input(
            "Travel for Visitation",
            min_value=0.0, value=0.0, step=25.0,
            help="Monthly travel expenses for visitation",
        )

        st.divider()
        st.subheader("About")
        st.markdown(
            "This calculator implements the **California guideline "
            "child support formula** from Family Code § 4055:\n\n"
            "```\nCS = K[HN − (H%)(TN)]\n```\n\n"
            "Tax estimates use **2025 tax year** brackets."
        )

    # ---- Main Content: Parent Income ----
    tab_input, tab_results, tab_formula = st.tabs([
        "📝 Income & Deductions",
        "📊 Results",
        "📖 Formula Explanation",
    ])

    with tab_input:
        col_a, col_b = st.columns(2)

        with col_a:
            parent_a_inputs = render_income_section("Parent A", "pa")

        with col_b:
            parent_b_inputs = render_income_section("Parent B", "pb")

    # ---- Calculate ----
    parent_a_breakdown = calc_net_monthly_disposable_income(**parent_a_inputs)
    parent_b_breakdown = calc_net_monthly_disposable_income(**parent_b_inputs)

    pa_nmdi = parent_a_breakdown["net_monthly_disposable_income"]
    pb_nmdi = parent_b_breakdown["net_monthly_disposable_income"]

    cs_result = calc_child_support(
        parent_a_nmdi=pa_nmdi,
        parent_b_nmdi=pb_nmdi,
        num_children=num_children,
        parent_a_timeshare_pct=parent_a_timeshare,
    )

    addon_result = calc_addons(
        parent_a_nmdi=pa_nmdi,
        parent_b_nmdi=pb_nmdi,
        childcare_costs=childcare,
        uninsured_healthcare=healthcare,
        education_costs=education,
        travel_costs=travel,
    )

    # ---- Results Tab ----
    with tab_results:
        st.header("Guideline Child Support Calculation")

        # Key result
        total_from_payer = cs_result["child_support"]
        # Determine add-on adjustments
        # The payer's share of add-ons increases their obligation;
        # the payee's share reduces it (they pay directly).
        if cs_result["payer"] == "Parent A":
            payer_addon = addon_result["parent_a_addon_amount"]
        else:
            payer_addon = addon_result["parent_b_addon_amount"]

        total_support = total_from_payer + payer_addon

        # Display key metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                "Base Child Support",
                format_currency(cs_result["child_support"]),
            )
        with col2:
            st.metric(
                "Add-On (Payer's Share)",
                format_currency(payer_addon),
            )
        with col3:
            st.metric(
                "Total Monthly Support",
                format_currency(total_support),
            )
        with col4:
            st.metric(
                "Annual Support",
                format_currency(total_support * 12),
            )

        st.success(
            f"**{cs_result['payer']}** pays **{cs_result['payee']}** "
            f"a total of **{format_currency(total_support)}/month** "
            f"in child support ({format_currency(cs_result['child_support'])} "
            f"base + {format_currency(payer_addon)} add-ons)."
        )

        st.divider()

        # Formula breakdown
        st.subheader("Formula Breakdown: CS = K[HN − (H%)(TN)]")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Variable** | **Value**")
            st.markdown("---|---")
            st.markdown(
                f"TN (Total Net) | {format_currency(cs_result['tn'])}"
            )
            st.markdown(
                f"HN (High Earner Net) | "
                f"{format_currency(cs_result['hn'])} "
                f"({cs_result['high_earner']})"
            )
            st.markdown(
                f"H% (High Earner Timeshare) | "
                f"{format_pct(cs_result['h_pct'])}"
            )
            st.markdown(
                f"K Fraction ({cs_result['num_children']} "
                f"{'child' if cs_result['num_children'] == 1 else 'children'}) | "
                f"{cs_result['fraction']}"
            )
            st.markdown(f"K Factor | {cs_result['k_factor']:.4f}")

        with col2:
            st.markdown("**Step-by-Step Calculation**")
            h_times_tn = cs_result["h_pct"] * cs_result["tn"]
            hn_minus = cs_result["hn"] - h_times_tn
            st.markdown(
                f"1. H% × TN = {format_pct(cs_result['h_pct'])} × "
                f"{format_currency(cs_result['tn'])} = "
                f"{format_currency(h_times_tn)}"
            )
            st.markdown(
                f"2. HN − (H% × TN) = {format_currency(cs_result['hn'])} − "
                f"{format_currency(h_times_tn)} = "
                f"{format_currency(hn_minus)}"
            )
            st.markdown(
                f"3. K × [HN − (H%)(TN)] = {cs_result['k_factor']:.4f} × "
                f"{format_currency(hn_minus)} = "
                f"**{format_currency(cs_result['child_support'])}**"
            )

        st.divider()

        # Income breakdown details
        st.subheader("Net Monthly Disposable Income Breakdown")
        col1, col2 = st.columns(2)
        with col1:
            render_nmdi_breakdown("Parent A", parent_a_breakdown)
        with col2:
            render_nmdi_breakdown("Parent B", parent_b_breakdown)

        # Add-on breakdown
        if addon_result["total_addons"] > 0:
            st.divider()
            st.subheader("Add-On Expenses Breakdown (§ 4062)")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**Expense**")
                if addon_result["childcare_costs"] > 0:
                    st.text(f"Childcare: {format_currency(addon_result['childcare_costs'])}")
                if addon_result["uninsured_healthcare"] > 0:
                    st.text(f"Healthcare: {format_currency(addon_result['uninsured_healthcare'])}")
                if addon_result["education_costs"] > 0:
                    st.text(f"Education: {format_currency(addon_result['education_costs'])}")
                if addon_result["travel_costs"] > 0:
                    st.text(f"Travel: {format_currency(addon_result['travel_costs'])}")
                st.markdown(f"**Total: {format_currency(addon_result['total_addons'])}**")

            with col2:
                st.markdown(
                    f"**Parent A's Share "
                    f"({format_pct(addon_result['parent_a_share_pct'])})**"
                )
                st.markdown(
                    f"{format_currency(addon_result['parent_a_addon_amount'])}"
                )

            with col3:
                st.markdown(
                    f"**Parent B's Share "
                    f"({format_pct(addon_result['parent_b_share_pct'])})**"
                )
                st.markdown(
                    f"{format_currency(addon_result['parent_b_addon_amount'])}"
                )

    # ---- Formula Explanation Tab ----
    with tab_formula:
        st.header("Understanding the California Guideline Formula")

        st.markdown("""
### The Formula: CS = K[HN − (H%)(TN)]

California Family Code § 4055 establishes the **statewide uniform guideline**
for determining child support. The formula considers both parents' incomes and
the amount of time each parent spends with the children.

---

### Variables

| Variable | Definition |
|----------|-----------|
| **CS** | Child Support amount (monthly) |
| **K** | Combined allocation factor — portion of both parents' combined income devoted to child support |
| **HN** | High earner's Net monthly disposable income |
| **H%** | Percentage of time the **high earner** has primary physical responsibility for the children |
| **TN** | Total Net monthly disposable income (both parents combined) |

---

### How K Is Calculated (§ 4055(b))

K depends on:
1. The **number of children**
2. The **high earner's timeshare** (H%)

**Fraction by number of children:**

| Children | Fraction |
|----------|----------|
| 1 | 0.20 (20%) |
| 2 | 0.275 (27.5%) |
| 3 | 0.34 (34%) |
| 4 | 0.355 (35.5%) |
| 5 | 0.37 (37%) |

**K factor formula:**
- If **H% ≤ 50%**: K = (1 + H%) × Fraction
- If **H% > 50%**: K = (2 − H%) × Fraction

When the high earner has **less** time with the children (H% low), K is higher
because more support flows from the high earner to the other parent. When the
high earner has **more** time (H% high), K decreases and the formula may even
produce a **negative** result, meaning the lower earner pays the higher earner.

---

### Net Monthly Disposable Income (§ 4059-4060)

Net Monthly Disposable Income (NMDI) starts with **gross income from all
sources** (§ 4058) and subtracts:

1. **Federal income tax** (actual or estimated)
2. **State income tax** (actual or estimated)
3. **FICA** — Social Security (6.2%) and Medicare (1.45%)
4. **State Disability Insurance** (SDI)
5. **Mandatory retirement contributions** (not voluntary)
6. **Mandatory union dues**
7. **Health insurance premiums** (for the parent, not the children)
8. **Hardship deductions** (§ 4070-4073)
9. **Child support for other relationships**

---

### Add-On Expenses (§ 4062)

In addition to the base child support amount, the court may order parents to
share these costs **in proportion to their respective net incomes**:

- **Childcare** related to employment or education
- **Uninsured healthcare** costs for the children
- **Special educational needs** of the children
- **Travel expenses** for visitation

---

### Important Notes

- The guideline amount is **presumed correct** under § 4057, but a court may
  deviate if it would be unjust or inappropriate.
- A **low-income adjustment** may apply when the obligor's net income is very
  low (§ 4055(b)(7)).
- This calculator uses **2025 tax year** brackets for estimating taxes. Actual
  tax withholdings may differ.
- Courts use **DissoMaster** or similar certified software for official
  calculations. This tool is for educational and estimation purposes.

---

### Relevant Code Sections

| Section | Topic |
|---------|-------|
| § 4050 | Legislative intent |
| § 4053 | Mandatory adherence principles |
| § 4055 | Guideline formula |
| § 4057 | Presumption of correctness; deviation |
| § 4058 | Annual gross income |
| § 4059 | Deductions from gross income |
| § 4060 | Net disposable income |
| § 4062 | Additional child support (add-ons) |
| § 4070-4073 | Hardship deductions |
        """)


if __name__ == "__main__":
    main()
