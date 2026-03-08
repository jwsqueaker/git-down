#!/usr/bin/env python3
"""Standalone CLI Portfolio Analyzer — runs with Python stdlib only (no pip needed).

Usage:
    python3 cli_portfolio.py                          # uses sample_data/portfolio_example.csv
    python3 cli_portfolio.py sample_data/test_portfolio.csv
    python3 cli_portfolio.py --interactive
"""
import csv
import sys
import math
import statistics
from datetime import datetime, date
from collections import defaultdict

# ─── Data ────────────────────────────────────────────────────────────────────

def load_portfolio(path):
    """Load portfolio positions from CSV."""
    positions = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            positions.append({
                "symbol": row["symbol"].strip().upper(),
                "shares": float(row["shares"]),
                "purchase_date": row["purchase_date"].strip(),
                "purchase_price": float(row["purchase_price"]),
                "asset_class": row.get("asset_class", "").strip(),
                "description": row.get("description", "").strip(),
            })
    return positions


# ─── Calculations (stdlib only) ──────────────────────────────────────────────

def cost_basis(pos):
    return pos["shares"] * pos["purchase_price"]

def portfolio_cost(positions):
    return sum(cost_basis(p) for p in positions)

def weight(pos, total_cost):
    return cost_basis(pos) / total_cost if total_cost else 0

def days_held(pos):
    pd = datetime.strptime(pos["purchase_date"], "%Y-%m-%d").date()
    return (date.today() - pd).days

def years_held(pos):
    d = days_held(pos)
    return d / 365.25 if d > 0 else 0.001

def hhi(positions, total_cost):
    """Herfindahl-Hirschman Index — portfolio concentration."""
    return sum(weight(p, total_cost) ** 2 for p in positions)

def effective_positions(positions, total_cost):
    """1 / HHI — equivalent number of equally weighted positions."""
    h = hhi(positions, total_cost)
    return 1 / h if h > 0 else len(positions)


# ─── Display helpers ─────────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
GREEN  = "\033[32m"
RED    = "\033[31m"
CYAN   = "\033[36m"
YELLOW = "\033[33m"
BLUE   = "\033[34m"
WHITE  = "\033[97m"
BG_BLUE = "\033[44m"

def fmt_usd(v):
    sign = "-" if v < 0 else ""
    return f"{sign}${abs(v):,.2f}"

def fmt_pct(v):
    return f"{v:+.2f}%" if v != 0 else "0.00%"

def bar(value, max_val, width=20):
    filled = int((value / max_val) * width) if max_val else 0
    return "█" * filled + "░" * (width - filled)

def sparkline(values, width=20):
    if not values:
        return ""
    mn, mx = min(values), max(values)
    chars = " ▁▂▃▄▅▆▇█"
    rng = mx - mn if mx != mn else 1
    return "".join(chars[min(int((v - mn) / rng * 8), 8)] for v in values[-width:])

def table(headers, rows, alignments=None):
    """Print a formatted table."""
    if not rows:
        print("  (no data)")
        return
    col_widths = [len(h) for h in headers]
    str_rows = []
    for row in rows:
        sr = [str(c) for c in row]
        str_rows.append(sr)
        for i, c in enumerate(sr):
            col_widths[i] = max(col_widths[i], len(c))

    if not alignments:
        alignments = ["l"] * len(headers)

    def fmt_cell(val, w, align):
        if align == "r":
            return val.rjust(w)
        return val.ljust(w)

    header_line = "  ".join(fmt_cell(h, col_widths[i], alignments[i]) for i, h in enumerate(headers))
    print(f"  {BOLD}{header_line}{RESET}")
    print(f"  {'─' * len(header_line)}")
    for sr in str_rows:
        line = "  ".join(fmt_cell(sr[i], col_widths[i], alignments[i]) for i in range(len(headers)))
        print(f"  {line}")


# ─── Reports ─────────────────────────────────────────────────────────────────

def print_header(title):
    w = 60
    print()
    print(f"  {BG_BLUE}{WHITE}{BOLD} {title.center(w)} {RESET}")
    print()

def print_section(title):
    print(f"\n  {CYAN}{BOLD}{'─' * 3} {title} {'─' * 40}{RESET}\n")

