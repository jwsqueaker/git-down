"""Portfolio Analysis & Tracking Dashboard - Main Application."""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json

# Local imports
from models.database import init_db, get_session, PortfolioPosition
from models.portfolio import Position, PortfolioSnapshot
from services.data_fetcher import MarketDataFetcher, MacroDataFetcher, CorrelationAnalyzer
from services.portfolio_calculator import PortfolioCalculator
from services.monte_carlo import MonteCarloSimulator, estimate_parameters_from_returns
from services.retirement_planner import RetirementPlanner, calculate_retirement_number
from services.tax_planning import TaxPlanner
from services.rebalancing import RebalancingAssistant
from services.dividend_tracker import DividendTracker
from services.portfolio_optimization import PortfolioOptimizer
from services.sector_analysis import SectorAnalyzer
from services.goal_planner import GoalPlanner, Goal
from services.ai_insights import AIInsights
from services.factor_analysis import FactorAnalysis
from services.risk_management import RiskManager
from services.performance_attribution import PerformanceAttribution
from services.fixed_income import FixedIncomeAnalytics
from services.esg_compliance import ESGAnalyzer
from services.liquidity_analysis import LiquidityAnalyzer
from services.multi_portfolio import MultiPortfolioManager, Fund
from services.client_reporting import ClientReportGenerator
from utils.csv_handler import CSVHandler
from utils.helpers import format_percentage, format_currency, get_date_range
from config.settings import BENCHMARKS, MACRO_INDICATORS

# Page configuration
st.set_page_config(
    page_title="Institutional Portfolio Management Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Mobile-responsive CSS optimized for iPhone 16 Pro (393x852pt, 3x)
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Portfolio">
<meta name="theme-color" content="#1f77b4">
<link rel="manifest" href="./static/manifest.json">
<link rel="apple-touch-icon" href="./static/icon-192.png">

<style>
/* ===== iPhone 16 Pro Responsive Layout (393x852pt) ===== */

/* Global mobile reset */
@media screen and (max-width: 480px) {
    /* Safe area insets for Dynamic Island */
    .main .block-container {
        padding-top: env(safe-area-inset-top, 20px) !important;
        padding-bottom: env(safe-area-inset-bottom, 20px) !important;
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        max-width: 100% !important;
    }

    /* Stack all columns vertically on mobile */
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }

    /* Horizontal row -> vertical stack */
    .row-widget.stHorizontalBlock,
    [data-testid="stHorizontalBlock"] {
        flex-direction: column !important;
        gap: 0.5rem !important;
    }

    /* Sidebar: full-width overlay on mobile */
    [data-testid="stSidebar"] {
        min-width: 100vw !important;
        max-width: 100vw !important;
        z-index: 999 !important;
    }

    [data-testid="stSidebar"][aria-expanded="false"] {
        min-width: 0 !important;
        max-width: 0 !important;
    }

    /* Compact header */
    h1 {
        font-size: 1.4rem !important;
        line-height: 1.2 !important;
    }
    h2 {
        font-size: 1.15rem !important;
    }
    h3 {
        font-size: 1rem !important;
    }

    /* Metric cards: compact for mobile */
    [data-testid="stMetric"] {
        padding: 0.5rem !important;
        background: var(--secondary-background-color, #f0f2f6);
        border-radius: 8px;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.1rem !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.7rem !important;
    }

    /* Tabs: scrollable horizontal strip */
    .stTabs [data-baseweb="tab-list"] {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
        flex-wrap: nowrap !important;
        gap: 0 !important;
        padding-bottom: 2px;
    }
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
        display: none;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 0.7rem !important;
        padding: 0.4rem 0.6rem !important;
        white-space: nowrap !important;
        flex-shrink: 0 !important;
    }

    /* Tables: horizontal scroll */
    [data-testid="stDataFrame"],
    [data-testid="stTable"],
    .stDataFrame {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
        font-size: 0.75rem !important;
    }

    /* Charts: full-width, constrained height */
    [data-testid="stPlotlyChart"],
    .js-plotly-plot {
        width: 100% !important;
        max-height: 300px !important;
    }
    [data-testid="stPlotlyChart"] .plotly .main-svg {
        width: 100% !important;
    }

    /* Buttons: full width, touch-friendly */
    .stButton > button {
        width: 100% !important;
        min-height: 44px !important; /* Apple HIG min tap target */
        font-size: 0.9rem !important;
        border-radius: 10px !important;
    }

    /* Inputs: touch-friendly sizing */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        min-height: 44px !important;
        font-size: 16px !important; /* Prevents iOS zoom on focus */
    }

    /* Slider: larger touch target */
    .stSlider [data-baseweb="slider"] [role="slider"] {
        width: 28px !important;
        height: 28px !important;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        padding: 1rem !important;
    }
    [data-testid="stFileUploader"] section {
        padding: 1rem !important;
    }

    /* Expander: touch-friendly */
    .streamlit-expanderHeader {
        min-height: 44px !important;
        font-size: 0.9rem !important;
    }

    /* Remove excessive whitespace */
    .element-container {
        margin-bottom: 0.5rem !important;
    }

    /* Toast/alerts: edge-to-edge */
    [data-testid="stAlert"] {
        border-radius: 8px !important;
        font-size: 0.85rem !important;
    }
}

/* ===== PWA standalone mode tweaks ===== */
@media screen and (display-mode: standalone) {
    /* Hide Streamlit menu and footer in PWA mode */
    #MainMenu, header[data-testid="stHeader"], footer {
        display: none !important;
    }
    .main .block-container {
        padding-top: env(safe-area-inset-top, 48px) !important;
    }
}

/* ===== iPhone landscape ===== */
@media screen and (max-height: 430px) and (orientation: landscape) {
    .main .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }
    h1 { font-size: 1.1rem !important; }
}

/* ===== Smooth scrolling & touch ===== */
html {
    -webkit-text-size-adjust: 100%;
    scroll-behavior: smooth;
}
* {
    -webkit-tap-highlight-color: transparent;
}
</style>

