"""
California Child Support Calculator
Based on California Family Code §§ 4050-4076
Updated for SB 343 (operative September 1, 2024)

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
    - SB 343 (2024): Updated K-factor table, add-on proportional split
"""

import math

# ---------------------------------------------------------------------------
# Tax Tables (2025 Tax Year)
# ---------------------------------------------------------------------------

# Federal income tax brackets - Single (2025, per One Big Beautiful Bill Act)
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

# Federal standard deductions (2025, updated by One Big Beautiful Bill Act)
FEDERAL_STD_DEDUCTION = {
    "Single": 15_750,
    "Married Filing Jointly": 31_500,
    "Head of Household": 23_625,
}

# California state income tax brackets 2025 - Single (Schedule X)
CA_BRACKETS_SINGLE = [
    (11_079, 0.01),
    (26_264, 0.02),
    (41_452, 0.04),
    (57_542, 0.06),
    (72_724, 0.08),
    (371_479, 0.093),
    (445_771, 0.103),
    (742_953, 0.113),
    (1_000_000, 0.123),
    (float("inf"), 0.133),  # includes 1% Mental Health Services Tax
]

# California state income tax brackets 2025 - Married Filing Jointly (Schedule Y)
CA_BRACKETS_MFJ = [
    (21_512, 0.01),
    (50_998, 0.02),
    (80_490, 0.04),
    (111_732, 0.06),
    (141_212, 0.08),
    (286_492, 0.093),
    (343_788, 0.103),
    (572_980, 0.113),
    (1_000_000, 0.123),
    (float("inf"), 0.133),
]

# California state income tax brackets 2025 - Head of Household (Schedule Z)
CA_BRACKETS_HOH = [
    (22_158, 0.01),
    (52_528, 0.02),
    (82_904, 0.04),
    (115_084, 0.06),
    (145_448, 0.08),
    (742_958, 0.093),
    (891_542, 0.103),
    (1_485_906, 0.113),
    (float("inf"), 0.123),
    # Mental Health Services Tax: +1% over $1,000,000 handled separately
]

# California standard deduction (2025)
CA_STD_DEDUCTION = {
    "Single": 5_706,
    "Married Filing Jointly": 11_412,
    "Head of Household": 11_412,
}

# California exemption credits (2025)
CA_PERSONAL_EXEMPTION_CREDIT = {
    "Single": 153,
    "Head of Household": 153,
    "Married Filing Jointly": 306,
}
CA_DEPENDENT_EXEMPTION_CREDIT = 475  # per dependent

# FICA rates (2025)
SS_RATE = 0.062
SS_WAGE_BASE = 176_100
MEDICARE_RATE = 0.0145
MEDICARE_ADDITIONAL_RATE = 0.009  # on wages over threshold
MEDICARE_ADDITIONAL_THRESHOLD_SINGLE = 200_000
MEDICARE_ADDITIONAL_THRESHOLD_MFJ = 250_000

# California State Disability Insurance (2025)
CA_SDI_RATE = 0.012  # 1.2%, uncapped since 2024 (SB 951)

# California minimum wage (2025) for low-income adjustment
CA_MIN_WAGE_HOURLY = 16.50
CA_MIN_WAGE_MONTHLY_GROSS = CA_MIN_WAGE_HOURLY * 40 * 52 / 12  # ~$2,860

# ---------------------------------------------------------------------------
# SB 343 K-Factor Income Fraction Table (operative Sept 1, 2024)
# ---------------------------------------------------------------------------
# This table provides the base income fraction for ONE child.
# For multiple children, the fraction is scaled by child-count percentages.

# Child-count percentages of combined net income (§ 4055)
CHILD_SUPPORT_PERCENTAGES = {
    1: 0.25,
    2: 0.40,
    3: 0.50,
    4: 0.60,
}


