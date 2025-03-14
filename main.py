import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from datetime import timedelta


import calculation as c

st.title("Stock Data Viewer")

# Sidebar for user inputs
st.sidebar.header("Stock Selection")

# Stock selection with AAPL as default
stock_options = ["AAPL", "GOLD", "BTC-USD"]  # Moved AAPL to first position
stock_name = st.sidebar.selectbox(
    "Select a stock", stock_options + ["Other"], index=0
)  # index=0 sets AAPL as default
if stock_name == "Other":
    stock_name = st.sidebar.text_input("Enter the stock name")

# Duration selection with 3mo as default
period_options = ["3mo", "1mo", "6mo", "1y"]  # Moved 3mo to first position
period = st.sidebar.selectbox(
    "Select period", period_options, index=0
)  # index=0 sets 3mo as default

# Interval selection
interval_options = ["1d", "1wk"]
interval = st.sidebar.selectbox("Select interval", interval_options)

# Checkbox for support/resistance lines
display_support_resistance = st.sidebar.checkbox("Display Support and Resistance Lines")

# Checkbox for count stop points
display_count_stop_points = st.sidebar.checkbox("Display Count Stop Points")

# Download data with yfinance
if st.sidebar.button("Download Data"):
    data = yf.download(tickers=stock_name, period=period, interval=interval)
    st.write(f"Data for {stock_name}")
    # st.write(data)

    if display_support_resistance:
        pass

    if display_count_stop_points:
        pass

    # Drop multiline column names and make one word
    data.columns = [col[0] for col in data.columns]

    data_calculated = c.td_sequential(data)
    # st.write(data_calculated)

    data_advanced = c.calculate_support_resistance_stop_loss(data_calculated)
    st.write(data_advanced)

    fig = c.plot_td_sequential(
        data_advanced,
        draw_suport_resitantce=display_support_resistance,
        draw_count_stop_points=display_count_stop_points,
    )
    st.plotly_chart(fig)
