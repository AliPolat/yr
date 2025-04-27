from datetime import datetime, timedelta
import streamlit as st
import yfinance as yf

from calculate_tds import calculate_tdsequential
from plot_tds import plot_tdsequential
from calculate_eqcrv import (
    calculate_performance_metrics,
    apply_simple_strategy,
    create_performance_plots,
)


def get_stock_data(ticker, start_date, end_date, interval):
    """Download stock data using yfinance and fix column names"""
    try:
        data = yf.download(ticker, start=start_date, end=end_date, interval=interval)
        # Fix column names
        data.columns = [col[0] for col in data.columns]
        return data
    except Exception as e:
        st.error(f"Error downloading data: {e}")
        return None


# Set the page title
st.title("TD Sequential Indicator")

# Sidebar for stock selection
st.sidebar.header("Settings")
stock_options = ["AAPL", "GOLD", "BITCOIN", "Other"]
selected_stock_option = st.sidebar.selectbox("Select Stock/Asset", stock_options)

# If "Other" is selected, let the user input a custom stock symbol
if selected_stock_option == "BITCOIN":
    ticker = "BTC-USD"
elif selected_stock_option == "Other":
    ticker = st.sidebar.text_input("Enter Stock Symbol", "MSFT")
else:
    ticker = selected_stock_option

# Time period selection
period_options = [
    "3 months",
    "1 day",
    "1 week",
    "1 month",
    "6 months",
    "1 year",
    "Other",
]
selected_period = st.sidebar.selectbox("Select Time Period", period_options)

# If "Other" is selected, let the user input a custom period
if selected_period == "Other":
    custom_period_days = st.sidebar.number_input(
        "Enter Number of Days", min_value=1, value=30
    )
    end_date = datetime.now()
    start_date = end_date - timedelta(days=custom_period_days)
else:
    end_date = datetime.now()
    period_days = {
        "1 day": 1,
        "1 week": 7,
        "1 month": 30,
        "3 months": 90,
        "6 months": 180,
        "1 year": 365,
    }
    start_date = end_date - timedelta(days=period_days.get(selected_period, 90))

# Interval selection
interval_options = ["1d", "5m", "15m", "1h", "4h", "1wk", "1mo"]
interval_names = {
    "1d": "1 Day",
    "5m": "5 Minutes",
    "15m": "15 Minutes",
    "1h": "1 Hour",
    "4h": "4 Hours",
    "1wk": "1 Week",
    "1mo": "1 Month",
}
selected_interval = st.sidebar.selectbox(
    "Select Interval", interval_options, format_func=lambda x: interval_names[x]
)

# Add note about intraday data limitations
if selected_interval in ["5m", "15m", "1h", "4h"]:
    st.sidebar.info(
        "Note: Intraday data (minutes/hours) is typically only available for the last 60 days. "
        "For longer periods, please use daily intervals or higher."
    )

# Add checkboxes for display options
display_options = st.sidebar.expander("Display Options", expanded=False)
show_support_resistance = display_options.checkbox(
    "Display Support/Resistance",
    value=True,
    help="Show support and resistance levels on the chart",
)
show_setup_stop_loss = display_options.checkbox(
    "Display Setup Stop Loss",
    value=True,
    help="Show stop loss levels for TD Sequential setups",
)
show_countdown_stop_loss = display_options.checkbox(
    "Display Countdown Stop Loss",
    value=True,
    help="Show stop loss levels for TD Sequential countdowns",
)

# Strategy settings
strategy_options = st.sidebar.expander("Strategy Options", expanded=False)
initial_capital = strategy_options.number_input(
    "Initial Capital", value=100000, step=10000
)
strategy_types = ["dabak", "sma_crossover", "mean_reversion", "other"]
strategy_type = strategy_options.selectbox("Strategy Type", strategy_types)

# If "other" is selected, let the user input a custom strategy name
if strategy_type == "other":
    custom_strategy = strategy_options.text_input(
        "Enter Custom Strategy Name", "custom_strategy"
    )
    strategy_type = custom_strategy

# Display Analysis button (renamed from Download Data)
if st.sidebar.button("Display Analysis"):
    # Load data
    data = get_stock_data(ticker, start_date, end_date, selected_interval)

    # Display data information
    if data is not None and not data.empty:
        st.header(f"{ticker} Analysis")
        st.write(
            f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        )
        st.write(f"Interval: {interval_names[selected_interval]}")

        # Apply TD Sequential calculation
        td_data = calculate_tdsequential(data, stock_name=ticker)

        # Apply strategy
        df_strategy = apply_simple_strategy(
            td_data,
            initial_capital=initial_capital,
            strategy_type=strategy_type,
            fast_period=20,  # Could make configurable
            slow_period=50,  # Could make configurable
        )

        # Calculate metrics
        metrics = calculate_performance_metrics(
            df_strategy, initial_capital=initial_capital
        )

        # Create visualizations
        title = f"{ticker} Trading Performance: {strategy_type.replace('_', ' ').title()} Strategy"
        equity_fig, metrics_fig = create_performance_plots(df_strategy, metrics, title)

        # Plot candlestick chart with TD Sequential indicators
        td_fig = plot_tdsequential(
            td_data,
            stock_name=ticker,
            window=1000,
            show_support_resistance=show_support_resistance,
            show_setup_stop_loss=show_setup_stop_loss,
            show_countdown_stop_loss=show_countdown_stop_loss,
        )

        # Create tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(
            ["TD Sequential Chart", "Data Table", "Equity Curve", "Performance Metrics"]
        )

        with tab1:
            st.plotly_chart(td_fig, use_container_width=True)

        with tab2:
            st.dataframe(td_data)

        with tab3:
            st.plotly_chart(equity_fig, use_container_width=True)

        with tab4:
            st.plotly_chart(metrics_fig, use_container_width=True)
