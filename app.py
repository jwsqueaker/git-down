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
from utils.csv_handler import CSVHandler
from utils.helpers import format_percentage, format_currency, get_date_range
from config.settings import BENCHMARKS, MACRO_INDICATORS

# Page configuration
st.set_page_config(
    page_title="Portfolio Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
init_db()

# Initialize session state
if 'portfolio_positions' not in st.session_state:
    st.session_state.portfolio_positions = []
if 'ltcma_data' not in st.session_state:
    st.session_state.ltcma_data = None


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

            # Calculate simple total return
            simple_return = (hist_data['value'].iloc[-1] / hist_data['value'].iloc[0] - 1) * 100
            st.write(f"**Simple Total Return:** {simple_return:.2f}%")

            # Show if there were cash flows
            cost_change = hist_data['cost_basis'].iloc[-1] - hist_data['cost_basis'].iloc[0]
            if abs(cost_change) > 0.01:
                st.warning(f"⚠️ Net cash flows detected: {format_currency(cost_change)}")
                st.write("Returns are adjusted for cash flows (money added/removed)")
            else:
                st.success("✓ No cash flows - simple return calculation applies")

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


def main():
    """Main application."""
    # Render sidebar
    sidebar()

    # Title
    st.title("📊 Portfolio Analysis & Tracking Dashboard")

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

    # Tabs for different sections
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13, tab14, tab15 = st.tabs([
        "Overview",
        "Performance",
        "Benchmark",
        "Macro Indicators",
        "Correlations",
        "LTCMA",
        "Monte Carlo",
        "Retirement",
        "Tax Planning",
        "Rebalancing",
        "Dividends",
        "Optimization",
        "Sectors",
        "Goals",
        "AI Insights"
    ])

    with tab1:
        display_portfolio_overview(calculator)

    with tab2:
        display_performance_metrics(calculator)

    with tab3:
        display_benchmark_comparison(calculator)

    with tab4:
        display_macro_indicators()

    with tab5:
        display_correlation_analysis(calculator)

    with tab6:
        display_ltcma_analysis()

    with tab7:
        display_monte_carlo_simulation(calculator)

    with tab8:
        display_retirement_planning(calculator)

    with tab9:
        display_tax_planning(calculator)

    with tab10:
        display_rebalancing(calculator)

    with tab11:
        display_dividends(calculator)

    with tab12:
        display_optimization(calculator)

    with tab13:
        display_sector_analysis(calculator)

    with tab14:
        display_goal_planning(calculator)

    with tab15:
        display_ai_insights(calculator)


if __name__ == "__main__":
    main()