def get_income_fraction(tn_monthly: float) -> float:
    """
    Get the base income fraction from the SB 343 K-factor table.

    This fraction is for ONE child. It varies based on the combined
    Total Net monthly disposable income (TN).

    Table (CA Family Code § 4055(b)(1), as amended by SB 343):
        $0 - $2,900:       0.165 + TN / 82,857
        $2,901 - $5,000:   0.131 + TN / 42,149
        $5,001 - $6,666:   0.25
        $6,667 - $10,000:  0.10 + 1,499 / TN
        Over $10,000:       0.12 + 1,200 / TN
    """
    if tn_monthly <= 0:
        return 0.165
    if tn_monthly <= 2_900:
        return 0.165 + tn_monthly / 82_857
    if tn_monthly <= 5_000:
        return 0.131 + tn_monthly / 42_149
    if tn_monthly <= 6_666:
        return 0.25
    if tn_monthly <= 10_000:
        return 0.10 + 1_499 / tn_monthly
    return 0.12 + 1_200 / tn_monthly


def get_child_count_multiplier(num_children: int) -> float:
    """
    Get the multiplier to scale the base income fraction for multiple children.

    The income fraction table is for 1 child (base 25%).
    For N children, scale by: child_pct[N] / child_pct[1].
    """
    if num_children <= 0:
        return 0.0
    if num_children == 1:
        return 1.0
    base_pct = CHILD_SUPPORT_PERCENTAGES[1]  # 0.25
    if num_children <= 4:
        return CHILD_SUPPORT_PERCENTAGES[num_children] / base_pct
    # 5+ children: court discretion, estimate continued increase
    return (0.60 + (num_children - 4) * 0.04) / base_pct


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
                      num_exemptions: int = 1,
                      num_dependents: int = 0) -> float:
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

    # For HOH, add Mental Health Services Tax separately (1% over $1M)
    if filing_status == "Head of Household" and taxable_income > 1_000_000:
        tax += (taxable_income - 1_000_000) * 0.01

    # Apply personal exemption credits
    personal_credit = CA_PERSONAL_EXEMPTION_CREDIT.get(filing_status, 153)
    tax -= personal_credit

    # Apply dependent exemption credits
    tax -= num_dependents * CA_DEPENDENT_EXEMPTION_CREDIT

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
    """Calculate California State Disability Insurance (uncapped since 2024)."""
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
            annual_gross, filing_status, num_tax_exemptions,
            num_dependents_for_credits
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
# Child Support Formula (CA Family Code § 4055, as amended by SB 343)
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

    K = time-sharing multiplier x income fraction x child-count multiplier

    Under SB 343 (operative Sept 1, 2024):
    - Income fraction comes from the new income-based table
    - Child-count scaling: 1 child=25%, 2=40%, 3=50%, 4=60%
    """
    tn = parent_a_nmdi + parent_b_nmdi  # Total Net

    # Determine high earner
    if parent_a_nmdi >= parent_b_nmdi:
        hn = parent_a_nmdi
        high_earner = "Parent A (higher earner)"
        h_pct = parent_a_timeshare_pct / 100.0
    else:
        hn = parent_b_nmdi
        high_earner = "Parent B (higher earner)"
        h_pct = (100 - parent_a_timeshare_pct) / 100.0

    # Income fraction from SB 343 table (base for 1 child)
    income_fraction = get_income_fraction(tn)

    # Scale for number of children
    child_multiplier = get_child_count_multiplier(num_children)
    adjusted_fraction = income_fraction * child_multiplier

    # Time-sharing multiplier per § 4055(b)
    if h_pct <= 0.50:
        time_multiplier = 1 + h_pct
    else:
        time_multiplier = 2 - h_pct

    # K = time-sharing multiplier x adjusted income fraction
    k = time_multiplier * adjusted_fraction

    # Guideline child support
    cs = k * (hn - (h_pct * tn))

    # Determine who pays whom
    if parent_a_nmdi >= parent_b_nmdi:
        if cs >= 0:
            payer = "Parent A"
            payee = "Parent B"
        else:
            payer = "Parent B"
            payee = "Parent A"
            cs = abs(cs)
    else:
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
        "income_fraction": income_fraction,
        "child_multiplier": child_multiplier,
        "adjusted_fraction": adjusted_fraction,
        "time_multiplier": time_multiplier,
        "k_factor": k,
        "num_children": num_children,
    }


def calc_low_income_adjustment(
    cs_amount: float,
    obligor_nmdi: float,
    obligor_monthly_gross: float,
) -> dict:
    """
    Calculate low-income adjustment per § 4055(b)(7).

    If the obligor's net disposable income is below full-time minimum wage
    gross income, the support may be reduced.

    Reduction = CS x (MinWageGross - ObligorNDI) / MinWageGross
    """
    min_wage_gross = CA_MIN_WAGE_MONTHLY_GROSS  # ~$2,860

    if obligor_nmdi >= min_wage_gross or obligor_nmdi <= 0:
        return {
            "applies": False,
            "reduction_fraction": 0,
            "max_reduction": 0,
            "adjusted_cs": cs_amount,
            "min_wage_gross": min_wage_gross,
        }

    reduction_fraction = (min_wage_gross - obligor_nmdi) / min_wage_gross
    max_reduction = cs_amount * reduction_fraction
    adjusted_cs = cs_amount - max_reduction

    return {
        "applies": True,
        "reduction_fraction": reduction_fraction,
        "max_reduction": max_reduction,
        "adjusted_cs": max(0, adjusted_cs),
        "min_wage_gross": min_wage_gross,
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

    Under SB 343, add-ons are split in proportion to each parent's share
    of total net income (previously was 50/50 by default).
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
             "(employment, self-employment, rental, investments, "
             "capital gains, etc.) per CA Family Code § 4058",
    )

    filing_status = st.selectbox(
        "Tax Filing Status",
        ["Single", "Head of Household", "Married Filing Jointly"],
        key=f"{key_prefix}_filing",
        help="Federal and state tax filing status. "
             "Custodial parents typically file as Head of Household.",
    )

    col1, col2 = st.columns(2)
    with col1:
        num_tax_exemptions = st.number_input(
            "CA Tax Exemptions",
            min_value=1,
            max_value=20,
            value=1,
            key=f"{key_prefix}_exemptions",
            help="Number of California personal exemptions claimed",
        )
    with col2:
        num_dependents = st.number_input(
            "Dependents (for tax credits)",
            min_value=0,
            max_value=20,
            value=0,
            key=f"{key_prefix}_dependents",
            help="Number of dependents for federal child tax credit "
                 "and CA dependent exemption credit",
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
            "Monthly Health Insurance (parent & children)",
            min_value=0.0, value=0.0, step=25.0,
            key=f"{key_prefix}_health",
            help="Health insurance premiums for the parent and any "
                 "children the parent is obligated to support (§ 4059(d))",
        )
        mandatory_retirement = st.number_input(
            "Monthly Mandatory Retirement Contributions",
            min_value=0.0, value=0.0, step=25.0,
            key=f"{key_prefix}_retirement",
            help="Required retirement contributions as a condition "
                 "of employment (not voluntary 401k)",
        )
        union_dues = st.number_input(
            "Monthly Union Dues",
            min_value=0.0, value=0.0, step=10.0,
            key=f"{key_prefix}_union",
            help="Mandatory union dues required as a condition of employment",
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
            "Monthly Child Support / Spousal Support Paid",
            min_value=0.0, value=0.0, step=25.0,
            key=f"{key_prefix}_other_cs",
            help="Court-ordered child support or spousal support paid "
                 "for persons not subject to this order (§ 4059(e))",
        )

    return {
        "monthly_gross": monthly_gross,
        "filing_status": filing_status,
        "num_tax_exemptions": num_tax_exemptions,
        "num_dependents_for_credits": num_dependents,
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
        ("Other Support Paid", -breakdown["other_child_support"]),
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
        st.markdown(
            f"**{format_currency(breakdown['net_monthly_disposable_income'])}**"
        )


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
        "Statewide Uniform Guideline — Updated for SB 343 (2024)"
    )

    st.warning(
        "**Disclaimer:** This calculator provides estimates based on the "
        "California guideline child support formula. It is for informational "
        "purposes only and does not constitute legal advice. Actual court "
        "orders may differ based on judicial discretion, deviations under "
        "§ 4057, and other factors. Consult a family law attorney for "
        "specific legal guidance. Courts use DissoMaster or similar "
        "certified software for official calculations."
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
            "Monthly expenses shared proportionally to income (SB 343)."
        )

        childcare = st.number_input(
            "Childcare Costs (actually incurred)",
            min_value=0.0, value=0.0, step=50.0,
            help="Monthly childcare costs actually incurred and related "
                 "to employment or education (SB 343 requires costs be "
                 "actually incurred, not estimated)",
        )
        healthcare = st.number_input(
            "Uninsured Healthcare Costs",
            min_value=0.0, value=0.0, step=25.0,
            help="Monthly reasonable uninsured health-care costs "
                 "for the children",
        )
        education = st.number_input(
            "Educational Expenses",
            min_value=0.0, value=0.0, step=25.0,
            help="Monthly costs for children's educational "
                 "or special needs",
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
            "Updated for **SB 343** (operative Sept 1, 2024).\n"
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

    # Low-income adjustment
    if cs_result["payer"] == "Parent A":
        obligor_nmdi = pa_nmdi
        obligor_gross = parent_a_inputs["monthly_gross"]
    else:
        obligor_nmdi = pb_nmdi
        obligor_gross = parent_b_inputs["monthly_gross"]

    low_income = calc_low_income_adjustment(
        cs_result["child_support"], obligor_nmdi, obligor_gross
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

        base_cs = cs_result["child_support"]

        # Apply low-income adjustment if applicable
        if low_income["applies"]:
            effective_cs = low_income["adjusted_cs"]
        else:
            effective_cs = base_cs

        # Add-on: payer's proportional share
        if cs_result["payer"] == "Parent A":
            payer_addon = addon_result["parent_a_addon_amount"]
        else:
            payer_addon = addon_result["parent_b_addon_amount"]

        total_support = effective_cs + payer_addon

        # Display key metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Base Child Support", format_currency(base_cs))
        with col2:
            if low_income["applies"]:
                st.metric(
                    "After Low-Income Adj.",
                    format_currency(effective_cs),
                )
            else:
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
            st.metric("Annual Support", format_currency(total_support * 12))

        st.success(
            f"**{cs_result['payer']}** pays **{cs_result['payee']}** "
            f"a total of **{format_currency(total_support)}/month** "
            f"in child support."
        )

        if low_income["applies"]:
            st.info(
                f"**Low-Income Adjustment Applied (§ 4055(b)(7)):** "
                f"The obligor's net disposable income "
                f"({format_currency(obligor_nmdi)}) is below the "
                f"full-time minimum wage threshold "
                f"({format_currency(low_income['min_wage_gross'])}). "
                f"Base support reduced by up to "
                f"{format_currency(low_income['max_reduction'])} "
                f"(reduction factor: {format_pct(low_income['reduction_fraction'])})."
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
                f"Income Fraction (from table) | "
                f"{cs_result['income_fraction']:.4f}"
            )
            if num_children > 1:
                st.markdown(
                    f"Child-Count Multiplier "
                    f"({num_children} children) | "
                    f"{cs_result['child_multiplier']:.2f}x"
                )
                st.markdown(
                    f"Adjusted Fraction | "
                    f"{cs_result['adjusted_fraction']:.4f}"
                )
            st.markdown(
                f"Time-Sharing Multiplier | "
                f"{cs_result['time_multiplier']:.2f}"
            )
            st.markdown(f"**K Factor** | **{cs_result['k_factor']:.4f}**")

        with col2:
            st.markdown("**Step-by-Step Calculation**")
            h_times_tn = cs_result["h_pct"] * cs_result["tn"]
            hn_minus = cs_result["hn"] - h_times_tn
            st.markdown(
                f"1. Income fraction (TN="
                f"{format_currency(cs_result['tn'])}): "
                f"**{cs_result['income_fraction']:.4f}**"
            )
            if num_children > 1:
                st.markdown(
                    f"2. Adjusted for {num_children} children: "
                    f"{cs_result['income_fraction']:.4f} × "
                    f"{cs_result['child_multiplier']:.2f} = "
                    f"**{cs_result['adjusted_fraction']:.4f}**"
                )
            st.markdown(
                f"{'3' if num_children > 1 else '2'}. "
                f"K = {cs_result['time_multiplier']:.2f} × "
                f"{cs_result['adjusted_fraction']:.4f} = "
                f"**{cs_result['k_factor']:.4f}**"
            )
            st.markdown(
                f"{'4' if num_children > 1 else '3'}. "
                f"H% × TN = {format_pct(cs_result['h_pct'])} × "
                f"{format_currency(cs_result['tn'])} = "
                f"{format_currency(h_times_tn)}"
            )
            st.markdown(
                f"{'5' if num_children > 1 else '4'}. "
                f"HN − (H% × TN) = {format_currency(cs_result['hn'])} − "
                f"{format_currency(h_times_tn)} = "
                f"{format_currency(hn_minus)}"
            )
            st.markdown(
                f"{'6' if num_children > 1 else '5'}. "
                f"CS = K × [HN − (H%)(TN)] = "
                f"{cs_result['k_factor']:.4f} × "
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
                    st.text(
                        f"Childcare: "
                        f"{format_currency(addon_result['childcare_costs'])}"
                    )
                if addon_result["uninsured_healthcare"] > 0:
                    st.text(
                        f"Healthcare: "
                        f"{format_currency(addon_result['uninsured_healthcare'])}"
                    )
                if addon_result["education_costs"] > 0:
                    st.text(
                        f"Education: "
                        f"{format_currency(addon_result['education_costs'])}"
                    )
                if addon_result["travel_costs"] > 0:
                    st.text(
                        f"Travel: "
                        f"{format_currency(addon_result['travel_costs'])}"
                    )
                st.markdown(
                    f"**Total: "
                    f"{format_currency(addon_result['total_addons'])}**"
                )

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

**Updated by SB 343** (operative September 1, 2024), which introduced a new
income-based K-factor table and proportional add-on expense splitting.

---

### Variables

| Variable | Definition |
|----------|-----------|
| **CS** | Child Support amount (monthly). Positive = high earner pays low earner. Negative = low earner pays high earner. |
| **K** | Combined allocation factor — portion of parents' combined income devoted to child support |
| **HN** | High earner's Net monthly disposable income |
| **H%** | Percentage of time the **high earner** has primary physical responsibility for the children. For multiple children with different arrangements, H% = average. |
| **TN** | Total Net monthly disposable income (both parents combined) |

---

### How K Is Calculated (§ 4055(b), as amended by SB 343)

K is the product of three components:

**K = Time-Sharing Multiplier × Income Fraction × Child-Count Multiplier**

#### 1. Time-Sharing Multiplier

| Condition | Multiplier |
|-----------|------------|
| H% ≤ 50% | 1 + H% |
| H% > 50% | 2 − H% |

#### 2. Income Fraction (SB 343 Table)

The income fraction is based on **Total Net Disposable Income (TN)** and
represents the base allocation for **one child**:

| Total Net Income (TN)/Month | Income Fraction |
|-----------------------------|-----------------|
| $0 – $2,900 | 0.165 + TN / 82,857 |
| $2,901 – $5,000 | 0.131 + TN / 42,149 |
| $5,001 – $6,666 | 0.25 |
| $6,667 – $10,000 | 0.10 + 1,499 / TN |
| Over $10,000 | 0.12 + 1,200 / TN |

#### 3. Child-Count Percentage

The income fraction is scaled for the number of children:

| Number of Children | % of Combined Net Income | Multiplier vs. 1 child |
|--------------------|--------------------------|------------------------|
| 1 | 25% | 1.0x |
| 2 | 40% | 1.6x |
| 3 | 50% | 2.0x |
| 4 | 60% | 2.4x |
| 5+ | Higher (court discretion) | — |

---

### Net Monthly Disposable Income (§ 4059-4060)

Net Monthly Disposable Income (NMDI) starts with **gross income from all
sources** (§ 4058) and subtracts:

1. **Federal income tax** — actually payable, reflecting accurate filing status
2. **State income tax** — actually payable
3. **FICA** — Social Security (6.2% up to $176,100) and Medicare (1.45% + 0.9% above $200k)
4. **State Disability Insurance** — 1.2% of all wages (uncapped since 2024)
5. **Mandatory retirement contributions** — required as condition of employment
6. **Mandatory union dues** — required as condition of employment
7. **Health insurance premiums** — for parent and children (§ 4059(d))
8. **Existing court-ordered support** — child/spousal support being paid (§ 4059(e))
9. **Hardship deductions** — (§ 4070-4073) extraordinary health expenses,
   uninsured catastrophic losses, or support of children from other
   relationships

Monthly NMDI = Annual Net Disposable Income / 12

---

### Gross Income (§ 4058, as amended by SB 343)

Income from **whatever source derived**, including:
- Wages, salaries, commissions, bonuses
- Self-employment income (gross receipts minus operating expenses)
- Rental income, royalties, dividends, interest, trust income
- **Capital gains** (added by SB 343)
- Workers' compensation, unemployment, disability benefits
- Social Security benefits, pensions, annuities
- Spousal support received from third parties
- Military housing and food allowances

**Excluded:** Child support received, needs-based public assistance
(CalWORKs, SSI, Medi-Cal).

---

### Add-On Expenses (§ 4062, as amended by SB 343)

In addition to base support, the court may order parents to share costs
**in proportion to their respective net incomes** (changed from 50/50 default
by SB 343):

**Mandatory add-ons** (court SHALL order):
- **Childcare** related to employment/education — must be **actually incurred**
  (SB 343 change; 90-day reimbursement window, up from 30 days)
- **Reasonable uninsured healthcare** costs for the children

**Discretionary add-ons** (court MAY order):
- **Educational or special needs** of the children
- **Travel expenses** for visitation

---

### Low-Income Adjustment (§ 4055(b)(7))

If the obligor's net disposable income is **below full-time minimum wage**
gross income (~$2,860/month at $16.50/hr in 2025), the court may reduce
support by:

**Reduction = CS × (MinWageGross − ObligorNDI) / MinWageGross**

The court has discretion within this range. Software must show the
**range** of the permitted adjustment.

---

### Default Proceedings (§ 4055(b)(6))

If the noncustodial parent fails to appear and there is no evidence of
their custody percentage:
- If noncustodial parent is higher earner: **H% = 0**
- If custodial parent is higher earner: **H% = 100%**

---

### Important Notes

- The guideline amount is **presumed correct** under § 4057, but a court may
  deviate if it would be unjust or inappropriate.
- SB 343 changes became **operative September 1, 2024**.
- This calculator uses **2025 tax year** brackets (federal updated by the
  One Big Beautiful Bill Act, July 2025).
- Courts use **DissoMaster** or similar certified software for official
  calculations. This tool is for **educational and estimation purposes**.

---

### Relevant Code Sections

| Section | Topic |
|---------|-------|
| § 4050 | Legislative intent |
| § 4053 | Mandatory adherence principles |
| § 4055 | Guideline formula (amended by SB 343) |
| § 4057 | Presumption of correctness; deviation |
| § 4058 | Annual gross income (amended by SB 343) |
| § 4059 | Deductions from gross income |
| § 4060 | Net disposable income |
| § 4062 | Additional child support / add-ons (amended by SB 343) |
| § 4070-4073 | Hardship deductions |
| SB 343 | 2024 amendments to child support calculation |
        """)


if __name__ == "__main__":
    main()