<script>
// Register service worker for PWA
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('./static/sw.js').catch(() => {});
}
</script>
""", unsafe_allow_html=True)

# Initialize database
init_db()

# Initialize session state
if 'portfolio_positions' not in st.session_state:
    st.session_state.portfolio_positions = []
if 'ltcma_data' not in st.session_state:
    st.session_state.ltcma_data = None
if 'multi_portfolio_manager' not in st.session_state:
    st.session_state.multi_portfolio_manager = MultiPortfolioManager()


def load_portfolio_from_db():
    """Load portfolio positions from database."""
    session = get_session()
    positions = session.query(PortfolioPosition).all()
    session.close()

    return [
        Position(
            symbol=p.symbol,
            shares=p.shares,
            purchase_date=p.purchase_date,
            purchase_price=p.purchase_price,
            asset_class=p.asset_class,
            description=p.description
        )
        for p in positions
    ]


def save_portfolio_to_db(positions):
    """Save portfolio positions to database."""
    session = get_session()

    # Clear existing positions
    session.query(PortfolioPosition).delete()

    # Add new positions
    for pos in positions:
        db_pos = PortfolioPosition(
            symbol=pos.symbol,
            shares=pos.shares,
            purchase_date=pos.purchase_date,
            purchase_price=pos.purchase_price,
            asset_class=pos.asset_class,
            description=pos.description
        )
        session.add(db_pos)

    session.commit()
    session.close()


def display_portfolio_overview(calculator):
    """Display portfolio overview section."""
    st.header("📈 Portfolio Overview")

    # Update prices
    with st.spinner("Fetching current prices..."):
        calculator.update_current_prices()

    # Get snapshot
    snapshot = calculator.get_snapshot()

    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Value",
            format_currency(snapshot.total_value),
            delta=format_currency(snapshot.total_gain_loss)
        )

    with col2:
        st.metric(
            "Total Return",
            format_percentage(snapshot.total_return_pct / 100),
            delta=None
        )

    with col3:
        st.metric(
            "Cost Basis",
            format_currency(snapshot.total_cost_basis)
        )

    with col4:
        st.metric(
            "Positions",
            len(snapshot.positions)
        )

    # Display positions table
    st.subheader("Holdings")
    df = snapshot.to_dataframe()

    if not df.empty:
        # Format columns
        df['Avg. Price Paid'] = df['Avg. Price Paid'].apply(lambda x: format_currency(x))
        df['Price'] = df['Price'].apply(lambda x: format_currency(x))
        df['Cost'] = df['Cost'].apply(lambda x: format_currency(x))
        df['Value'] = df['Value'].apply(lambda x: format_currency(x))
        df['Unrealized G/L Amt.'] = df['Unrealized G/L Amt.'].apply(lambda x: format_currency(x))
        df['% of Portfolio'] = df['% of Portfolio'].apply(lambda x: format_percentage(x / 100))
        df['Quantity'] = df['Quantity'].apply(lambda x: f"{x:.2f}")

        st.dataframe(df, use_container_width=True)

        # Asset allocation pie chart
        st.subheader("Asset Allocation")
        allocation = snapshot.get_allocation()

        fig = px.pie(
            values=list(allocation.values()),
            names=list(allocation.keys()),
            title="Portfolio Allocation"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No positions in portfolio")


def display_performance_metrics(calculator, period='1Y'):
    """Display performance metrics section."""
    st.header("📊 Performance Metrics")

    # Date range selector
    col1, col2 = st.columns([1, 3])

    with col1:
        period = st.selectbox(
            "Time Period",
            options=['1M', '3M', '6M', '1Y', '3Y', '5Y', '10Y', 'YTD', 'Inception', 'MAX'],
            index=3
        )

    # Calculate inception date (earliest purchase date)
    snapshot = calculator.get_snapshot()
    if snapshot.positions:
        inception_date = min(p.purchase_date for p in snapshot.positions)
        inception_str = inception_date.strftime('%Y-%m-%d')
    else:
        inception_str = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

    # Get date range
    if period == 'Inception':
        start_date = inception_str
        end_date = datetime.now().strftime('%Y-%m-%d')
    else:
        start_date, end_date = get_date_range(period)

    # Display date range
    with col2:
        st.info(f"📅 Analysis Period: {start_date} to {end_date}")

    # Get historical data first for debugging
    hist_data = calculator.calculate_historical_values(start_date, end_date)

    # Show calculation details
    with st.expander("🔍 Calculation Details (Debug Info)"):
        if not hist_data.empty:
            st.write(f"**Data Points:** {len(hist_data)}")
            st.write(f"**Start Date:** {hist_data.index[0]}")
            st.write(f"**End Date:** {hist_data.index[-1]}")
            st.write(f"**Starting Portfolio Value:** {format_currency(hist_data['value'].iloc[0])}")
            st.write(f"**Ending Portfolio Value:** {format_currency(hist_data['value'].iloc[-1])}")
            st.write(f"**Starting Cost Basis:** {format_currency(hist_data['cost_basis'].iloc[0])}")
            st.write(f"**Ending Cost Basis:** {format_currency(hist_data['cost_basis'].iloc[-1])}")

            # Calculate CORRECT return based on total invested
            end_value = hist_data['value'].iloc[-1]
            total_invested = hist_data['cost_basis'].iloc[-1]
            total_gain = end_value - total_invested

            if total_invested > 0:
                correct_return = (total_gain / total_invested) * 100
            else:
                correct_return = 0

            st.write("---")
            st.write("**📊 CORRECT RETURN CALCULATION:**")
            st.write(f"**Total Invested (Cost Basis):** {format_currency(total_invested)}")
            st.write(f"**Current Value:** {format_currency(end_value)}")
            st.write(f"**Total Gain/Loss:** {format_currency(total_gain)}")
            st.write(f"**Return:** {correct_return:.2f}%")
            st.write(f"*Formula: (Current Value - Total Invested) / Total Invested × 100*")
            st.write("---")

            # Show if there were cash flows
            cost_change = hist_data['cost_basis'].iloc[-1] - hist_data['cost_basis'].iloc[0]
            if abs(cost_change) > 0.01:
                st.info(f"💰 Money added during period: {format_currency(cost_change)}")
                st.write("This is normal if you added positions during the selected time period.")
            else:
                st.success("✓ No new money added during this period")

            # Show sample of data
            st.write("**Sample Data (first 5 rows):**")
            sample = hist_data.head().copy()
            sample['value'] = sample['value'].apply(format_currency)
            sample['cost_basis'] = sample['cost_basis'].apply(format_currency)
            sample['returns'] = sample['returns'].apply(lambda x: f"{x*100:.2f}%" if pd.notna(x) else "N/A")
            st.dataframe(sample)
        else:
            st.error("No historical data available for this period")

    # Calculate metrics
    with st.spinner("Calculating performance metrics..."):
        metrics = calculator.calculate_performance_metrics(
            start_date=start_date,
            end_date=end_date,
            benchmark='^GSPC'  # S&P 500
        )

    # Display metrics
    metrics_dict = metrics.to_dict()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Annualized Return", f"{metrics_dict['Annualized Return (%)']}%")
        st.metric("Total Return", f"{metrics_dict['Total Return (%)']}%")

    with col2:
        st.metric("Sharpe Ratio", metrics_dict['Sharpe Ratio'])
        st.metric("Sortino Ratio", metrics_dict['Sortino Ratio'])

    with col3:
        st.metric("Max Drawdown", f"{metrics_dict['Max Drawdown (%)']}%")
        st.metric("Calmar Ratio", metrics_dict['Calmar Ratio'])

    with col4:
        st.metric("Volatility", f"{metrics_dict['Volatility (%)']}%")
        if metrics_dict.get('Beta'):
            st.metric("Beta", metrics_dict['Beta'])

    # Additional metrics if available
    if metrics_dict.get('Alpha (%)'):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Alpha", f"{metrics_dict['Alpha (%)']}%")
        with col2:
            if metrics_dict.get('Treynor Ratio'):
                st.metric("Treynor Ratio", metrics_dict['Treynor Ratio'])
        with col3:
            if metrics_dict.get('Information Ratio'):
                st.metric("Information Ratio", metrics_dict['Information Ratio'])

    # Multi-Period Returns Table
    st.subheader("📅 Returns by Period")

    with st.spinner("Calculating multi-period returns..."):
        multi_period_returns = calculator.calculate_multi_period_returns()

    if multi_period_returns:
        # Create DataFrame for display
        returns_data = []
        for period, data in multi_period_returns.items():
            returns_data.append({
                'Period': period,
                'Total Return': f"{data['total_return']:.2f}%",
                'Annualized Return': f"{data['annualized_return']:.2f}%",
                'Total Invested': format_currency(data['total_invested']),
                'Current Value': format_currency(data['current_value']),
                'Gain/Loss': format_currency(data['total_gain']),
                'Start Date': data['start_date'],
                'End Date': data['end_date']
            })

        returns_df = pd.DataFrame(returns_data)

        # Display the table
        st.dataframe(returns_df, use_container_width=True, hide_index=True)

        # Show calculation explanation
        st.info("""
        **How Returns are Calculated:**
        - **Total Invested** = Cost basis at end of period (all money you put in)
        - **Current Value** = Market value at end of period
        - **Gain/Loss** = Current Value - Total Invested
        - **Return %** = (Gain/Loss / Total Invested) × 100
        """)


        # Show a bar chart of returns
        fig_returns = go.Figure()

        fig_returns.add_trace(go.Bar(
            x=[r['Period'] for r in returns_data],
            y=[float(r['Total Return'].replace('%', '')) for r in returns_data],
            name='Total Return',
            marker_color='lightblue',
            text=[r['Total Return'] for r in returns_data],
            textposition='outside'
        ))

        fig_returns.add_trace(go.Bar(
            x=[r['Period'] for r in returns_data],
            y=[float(r['Annualized Return'].replace('%', '')) for r in returns_data],
            name='Annualized Return',
            marker_color='darkblue',
            text=[r['Annualized Return'] for r in returns_data],
            textposition='outside'
        ))

        fig_returns.update_layout(
            title="Returns by Time Period",
            xaxis_title="Period",
            yaxis_title="Return (%)",
            barmode='group',
            height=400
        )

        st.plotly_chart(fig_returns, use_container_width=True)
    else:
        st.info("Not enough historical data to calculate multi-period returns")

    # Historical performance chart
    st.subheader("Historical Performance")

    hist_data = calculator.calculate_historical_values(start_date, end_date)

    if not hist_data.empty:
        # Normalize to 100
        normalized = (hist_data['value'] / hist_data['value'].iloc[0]) * 100

        # Get benchmark data
        benchmark_data = MarketDataFetcher.get_benchmark_data('S&P 500', start_date, end_date)

        if not benchmark_data.empty:
            benchmark_normalized = (benchmark_data['Close'] / benchmark_data['Close'].iloc[0]) * 100

            # Create comparison chart
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=normalized.index,
                y=normalized.values,
                mode='lines',
                name='Portfolio',
                line=dict(color='#1f77b4', width=2)
            ))

            fig.add_trace(go.Scatter(
                x=benchmark_normalized.index,
                y=benchmark_normalized.values,
                mode='lines',
                name='S&P 500',
                line=dict(color='#ff7f0e', width=2)
            ))

            fig.update_layout(
                title="Portfolio vs S&P 500 (Normalized to 100)",
                xaxis_title="Date",
                yaxis_title="Value (Base 100)",
                hovermode='x unified',
                height=500
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            # Just plot portfolio
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=normalized.index,
                y=normalized.values,
                mode='lines',
                name='Portfolio'
            ))
            fig.update_layout(title="Portfolio Performance", height=500)
            st.plotly_chart(fig, use_container_width=True)

        # Portfolio Value vs Cost Basis
        st.subheader("Portfolio Value vs Cost Basis")

        fig2 = go.Figure()

        fig2.add_trace(go.Scatter(
            x=hist_data.index,
            y=hist_data['value'],
            mode='lines',
            name='Market Value',
            line=dict(color='#1f77b4', width=2),
            fill='tonexty'
        ))

        fig2.add_trace(go.Scatter(
            x=hist_data.index,
            y=hist_data['cost_basis'],
            mode='lines',
            name='Cost Basis',
            line=dict(color='#ff7f0e', width=2, dash='dash')
        ))

        # Add unrealized gains area
        gains = hist_data['value'] - hist_data['cost_basis']
        fig2.add_trace(go.Scatter(
            x=hist_data.index,
            y=gains,
            mode='lines',
            name='Unrealized Gain/Loss',
            line=dict(color='green', width=1),
            yaxis='y2'
        ))

        fig2.update_layout(
            title="Portfolio Value vs Cost Basis Over Time",
            xaxis_title="Date",
            yaxis_title="Dollar Value ($)",
            yaxis2=dict(
                title="Gain/Loss ($)",
                overlaying='y',
                side='right'
            ),
            hovermode='x unified',
            height=500
        )

        st.plotly_chart(fig2, use_container_width=True)

        # Summary statistics
        st.subheader("Period Summary")

        current_value = hist_data['value'].iloc[-1]
        current_cost = hist_data['cost_basis'].iloc[-1]
        total_gain = current_value - current_cost
        total_return_pct = (total_gain / current_cost * 100) if current_cost > 0 else 0

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Current Value", format_currency(current_value))
        with col2:
            st.metric("Total Cost Basis", format_currency(current_cost))
        with col3:
            st.metric("Total Gain/Loss", format_currency(total_gain),
                     delta=f"{total_return_pct:.2f}%")
        with col4:
            st.metric("Return %", f"{total_return_pct:.2f}%")


def display_benchmark_comparison(calculator):
    """Display benchmark comparison section."""
    st.header("🎯 Benchmark Comparison")

    col1, col2 = st.columns([1, 3])

    with col1:
        benchmark = st.selectbox(
            "Select Benchmark",
            options=list(BENCHMARKS.keys()),
            index=0
        )

        period = st.selectbox(
            "Period",
            options=['1M', '3M', '6M', '1Y', '3Y', '5Y'],
            index=3,
            key='benchmark_period'
        )

    start_date, end_date = get_date_range(period)

    # Calculate comparison
    with st.spinner("Comparing to benchmark..."):
        comparison = calculator.compare_to_benchmark(
            benchmark=BENCHMARKS[benchmark],
            start_date=start_date,
            end_date=end_date
        )

    if comparison:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Portfolio Return",
                format_percentage(comparison['portfolio_return'])
            )
            st.metric(
                "Portfolio Sharpe",
                f"{comparison['portfolio_sharpe']:.2f}"
            )

        with col2:
            st.metric(
                f"{benchmark} Return",
                format_percentage(comparison['benchmark_return'])
            )
            st.metric(
                f"{benchmark} Sharpe",
                f"{comparison['benchmark_sharpe']:.2f}"
            )

        with col3:
            st.metric("Beta", f"{comparison['beta']:.2f}")
            st.metric("Alpha", format_percentage(comparison['alpha']))

        # Additional metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Correlation", f"{comparison['correlation']:.2f}")
        with col2:
            st.metric("Tracking Error", format_percentage(comparison['tracking_error']))
        with col3:
            st.metric("Information Ratio", f"{comparison['information_ratio']:.2f}")


def display_macro_indicators():
    """Display macro economic indicators."""
    st.header("🌍 Macro Economic Indicators")

    macro_fetcher = MacroDataFetcher()

    if macro_fetcher.fred is None:
        st.warning("FRED API key not configured. Please add FRED_API_KEY to .env file.")
        st.info("Get a free API key at: https://fred.stlouisfed.org/docs/api/api_key.html")
        return

    # Get latest values
    with st.spinner("Fetching macro indicators..."):
        latest_values = macro_fetcher.get_latest_values()

    if not latest_values:
        st.error("Unable to fetch macro indicators. Please check your FRED API key.")
        return

    # Display in cards
    st.subheader("Current Values")

    # Create 3 columns
    indicators_list = list(latest_values.items())
    rows = [indicators_list[i:i+3] for i in range(0, len(indicators_list), 3)]

    for row in rows:
        cols = st.columns(3)
        for idx, (name, value) in enumerate(row):
            with cols[idx]:
                # Get YoY change
                yoy = macro_fetcher.get_yoy_change(name)
                if yoy is not None:
                    st.metric(
                        name,
                        f"{value:.2f}",
                        delta=f"{yoy:+.2f}% YoY"
                    )
                else:
                    st.metric(name, f"{value:.2f}")

    # Historical chart
    st.subheader("Historical Trends")

    selected_indicators = st.multiselect(
        "Select indicators to chart",
        options=list(MACRO_INDICATORS.keys()),
        default=['GDP Growth', 'CPI (Inflation)', 'Unemployment Rate']
    )

    if selected_indicators:
        period = st.selectbox(
            "Time Period",
            options=['1Y', '3Y', '5Y', '10Y'],
            index=2,
            key='macro_period'
        )

        start_date, end_date = get_date_range(period)

        indicator_data = {}
        for indicator in selected_indicators:
            series = macro_fetcher.get_indicator(indicator, start_date, end_date)
            if not series.empty:
                indicator_data[indicator] = series

        if indicator_data:
            fig = go.Figure()

            for name, series in indicator_data.items():
                fig.add_trace(go.Scatter(
                    x=series.index,
                    y=series.values,
                    mode='lines',
                    name=name
                ))

            fig.update_layout(
                title="Macro Indicators Over Time",
                xaxis_title="Date",
                yaxis_title="Value",
                hovermode='x unified',
                height=500
            )

            st.plotly_chart(fig, use_container_width=True)


def display_correlation_analysis(calculator):
    """Display correlation analysis."""
    st.header("🔗 Correlation Analysis")

    period = st.selectbox(
        "Analysis Period",
        options=['1Y', '3Y', '5Y'],
        index=1,
        key='corr_period'
    )

    start_date, end_date = get_date_range(period)

    # Calculate correlation matrix
    with st.spinner("Calculating correlations..."):
        corr_matrix = calculator.get_correlation_matrix(start_date, end_date)

    if not corr_matrix.empty:
        st.subheader("Position Correlation Matrix")

        # Create heatmap
        fig = px.imshow(
            corr_matrix,
            labels=dict(color="Correlation"),
            x=corr_matrix.columns,
            y=corr_matrix.index,
            color_continuous_scale='RdBu_r',
            zmin=-1,
            zmax=1
        )

        fig.update_layout(
            title="Correlation Heatmap",
            height=600
        )

        st.plotly_chart(fig, use_container_width=True)

        # Display matrix as table
        with st.expander("View Correlation Table"):
            st.dataframe(corr_matrix.style.background_gradient(cmap='RdBu_r', vmin=-1, vmax=1))


def display_ltcma_analysis():
    """Display LTCMA correlation analysis."""
    st.header("📉 JP Morgan Long-Term Capital Market Assumptions")

    if st.session_state.ltcma_data is None:
        st.info("Upload JP Morgan LTCMA data to analyze long-term expected returns and volatility by asset class.")

        # Show template
        with st.expander("Download CSV Template"):
            template = CSVHandler.create_ltcma_template()
            st.download_button(
                "Download LTCMA Template",
                template,
                file_name="ltcma_template.csv",
                mime="text/csv"
            )
        return

    ltcma_df = st.session_state.ltcma_data.copy()

    # Format for display
    display_df = ltcma_df.copy()

    # Convert to percentages for display
    display_df['Expected Return (%)'] = (display_df['expected_return'] * 100).round(2)
    display_df['Volatility (%)'] = (display_df['volatility'] * 100).round(2)

    # Rename and select columns for display
    display_df = display_df.rename(columns={'asset_class': 'Asset Class'})
    display_df = display_df[['Asset Class', 'Expected Return (%)', 'Volatility (%)']]

    st.subheader("📊 Long-Term Capital Market Assumptions")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Display as chart
    st.subheader("Expected Returns by Asset Class")

    fig = go.Figure()

    # Sort by return for better visualization
    plot_df = ltcma_df.sort_values('expected_return', ascending=True)

    fig.add_trace(go.Bar(
        y=plot_df['asset_class'],
        x=plot_df['expected_return'] * 100,
        name='Expected Return',
        marker_color='#1f77b4',
        orientation='h'
    ))

    fig.update_layout(
        title="LTCMA Expected Returns by Asset Class",
        yaxis_title="Asset Class",
        xaxis_title="Expected Return (%)",
        height=max(500, len(ltcma_df) * 25),
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

    # Risk-Return scatter
    st.subheader("Risk-Return Efficient Frontier")

    fig = px.scatter(
        ltcma_df,
        x='volatility',
        y='expected_return',
        text='asset_class',
        labels={
            'volatility': 'Volatility (Risk) %',
            'expected_return': 'Expected Return %'
        },
        hover_data={'asset_class': True, 'volatility': ':.2f', 'expected_return': ':.2f'}
    )

    # Convert to percentage for display
    fig.update_traces(
        textposition='top center',
        textfont_size=8,
        marker=dict(size=10, color='#1f77b4')
    )

    # Update axes to show percentages
    fig.update_xaxes(tickformat='.1f', title='Volatility (%)')
    fig.update_yaxes(tickformat='.1f', title='Expected Return (%)')

    # Scale values to percentages
    fig.data[0].x = fig.data[0].x * 100
    fig.data[0].y = fig.data[0].y * 100

    fig.update_layout(height=600)

    st.plotly_chart(fig, use_container_width=True)

    # Summary statistics
    st.subheader("Summary Statistics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        avg_return = ltcma_df['expected_return'].mean() * 100
        st.metric("Average Expected Return", f"{avg_return:.2f}%")

    with col2:
        avg_vol = ltcma_df['volatility'].mean() * 100
        st.metric("Average Volatility", f"{avg_vol:.2f}%")

    with col3:
        max_return = ltcma_df['expected_return'].max() * 100
        best_asset = ltcma_df.loc[ltcma_df['expected_return'].idxmax(), 'asset_class']
        st.metric("Highest Return", f"{max_return:.2f}%", delta=best_asset)

    with col4:
        min_vol = ltcma_df['volatility'].min() * 100
        safest_asset = ltcma_df.loc[ltcma_df['volatility'].idxmin(), 'asset_class']
        st.metric("Lowest Volatility", f"{min_vol:.2f}%", delta=safest_asset)


def display_monte_carlo_simulation(calculator):
    """Display Monte Carlo simulation projections."""
    st.header("🎲 Monte Carlo Simulation")

    st.markdown("""
    Project future portfolio values using Monte Carlo simulation with thousands of randomized scenarios.
    Adjust assumptions below to see how different parameters affect your projections.
    """)

    # Get current portfolio value
    snapshot = calculator.get_snapshot()
    current_value = snapshot.total_value

    # Sidebar for simulation parameters
    st.subheader("Simulation Parameters")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Portfolio Settings**")

        initial_value = st.number_input(
            "Initial Portfolio Value ($)",
            min_value=1000.0,
            value=float(current_value),
            step=1000.0,
            help="Starting portfolio value for simulation"
        )

        years = st.slider(
            "Time Horizon (Years)",
            min_value=1,
            max_value=50,
            value=30,
            help="Number of years to simulate"
        )

        annual_contribution = st.number_input(
            "Annual Contribution ($)",
            min_value=0.0,
            value=0.0,
            step=1000.0,
            help="Additional yearly investment"
        )

        contribution_growth = st.slider(
            "Contribution Growth Rate (%/year)",
            min_value=0.0,
            max_value=10.0,
            value=3.0,
            step=0.5,
            help="Annual increase in contributions (inflation adjustment)"
        ) / 100

    with col2:
        st.markdown("**Return Assumptions**")

        # Option to use historical data or custom assumptions
        use_historical = st.checkbox(
            "Use Historical Portfolio Returns",
            value=True,
            help="Calculate expected return and volatility from your portfolio's historical performance"
        )

        if use_historical:
            try:
                # Calculate historical returns
                returns = calculator.calculate_returns(
                    start_date=(datetime.now() - timedelta(days=365*3)).strftime('%Y-%m-%d')
                )

                if not returns.empty:
                    exp_return, volatility = estimate_parameters_from_returns(returns)
                    st.info(f"📊 Historical: {exp_return*100:.1f}% return, {volatility*100:.1f}% volatility")
                else:
                    st.warning("No historical data available, using custom assumptions")
                    use_historical = False
                    exp_return = 0.08
                    volatility = 0.15
            except:
                st.warning("Error calculating historical returns, using custom assumptions")
                use_historical = False
                exp_return = 0.08
                volatility = 0.15

        if not use_historical:
            exp_return = st.slider(
                "Expected Annual Return (%)",
                min_value=-10.0,
                max_value=30.0,
                value=8.0,
                step=0.5,
                help="Average annual return assumption"
            ) / 100

            volatility = st.slider(
                "Annual Volatility/Risk (%)",
                min_value=1.0,
                max_value=50.0,
                value=15.0,
                step=1.0,
                help="Standard deviation of returns (higher = more risk)"
            ) / 100

    # Advanced settings
    with st.expander("⚙️ Advanced Settings"):
        col1, col2, col3 = st.columns(3)

        with col1:
            n_simulations = st.select_slider(
                "Number of Simulations",
                options=[1000, 5000, 10000, 25000, 50000],
                value=10000,
                help="More simulations = more accurate but slower"
            )

        with col2:
            distribution = st.selectbox(
                "Return Distribution",
                options=['lognormal', 'normal'],
                index=0,
                help="Log-normal is more realistic for stocks"
            )

        with col3:
            rebalance_freq = st.selectbox(
                "Rebalance Frequency",
                options=['annual', 'monthly', 'daily'],
                index=0,
                help="How often to apply returns"
            )

        random_seed = st.number_input(
            "Random Seed (for reproducibility)",
            min_value=0,
            max_value=9999,
            value=42,
            help="Same seed = same results"
        )

    # Run simulation button
    if st.button("🚀 Run Simulation", type="primary"):
        with st.spinner(f"Running {n_simulations:,} simulations..."):
            # Create simulator
            simulator = MonteCarloSimulator(
                initial_value=initial_value,
                expected_return=exp_return,
                volatility=volatility,
                years=years,
                simulations=n_simulations,
                annual_contribution=annual_contribution,
                contribution_growth=contribution_growth,
                random_seed=random_seed
            )

            # Run simulation
            results_df = simulator.run_simulation(
                distribution=distribution,
                rebalance_frequency=rebalance_freq
            )

            # Store in session state
            st.session_state.monte_carlo_results = {
                'simulator': simulator,
                'results': results_df,
                'parameters': {
                    'initial_value': initial_value,
                    'years': years,
                    'expected_return': exp_return,
                    'volatility': volatility,
                    'simulations': n_simulations
                }
            }

        st.success("✅ Simulation complete!")

    # Display results if available
    if 'monte_carlo_results' in st.session_state:
        results = st.session_state.monte_carlo_results
        simulator = results['simulator']
        results_df = results['results']
        params = results['parameters']

        st.markdown("---")
        st.subheader("📊 Simulation Results")

        # Summary statistics
        stats = simulator.get_statistics()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Median Final Value",
                format_currency(stats['median']),
                delta=format_currency(stats['median'] - params['initial_value'])
            )

        with col2:
            st.metric(
                "Mean Final Value",
                format_currency(stats['mean']),
                delta=format_currency(stats['mean'] - params['initial_value'])
            )

        with col3:
            median_return = ((stats['median'] / params['initial_value']) ** (1/params['years']) - 1) * 100
            st.metric(
                "Median Annual Return",
                f"{median_return:.1f}%"
            )

        with col4:
            st.metric(
                "Probability of Loss",
                f"{stats['probability_of_loss']*100:.1f}%"
            )

        # Percentile ranges
        st.subheader("Outcome Ranges")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Pessimistic (5th percentile)**")
            st.metric("Final Value", format_currency(stats['p5']))

        with col2:
            st.markdown("**Expected (50th percentile)**")
            st.metric("Final Value", format_currency(stats['median']))

        with col3:
            st.markdown("**Optimistic (95th percentile)**")
            st.metric("Final Value", format_currency(stats['p95']))

        # Fan chart showing percentile ranges
        st.subheader("Projected Portfolio Value Over Time")

        fig = go.Figure()

        # Add percentile bands
        fig.add_trace(go.Scatter(
            x=results_df['date'],
            y=results_df['p95'],
            name='95th Percentile',
            line=dict(color='rgba(31, 119, 180, 0.3)'),
            mode='lines'
        ))

        fig.add_trace(go.Scatter(
            x=results_df['date'],
            y=results_df['p75'],
            name='75th Percentile',
            fill='tonexty',
            fillcolor='rgba(31, 119, 180, 0.2)',
            line=dict(color='rgba(31, 119, 180, 0.4)'),
            mode='lines'
        ))

        fig.add_trace(go.Scatter(
            x=results_df['date'],
            y=results_df['median'],
            name='Median (50th)',
            line=dict(color='#1f77b4', width=3),
            mode='lines'
        ))

        fig.add_trace(go.Scatter(
            x=results_df['date'],
            y=results_df['p25'],
            name='25th Percentile',
            fill='tonexty',
            fillcolor='rgba(31, 119, 180, 0.2)',
            line=dict(color='rgba(31, 119, 180, 0.4)'),
            mode='lines'
        ))

        fig.add_trace(go.Scatter(
            x=results_df['date'],
            y=results_df['p5'],
            name='5th Percentile',
            fill='tonexty',
            fillcolor='rgba(31, 119, 180, 0.2)',
            line=dict(color='rgba(31, 119, 180, 0.3)'),
            mode='lines'
        ))

        fig.update_layout(
            title="Portfolio Value Projection (Percentile Bands)",
            xaxis_title="Date",
            yaxis_title="Portfolio Value ($)",
            hovermode='x unified',
            height=600
        )

        st.plotly_chart(fig, use_container_width=True)

        # Distribution of final values
        st.subheader("Distribution of Final Portfolio Values")

        fig = go.Figure()

        fig.add_trace(go.Histogram(
            x=simulator.final_values,
            nbinsx=50,
            name='Final Values',
            marker_color='#1f77b4'
        ))

        # Add vertical lines for percentiles
        fig.add_vline(x=stats['p5'], line_dash="dash", line_color="red",
                     annotation_text="5th percentile")
        fig.add_vline(x=stats['median'], line_dash="dash", line_color="green",
                     annotation_text="Median")
        fig.add_vline(x=stats['p95'], line_dash="dash", line_color="red",
                     annotation_text="95th percentile")

        fig.update_layout(
            title="Distribution of Final Values",
            xaxis_title="Final Portfolio Value ($)",
            yaxis_title="Frequency",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

        # Sample paths
        st.subheader("Sample Simulation Paths")

        sample_paths = simulator.get_sample_paths(n_samples=100)

        fig = go.Figure()

        for col in sample_paths.columns:
            fig.add_trace(go.Scatter(
                x=results_df['date'],
                y=sample_paths[col],
                mode='lines',
                line=dict(width=0.5, color='rgba(100, 100, 100, 0.1)'),
                showlegend=False,
                hoverinfo='skip'
            ))

        # Add median line
        fig.add_trace(go.Scatter(
            x=results_df['date'],
            y=results_df['median'],
            name='Median',
            line=dict(color='red', width=3),
            mode='lines'
        ))

        fig.update_layout(
            title="100 Random Simulation Paths",
            xaxis_title="Date",
            yaxis_title="Portfolio Value ($)",
            height=500
        )

        st.plotly_chart(fig, use_container_width=True)

        # Goal probability calculator
        st.subheader("🎯 Goal Achievement Calculator")

        goal_amount = st.number_input(
            "Target Portfolio Value ($)",
            min_value=1000.0,
            value=float(params['initial_value'] * 2),
            step=10000.0
        )

        if goal_amount:
            probability = simulator.get_probability_of_goal(goal_amount)

            col1, col2 = st.columns([1, 2])

            with col1:
                st.metric(
                    "Probability of Success",
                    f"{probability*100:.1f}%"
                )

            with col2:
                if probability >= 0.9:
                    st.success(f"🎉 Very likely to reach ${goal_amount:,.0f}")
                elif probability >= 0.75:
                    st.info(f"✅ Good chance of reaching ${goal_amount:,.0f}")
                elif probability >= 0.5:
                    st.warning(f"⚠️ Moderate chance of reaching ${goal_amount:,.0f}")
                else:
                    st.error(f"❌ Unlikely to reach ${goal_amount:,.0f} with current assumptions")

        # Detailed statistics table
        with st.expander("📈 Detailed Statistics"):
            stats_df = pd.DataFrame({
                'Metric': [
                    'Mean', 'Median', 'Std Dev',
                    'Minimum', 'Maximum',
                    '5th Percentile', '10th Percentile', '25th Percentile',
                    '75th Percentile', '90th Percentile', '95th Percentile',
                    'Probability of Loss'
                ],
                'Value': [
                    format_currency(stats['mean']),
                    format_currency(stats['median']),
                    format_currency(stats['std']),
                    format_currency(stats['min']),
                    format_currency(stats['max']),
                    format_currency(stats['p5']),
                    format_currency(stats['p10']),
                    format_currency(stats['p25']),
                    format_currency(stats['p75']),
                    format_currency(stats['p90']),
                    format_currency(stats['p95']),
                    f"{stats['probability_of_loss']*100:.2f}%"
                ]
            })

            st.dataframe(stats_df, use_container_width=True)

    else:
        st.info("👆 Configure parameters above and click 'Run Simulation' to see projections")


def display_retirement_planning(calculator):
    """Display retirement planning and goal achievement analysis."""
    st.header("🏖️ Retirement Planning")

    st.markdown("""
    Calculate the likelihood of reaching your retirement goals with comprehensive scenario analysis.
    See if you're on track and what adjustments might be needed.
    """)

    # Get current portfolio value
    snapshot = calculator.get_snapshot()
    current_value = snapshot.total_value

    # Personal Information
    st.subheader("📋 Your Information")

    col1, col2, col3 = st.columns(3)

    with col1:
        current_age = st.number_input(
            "Current Age",
            min_value=18,
            max_value=100,
            value=35,
            step=1
        )

    with col2:
        retirement_age = st.number_input(
            "Target Retirement Age",
            min_value=current_age + 1,
            max_value=100,
            value=65,
            step=1
        )

    with col3:
        life_expectancy = st.number_input(
            "Life Expectancy",
            min_value=retirement_age + 1,
            max_value=120,
            value=90,
            step=1
        )

    # Financial Inputs
    st.subheader("💰 Financial Inputs")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Accumulation Phase (Until Retirement)**")

        current_portfolio = st.number_input(
            "Current Portfolio Value ($)",
            min_value=0.0,
            value=float(current_value),
            step=1000.0
        )

        annual_contribution = st.number_input(
            "Annual Contribution/Savings ($)",
            min_value=0.0,
            value=20000.0,
            step=1000.0,
            help="How much you save each year"
        )

        contribution_growth = st.slider(
            "Contribution Growth Rate (%/year)",
            min_value=0.0,
            max_value=10.0,
            value=3.0,
            step=0.5,
            help="Annual increase in savings (raises, inflation)"
        ) / 100

        accumulation_return = st.slider(
            "Expected Return - Working Years (%)",
            min_value=0.0,
            max_value=15.0,
            value=8.0,
            step=0.5
        ) / 100

        accumulation_volatility = st.slider(
            "Volatility - Working Years (%)",
            min_value=1.0,
            max_value=30.0,
            value=15.0,
            step=1.0
        ) / 100

    with col2:
        st.markdown("**Retirement Phase**")

        desired_income = st.number_input(
            "Desired Annual Retirement Income ($)",
            min_value=0.0,
            value=80000.0,
            step=5000.0,
            help="Annual income needed in retirement (today's dollars)"
        )

        st.markdown("**Other Income Sources**")

        social_security = st.number_input(
            "Expected Social Security ($/year)",
            min_value=0.0,
            value=25000.0,
            step=1000.0
        )

        pension = st.number_input(
            "Pension Income ($/year)",
            min_value=0.0,
            value=0.0,
            step=1000.0
        )

        healthcare_costs = st.number_input(
            "Annual Healthcare Costs ($)",
            min_value=0.0,
            value=10000.0,
            step=1000.0
        )

        retirement_return = st.slider(
            "Expected Return - Retirement (%)",
            min_value=0.0,
            max_value=12.0,
            value=6.0,
            step=0.5,
            help="Typically lower than working years"
        ) / 100

        retirement_volatility = st.slider(
            "Volatility - Retirement (%)",
            min_value=1.0,
            max_value=20.0,
            value=10.0,
            step=1.0,
            help="Typically lower than working years"
        ) / 100

    # Advanced Settings
    with st.expander("⚙️ Advanced Settings"):
        col1, col2 = st.columns(2)

        with col1:
            inflation_rate = st.slider(
                "Inflation Rate (%)",
                min_value=0.0,
                max_value=10.0,
                value=3.0,
                step=0.5
            ) / 100

            simulations = st.select_slider(
                "Monte Carlo Simulations",
                options=[5000, 10000, 25000],
                value=10000
            )

        with col2:
            other_expenses = st.number_input(
                "Other Annual Expenses ($)",
                min_value=0.0,
                value=0.0,
                step=1000.0
            )

    # Calculate Button
    if st.button("🚀 Analyze Retirement Plan", type="primary"):
        with st.spinner("Running retirement analysis..."):
            # Create retirement planner
            planner = RetirementPlanner(
                current_age=current_age,
                retirement_age=retirement_age,
                life_expectancy=life_expectancy,
                current_portfolio_value=current_portfolio,
                annual_contribution=annual_contribution,
                contribution_growth_rate=contribution_growth,
                expected_return=accumulation_return,
                volatility=accumulation_volatility,
                simulations=simulations
            )

            # Calculate retirement readiness
            analysis = planner.calculate_retirement_readiness(
                desired_annual_income=desired_income,
                social_security_annual=social_security,
                pension_annual=pension,
                healthcare_annual=healthcare_costs,
                other_expenses_annual=other_expenses,
                inflation_rate=inflation_rate,
                retirement_return=retirement_return,
                retirement_volatility=retirement_volatility
            )

            # Store in session state
            st.session_state.retirement_analysis = analysis
            st.session_state.retirement_planner = planner

        st.success("✅ Analysis complete!")

    # Display Results
    if 'retirement_analysis' in st.session_state:
        analysis = st.session_state.retirement_analysis

        st.markdown("---")
        st.subheader("📊 Retirement Readiness Analysis")

        # Success Rate - Big Display
        success_rate = analysis['success_rate']
        readiness_level = analysis['readiness_level']
        readiness_color = analysis['readiness_color']

        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            st.markdown(f"""
            <div style="text-align: center; padding: 30px; background-color: {readiness_color}20; border-radius: 10px;">
                <h1 style="color: {readiness_color}; margin: 0;">{success_rate*100:.1f}%</h1>
                <h3 style="margin: 10px 0;">Probability of Success</h3>
                <p style="font-size: 18px; margin: 0;"><b>{readiness_level}</b></p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.metric(
                "Years to Retirement",
                f"{analysis['years_to_retirement']} years"
            )
            st.metric(
                "Years in Retirement",
                f"{analysis['years_in_retirement']} years"
            )

        with col3:
            st.metric(
                "Successful Scenarios",
                f"{analysis['successful_scenarios']:,}"
            )
            st.metric(
                "Failed Scenarios",
                f"{analysis['failed_scenarios']:,}"
            )

        # Interpretation
        st.markdown("### What This Means")

        if success_rate >= 0.90:
            st.success(f"""
            🎉 **Excellent!** Your retirement plan has a {success_rate*100:.0f}% chance of success.
            You're very likely to meet your retirement goals with your current strategy.
            """)
        elif success_rate >= 0.75:
            st.info(f"""
            ✅ **Good!** Your retirement plan has a {success_rate*100:.0f}% chance of success.
            You're on a solid track, though you might consider boosting savings to increase your margin of safety.
            """)
        elif success_rate >= 0.60:
            st.warning(f"""
            ⚠️ **Fair.** Your retirement plan has a {success_rate*100:.0f}% chance of success.
            Consider increasing savings, working longer, or adjusting retirement expectations.
            """)
        else:
            st.error(f"""
            ❌ **Needs Improvement.** Your retirement plan has only a {success_rate*100:.0f}% chance of success.
            Significant adjustments are recommended to meet your retirement goals.
            """)

        # Portfolio Projections
        st.subheader("💼 Projected Retirement Portfolio")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Median at Retirement",
                format_currency(analysis['median_retirement_value']),
                help="50% chance of having more, 50% less"
            )

        with col2:
            st.metric(
                "Pessimistic (10th %)",
                format_currency(analysis['p10_retirement_value']),
                help="90% chance of having more than this"
            )

        with col3:
            st.metric(
                "Optimistic (90th %)",
                format_currency(analysis['p90_retirement_value']),
                help="10% chance of having more than this"
            )

        # Income Analysis
        st.subheader("💵 Retirement Income Analysis")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Income Sources**")

            total_income = desired_income
            income_from_portfolio = analysis['net_income_needed']
            other_income = social_security + pension

            income_breakdown = pd.DataFrame({
                'Source': ['Portfolio Withdrawals', 'Social Security', 'Pension', 'Total'],
                'Annual Amount': [
                    format_currency(income_from_portfolio),
                    format_currency(social_security),
                    format_currency(pension),
                    format_currency(total_income)
                ]
            })

            st.dataframe(income_breakdown, use_container_width=True, hide_index=True)

        with col2:
            st.markdown("**Withdrawal Analysis**")

            withdrawal_rate = analysis['withdrawal_rate']
            sustainable_4pct = analysis['sustainable_income_4pct']

            withdrawal_comparison = pd.DataFrame({
                'Metric': [
                    'Your Withdrawal Rate',
                    'Traditional 4% Rule',
                    'Sustainable Income (4%)',
                    'Difference'
                ],
                'Value': [
                    f"{withdrawal_rate*100:.2f}%",
                    "4.00%",
                    format_currency(sustainable_4pct),
                    format_currency(sustainable_4pct - income_from_portfolio)
                ]
            })

            st.dataframe(withdrawal_comparison, use_container_width=True, hide_index=True)

            if withdrawal_rate > 0.04:
                st.warning(f"⚠️ Your {withdrawal_rate*100:.1f}% withdrawal rate exceeds the traditional 4% rule")
            else:
                st.success(f"✅ Your {withdrawal_rate*100:.1f}% withdrawal rate is sustainable")

        # Shortfall/Surplus Analysis
        st.subheader("📈 Gap Analysis")

        shortfall = analysis['shortfall']
        surplus = analysis['surplus']

        if shortfall > 0:
            st.error(f"""
            **Shortfall: {format_currency(shortfall)}**

            To achieve 90% probability of success, you need approximately {format_currency(shortfall)} more in your retirement portfolio.
            """)

            # Calculate what's needed
            years_remaining = retirement_age - current_age
            if years_remaining > 0:
                # Additional monthly savings needed
                # Simple calculation: shortfall / years / 12
                additional_monthly = shortfall / years_remaining / 12

                st.markdown("**Ways to Close the Gap:**")
                st.markdown(f"""
                - 💰 Increase annual savings by ~{format_currency(shortfall/years_remaining)} ({format_currency(additional_monthly)}/month)
                - 📅 Work {int(shortfall / (current_portfolio * 0.08))} additional year(s)
                - 📉 Reduce retirement spending by {format_currency(shortfall * 0.04)}/year
                - 📊 Target higher investment returns (riskier)
                """)
        else:
            st.success(f"""
            **Surplus: {format_currency(surplus)}**

            Great news! Your projected portfolio exceeds the amount needed for a 90% success rate.
            You have a comfortable margin of safety.
            """)

            st.markdown("**Options with Your Surplus:**")
            st.markdown(f"""
            - 🏖️ Retire earlier (potentially {int(surplus / (annual_contribution * 1.5))} years sooner)
            - 💸 Increase retirement spending by {format_currency(surplus * 0.04)}/year
            - 🎁 Leave a larger legacy/inheritance
            - 😌 Reduce current savings rate and enjoy life now
            """)

        # Total Contributions Summary
        st.subheader("📊 Savings Summary")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Total Contributions",
                format_currency(analysis['total_contributions']),
                help="Sum of all contributions until retirement"
            )

        with col2:
            median_growth = analysis['median_retirement_value'] - current_portfolio - analysis['total_contributions']
            st.metric(
                "Projected Investment Growth",
                format_currency(median_growth),
                help="Expected growth from returns"
            )

        with col3:
            if analysis['total_contributions'] > 0:
                growth_multiple = analysis['median_retirement_value'] / analysis['total_contributions']
                st.metric(
                    "Growth Multiple",
                    f"{growth_multiple:.1f}x",
                    help="Portfolio value / contributions"
                )

        # Scenario Analysis
        st.subheader("🎯 What-If Scenarios")

        tab1, tab2 = st.tabs(["Retirement Age", "Income Level"])

        with tab1:
            st.markdown("**How does changing your retirement age affect success?**")

            # Calculate scenarios for different retirement ages
            ages_to_test = [
                max(current_age + 5, 60),
                retirement_age - 5,
                retirement_age,
                retirement_age + 5,
                min(retirement_age + 10, 75)
            ]
            ages_to_test = sorted(list(set([age for age in ages_to_test if current_age < age <= 75])))

            scenario_results = []
            for age in ages_to_test:
                test_planner = RetirementPlanner(
                    current_age=current_age,
                    retirement_age=age,
                    life_expectancy=life_expectancy,
                    current_portfolio_value=current_portfolio,
                    annual_contribution=annual_contribution,
                    contribution_growth_rate=contribution_growth,
                    expected_return=accumulation_return,
                    volatility=accumulation_volatility,
                    simulations=5000
                )

                result = test_planner.calculate_retirement_readiness(
                    desired_annual_income=desired_income,
                    social_security_annual=social_security,
                    pension_annual=pension,
                    healthcare_annual=healthcare_costs,
                    inflation_rate=inflation_rate,
                    retirement_return=retirement_return,
                    retirement_volatility=retirement_volatility
                )

                scenario_results.append({
                    'Retirement Age': age,
                    'Years Working': age - current_age,
                    'Success Rate': f"{result['success_rate']*100:.1f}%",
                    'Median Portfolio': format_currency(result['median_retirement_value']),
                    'Status': result['readiness_level']
                })

            scenario_df = pd.DataFrame(scenario_results)
            st.dataframe(scenario_df, use_container_width=True, hide_index=True)

        with tab2:
            st.markdown("**How does desired income affect success?**")

            income_scenarios = [
                desired_income * 0.7,
                desired_income * 0.85,
                desired_income,
                desired_income * 1.15,
                desired_income * 1.3
            ]

            income_results = []
            planner = st.session_state.retirement_planner

            for income in income_scenarios:
                result = planner.calculate_retirement_readiness(
                    desired_annual_income=income,
                    social_security_annual=social_security,
                    pension_annual=pension,
                    healthcare_annual=healthcare_costs,
                    inflation_rate=inflation_rate,
                    retirement_return=retirement_return,
                    retirement_volatility=retirement_volatility
                )

                income_results.append({
                    'Annual Income': format_currency(income),
                    'Success Rate': f"{result['success_rate']*100:.1f}%",
                    'Withdrawal Rate': f"{result['withdrawal_rate']*100:.2f}%",
                    'Status': result['readiness_level']
                })

            income_df = pd.DataFrame(income_results)
            st.dataframe(income_df, use_container_width=True, hide_index=True)

        # Action Items
        if success_rate < 0.90:
            st.subheader("✅ Recommended Actions")

            st.markdown("**To improve your retirement outlook:**")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Increase Savings**")
                # Calculate required savings for 90% success
                required_info = calculate_retirement_number(
                    desired_annual_income=analysis['net_income_needed'],
                    withdrawal_rate=0.04
                )
                additional_needed = required_info - analysis['median_retirement_value']

                if additional_needed > 0 and (retirement_age - current_age) > 0:
                    additional_annual = additional_needed / (retirement_age - current_age)
                    additional_monthly = additional_annual / 12

                    st.info(f"Save an additional **{format_currency(additional_monthly)}/month**")

            with col2:
                st.markdown("**Adjust Timeline**")
                # Estimate years needed to work for 90% success
                years_to_add = max(1, int((analysis['required_value_90pct'] - analysis['median_retirement_value']) / (annual_contribution * 1.5)))

                st.info(f"Work **{years_to_add} more year(s)** (retire at {retirement_age + years_to_add})")

    else:
        st.info("👆 Fill in your information above and click 'Analyze Retirement Plan' to see your personalized retirement analysis")