def report_overview(positions):
    total = portfolio_cost(positions)
    print_header("PORTFOLIO OVERVIEW")

    print(f"  {DIM}Total Cost Basis{RESET}     {BOLD}{fmt_usd(total)}{RESET}")
    print(f"  {DIM}Positions{RESET}            {BOLD}{len(positions)}{RESET}")
    print(f"  {DIM}Effective Positions{RESET}  {BOLD}{effective_positions(positions, total):.1f}{RESET}")
    hhi_val = hhi(positions, total)
    conc = "Low" if hhi_val < 0.15 else "Moderate" if hhi_val < 0.25 else "High"
    color = GREEN if hhi_val < 0.15 else YELLOW if hhi_val < 0.25 else RED
    print(f"  {DIM}Concentration (HHI){RESET}  {color}{BOLD}{hhi_val:.4f} ({conc}){RESET}")

def report_positions(positions):
    total = portfolio_cost(positions)
    print_section("POSITIONS")

    sorted_pos = sorted(positions, key=lambda p: cost_basis(p), reverse=True)
    rows = []
    max_cost = max(cost_basis(p) for p in sorted_pos)
    for p in sorted_pos:
        cb = cost_basis(p)
        w = weight(p, total) * 100
        rows.append([
            p["symbol"],
            f"{p['shares']:,.0f}",
            fmt_usd(p["purchase_price"]),
            fmt_usd(cb),
            f"{w:.1f}%",
            bar(cb, max_cost, 15),
            p["purchase_date"],
        ])
    table(
        ["Symbol", "Shares", "Price", "Cost Basis", "Weight", "Allocation", "Purchased"],
        rows,
        ["l", "r", "r", "r", "r", "l", "l"],
    )

def report_allocation_by_class(positions):
    total = portfolio_cost(positions)
    print_section("ASSET CLASS ALLOCATION")

    by_class = defaultdict(float)
    for p in positions:
        cls = p["asset_class"] or "Unclassified"
        by_class[cls] += cost_basis(p)

    sorted_classes = sorted(by_class.items(), key=lambda x: x[1], reverse=True)
    max_val = max(v for _, v in sorted_classes) if sorted_classes else 1
    rows = []
    for cls, val in sorted_classes:
        pct = (val / total) * 100
        rows.append([cls, fmt_usd(val), f"{pct:.1f}%", bar(val, max_val, 20)])
    table(["Asset Class", "Cost Basis", "Weight", ""], rows, ["l", "r", "r", "l"])

def report_concentration(positions):
    total = portfolio_cost(positions)
    print_section("CONCENTRATION RISK")

    sorted_pos = sorted(positions, key=lambda p: cost_basis(p), reverse=True)
    cumulative = 0
    rows = []
    for i, p in enumerate(sorted_pos, 1):
        w = weight(p, total) * 100
        cumulative += w
        marker = " ◄ 50%" if cumulative >= 50 and cumulative - w < 50 else ""
        marker = " ◄ 80%" if cumulative >= 80 and cumulative - w < 80 else marker
        rows.append([str(i), p["symbol"], f"{w:.1f}%", f"{cumulative:.1f}%", marker])
    table(["#", "Symbol", "Weight", "Cumulative", ""], rows, ["r", "l", "r", "r", "l"])

def report_holding_period(positions):
    print_section("HOLDING PERIOD")

    rows = []
    sorted_pos = sorted(positions, key=lambda p: days_held(p), reverse=True)
    max_days = max(days_held(p) for p in sorted_pos) if sorted_pos else 1
    for p in sorted_pos:
        d = days_held(p)
        y = years_held(p)
        rows.append([
            p["symbol"],
            p["purchase_date"],
            f"{d:,}d",
            f"{y:.1f}y",
            bar(d, max_days, 15),
            "LT" if y >= 1 else "ST",
        ])
    table(["Symbol", "Purchased", "Days", "Years", "", "Tax"], rows, ["l", "l", "r", "r", "l", "l"])

