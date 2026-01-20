"""Portfolio Analysis & Tracking Dashboard - Main Application."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json

# Local imports
from models.database import init_db, get_session, PortfolioPosition
from models.portfolio import Position, PortfolioSnapshot
from services.data_fetcher import MarketDataFetcher, MacroDataFetcher, CorrelationAnalyzer
from services.portfolio_calculator import PortfolioCalculator
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
            purchase_price=p.purchase_price
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
            purchase_price=pos.purchase_price
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
        df['Purchase Price'] = df['Purchase Price'].apply(lambda x: format_currency(x))
        df['Current Price'] = df['Current Price'].apply(lambda x: format_currency(x))
        df['Cost Basis'] = df['Cost Basis'].apply(lambda x: format_currency(x))
        df['Current Value'] = df['Current Value'].apply(lambda x: format_currency(x))
        df['Gain/Loss'] = df['Gain/Loss'].apply(lambda x: format_currency(x))
        df['Return %'] = df['Return %'].apply(lambda x: format_percentage(x / 100))

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
            options=['1M', '3M', '6M', '1Y', '3Y', '5Y', 'YTD', 'MAX'],
            index=3
        )

    start_date, end_date = get_date_range(period)

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
    st.header("📉 LTCMA Analysis")

    if st.session_state.ltcma_data is None:
        st.info("Upload JP Morgan LTCMA data to analyze correlations with expected returns.")

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

    ltcma_df = st.session_state.ltcma_data

    st.subheader("LTCMA Expectations")
    st.dataframe(ltcma_df, use_container_width=True)

    # Display as chart
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=ltcma_df['asset_class'],
        y=ltcma_df['expected_return'] * 100,
        name='Expected Return',
        marker_color='#1f77b4'
    ))

    fig.update_layout(
        title="LTCMA Expected Returns by Asset Class",
        xaxis_title="Asset Class",
        yaxis_title="Expected Return (%)",
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

    # Risk-Return scatter
    st.subheader("Risk-Return Profile")

    fig = px.scatter(
        ltcma_df,
        x='volatility',
        y='expected_return',
        text='asset_class',
        labels={
            'volatility': 'Volatility (Risk)',
            'expected_return': 'Expected Return'
        }
    )

    fig.update_traces(textposition='top center')
    fig.update_layout(height=500)

    st.plotly_chart(fig, use_container_width=True)


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
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Overview",
        "Performance",
        "Benchmark",
        "Macro Indicators",
        "Correlations",
        "LTCMA"
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


if __name__ == "__main__":
    main()