def sidebar():
    """Render sidebar."""
    st.sidebar.title("Portfolio Dashboard")

    st.sidebar.header("📁 Data Management")

    # Portfolio upload
    st.sidebar.subheader("Upload Portfolio")

    uploaded_file = st.sidebar.file_uploader(
        "Upload CSV",
        type=['csv'],
        help="Upload portfolio positions",
        key='portfolio_upload'
    )

    if uploaded_file is not None:
        try:
            content = uploaded_file.read()
            positions = CSVHandler.parse_portfolio_csv(content)

            # Validate
            validation = CSVHandler.validate_portfolio_data(positions)

            if validation['errors']:
                st.sidebar.error("Errors found:")
                for error in validation['errors']:
                    st.sidebar.error(f"- {error}")
            else:
                if validation['warnings']:
                    st.sidebar.warning("Warnings:")
                    for warning in validation['warnings']:
                        st.sidebar.warning(f"- {warning}")

                # Save to session and database
                st.session_state.portfolio_positions = positions
                save_portfolio_to_db(positions)
                st.sidebar.success(f"Loaded {len(positions)} positions!")

        except Exception as e:
            st.sidebar.error(f"Error: {str(e)}")

    # Portfolio template
    with st.sidebar.expander("Download Portfolio Template"):
        template = CSVHandler.create_portfolio_template()
        st.download_button(
            "Download Template",
            template,
            file_name="portfolio_template.csv",
            mime="text/csv"
        )

    # LTCMA upload
    st.sidebar.subheader("Upload LTCMA Data")

    ltcma_file = st.sidebar.file_uploader(
        "Upload LTCMA CSV",
        type=['csv'],
        help="Upload JP Morgan LTCMA data",
        key='ltcma_upload'
    )

    if ltcma_file is not None:
        try:
            content = ltcma_file.read()
            ltcma_df = CSVHandler.parse_ltcma_csv(content)
            st.session_state.ltcma_data = ltcma_df
            st.sidebar.success(f"Loaded {len(ltcma_df)} asset classes!")
        except Exception as e:
            st.sidebar.error(f"Error: {str(e)}")

    # Load existing portfolio from DB
    if st.sidebar.button("Load from Database"):
        positions = load_portfolio_from_db()
        if positions:
            st.session_state.portfolio_positions = positions
            st.sidebar.success(f"Loaded {len(positions)} positions from database!")
        else:
            st.sidebar.info("No positions found in database")