def report_diversification_score(positions):
    total = portfolio_cost(positions)
    print_section("DIVERSIFICATION SCORECARD")

    n = len(positions)
    eff = effective_positions(positions, total)
    h = hhi(positions, total)

    # Unique asset classes
    classes = set(p["asset_class"] or "Unclassified" for p in positions)
    n_classes = len(classes)

    # Top-heavy check
    sorted_pos = sorted(positions, key=lambda p: cost_basis(p), reverse=True)
    top3_weight = sum(weight(p, total) for p in sorted_pos[:3]) * 100

    # Score (0-100)
    score = 0
    score += min(25, n * 2.5)                           # more positions = better (up to 10)
    score += min(25, eff * 2.5)                          # higher effective positions
    score += min(25, n_classes * 8)                      # more asset classes
    score += max(0, 25 - max(0, top3_weight - 30))       # penalty if top 3 > 30%
    score = min(100, score)

    grade = "A+" if score >= 90 else "A" if score >= 80 else "B" if score >= 70 else "C" if score >= 60 else "D" if score >= 50 else "F"
    color = GREEN if score >= 70 else YELLOW if score >= 50 else RED

    print(f"  {color}{BOLD}Overall Score: {score:.0f}/100 ({grade}){RESET}")
    print()
    print(f"  Positions:          {n:>3}     (target: 10+)")
    print(f"  Effective Positions:{eff:>6.1f}  (target: 8+)")
    print(f"  Asset Classes:      {n_classes:>3}     (target: 3+)")
    print(f"  Top 3 Concentration:{top3_weight:>5.1f}%  (target: <30%)")
    print(f"  HHI:                {h:>.4f}  (target: <0.15)")

def report_summary_stats(positions):
    total = portfolio_cost(positions)
    print_section("SUMMARY STATISTICS")

    weights = [weight(p, total) * 100 for p in positions]
    costs = [cost_basis(p) for p in positions]

    print(f"  {DIM}Total Cost Basis{RESET}      {fmt_usd(total)}")
    print(f"  {DIM}Mean Position Size{RESET}     {fmt_usd(statistics.mean(costs))}")
    print(f"  {DIM}Median Position Size{RESET}   {fmt_usd(statistics.median(costs))}")
    if len(costs) > 1:
        print(f"  {DIM}Std Dev (Cost){RESET}        {fmt_usd(statistics.stdev(costs))}")
    print(f"  {DIM}Min Weight{RESET}             {min(weights):.1f}%")
    print(f"  {DIM}Max Weight{RESET}             {max(weights):.1f}%")
    print(f"  {DIM}Weight Range{RESET}           {max(weights) - min(weights):.1f}pp")


# ─── Interactive Mode ────────────────────────────────────────────────────────

def interactive(positions):
    """Simple interactive REPL for portfolio queries."""
    total = portfolio_cost(positions)

    commands = {
        "overview":       ("Portfolio overview",          lambda: report_overview(positions)),
        "positions":      ("Position details",            lambda: report_positions(positions)),
        "allocation":     ("Asset class allocation",      lambda: report_allocation_by_class(positions)),
        "concentration":  ("Concentration risk",          lambda: report_concentration(positions)),
        "holding":        ("Holding period analysis",     lambda: report_holding_period(positions)),
        "diversification":("Diversification scorecard",   lambda: report_diversification_score(positions)),
        "stats":          ("Summary statistics",          lambda: report_summary_stats(positions)),
        "all":            ("Run all reports",             None),
    }

    print(f"\n  {BOLD}Portfolio loaded: {len(positions)} positions, {fmt_usd(total)} cost basis{RESET}")
    print(f"\n  {DIM}Commands:{RESET}")
    for cmd, (desc, _) in commands.items():
        print(f"    {CYAN}{cmd:18s}{RESET} {desc}")
    print(f"    {CYAN}{'quit':18s}{RESET} Exit")
    print()

    while True:
        try:
            raw = input(f"  {BLUE}{BOLD}portfolio>{RESET} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not raw:
            continue
        if raw in ("quit", "exit", "q"):
            break
        if raw == "all":
            for cmd, (_, fn) in commands.items():
                if fn:
                    fn()
            continue
        if raw in commands:
            commands[raw][1]()
        else:
            # Fuzzy match
            matches = [k for k in commands if k.startswith(raw)]
            if len(matches) == 1:
                cmd = matches[0]
                if cmd == "all":
                    for c, (_, fn) in commands.items():
                        if fn:
                            fn()
                else:
                    commands[cmd][1]()
            else:
                print(f"  Unknown command: {raw}. Type a command from the list above.")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    csv_path = "sample_data/portfolio_example.csv"
    interactive_mode = False

    for arg in sys.argv[1:]:
        if arg in ("--interactive", "-i"):
            interactive_mode = True
        elif not arg.startswith("-"):
            csv_path = arg

    positions = load_portfolio(csv_path)

    if interactive_mode:
        interactive(positions)
    else:
        report_overview(positions)
        report_positions(positions)
        report_allocation_by_class(positions)
        report_concentration(positions)
        report_holding_period(positions)
        report_diversification_score(positions)
        report_summary_stats(positions)
        print()


if __name__ == "__main__":
    main()
