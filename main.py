from datetime import datetime, timedelta
import streamlit as st
import yfinance as yf
import pandas as pd

from calculate_tds import calculate_tdsequential
from plot_tds import plot_tdsequential

# Define functions first, before the Streamlit interface code

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


# Begin Streamlit UI code

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
period_options = ["3 months", "1 month", "6 months", "1 year", "Other"]
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
    if selected_period == "1 month":
        start_date = end_date - timedelta(days=30)
    elif selected_period == "3 months":
        start_date = end_date - timedelta(days=90)
    elif selected_period == "6 months":
        start_date = end_date - timedelta(days=180)
    else:  # 1 year
        start_date = end_date - timedelta(days=365)

# Interval selection
interval_options = ["1d", "1wk", "1mo"]
interval_names = {"1d": "1 Day", "1wk": "1 Week", "1mo": "1 Month"}
selected_interval = st.sidebar.selectbox(
    "Select Interval", interval_options, format_func=lambda x: interval_names[x]
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

# Download button
if st.sidebar.button("Download Data"):
    # Load data
    data = get_stock_data(ticker, start_date, end_date, selected_interval)

    # Display data information
    if data is not None and not data.empty:
        st.header(f"{ticker} Historical Data")
        st.write(
            f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        )
        st.write(f"Interval: {interval_names[selected_interval]}")

        # Apply TD Sequential calculation
        td_data = calculate_tdsequential(data, stock_name=ticker)

        # Plot candlestick chart with TD Sequential indicators
        fig = plot_tdsequential(
            td_data,
            stock_name=ticker,
            window=1000,
            show_support_resistance=show_support_resistance,
            show_setup_stop_loss=show_setup_stop_loss,
            show_countdown_stop_loss=show_countdown_stop_loss,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Display the dataframe
        st.subheader("Data Table")
        display_cols = ["Open", "High", "Low", "Close", "Volume"]
        st.dataframe(td_data)