def display_tax_planning(calculator):
    """Display tax planning and optimization tools."""
    st.header("💰 Tax Planning & Optimization")

    st.markdown("""
    Identify tax-loss harvesting opportunities, optimize withdrawal strategies, and minimize your tax burden.
    """)

    snapshot = calculator.get_snapshot()

    if not snapshot.positions:
        st.warning("No positions available for tax analysis")
        return

    # Initialize TaxPlanner with positions
    tax_planner = TaxPlanner(snapshot.positions)

    # Tax-Loss Harvesting Opportunities
    st.subheader("📉 Tax-Loss Harvesting Opportunities")

    try:
        tlh_opportunities = tax_planner.identify_tax_loss_harvest_opportunities(min_loss_threshold=1000.0)

        if tlh_opportunities.empty:
            st.success("✓ No tax-loss harvesting opportunities found. All positions are profitable!")
        else:
            st.warning(f"Found {len(tlh_opportunities)} positions with unrealized losses")

            # Format for display
            display_df = tlh_opportunities.copy()
            display_df['unrealized_gain_loss'] = display_df['unrealized_gain_loss'].apply(format_currency)
            display_df['estimated_tax_benefit'] = display_df['estimated_tax_benefit'].apply(format_currency)
            display_df['gain_loss_pct'] = display_df['gain_loss_pct'].apply(lambda x: f"{x:.2f}%")

            st.dataframe(display_df, use_container_width=True)

            total_losses = tlh_opportunities['unrealized_gain_loss'].sum()
            total_benefit = tlh_opportunities['estimated_tax_benefit'].sum()

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Harvestable Losses", format_currency(abs(total_losses)))
            with col2:
                st.metric("Estimated Tax Benefit", format_currency(abs(total_benefit)))
    except Exception as e:
        st.error(f"Error analyzing tax-loss harvesting: {e}")

    # Unrealized Gains Analysis
    st.subheader("📈 Unrealized Gains Analysis")

    try:
        gains_df = tax_planner.calculate_unrealized_gains()

        if not gains_df.empty:
            total_unrealized = gains_df['unrealized_gain_loss'].sum()
            long_term_gains = gains_df[gains_df['is_long_term']]['unrealized_gain_loss'].sum()
            short_term_gains = gains_df[~gains_df['is_long_term']]['unrealized_gain_loss'].sum()

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Unrealized Gains", format_currency(total_unrealized))
            with col2:
                st.metric("Long-Term Gains", format_currency(long_term_gains))
            with col3:
                st.metric("Short-Term Gains", format_currency(short_term_gains))

            # Display details
            st.dataframe(
                gains_df[['symbol', 'shares', 'cost_basis', 'current_value',
                         'unrealized_gain_loss', 'gain_loss_pct', 'holding_days', 'is_long_term']],
                use_container_width=True
            )
        else:
            st.info("No unrealized gains data available")

    except Exception as e:
        st.error(f"Error calculating unrealized gains: {e}")

    # Tax Impact Estimation
    st.subheader("⚙️ Annual Tax Impact Estimation")

    col1, col2 = st.columns(2)
    with col1:
        ordinary_income = st.number_input(
            "Annual Ordinary Income ($)",
            min_value=0.0,
            value=100000.0,
            step=10000.0
        )
    with col2:
        dividend_income = st.number_input(
            "Expected Dividend Income ($)",
            min_value=0.0,
            value=0.0,
            step=1000.0
        )

    if st.button("Calculate Tax Impact"):
        try:
            tax_impact = tax_planner.estimate_annual_tax_impact(
                realized_gains=0.0,
                realized_losses=0.0,
                dividend_income=dividend_income,
                ordinary_income=ordinary_income
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Dividend Tax", format_currency(tax_impact['dividend_tax']))
            with col2:
                st.metric("Total Investment Tax", format_currency(tax_impact['total_investment_tax']))
            with col3:
                st.metric("Effective Rate", f"{tax_impact['effective_rate']:.2f}%")
        except Exception as e:
            st.error(f"Error calculating tax impact: {e}")


def display_rebalancing(calculator):
    """Display portfolio rebalancing recommendations."""
    st.header("⚖️ Portfolio Rebalancing")

    st.markdown("""
    Analyze your current allocation vs targets and get specific trade recommendations.
    """)

    snapshot = calculator.get_snapshot()

    if not snapshot.positions:
        st.warning("No positions available for rebalancing analysis")
        return

    # Get current allocation (as decimal weights)
    current_allocation_pct = snapshot.get_allocation()
    current_allocation = {k: v / 100.0 for k, v in current_allocation_pct.items() if k != 'CASH'}

    if not current_allocation:
        st.warning("No positions available for rebalancing analysis")
        return

    # Target Allocation Input
    st.subheader("🎯 Target Allocation")

    st.markdown("Set your target allocation percentages (must sum to 100%):")

    target_allocation_pct = {}
    cols = st.columns(len(current_allocation))

    for idx, (symbol, current_weight) in enumerate(current_allocation.items()):
        with cols[idx]:
            target_pct = st.number_input(
                symbol,
                min_value=0.0,
                max_value=100.0,
                value=float(current_weight * 100),
                step=0.1,
                key=f"target_{symbol}"
            )
            target_allocation_pct[symbol] = target_pct

    total_target = sum(target_allocation_pct.values())

    if abs(total_target - 100.0) > 0.1:
        st.error(f"⚠️ Target allocation sums to {total_target:.1f}% (must be 100%)")
        return

    # Convert to decimal weights
    target_allocation = {k: v / 100.0 for k, v in target_allocation_pct.items()}

    # Rebalancing threshold
    threshold = st.slider(
        "Rebalancing Tolerance (%)",
        0.5, 10.0, 5.0, 0.5,
        help="Only rebalance positions that drift more than this amount"
    ) / 100.0  # Convert to decimal

    # Initialize RebalancingAssistant with positions and target allocation
    rebalancer = RebalancingAssistant(
        positions=snapshot.positions,
        target_allocation=target_allocation,
        tolerance=threshold
    )

    # Calculate drift
    st.subheader("📊 Allocation Drift")

    try:
        drift_df = rebalancer.calculate_drift()

        if not drift_df.empty:
            # Format for display
            display_drift = drift_df.copy()
            display_drift['current_weight'] = display_drift['current_weight'].apply(lambda x: f"{x*100:.2f}%")
            display_drift['target_weight'] = display_drift['target_weight'].apply(lambda x: f"{x*100:.2f}%")
            display_drift['drift'] = display_drift['drift'].apply(lambda x: f"{x*100:.2f}%")
            display_drift['drift_pct'] = display_drift['drift_pct'].apply(lambda x: f"{x:.2f}%")

            st.dataframe(display_drift, use_container_width=True)

        # Generate trades
        st.subheader("💼 Recommended Trades")

        trades = rebalancer.generate_rebalancing_trades(
            total_portfolio_value=snapshot.total_value,
            additional_contribution=0.0
        )

        if not trades or len(trades) == 0:
            st.success(f"✓ Portfolio is within tolerance. No rebalancing needed!")
        else:
            st.info(f"Found {len(trades)} recommended trades")

            # Convert to DataFrame and format
            trades_df = pd.DataFrame(trades)
            display_trades = trades_df.copy()
            display_trades['value'] = display_trades['value'].apply(format_currency)
            display_trades['current_value'] = display_trades['current_value'].apply(format_currency)
            display_trades['target_value'] = display_trades['target_value'].apply(format_currency)
            display_trades['shares'] = display_trades['shares'].apply(lambda x: f"{x:.2f}")

            st.dataframe(display_trades[['symbol', 'action', 'shares', 'value', 'current_value', 'target_value']],
                        use_container_width=True)

    except Exception as e:
        st.error(f"Error calculating rebalancing: {e}")


def display_dividends(calculator):
    """Display dividend tracking and analysis."""
    st.header("💵 Dividend Income Tracker")

    st.markdown("""
    Track dividend income, analyze yield trends, and project future dividend payments.
    """)

    snapshot = calculator.get_snapshot()

    if not snapshot.positions:
        st.warning("No positions available for dividend analysis")
        return

    # Initialize DividendTracker with positions
    dividend_tracker = DividendTracker(snapshot.positions)

    st.subheader("📊 Dividend Summary")

    # Fetch dividend data
    with st.spinner("Fetching dividend data..."):
        try:
            div_data = dividend_tracker.fetch_dividend_data(years_back=2)

            if div_data.empty:
                st.info("No dividend data found for your holdings")
                return

            # Calculate metrics
            total_annual_div = div_data['total_dividend'].sum()

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Dividend Income (2 years)", format_currency(total_annual_div))
            with col2:
                portfolio_value = snapshot.total_value
                yield_pct = (total_annual_div / portfolio_value / 2 * 100) if portfolio_value > 0 else 0
                st.metric("Estimated Annual Yield", f"{yield_pct:.2f}%")
            with col3:
                num_payments = len(div_data)
                st.metric("Total Dividend Payments", num_payments)

            # Dividend by stock
            st.subheader("💰 Dividend Income by Holding")

            div_by_symbol = div_data.groupby('symbol')['total_dividend'].sum().reset_index()
            div_by_symbol.columns = ['Symbol', 'Total Dividends']
            div_by_symbol = div_by_symbol.sort_values('Total Dividends', ascending=False)

            fig = px.bar(
                div_by_symbol,
                x='Symbol',
                y='Total Dividends',
                title="Total Dividend Income by Stock (2 years)"
            )
            st.plotly_chart(fig, use_container_width=True)

            # Yield on Cost Analysis
            st.subheader("📈 Yield on Cost")

            yield_df = dividend_tracker.calculate_dividend_yield_on_cost()

            if not yield_df.empty:
                display_yield = yield_df.copy()
                display_yield['purchase_price'] = display_yield['purchase_price'].apply(format_currency)
                display_yield['current_price'] = display_yield['current_price'].apply(lambda x: format_currency(x) if x else 'N/A')
                display_yield['annual_dividend_per_share'] = display_yield['annual_dividend_per_share'].apply(format_currency)
                display_yield['current_yield'] = display_yield['current_yield'].apply(lambda x: f"{x*100:.2f}%" if x else 'N/A')
                display_yield['yield_on_cost'] = display_yield['yield_on_cost'].apply(lambda x: f"{x*100:.2f}%")
                display_yield['annual_income'] = display_yield['annual_income'].apply(format_currency)

                st.dataframe(display_yield[['symbol', 'shares', 'annual_dividend_per_share',
                                           'current_yield', 'yield_on_cost', 'annual_income']],
                            use_container_width=True)
            else:
                st.info("No yield data available")

        except Exception as e:
            st.error(f"Error fetching dividend data: {e}")


def display_optimization(calculator):
    """Display portfolio optimization tools."""
    st.header("📈 Portfolio Optimization")

    st.markdown("""
    Optimize your portfolio using Modern Portfolio Theory to maximize risk-adjusted returns.
    """)

    snapshot = calculator.get_snapshot()

    if len(snapshot.positions) < 2:
        st.warning("Need at least 2 positions for portfolio optimization")
        return

    symbols = [pos.symbol for pos in snapshot.positions]

    st.subheader("⚙️ Optimization Settings")

    col1, col2 = st.columns(2)

    with col1:
        period = st.selectbox(
            "Historical Period",
            ["1y", "2y", "3y", "5y"],
            index=1,
            help="Period for calculating historical returns and correlations"
        )

    with col2:
        risk_free_rate = st.number_input(
            "Risk-Free Rate (%)",
            0.0, 10.0, 4.5, 0.1,
            help="Current risk-free rate (e.g., 10-year Treasury yield)"
        ) / 100

    if st.button("🚀 Run Optimization", type="primary"):
        with st.spinner("Optimizing portfolio... This may take a minute"):
            try:
                # Fetch historical data
                import yfinance as yf

                period_map = {"1y": "1y", "2y": "2y", "3y": "3y", "5y": "5y"}
                data = yf.download(symbols, period=period_map[period], progress=False)

                if 'Adj Close' in data.columns:
                    prices = data['Adj Close']
                else:
                    prices = data['Close']

                # Calculate daily returns
                returns = prices.pct_change().dropna()

                if returns.empty or len(returns) < 50:
                    st.error("Insufficient historical data for optimization")
                    return

                # Initialize PortfolioOptimizer with returns DataFrame
                optimizer = PortfolioOptimizer(returns, risk_free_rate=risk_free_rate)

                # Find optimal portfolios
                max_sharpe = optimizer.find_max_sharpe_portfolio()
                min_vol = optimizer.find_min_volatility_portfolio()

                # Display results
                st.subheader("🎯 Optimal Portfolios")

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Maximum Sharpe Ratio Portfolio**")
                    st.metric("Expected Return", f"{max_sharpe['expected_return']*100:.2f}%")
                    st.metric("Volatility", f"{max_sharpe['volatility']*100:.2f}%")
                    st.metric("Sharpe Ratio", f"{max_sharpe['sharpe_ratio']:.2f}")

                    st.markdown("**Weights:**")
                    for symbol, weight in max_sharpe['weights'].items():
                        if weight > 0.01:
                            st.write(f"{symbol}: {weight*100:.1f}%")

                with col2:
                    st.markdown("**Minimum Volatility Portfolio**")
                    st.metric("Expected Return", f"{min_vol['expected_return']*100:.2f}%")
                    st.metric("Volatility", f"{min_vol['volatility']*100:.2f}%")
                    st.metric("Sharpe Ratio", f"{min_vol['sharpe_ratio']:.2f}")

                    st.markdown("**Weights:**")
                    for symbol, weight in min_vol['weights'].items():
                        if weight > 0.01:
                            st.write(f"{symbol}: {weight*100:.1f}%")

                # Efficient Frontier
                st.subheader("📊 Efficient Frontier")

                frontier = optimizer.generate_efficient_frontier(num_portfolios=50)

                if not frontier.empty:
                    fig = go.Figure()

                    # Plot frontier
                    fig.add_trace(go.Scatter(
                        x=frontier['volatility'] * 100,
                        y=frontier['return'] * 100,
                        mode='markers',
                        marker=dict(
                            size=5,
                            color=frontier['sharpe_ratio'],
                            colorscale='Viridis',
                            showscale=True,
                            colorbar=dict(title="Sharpe Ratio")
                        ),
                        name='Efficient Frontier'
                    ))

                    # Mark optimal portfolios
                    fig.add_trace(go.Scatter(
                        x=[max_sharpe['volatility'] * 100],
                        y=[max_sharpe['expected_return'] * 100],
                        mode='markers',
                        marker=dict(size=15, color='red', symbol='star'),
                        name='Max Sharpe'
                    ))

                    fig.add_trace(go.Scatter(
                        x=[min_vol['volatility'] * 100],
                        y=[min_vol['expected_return'] * 100],
                        mode='markers',
                        marker=dict(size=15, color='green', symbol='star'),
                        name='Min Volatility'
                    ))

                    fig.update_layout(
                        title="Efficient Frontier",
                        xaxis_title="Volatility (%)",
                        yaxis_title="Expected Return (%)",
                        height=600
                    )

                    st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.error(f"Error during optimization: {e}")


def display_sector_analysis(calculator):
    """Display sector and geographic exposure analysis."""
    st.header("🌐 Sector & Geographic Analysis")

    st.markdown("""
    Analyze your portfolio's sector and geographic diversification.
    """)

    snapshot = calculator.get_snapshot()

    if not snapshot.positions:
        st.warning("No positions available for sector analysis")
        return

    # Initialize SectorAnalyzer with positions
    analyzer = SectorAnalyzer(snapshot.positions)

    with st.spinner("Fetching sector and geographic data..."):
        try:
            # Sector exposure
            st.subheader("🏢 Sector Exposure")

            sector_df = analyzer.get_sector_exposure()

            if not sector_df.empty:
                # Format for display
                display_sector = sector_df.copy()
                display_sector['weight'] = display_sector['weight'] * 100
                display_sector['value'] = display_sector['value'].apply(format_currency)

                fig = px.pie(
                    display_sector,
                    values='weight',
                    names='sector',
                    title="Portfolio Sector Allocation"
                )
                st.plotly_chart(fig, use_container_width=True)

                st.dataframe(display_sector[['sector', 'value', 'num_positions', 'weight']],
                            use_container_width=True)
            else:
                st.info("Sector data not available for your holdings")

            # Geographic exposure
            st.subheader("🗺️ Geographic Exposure")

            geo_df = analyzer.get_geographic_exposure()

            if not geo_df.empty:
                # Format for display
                display_geo = geo_df.copy()
                display_geo['weight'] = display_geo['weight'] * 100
                display_geo['value'] = display_geo['value'].apply(format_currency)

                fig = px.bar(
                    display_geo,
                    x='country',
                    y='weight',
                    title="Portfolio Geographic Allocation"
                )
                st.plotly_chart(fig, use_container_width=True)

                st.dataframe(display_geo[['country', 'value', 'num_positions', 'weight']],
                            use_container_width=True)
            else:
                st.info("Geographic data not available for your holdings")

            # Concentration risk
            st.subheader("⚠️ Concentration Risk")

            threshold = st.slider(
                "Concentration Threshold (%)",
                5.0, 30.0, 15.0, 1.0,
                help="Alert if any sector exceeds this percentage"
            ) / 100.0

            concentration = analyzer.check_concentration_risk(threshold=threshold)

            col1, col2 = st.columns(2)

            with col1:
                st.metric("Max Sector Weight", f"{concentration['max_sector_weight']*100:.1f}%")
            with col2:
                hhi = concentration['herfindahl_index']
                st.metric("Herfindahl Index", f"{hhi:.3f}")

                if hhi < 0.15:
                    st.success("Well diversified")
                elif hhi < 0.25:
                    st.warning("Moderate concentration")
                else:
                    st.error("High concentration risk")

            if concentration['has_risk']:
                st.warning("⚠️ Concentrated sectors detected:")
                for sector_info in concentration['concentrated_sectors']:
                    st.write(f"- {sector_info['sector']}: {sector_info['weight']*100:.1f}%")

        except Exception as e:
            st.error(f"Error analyzing sectors: {e}")


def display_goal_planning(calculator):
    """Display goal-based planning tools."""
    st.header("🎯 Goal-Based Planning")

    st.markdown("""
    Set financial goals and track your progress toward achieving them.
    """)

    snapshot = calculator.get_snapshot()
    current_value = snapshot.total_value

    # Goal Management
    st.subheader("📋 Your Financial Goals")

    # Initialize goals in session state if not exists
    if 'financial_goals' not in st.session_state:
        st.session_state.financial_goals = []

    # Add new goal
    with st.expander("➕ Add New Goal"):
        col1, col2 = st.columns(2)

        with col1:
            goal_name = st.text_input("Goal Name")
            target_amount = st.number_input("Target Amount ($)", min_value=0.0, step=1000.0)
            years_until = st.number_input("Years to Goal", min_value=1, max_value=50, value=10)

        with col2:
            priority = st.selectbox("Priority", [1, 2, 3, 4, 5])
            current_saved = st.number_input("Current Savings ($)", min_value=0.0, step=1000.0)

        if st.button("Add Goal"):
            if goal_name and target_amount > 0:
                goal = Goal(
                    name=goal_name,
                    target_amount=target_amount,
                    years_until=years_until,
                    priority=priority,
                    current_saved=current_saved
                )
                st.session_state.financial_goals.append(goal)
                st.success(f"Added goal: {goal_name}")
            else:
                st.error("Please provide goal name and target amount")

    # Display existing goals
    if st.session_state.financial_goals:
        for idx, goal in enumerate(st.session_state.financial_goals):
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

                with col1:
                    st.markdown(f"**{goal.name}**")
                with col2:
                    st.write(f"Target: {format_currency(goal.target_amount)}")
                with col3:
                    progress = (goal.current_saved / goal.target_amount * 100) if goal.target_amount > 0 else 0
                    st.progress(min(progress / 100, 1.0))
                    st.write(f"{progress:.1f}% complete")
                with col4:
                    if st.button("🗑️", key=f"delete_{idx}"):
                        st.session_state.financial_goals.pop(idx)
                        st.rerun()

        # Calculate required savings
        st.subheader("💰 Required Savings Analysis")

        col1, col2 = st.columns(2)
        with col1:
            annual_savings_available = st.number_input(
                "Annual Savings Available ($)",
                min_value=0.0,
                value=12000.0,
                step=1000.0,
                help="Total amount you can save per year"
            )
        with col2:
            expected_return = st.slider(
                "Expected Annual Return (%)",
                0.0, 15.0, 7.0, 0.5
            ) / 100

        # Initialize GoalPlanner with goals and total savings rate
        planner = GoalPlanner(
            goals=st.session_state.financial_goals,
            total_savings_rate=annual_savings_available
        )

        try:
            savings_df = planner.calculate_required_savings_per_goal(expected_return=expected_return)

            if not savings_df.empty:
                # Format for display
                display_savings = savings_df.copy()
                display_savings['target_amount'] = display_savings['target_amount'].apply(format_currency)
                display_savings['current_saved'] = display_savings['current_saved'].apply(format_currency)
                display_savings['amount_needed'] = display_savings['amount_needed'].apply(format_currency)
                display_savings['monthly_savings_required'] = display_savings['monthly_savings_required'].apply(format_currency)
                display_savings['annual_savings_required'] = display_savings['annual_savings_required'].apply(format_currency)

                st.dataframe(display_savings[['goal', 'target_amount', 'current_saved', 'years_until',
                                              'monthly_savings_required', 'annual_savings_required', 'on_track']],
                            use_container_width=True)

                # Summary metrics
                total_annual_needed = savings_df['annual_savings_required'].sum()
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Annual Savings Needed", format_currency(total_annual_needed))
                with col2:
                    st.metric("Annual Savings Available", format_currency(annual_savings_available))
                with col3:
                    shortfall = max(0, total_annual_needed - annual_savings_available)
                    if shortfall > 0:
                        st.metric("Shortfall", format_currency(shortfall), delta=f"-{format_currency(shortfall)}")
                    else:
                        surplus = annual_savings_available - total_annual_needed
                        st.metric("Surplus", format_currency(surplus), delta=f"+{format_currency(surplus)}")

        except Exception as e:
            st.error(f"Error calculating savings requirements: {e}")
    else:
        st.info("No goals added yet. Add your first financial goal above!")


def display_ai_insights(calculator):
    """Display AI-powered portfolio insights."""
    st.header("🤖 AI-Powered Insights")

    st.markdown("""
    Get intelligent insights about your portfolio's performance, risks, and opportunities.
    """)

    snapshot = calculator.get_snapshot()

    if not snapshot.positions:
        st.warning("No positions available for AI analysis")
        return

    # Get historical data
    with st.spinner("Fetching historical data..."):
        try:
            # Calculate portfolio returns
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

            # Get portfolio value history
            import yfinance as yf

            # Download benchmark data (S&P 500)
            benchmark_data = yf.download('^GSPC', start=start_date, progress=False)

            if benchmark_data.empty:
                st.warning("Unable to fetch benchmark data")
                return

            benchmark_returns = benchmark_data['Adj Close'].pct_change().dropna()

            # Download portfolio stocks
            symbols = [pos.symbol for pos in snapshot.positions]
            weights = np.array([pos.current_value / snapshot.total_value for pos in snapshot.positions])

            portfolio_data = yf.download(symbols, start=start_date, progress=False)

            if portfolio_data.empty:
                st.warning("Unable to fetch portfolio historical data")
                return

            # Calculate weighted portfolio returns
            if len(symbols) == 1:
                portfolio_prices = portfolio_data['Adj Close']
            else:
                portfolio_prices = portfolio_data['Adj Close']

            # Calculate returns for each stock
            if len(symbols) == 1:
                stock_returns = portfolio_prices.pct_change().dropna()
                portfolio_returns = stock_returns
            else:
                stock_returns = portfolio_prices.pct_change().dropna()
                # Weight returns by current portfolio weights
                portfolio_returns = (stock_returns * weights).sum(axis=1)

            # Align dates
            common_dates = portfolio_returns.index.intersection(benchmark_returns.index)
            portfolio_returns = portfolio_returns.loc[common_dates]
            benchmark_returns = benchmark_returns.loc[common_dates]

            if len(portfolio_returns) < 50:
                st.warning("Insufficient historical data for AI analysis (need at least 50 days)")
                return

        except Exception as e:
            st.error(f"Error fetching historical data: {e}")
            return

    # Initialize AIInsights with portfolio and benchmark returns
    ai = AIInsights(portfolio_returns=portfolio_returns, benchmark_returns=benchmark_returns)

    # Performance Insights
    st.subheader("💡 Performance Insights")

    with st.spinner("Generating insights..."):
        try:
            insights = ai.generate_performance_insights()

            for insight in insights:
                st.info(insight)

        except Exception as e:
            st.error(f"Error generating insights: {e}")

    # Anomaly Detection
    st.subheader("🔍 Anomaly Detection")

    with st.spinner("Detecting anomalies..."):
        try:
            threshold = st.slider(
                "Anomaly Threshold (Standard Deviations)",
                1.5, 4.0, 3.0, 0.1,
                help="Number of standard deviations from mean to flag as anomaly"
            )

            anomalies = ai.detect_anomalies(threshold_std=threshold)

            if anomalies.empty:
                st.success("✓ No unusual market movements detected")
            else:
                st.warning(f"Detected {len(anomalies)} unusual market days:")
                anomalies_display = anomalies.copy()
                anomalies_display['return'] = anomalies_display['return'].apply(lambda x: f"{x*100:.2f}%")
                anomalies_display['z_score'] = anomalies_display['z_score'].apply(lambda x: f"{x:.2f}")
                st.dataframe(anomalies_display, use_container_width=True)

        except Exception as e:
            st.error(f"Error detecting anomalies: {e}")

    # Actionable Suggestions
    st.subheader("📋 Suggested Actions")

    with st.spinner("Generating recommendations..."):
        try:
            suggestions = ai.suggest_actions()

            if suggestions:
                for suggestion in suggestions:
                    priority = suggestion['priority']
                    if priority == 'High':
                        st.error(f"**{suggestion['action']}** - {suggestion['reason']}")
                    elif priority == 'Medium':
                        st.warning(f"**{suggestion['action']}** - {suggestion['reason']}")
                    else:
                        st.info(f"**{suggestion['action']}** - {suggestion['reason']}")
                    st.write(f"💡 {suggestion['suggestion']}")
                    st.write("---")
            else:
                st.success("✓ No immediate actions recommended. Portfolio is performing well!")

        except Exception as e:
            st.error(f"Error generating suggestions: {e}")


def display_performance_attribution(calculator):
    """Display performance attribution analysis."""
    st.header("Performance Attribution")

    snapshot = calculator.get_snapshot()
    if not snapshot.positions:
        st.info("No positions to analyze.")
        return

    attribution_engine = PerformanceAttribution()

    st.subheader("Return Contribution Analysis")

    try:
        inception_date = min(p.purchase_date for p in snapshot.positions)
        start_date = inception_date.strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')

        returns_data = calculator.calculate_returns(start_date, end_date)

        if returns_data is not None and not returns_data.empty:
            # Get individual position returns
            symbols = list(set(p.symbol for p in snapshot.positions))
            total_value = snapshot.total_value

            weights = {}
            for p in snapshot.positions:
                weights[p.symbol] = weights.get(p.symbol, 0) + p.current_value / total_value

            # Contribution analysis using position returns
            fetcher = MarketDataFetcher()
            position_returns = {}
            for symbol in symbols:
                try:
                    ret = fetcher.get_returns(symbol, start_date, end_date)
                    if ret is not None and not ret.empty:
                        position_returns[symbol] = ret
                except Exception:
                    continue

            if position_returns:
                pos_returns_df = pd.DataFrame(position_returns).dropna()

                if not pos_returns_df.empty:
                    contrib = attribution_engine.calculate_contribution_analysis(
                        pos_returns_df, weights
                    )

                    if 'error' not in contrib:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Portfolio Return", f"{contrib['portfolio_return']*100:.2f}%")
                        with col2:
                            st.metric("Top Contributor",
                                      f"{contrib['top_contributors'][0][0]}" if contrib['top_contributors'] else "N/A")
                        with col3:
                            st.metric("Bottom Contributor",
                                      f"{contrib['bottom_contributors'][-1][0]}" if contrib['bottom_contributors'] else "N/A")

                        # Contribution chart
                        contrib_data = pd.DataFrame([
                            {'Symbol': k, 'Contribution (%)': v * 100}
                            for k, v in contrib['position_contributions'].items()
                        ]).sort_values('Contribution (%)', ascending=True)

                        fig = px.bar(
                            contrib_data, x='Contribution (%)', y='Symbol',
                            orientation='h', title='Return Contribution by Position',
                            color='Contribution (%)',
                            color_continuous_scale=['#e74c3c', '#f39c12', '#2ecc71']
                        )
                        st.plotly_chart(fig, use_container_width=True)

                        # % of return contribution table
                        pct_data = pd.DataFrame([
                            {'Symbol': k, 'Weight (%)': f"{weights.get(k, 0)*100:.2f}",
                             'Return (%)': f"{contrib['position_returns'].get(k, 0)*100:.2f}",
                             'Contribution (%)': f"{v*100:.4f}",
                             '% of Total': f"{contrib['pct_contributions'].get(k, 0):.1f}"}
                            for k, v in contrib['position_contributions'].items()
                        ])
                        st.dataframe(pct_data, use_container_width=True)

                    # Risk-adjusted attribution
                    st.subheader("Risk-Adjusted Attribution")
                    risk_adj = attribution_engine.calculate_risk_adjusted_attribution(
                        pos_returns_df, weights
                    )

                    ra_data = pd.DataFrame([
                        {
                            'Symbol': symbol,
                            'Weight (%)': f"{v['weight']*100:.2f}",
                            'Ann. Return (%)': f"{v['annualized_return']*100:.2f}",
                            'Ann. Vol (%)': f"{v['annualized_volatility']*100:.2f}",
                            'Sharpe': f"{v['sharpe_ratio']:.2f}",
                            'Sortino': f"{v['sortino_ratio']:.2f}",
                            'Max DD (%)': f"{v['max_drawdown']*100:.2f}",
                        }
                        for symbol, v in risk_adj.items()
                    ])
                    st.dataframe(ra_data, use_container_width=True)

            # Benchmark comparison batting average
            st.subheader("Batting Average vs Benchmark")
            try:
                benchmark_data = fetcher.get_returns('^GSPC', start_date, end_date)
                if benchmark_data is not None and not benchmark_data.empty:
                    for freq, label in [('M', 'Monthly'), ('Q', 'Quarterly')]:
                        ba = attribution_engine.calculate_batting_average(
                            returns_data, benchmark_data, frequency=freq
                        )
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric(f"{label} Batting Avg", f"{ba['batting_average']:.1f}%")
                        with col2:
                            st.metric(f"Up Capture", f"{ba['up_capture_ratio']:.1f}%")
                        with col3:
                            st.metric(f"Down Capture", f"{ba['down_capture_ratio']:.1f}%")
                        with col4:
                            st.metric(f"Capture Ratio", f"{ba['capture_ratio']:.2f}" if ba['capture_ratio'] != float('inf') else "N/A")
            except Exception as e:
                st.warning(f"Could not calculate batting average: {e}")

    except Exception as e:
        st.error(f"Error in attribution analysis: {e}")


def display_factor_analysis(calculator):
    """Display multi-factor risk model analysis."""
    st.header("Factor Analysis")

    snapshot = calculator.get_snapshot()
    if not snapshot.positions:
        st.info("No positions to analyze.")
        return

    inception_date = min(p.purchase_date for p in snapshot.positions)
    start_date = inception_date.strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')

    col1, col2 = st.columns(2)
    with col1:
        model = st.selectbox(
            "Factor Model",
            options=['capm', 'ff3', 'ff5', 'ff5_mom'],
            format_func=lambda x: {
                'capm': 'CAPM (Market Only)',
                'ff3': 'Fama-French 3 Factor',
                'ff5': 'Fama-French 5 Factor',
                'ff5_mom': 'FF5 + Momentum',
            }[x],
            index=2
        )
    with col2:
        rolling_window = st.slider("Rolling Window (days)", 30, 120, 60)

    try:
        returns_data = calculator.calculate_returns(start_date, end_date)

        if returns_data is not None and not returns_data.empty:
            factor_analyzer = FactorAnalysis()

            with st.spinner("Running factor regression..."):
                result = factor_analyzer.run_factor_regression(returns_data, model=model)

            if 'error' in result:
                st.warning(result['error'])
                return

            # Alpha display
            st.subheader("Factor Regression Results")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                alpha_color = "normal" if result['alpha_annualized'] >= 0 else "inverse"
                st.metric("Annualized Alpha",
                          f"{result['alpha_annualized']*100:.2f}%",
                          delta=f"t-stat: {result['alpha_t_stat']:.2f}")
            with col2:
                st.metric("R-Squared", f"{result['r_squared']*100:.1f}%")
            with col3:
                st.metric("Adj. R-Squared", f"{result['adj_r_squared']*100:.1f}%")
            with col4:
                st.metric("Information Ratio", f"{result['information_ratio']:.2f}")

            # Factor exposures (betas)
            st.subheader("Factor Exposures (Betas)")
            beta_data = []
            for factor, beta in result['betas'].items():
                t_stat = result['beta_t_stats'].get(factor, 0)
                p_val = result['beta_p_values'].get(factor, 1)
                sig = "***" if p_val < 0.01 else ("**" if p_val < 0.05 else ("*" if p_val < 0.10 else ""))
                beta_data.append({
                    'Factor': factor,
                    'Description': FactorAnalysis.FACTOR_DESCRIPTIONS.get(factor, ''),
                    'Beta': f"{beta:.3f}",
                    't-stat': f"{t_stat:.2f}",
                    'p-value': f"{p_val:.4f}",
                    'Significance': sig,
                })

            st.dataframe(pd.DataFrame(beta_data), use_container_width=True)

            # Factor exposure bar chart
            fig = px.bar(
                x=list(result['betas'].keys()),
                y=list(result['betas'].values()),
                labels={'x': 'Factor', 'y': 'Beta'},
                title='Factor Exposures',
                color=list(result['betas'].values()),
                color_continuous_scale='RdYlGn'
            )
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig, use_container_width=True)

            # Factor contribution to returns
            st.subheader("Factor Contribution to Returns")
            contrib_data = result.get('factor_contributions', {})
            if contrib_data:
                fig = px.bar(
                    x=list(contrib_data.keys()),
                    y=[v * 100 for v in contrib_data.values()],
                    labels={'x': 'Factor', 'y': 'Contribution (%)'},
                    title='Annualized Factor Return Contributions',
                    color=[v * 100 for v in contrib_data.values()],
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig, use_container_width=True)

            # Risk decomposition
            st.subheader("Risk Decomposition")
            with st.spinner("Decomposing risk..."):
                risk_decomp = factor_analyzer.factor_risk_decomposition(returns_data)

            if 'error' not in risk_decomp:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Risk", f"{risk_decomp['total_risk']*100:.2f}%")
                with col2:
                    st.metric("Systematic Risk",
                              f"{risk_decomp['systematic_risk']*100:.2f}%",
                              delta=f"{risk_decomp['systematic_pct']:.1f}% of total")
                with col3:
                    st.metric("Idiosyncratic Risk",
                              f"{risk_decomp['idiosyncratic_risk']*100:.2f}%",
                              delta=f"{risk_decomp['idiosyncratic_pct']:.1f}% of total")

                # Pie chart of systematic vs idiosyncratic
                fig = px.pie(
                    values=[risk_decomp['systematic_pct'], risk_decomp['idiosyncratic_pct']],
                    names=['Systematic (Factor)', 'Idiosyncratic (Stock-Specific)'],
                    title='Risk Decomposition',
                    color_discrete_sequence=['#3498db', '#e74c3c']
                )
                st.plotly_chart(fig, use_container_width=True)

            # Rolling factor exposures
            st.subheader("Rolling Factor Exposures")
            with st.spinner("Calculating rolling exposures..."):
                rolling = factor_analyzer.rolling_factor_exposure(
                    returns_data, window=rolling_window
                )

            if not rolling.empty:
                fig = go.Figure()
                for col in rolling.columns:
                    fig.add_trace(go.Scatter(
                        x=rolling.index, y=rolling[col],
                        mode='lines', name=col
                    ))
                fig.update_layout(
                    title=f'Rolling {rolling_window}-Day Factor Exposures',
                    yaxis_title='Beta / Alpha',
                    xaxis_title='Date'
                )
                st.plotly_chart(fig, use_container_width=True)

            # Style Analysis
            st.subheader("Returns-Based Style Analysis")
            with st.spinner("Running style analysis..."):
                style = factor_analyzer.style_analysis(returns_data)

            if 'error' not in style:
                st.write(f"**R-Squared:** {style['r_squared']*100:.1f}%")
                st.write(f"**Selection Return (Ann.):** {style['selection_return']*100:.2f}%")

                weights_data = pd.DataFrame([
                    {'Style': k, 'Weight (%)': v * 100}
                    for k, v in style['style_weights'].items() if v > 0.01
                ]).sort_values('Weight (%)', ascending=False)

                fig = px.bar(
                    weights_data, x='Style', y='Weight (%)',
                    title='Style Decomposition',
                    color='Weight (%)',
                    color_continuous_scale='Viridis'
                )
                st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error in factor analysis: {e}")


