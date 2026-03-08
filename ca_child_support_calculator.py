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
# Formatting Helpers
# ---------------------------------------------------------------------------

def format_currency(amount: float) -> str:
    """Format a number as currency."""
    if amount < 0:
        return f"-${abs(amount):,.2f}"
    return f"${amount:,.2f}"


def format_pct(pct: float) -> str:
    """Format a decimal as a percentage."""
    return f"{pct * 100:.1f}%"


# ---------------------------------------------------------------------------
# Main Entry Point — Plain-text calculator for conversational use
# ---------------------------------------------------------------------------

def calculate(
    parent_a_monthly_gross: float,
    parent_b_monthly_gross: float,
    num_children: int = 1,
    parent_a_timeshare_pct: float = 20.0,
    # Tax filing
    parent_a_filing: str = "Single",
    parent_b_filing: str = "Single",
    parent_a_exemptions: int = 1,
    parent_b_exemptions: int = 1,
    parent_a_dependents: int = 0,
    parent_b_dependents: int = 0,
    # Optional deductions (monthly)
    parent_a_health_insurance: float = 0,
    parent_b_health_insurance: float = 0,
    parent_a_mandatory_retirement: float = 0,
    parent_b_mandatory_retirement: float = 0,
    parent_a_union_dues: float = 0,
    parent_b_union_dues: float = 0,
    parent_a_hardship: float = 0,
    parent_b_hardship: float = 0,
    parent_a_other_support: float = 0,
    parent_b_other_support: float = 0,
    # Add-on expenses (monthly)
    childcare_costs: float = 0,
    uninsured_healthcare: float = 0,
    education_costs: float = 0,
    travel_costs: float = 0,
) -> str:
    """
    Calculate California guideline child support and return a formatted report.

    This is the main entry point for conversational use (no Streamlit needed).

    Args:
        parent_a_monthly_gross: Parent A's monthly gross income
        parent_b_monthly_gross: Parent B's monthly gross income
        num_children: Number of children (default 1)
        parent_a_timeshare_pct: % of time Parent A has children, 0-100 (default 20)
        parent_a_filing / parent_b_filing: "Single", "Head of Household", or
            "Married Filing Jointly" (default "Single")
        parent_a_exemptions / parent_b_exemptions: CA tax exemptions (default 1)
        parent_a_dependents / parent_b_dependents: Dependents for tax credits (default 0)
        *_health_insurance: Monthly health insurance premiums
        *_mandatory_retirement: Monthly mandatory retirement contributions
        *_union_dues: Monthly mandatory union dues
        *_hardship: Monthly hardship deduction (§ 4070-4073)
        *_other_support: Monthly court-ordered support for other relationships
        childcare_costs: Monthly childcare (must be actually incurred per SB 343)
        uninsured_healthcare: Monthly uninsured healthcare for children
        education_costs: Monthly educational/special needs costs
        travel_costs: Monthly visitation travel costs

    Returns:
        Formatted text report with full calculation breakdown.
    """
    # Calculate NMDI for each parent
    pa = calc_net_monthly_disposable_income(
        monthly_gross=parent_a_monthly_gross,
        filing_status=parent_a_filing,
        num_tax_exemptions=parent_a_exemptions,
        num_dependents_for_credits=parent_a_dependents,
        monthly_health_insurance=parent_a_health_insurance,
        monthly_mandatory_retirement=parent_a_mandatory_retirement,
        monthly_union_dues=parent_a_union_dues,
        monthly_hardship_deduction=parent_a_hardship,
        monthly_other_child_support=parent_a_other_support,
    )
    pb = calc_net_monthly_disposable_income(
        monthly_gross=parent_b_monthly_gross,
        filing_status=parent_b_filing,
        num_tax_exemptions=parent_b_exemptions,
        num_dependents_for_credits=parent_b_dependents,
        monthly_health_insurance=parent_b_health_insurance,
        monthly_mandatory_retirement=parent_b_mandatory_retirement,
        monthly_union_dues=parent_b_union_dues,
        monthly_hardship_deduction=parent_b_hardship,
        monthly_other_child_support=parent_b_other_support,
    )

    pa_nmdi = pa["net_monthly_disposable_income"]
    pb_nmdi = pb["net_monthly_disposable_income"]

    # Child support formula
    cs = calc_child_support(pa_nmdi, pb_nmdi, num_children, parent_a_timeshare_pct)

    # Low-income adjustment
    if cs["payer"] == "Parent A":
        obligor_nmdi = pa_nmdi
        obligor_gross = parent_a_monthly_gross
    else:
        obligor_nmdi = pb_nmdi
        obligor_gross = parent_b_monthly_gross
    low_inc = calc_low_income_adjustment(cs["child_support"], obligor_nmdi, obligor_gross)

    # Add-ons
    addons = calc_addons(pa_nmdi, pb_nmdi, childcare_costs,
                         uninsured_healthcare, education_costs, travel_costs)

    # Effective support
    base_cs = cs["child_support"]
    effective_cs = low_inc["adjusted_cs"] if low_inc["applies"] else base_cs
    payer_addon = (addons["parent_a_addon_amount"] if cs["payer"] == "Parent A"
                   else addons["parent_b_addon_amount"])
    total_support = effective_cs + payer_addon

    # Build report
    lines = []
    lines.append("=" * 60)
    lines.append("CALIFORNIA GUIDELINE CHILD SUPPORT CALCULATION")
    lines.append("CA Family Code § 4055 (updated for SB 343)")
    lines.append("=" * 60)
    lines.append("")

    # Result summary
    lines.append(f"  {cs['payer']} pays {cs['payee']}: "
                 f"{format_currency(total_support)}/month")
    lines.append(f"  Annual: {format_currency(total_support * 12)}")
    lines.append("")

    # Income breakdown
    for label, bk, gross in [("Parent A", pa, parent_a_monthly_gross),
                              ("Parent B", pb, parent_b_monthly_gross)]:
        lines.append(f"--- {label} ---")
        lines.append(f"  Monthly Gross Income:       {format_currency(bk['monthly_gross'])}")
        lines.append(f"  Federal Income Tax:        -{format_currency(bk['federal_tax'])}")
        lines.append(f"  CA State Income Tax:       -{format_currency(bk['state_tax'])}")
        lines.append(f"  FICA (SS + Medicare):      -{format_currency(bk['fica'])}")
        lines.append(f"  CA SDI:                    -{format_currency(bk['sdi'])}")
        if bk["health_insurance"]:
            lines.append(f"  Health Insurance:          -{format_currency(bk['health_insurance'])}")
        if bk["mandatory_retirement"]:
            lines.append(f"  Mandatory Retirement:      -{format_currency(bk['mandatory_retirement'])}")
        if bk["union_dues"]:
            lines.append(f"  Union Dues:                -{format_currency(bk['union_dues'])}")
        if bk["hardship_deduction"]:
            lines.append(f"  Hardship Deduction:        -{format_currency(bk['hardship_deduction'])}")
        if bk["other_child_support"]:
            lines.append(f"  Other Support Paid:        -{format_currency(bk['other_child_support'])}")
        lines.append(f"  Net Monthly Disposable:     {format_currency(bk['net_monthly_disposable_income'])}")
        lines.append("")

    # Formula breakdown
    lines.append("--- Formula: CS = K[HN - (H%)(TN)] ---")
    lines.append(f"  TN (Total Net):              {format_currency(cs['tn'])}")
    lines.append(f"  HN (High Earner Net):        {format_currency(cs['hn'])} ({cs['high_earner']})")
    lines.append(f"  H% (High Earner Timeshare):  {format_pct(cs['h_pct'])}")
    lines.append(f"  Income Fraction (table):     {cs['income_fraction']:.4f}")
    if num_children > 1:
        lines.append(f"  Child-Count Multiplier:      {cs['child_multiplier']:.2f}x ({num_children} children)")
        lines.append(f"  Adjusted Fraction:           {cs['adjusted_fraction']:.4f}")
    lines.append(f"  Time-Sharing Multiplier:     {cs['time_multiplier']:.2f}")
    lines.append(f"  K Factor:                    {cs['k_factor']:.4f}")
    lines.append("")

    h_times_tn = cs["h_pct"] * cs["tn"]
    hn_minus = cs["hn"] - h_times_tn
    lines.append("  Step-by-step:")
    step = 1
    lines.append(f"  {step}. Income fraction (TN={format_currency(cs['tn'])}): {cs['income_fraction']:.4f}")
    if num_children > 1:
        step += 1
        lines.append(f"  {step}. Adjusted for {num_children} children: "
                     f"{cs['income_fraction']:.4f} x {cs['child_multiplier']:.2f} = {cs['adjusted_fraction']:.4f}")
    step += 1
    lines.append(f"  {step}. K = {cs['time_multiplier']:.2f} x {cs['adjusted_fraction']:.4f} = {cs['k_factor']:.4f}")
    step += 1
    lines.append(f"  {step}. H% x TN = {format_pct(cs['h_pct'])} x {format_currency(cs['tn'])} = {format_currency(h_times_tn)}")
    step += 1
    lines.append(f"  {step}. HN - (H% x TN) = {format_currency(cs['hn'])} - {format_currency(h_times_tn)} = {format_currency(hn_minus)}")
    step += 1
    lines.append(f"  {step}. CS = {cs['k_factor']:.4f} x {format_currency(hn_minus)} = {format_currency(base_cs)}")
    lines.append("")

    # Low-income adjustment
    if low_inc["applies"]:
        lines.append("--- Low-Income Adjustment (§ 4055(b)(7)) ---")
        lines.append(f"  Obligor NMDI ({format_currency(obligor_nmdi)}) < "
                     f"Min wage threshold ({format_currency(low_inc['min_wage_gross'])})")
        lines.append(f"  Reduction factor: {format_pct(low_inc['reduction_fraction'])}")
        lines.append(f"  Max reduction: {format_currency(low_inc['max_reduction'])}")
        lines.append(f"  Base CS: {format_currency(base_cs)} -> Adjusted: {format_currency(low_inc['adjusted_cs'])}")
        lines.append("")

    # Add-ons
    if addons["total_addons"] > 0:
        lines.append("--- Add-On Expenses (§ 4062, proportional per SB 343) ---")
        if addons["childcare_costs"]:
            lines.append(f"  Childcare:              {format_currency(addons['childcare_costs'])}")
        if addons["uninsured_healthcare"]:
            lines.append(f"  Uninsured Healthcare:   {format_currency(addons['uninsured_healthcare'])}")
        if addons["education_costs"]:
            lines.append(f"  Education:              {format_currency(addons['education_costs'])}")
        if addons["travel_costs"]:
            lines.append(f"  Travel:                 {format_currency(addons['travel_costs'])}")
        lines.append(f"  Total Add-Ons:          {format_currency(addons['total_addons'])}")
        lines.append(f"  Parent A share ({format_pct(addons['parent_a_share_pct'])}): "
                     f"{format_currency(addons['parent_a_addon_amount'])}")
        lines.append(f"  Parent B share ({format_pct(addons['parent_b_share_pct'])}): "
                     f"{format_currency(addons['parent_b_addon_amount'])}")
        lines.append("")

    # Final summary
    lines.append("--- SUMMARY ---")
    lines.append(f"  Base Child Support:     {format_currency(base_cs)}")
    if low_inc["applies"]:
        lines.append(f"  After Low-Income Adj:   {format_currency(effective_cs)}")
    if payer_addon > 0:
        lines.append(f"  Payer's Add-On Share:   {format_currency(payer_addon)}")
    lines.append(f"  TOTAL MONTHLY SUPPORT:  {format_currency(total_support)}")
    lines.append(f"  ANNUAL SUPPORT:         {format_currency(total_support * 12)}")
    lines.append(f"  {cs['payer']} pays {cs['payee']}")
    lines.append("")
    lines.append("DISCLAIMER: This is an estimate for informational purposes only.")
    lines.append("It does not constitute legal advice. Courts use DissoMaster or")
    lines.append("similar certified software. Consult a family law attorney.")

    return "\n".join(lines)


if __name__ == "__main__":
    # Example: run from command line
    print(calculate(
        parent_a_monthly_gross=8000,
        parent_b_monthly_gross=4000,
        num_children=2,
        parent_a_timeshare_pct=20,
        parent_a_filing="Single",
        parent_b_filing="Head of Household",
    ))