def display_risk_management(calculator):
    """Display institutional risk management dashboard."""
    st.header("Risk Management")

    snapshot = calculator.get_snapshot()
    if not snapshot.positions:
        st.info("No positions to analyze.")
        return

    risk_mgr = RiskManager()
    total_value = snapshot.total_value

    inception_date = min(p.purchase_date for p in snapshot.positions)
    start_date = inception_date.strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')

    try:
        returns_data = calculator.calculate_returns(start_date, end_date)

        if returns_data is None or returns_data.empty:
            st.warning("Insufficient return data for risk analysis.")
            return

        # VaR and CVaR
        st.subheader("Value at Risk (VaR) & Expected Shortfall")

        col1, col2 = st.columns(2)
        with col1:
            confidence = st.selectbox("Confidence Level", [0.90, 0.95, 0.99], index=1)
        with col2:
            horizon = st.selectbox("Holding Period (days)", [1, 5, 10, 21], index=0)

        var_results = risk_mgr.calculate_var(
            returns_data, method='all', horizon=horizon,
            portfolio_value=total_value, confidence=confidence
        )
        cvar_results = risk_mgr.calculate_cvar(
            returns_data, method='all', horizon=horizon,
            portfolio_value=total_value, confidence=confidence
        )

        col1, col2, col3 = st.columns(3)
        for i, (method, label) in enumerate([
            ('historical', 'Historical'), ('parametric', 'Parametric'), ('cornish_fisher', 'Cornish-Fisher')
        ]):
            with [col1, col2, col3][i]:
                var = var_results.get(method, {})
                cvar = cvar_results.get(method, {})
                st.metric(
                    f"VaR ({label})",
                    format_currency(var.get('var_dollar', 0)),
                    delta=f"{var.get('var_pct', 0)*100:.2f}%"
                )
                st.metric(
                    f"CVaR ({label})",
                    format_currency(cvar.get('cvar_dollar', 0)),
                    delta=f"{cvar.get('cvar_pct', 0)*100:.2f}%"
                )

        # Tail Risk Metrics
        st.subheader("Tail Risk Analysis")
        tail = risk_mgr.calculate_tail_risk_metrics(returns_data)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Skewness", f"{tail['skewness']:.3f}")
            st.metric("Worst Day", f"{tail['worst_day']*100:.2f}%")
        with col2:
            st.metric("Excess Kurtosis", f"{tail['excess_kurtosis']:.3f}")
            st.metric("Worst Week", f"{tail['worst_week']*100:.2f}%")
        with col3:
            st.metric("Gain/Loss Ratio", f"{tail['gain_loss_ratio']:.2f}")
            st.metric("Worst Month", f"{tail['worst_month']*100:.2f}%")
        with col4:
            st.metric("Tail Ratio", f"{tail['tail_ratio']:.2f}")
            normality = "Yes" if tail['is_normal'] else "No"
            st.metric("Normal Distribution?", normality)

        # Returns distribution
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=returns_data.values * 100,
            nbinsx=50,
            name='Actual Returns',
            marker_color='#3498db',
            opacity=0.7
        ))
        # Normal overlay
        x_range = np.linspace(returns_data.min() * 100, returns_data.max() * 100, 100)
        from scipy.stats import norm
        normal_pdf = norm.pdf(x_range, returns_data.mean() * 100, returns_data.std() * 100)
        fig.add_trace(go.Scatter(
            x=x_range,
            y=normal_pdf * len(returns_data) * (returns_data.max() - returns_data.min()) * 100 / 50,
            mode='lines', name='Normal Distribution',
            line=dict(color='red', dash='dash')
        ))
        fig.update_layout(title='Return Distribution vs Normal', xaxis_title='Return (%)', yaxis_title='Frequency')
        st.plotly_chart(fig, use_container_width=True)

        # Drawdown Analysis
        st.subheader("Drawdown Analysis")
        dd = risk_mgr.calculate_drawdown_analysis(returns_data)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Max Drawdown", f"{dd['max_drawdown']*100:.2f}%")
        with col2:
            st.metric("Current Drawdown", f"{dd['current_drawdown']*100:.2f}%")
        with col3:
            st.metric("Avg Drawdown", f"{dd['average_drawdown']*100:.2f}%")
        with col4:
            st.metric("% Time in DD", f"{dd['pct_time_in_drawdown']:.1f}%")

        if dd.get('recovery_days') is not None:
            st.info(f"Recovery from max drawdown took {dd['recovery_days']} days")

        # Drawdown chart
        dd_series = dd['drawdown_series']
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dd_series.index, y=dd_series.values * 100,
            fill='tozeroy', fillcolor='rgba(231,76,60,0.3)',
            line=dict(color='#e74c3c'),
            name='Drawdown'
        ))
        fig.update_layout(title='Drawdown Over Time', yaxis_title='Drawdown (%)', xaxis_title='Date')
        st.plotly_chart(fig, use_container_width=True)

        # Top 5 drawdowns table
        if dd.get('top_5_drawdowns'):
            st.write("**Top 5 Drawdowns:**")
            dd_table = pd.DataFrame([
                {
                    'Start': d['start'].strftime('%Y-%m-%d'),
                    'Trough': d['trough'].strftime('%Y-%m-%d'),
                    'End': d['end'].strftime('%Y-%m-%d'),
                    'Depth (%)': f"{d['depth']*100:.2f}",
                    'Duration (Days)': d['duration_days'],
                }
                for d in dd['top_5_drawdowns']
            ])
            st.dataframe(dd_table, use_container_width=True)

        # Stress Testing
        st.subheader("Stress Testing")
        position_weights = {}
        asset_classes = {}
        for p in snapshot.positions:
            w = p.current_value / total_value if total_value > 0 else 0
            position_weights[p.symbol] = position_weights.get(p.symbol, 0) + w
            asset_classes[p.symbol] = p.asset_class or 'equity'

        stress_results = risk_mgr.run_stress_test(
            total_value, position_weights, asset_classes
        )

        if not stress_results.empty:
            stress_display = stress_results.copy()
            stress_display['Portfolio Impact ($)'] = stress_display['Portfolio Impact ($)'].apply(lambda x: format_currency(x))
            stress_display['Portfolio Impact (%)'] = stress_display['Portfolio Impact (%)'].apply(lambda x: f"{x:.2f}%")
            st.dataframe(stress_display, use_container_width=True)

            # Stress test bar chart
            fig = px.bar(
                stress_results, x='Scenario', y='Portfolio Impact (%)',
                title='Stress Test Impact',
                color='Portfolio Impact (%)',
                color_continuous_scale='RdYlGn'
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

        # Custom stress test
        st.subheader("Custom Stress Scenario")
        col1, col2 = st.columns(2)
        with col1:
            custom_equity_shock = st.slider("Equity Shock (%)", -60, 0, -20) / 100
        with col2:
            custom_bond_shock = st.slider("Bond Shock (%)", -30, 30, 0) / 100

        custom_stress = risk_mgr.run_custom_stress_test(
            returns_data, custom_equity_shock, custom_bond_shock, total_value
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Estimated Impact", f"{custom_stress['estimated_impact_pct']:.2f}%")
        with col2:
            st.metric("Dollar Impact", format_currency(custom_stress['estimated_impact_dollar']))
        with col3:
            st.metric("Stressed Value", format_currency(custom_stress['stressed_portfolio_value']))

    except Exception as e:
        st.error(f"Error in risk management: {e}")


def display_fixed_income():
    """Display fixed income analytics."""
    st.header("Fixed Income Analytics")

    fi = FixedIncomeAnalytics()

    st.subheader("Bond Calculator")

    col1, col2, col3 = st.columns(3)
    with col1:
        face_value = st.number_input("Face Value ($)", value=1000.0, step=100.0)
        coupon_rate = st.number_input("Coupon Rate (%)", value=5.0, step=0.25) / 100
    with col2:
        ytm = st.number_input("Yield to Maturity (%)", value=4.5, step=0.25) / 100
        years = st.number_input("Years to Maturity", value=10.0, step=0.5, min_value=0.5)
    with col3:
        frequency = st.selectbox("Coupon Frequency", [1, 2, 4],
                                  format_func=lambda x: {1: 'Annual', 2: 'Semi-Annual', 4: 'Quarterly'}[x],
                                  index=1)

    # Bond pricing
    pricing = fi.calculate_bond_price(face_value, coupon_rate, ytm, years, frequency)
    duration = fi.calculate_duration(face_value, coupon_rate, ytm, years, frequency)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Clean Price", format_currency(pricing['clean_price']))
        st.metric("Premium/Discount", format_currency(pricing['premium_discount']))
    with col2:
        st.metric("Macaulay Duration", f"{duration['macaulay_duration']:.3f} yrs")
        st.metric("Modified Duration", f"{duration['modified_duration']:.3f}")
    with col3:
        st.metric("DV01", format_currency(duration['dv01']))
        st.metric("Convexity", f"{duration['convexity']:.2f}")
    with col4:
        st.metric("Total Coupons", format_currency(pricing['total_coupons']))
        st.metric("Coupon Payment", format_currency(pricing['coupon_payment']))

    # Price sensitivity analysis
    st.subheader("Price Sensitivity Analysis")

    sensitivities = []
    for bps in [-200, -100, -50, -25, 25, 50, 100, 200]:
        sens = fi.price_sensitivity(face_value, coupon_rate, ytm, years, bps, frequency)
        sensitivities.append({
            'Yield Change (bps)': bps,
            'Duration Effect (%)': f"{sens['duration_effect_pct']:.3f}",
            'Convexity Effect (%)': f"{sens['convexity_effect_pct']:.3f}",
            'Total Change (%)': f"{sens['total_change_pct']:.3f}",
            'New Price': format_currency(sens['exact_new_price']),
            'Dollar Change': format_currency(sens['dollar_change']),
        })

    st.dataframe(pd.DataFrame(sensitivities), use_container_width=True)

    # Price-yield curve
    yield_range = np.arange(max(0.001, ytm - 0.04), ytm + 0.04, 0.002)
    prices = [fi.calculate_bond_price(face_value, coupon_rate, y, years, frequency)['clean_price']
              for y in yield_range]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=yield_range * 100, y=prices,
        mode='lines', name='Price-Yield Relationship',
        line=dict(color='#3498db', width=2)
    ))
    fig.add_trace(go.Scatter(
        x=[ytm * 100], y=[pricing['clean_price']],
        mode='markers', name='Current',
        marker=dict(color='red', size=12)
    ))
    fig.update_layout(
        title='Price-Yield Relationship',
        xaxis_title='Yield (%)',
        yaxis_title='Price ($)'
    )
    st.plotly_chart(fig, use_container_width=True)

    # Yield Curve Builder
    st.subheader("Yield Curve Analysis")

    st.write("Enter Treasury yields (or use defaults):")
    default_maturities = [0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30]
    default_yields = [4.8, 4.7, 4.5, 4.3, 4.2, 4.1, 4.15, 4.2, 4.4, 4.5]

    cols = st.columns(5)
    maturities = []
    yields_input = []
    for i, (mat, yld) in enumerate(zip(default_maturities, default_yields)):
        with cols[i % 5]:
            y = st.number_input(f"{mat}Y (%)", value=yld, step=0.05, key=f"yc_{mat}")
            maturities.append(mat)
            yields_input.append(y / 100)

    curve = fi.build_yield_curve(maturities, yields_input)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Curve Shape", curve['shape'])
    with col2:
        st.metric("Term Spread", f"{curve['term_spread_bps']:.0f} bps")
    with col3:
        st.metric("Short Rate", f"{curve['short_rate']*100:.2f}%")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=curve['maturities'], y=[y * 100 for y in curve['yields']],
        mode='lines+markers', name='Spot Curve',
        line=dict(color='#3498db', width=2)
    ))
    if curve['forward_rates']:
        fwd_x = [(f['from'] + f['to']) / 2 for f in curve['forward_rates']]
        fwd_y = [f['forward_rate'] * 100 for f in curve['forward_rates']]
        fig.add_trace(go.Scatter(
            x=fwd_x, y=fwd_y,
            mode='lines+markers', name='Forward Rates',
            line=dict(color='#e74c3c', dash='dash')
        ))
    fig.update_layout(
        title='Treasury Yield Curve',
        xaxis_title='Maturity (Years)',
        yaxis_title='Yield (%)'
    )
    st.plotly_chart(fig, use_container_width=True)


def display_esg_compliance(calculator):
    """Display ESG scoring and compliance monitoring."""
    st.header("ESG & Compliance")

    snapshot = calculator.get_snapshot()
    if not snapshot.positions:
        st.info("No positions to analyze.")
        return

    esg = ESGAnalyzer()
    symbols = list(set(p.symbol for p in snapshot.positions))
    total_value = snapshot.total_value
    weights = {}
    for p in snapshot.positions:
        weights[p.symbol] = weights.get(p.symbol, 0) + p.current_value / total_value

    # ESG Scores
    st.subheader("ESG Scores")
    with st.spinner("Calculating ESG scores..."):
        scores = esg.calculate_esg_scores(symbols, weights)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Portfolio ESG Score", f"{scores['portfolio_esg_score']:.1f}/100")
    with col2:
        st.metric("Environmental", f"{scores['portfolio_environmental']:.1f}")
    with col3:
        st.metric("Social", f"{scores['portfolio_social']:.1f}")
    with col4:
        st.metric("Governance", f"{scores['portfolio_governance']:.1f}")

    st.write(f"**Portfolio ESG Rating:** {scores['portfolio_esg_rating']}")

    # Position-level scores
    score_data = pd.DataFrame([
        {
            'Symbol': symbol,
            'ESG Score': v['total_esg'],
            'Rating': v['esg_rating'],
            'Environmental': v['environmental'],
            'Social': v['social'],
            'Governance': v['governance'],
            'Sector': v['sector'],
            'E Risk': v['e_risk'],
        }
        for symbol, v in scores['position_scores'].items()
    ]).sort_values('ESG Score', ascending=False)

    # ESG score heatmap
    fig = px.bar(
        score_data, x='Symbol', y=['Environmental', 'Social', 'Governance'],
        title='ESG Scores by Position',
        barmode='group',
        color_discrete_sequence=['#2ecc71', '#3498db', '#9b59b6']
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(score_data, use_container_width=True)

    # Exclusion Screening
    st.subheader("Exclusion Screening")
    screen_options = list(ESGAnalyzer.EXCLUSION_SCREENS.keys())
    selected_screens = st.multiselect(
        "Select screens to apply",
        screen_options,
        default=screen_options
    )

    screening = esg.run_exclusion_screening(symbols, selected_screens)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Compliant Positions", f"{screening['n_clean']}/{len(symbols)}")
    with col2:
        st.metric("Compliance Rate", f"{screening['pct_compliant']:.1f}%")
    with col3:
        violated = screening['n_violations']
        st.metric("Violations", violated)

    if screening['violations']:
        st.warning("Positions violating exclusion screens:")
        for symbol, screens in screening['violations'].items():
            st.write(f"- **{symbol}**: {', '.join(screens)}")

    # Compliance Rules
    st.subheader("Compliance Monitoring")
    compliance = esg.check_compliance_rules(weights)

    if compliance['is_compliant']:
        st.success("Portfolio is fully compliant with all rules.")
    else:
        st.error(f"Portfolio has {compliance['n_violations']} compliance violation(s).")

    if compliance['violations']:
        for v in compliance['violations']:
            st.error(f"**{v['rule']}** ({v['symbol']}): Limit {v['limit']}, Actual {v['actual']}")

    if compliance['warnings']:
        for w in compliance['warnings']:
            st.warning(f"**{w['rule']}** ({w['symbol']}): Limit {w['limit']}, Actual {w['actual']}")

    # Carbon Metrics
    st.subheader("Carbon Footprint")
    carbon = esg.calculate_carbon_metrics(symbols, weights, total_value)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Carbon Intensity", f"{carbon['portfolio_carbon_intensity']:.0f} tCO2e/$M")
    with col2:
        st.metric("Total Footprint", f"{carbon['total_footprint_tco2']:.1f} tCO2e")
    with col3:
        st.metric("vs Benchmark", f"{carbon['vs_benchmark_pct']:+.1f}%")
    with col4:
        st.metric("Carbon Risk", carbon['carbon_risk'])

    # Carbon by position
    carbon_data = pd.DataFrame([
        {'Symbol': s, 'Carbon Intensity': v['carbon_intensity'], 'Sector': v['sector']}
        for s, v in carbon['position_carbon'].items()
    ]).sort_values('Carbon Intensity', ascending=False)

    fig = px.bar(
        carbon_data, x='Symbol', y='Carbon Intensity',
        title='Carbon Intensity by Position (tCO2e per $M Revenue)',
        color='Sector',
    )
    fig.add_hline(y=carbon['benchmark_intensity'], line_dash="dash",
                  annotation_text="S&P 500 Benchmark", line_color="red")
    st.plotly_chart(fig, use_container_width=True)


def display_liquidity_analysis(calculator):
    """Display liquidity analysis dashboard."""
    st.header("Liquidity Analysis")

    snapshot = calculator.get_snapshot()
    if not snapshot.positions:
        st.info("No positions to analyze.")
        return

    analyzer = LiquidityAnalyzer()
    total_value = snapshot.total_value

    # Build positions dict
    positions = {}
    for p in snapshot.positions:
        positions[p.symbol] = positions.get(p.symbol, 0) + p.current_value

    lookback = st.slider("Lookback Period (days)", 30, 252, 90)

    with st.spinner("Analyzing liquidity..."):
        try:
            liq_report = analyzer.analyze_portfolio_liquidity(positions, lookback)
        except Exception as e:
            st.error(f"Error analyzing liquidity: {e}")
            return

    # Portfolio-level metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Liquidity Score", f"{liq_report['liquidity_score']:.0f}/100")
    with col2:
        st.metric("Liquidation Cost",
                   format_currency(liq_report['total_liquidation_cost']),
                   delta=f"{liq_report['liquidation_cost_pct']:.2f}%")
    with col3:
        st.metric("Max Days to Liquidate", f"{liq_report['max_days_to_full_liquidation']:.0f}")
    with col4:
        st.metric("Total AUM", format_currency(total_value))

    # Tier distribution
    st.subheader("Liquidity Tier Distribution")
    if liq_report['tier_distribution']:
        tier_data = pd.DataFrame([
            {'Tier': k, 'Weight (%)': v * 100}
            for k, v in liq_report['tier_distribution'].items()
        ])
        fig = px.pie(
            tier_data, values='Weight (%)', names='Tier',
            title='Portfolio Liquidity Distribution',
            color='Tier',
            color_discrete_map={t: v['color'] for t, v in LiquidityAnalyzer.LIQUIDITY_TIERS.items()}
        )
        st.plotly_chart(fig, use_container_width=True)

    # Position-level analysis
    st.subheader("Position Liquidity Details")
    pos_data = []
    for symbol, analysis in liq_report['position_analysis'].items():
        if 'error' in analysis:
            continue
        pos_data.append({
            'Symbol': symbol,
            'Value': format_currency(analysis['position_value']),
            'Avg Daily Value': format_currency(analysis['avg_daily_value']),
            'Spread (bps)': f"{analysis['spread_bps']:.1f}",
            'Days to Liquidate': f"{analysis['days_to_liquidate_10pct']:.1f}",
            'Tier': analysis['liquidity_tier'],
            '% of ADV': f"{analysis['pct_of_adv']:.1f}%",
            'Impact Cost': f"{analysis['market_impact']['total_cost_pct']:.3f}%" if 'market_impact' in analysis else 'N/A',
        })

    if pos_data:
        st.dataframe(pd.DataFrame(pos_data), use_container_width=True)

    # Liquidity at Risk
    st.subheader("Liquidity at Risk")
    lar = liq_report.get('liquidity_at_risk', {})
    if lar:
        lar_data = pd.DataFrame([
            {'Horizon': k.replace('_', ' ').title(), 'Liquidatable (%)': v['pct_of_portfolio'],
             'Liquidatable Value': format_currency(v['liquidatable_value'])}
            for k, v in lar.items()
        ])
        st.dataframe(lar_data, use_container_width=True)

        fig = px.bar(
            lar_data, x='Horizon', y='Liquidatable (%)',
            title='Portfolio Liquidity at Risk',
            color='Liquidatable (%)',
            color_continuous_scale='Greens'
        )
        fig.add_hline(y=100, line_dash="dash", line_color="green", annotation_text="100% Liquid")
        st.plotly_chart(fig, use_container_width=True)

    # Redemption scenario
    st.subheader("Redemption Scenario Analysis")
    col1, col2 = st.columns(2)
    with col1:
        redemption_pct = st.slider("Redemption Size (% of AUM)", 1, 50, 10)
    with col2:
        urgency = st.selectbox("Urgency", ['urgent', 'normal', 'planned'],
                                format_func=lambda x: {'urgent': 'Urgent (1 day)', 'normal': 'Normal (5 days)',
                                                       'planned': 'Planned (20 days)'}[x])

    redemption_amount = total_value * redemption_pct / 100

    with st.spinner("Analyzing redemption scenario..."):
        try:
            redemption = analyzer.calculate_redemption_risk(positions, redemption_amount, urgency)
            if 'error' not in redemption:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Redemption Amount", format_currency(redemption_amount))
                with col2:
                    st.metric("Market Impact Cost",
                              format_currency(redemption['total_market_impact']),
                              delta=f"{redemption['impact_pct']:.2f}%")
                with col3:
                    feasible = "Yes" if redemption['is_feasible'] else "No"
                    st.metric("Feasible?", feasible)
        except Exception as e:
            st.warning(f"Could not complete redemption analysis: {e}")


def display_multi_portfolio():
    """Display multi-portfolio management."""
    st.header("Multi-Portfolio Management")

    if 'multi_portfolio_manager' not in st.session_state:
        st.session_state.multi_portfolio_manager = MultiPortfolioManager()

    manager = st.session_state.multi_portfolio_manager

    # Add current portfolio as a fund
    if st.session_state.portfolio_positions:
        if st.button("Add Current Portfolio as Fund"):
            fund_name = st.text_input("Fund Name", value="Main Portfolio", key="new_fund_name")
            fund = Fund(
                name=fund_name if fund_name else "Main Portfolio",
                fund_id=f"fund_{len(manager.funds) + 1}",
                positions=st.session_state.portfolio_positions,
                strategy='Long Only',
            )
            manager.add_fund(fund)
            st.success(f"Added {fund.name} to multi-portfolio manager.")

    if not manager.funds:
        st.info("No funds added yet. Add the current portfolio as a fund to get started.")
        st.markdown("""
        ### Multi-Portfolio Management

        This tab allows institutional managers to:
        - **Track multiple portfolios/funds** simultaneously
        - **Compare performance** across funds
        - **Identify position overlap** between portfolios
        - **Calculate firm-wide exposure** and concentration risk
        - **Aggregate AUM reporting** across all managed assets

        Upload portfolios or add the current portfolio as a fund to begin.
        """)
        return

    # Fund overview
    st.subheader("Fund Overview")
    fund_list = manager.list_funds()
    fund_df = pd.DataFrame(fund_list)
    if not fund_df.empty:
        fund_df['total_value'] = fund_df['total_value'].apply(lambda x: format_currency(x))
        fund_df['total_return_pct'] = fund_df['total_return_pct'].apply(lambda x: f"{x:.2f}%")
        st.dataframe(fund_df, use_container_width=True)

    # Aggregate view
    st.subheader("Firm-Wide Aggregate View")
    aggregate = manager.get_aggregate_view()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total AUM", format_currency(aggregate['total_aum']))
    with col2:
        st.metric("Total Return", f"{aggregate['total_return_pct']:.2f}%")
    with col3:
        st.metric("Unique Positions", aggregate['n_unique_positions'])
    with col4:
        st.metric("Diversification", aggregate['diversification'])

    # Cross-fund comparison
    if len(manager.funds) > 1:
        st.subheader("Fund Comparison")
        comparison = manager.compare_funds()
        st.dataframe(comparison, use_container_width=True)

        # Overlap analysis
        st.subheader("Position Overlap Analysis")
        fund_ids = list(manager.funds.keys())
        for i in range(len(fund_ids)):
            for j in range(i + 1, len(fund_ids)):
                overlap = manager.find_overlap(fund_ids[i], fund_ids[j])
                st.write(f"**{overlap['fund_1']} vs {overlap['fund_2']}:**")
                st.write(f"- Common positions: {overlap['n_common']} ({overlap['jaccard_similarity']:.1f}% Jaccard similarity)")
                st.write(f"- Overlap weight: {overlap['overlap_weight_fund_1']:.1f}% / {overlap['overlap_weight_fund_2']:.1f}%")


def display_client_report(calculator):
    """Display client report generation."""
    st.header("Client Report")

    snapshot = calculator.get_snapshot()
    if not snapshot.positions:
        st.info("No positions for report generation.")
        return

    reporter = ClientReportGenerator()
    total_value = snapshot.total_value

    st.subheader("Report Configuration")
    col1, col2 = st.columns(2)
    with col1:
        report_period = st.selectbox("Report Period", ['MTD', 'QTD', 'YTD', '1Y'], index=2)
        management_fee = st.number_input("Management Fee (%)", value=0.75, step=0.05) / 100
    with col2:
        benchmark_name = st.selectbox("Benchmark", list(BENCHMARKS.keys()), index=0)
        performance_fee = st.number_input("Performance Fee (%)", value=0.0, step=1.0) / 100

    if st.button("Generate Report"):
        with st.spinner("Generating institutional client report..."):
            # Executive Summary
            st.subheader("Executive Summary")
            inception_date = min(p.purchase_date for p in snapshot.positions)
            total_return = snapshot.total_return_pct / 100

            summary = reporter.generate_executive_summary(
                total_value, total_return, 0, report_period, inception_date
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Portfolio Value", format_currency(summary['portfolio_value']))
            with col2:
                st.metric("Total Return", f"{summary['total_return']*100:.2f}%")
            with col3:
                st.metric("Active Return", f"{summary['active_return']*100:.2f}%")

            st.write(f"**Report Date:** {summary['report_date']}")
            st.write(f"**Inception:** {summary['inception_date']}")

            # Holdings
            st.subheader("Top Holdings")
            positions_data = [
                {
                    'symbol': p.symbol,
                    'description': p.description or p.symbol,
                    'asset_class': p.asset_class or 'N/A',
                    'value': p.current_value,
                    'return_pct': p.unrealized_gain_loss_pct,
                }
                for p in snapshot.positions
            ]
            holdings_df = reporter.generate_holdings_summary(positions_data, total_value)
            st.dataframe(holdings_df, use_container_width=True)

            # Allocation Summary
            st.subheader("Asset Allocation")
            allocation = snapshot.get_allocation()
            alloc_df = reporter.generate_allocation_summary(allocation)
            st.dataframe(alloc_df, use_container_width=True)

            fig = px.pie(
                values=list(allocation.values()),
                names=list(allocation.keys()),
                title="Portfolio Allocation"
            )
            st.plotly_chart(fig, use_container_width=True)

            # Fee Disclosure
            st.subheader("Fee Disclosure")
            fees = reporter.generate_fee_disclosure(
                total_value, management_fee, performance_fee, total_return
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Gross Return", f"{fees['gross_return_pct']:.2f}%")
            with col2:
                st.metric("Total Fees", format_currency(fees['total_fees_dollar']))
            with col3:
                st.metric("Net Return", f"{fees['net_return_pct']:.2f}%")

            # Commentary
            st.subheader("Performance Commentary")
            top = sorted(positions_data, key=lambda x: x.get('return_pct', 0), reverse=True)[:3]
            bottom = sorted(positions_data, key=lambda x: x.get('return_pct', 0))[:3]

            top_contrib = [{'symbol': p['symbol'], 'contribution': p['return_pct'] / 100} for p in top]
            bottom_contrib = [{'symbol': p['symbol'], 'contribution': p['return_pct'] / 100} for p in bottom]

            commentary = reporter.generate_commentary(
                total_return, 0, top_contrib, bottom_contrib
            )
            st.markdown(commentary)

            # Export button
            report_data = reporter.generate_full_report(
                {
                    'total_value': total_value,
                    'total_return': total_return,
                    'positions': positions_data,
                    'top_contributors': top_contrib,
                    'bottom_contributors': bottom_contrib,
                },
            )

            report_json = reporter.export_report_data(report_data, format='json')
            st.download_button(
                "Download Report (JSON)",
                report_json,
                file_name=f"client_report_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )


def main():
    """Main application."""
    # Render sidebar
    sidebar()

    # Title
    st.title("📊 Institutional Portfolio Management Platform")

    # Check if portfolio is loaded
    if not st.session_state.portfolio_positions:
        st.info("👈 Upload a portfolio CSV file to get started")

        # Show instructions
        st.markdown("""
        ### Getting Started

        1. **Upload Portfolio**: Use the sidebar to upload your portfolio positions as a CSV file
        2. **View Metrics**: See comprehensive performance metrics and risk-adjusted returns
        3. **Compare Benchmarks**: Compare your portfolio against major indices
        4. **Analyze Correlations**: Understand relationships between your positions
        5. **Track Macro Indicators**: Monitor economic indicators that may affect your portfolio

        #### Required CSV Format

        Your portfolio CSV should have these columns:
        - `symbol`: Stock ticker (e.g., AAPL, MSFT)
        - `shares`: Number of shares
        - `purchase_date`: Date of purchase (YYYY-MM-DD)
        - `purchase_price`: Price per share at purchase

        Download the template from the sidebar to get started!
        """)

        return

    # Create calculator
    calculator = PortfolioCalculator(st.session_state.portfolio_positions)

    # Tabs for different sections - Institutional Grade
    tab_names = [
        "Overview",
        "Performance",
        "Attribution",
        "Benchmark",
        "Factor Analysis",
        "Risk Management",
        "Macro Indicators",
        "Correlations",
        "Fixed Income",
        "ESG & Compliance",
        "Liquidity",
        "LTCMA",
        "Monte Carlo",
        "Retirement",
        "Tax Planning",
        "Rebalancing",
        "Dividends",
        "Optimization",
        "Sectors",
        "Goals",
        "AI Insights",
        "Multi-Portfolio",
        "Client Report",
    ]
    tabs = st.tabs(tab_names)

    with tabs[0]:
        display_portfolio_overview(calculator)

    with tabs[1]:
        display_performance_metrics(calculator)

    with tabs[2]:
        display_performance_attribution(calculator)

    with tabs[3]:
        display_benchmark_comparison(calculator)

    with tabs[4]:
        display_factor_analysis(calculator)

    with tabs[5]:
        display_risk_management(calculator)

    with tabs[6]:
        display_macro_indicators()

    with tabs[7]:
        display_correlation_analysis(calculator)

    with tabs[8]:
        display_fixed_income()

    with tabs[9]:
        display_esg_compliance(calculator)

    with tabs[10]:
        display_liquidity_analysis(calculator)

    with tabs[11]:
        display_ltcma_analysis()

    with tabs[12]:
        display_monte_carlo_simulation(calculator)

    with tabs[13]:
        display_retirement_planning(calculator)

    with tabs[14]:
        display_tax_planning(calculator)

    with tabs[15]:
        display_rebalancing(calculator)

    with tabs[16]:
        display_dividends(calculator)

    with tabs[17]:
        display_optimization(calculator)

    with tabs[18]:
        display_sector_analysis(calculator)

    with tabs[19]:
        display_goal_planning(calculator)

    with tabs[20]:
        display_ai_insights(calculator)

    with tabs[21]:
        display_multi_portfolio()

    with tabs[22]:
        display_client_report(calculator)


if __name__ == "__main__":
    main()
