import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

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


def calculate_td_sequential(data):
    """Calculate TD Sequential indicator with buy/sell setup and countdown signals"""
    # Copy the dataframe to avoid modifying the original
    df = data.copy()

    # Initialize all columns
    df["buy_setup"] = 0
    df["sell_setup"] = 0
    df["buy_countdown"] = 0
    df["sell_countdown"] = 0
    df["buy_setup_perfected"] = False
    df["sell_setup_perfected"] = False

    # For readability, we'll use separate methods for buy and sell scenarios

    # Buy Setup (price closing LOWER than the close 4 bars earlier)
    current_buy_setup = 0
    for i in range(4, len(df)):
        if df["Close"].iloc[i] < df["Close"].iloc[i - 4]:  # Buy setup condition
            current_buy_setup += 1
            df.loc[df.index[i], "buy_setup"] = current_buy_setup

            # Check if the setup is perfected (low of bars 8 or 9 is lower than the low of bars 6 and 7)
            if current_buy_setup == 9:
                if (df["Low"].iloc[i] < df["Low"].iloc[i - 2]) or (
                    df["Low"].iloc[i - 1] < df["Low"].iloc[i - 3]
                ):
                    df.loc[df.index[i], "buy_setup_perfected"] = True
        else:
            current_buy_setup = 0
            df.loc[df.index[i], "buy_setup"] = 0

    # Sell Setup (price closing HIGHER than the close 4 bars earlier)
    current_sell_setup = 0
    for i in range(4, len(df)):
        if df["Close"].iloc[i] > df["Close"].iloc[i - 4]:  # Sell setup condition
            current_sell_setup += 1
            df.loc[df.index[i], "sell_setup"] = current_sell_setup

            # Check if the setup is perfected (high of bars 8 or 9 is higher than the high of bars 6 and 7)
            if current_sell_setup == 9:
                if (df["High"].iloc[i] > df["High"].iloc[i - 2]) or (
                    df["High"].iloc[i - 1] > df["High"].iloc[i - 3]
                ):
                    df.loc[df.index[i], "sell_setup_perfected"] = True
        else:
            current_sell_setup = 0
            df.loc[df.index[i], "sell_setup"] = 0

    # Buy Countdown (only starts after a completed buy setup)
    # The close must be less than or equal to the low two bars earlier
    in_buy_countdown = False
    buy_countdown_count = 0
    buy_countdown_start_index = 0

    for i in range(4, len(df)):
        # Check for a completed buy setup (9 consecutive lower closes)
        if df["buy_setup"].iloc[i] == 9 and not in_buy_countdown:
            in_buy_countdown = True
            buy_countdown_count = 0
            buy_countdown_start_index = i + 1  # Start countdown from the next bar

        # If we're in a buy countdown, check conditions
        if in_buy_countdown and i >= buy_countdown_start_index:
            # Buy countdown condition: close less than or equal to the low two bars earlier
            if df["Close"].iloc[i] <= df["Low"].iloc[i - 2]:
                buy_countdown_count += 1
                df.loc[df.index[i], "buy_countdown"] = buy_countdown_count

                # Reset after reaching 13
                if buy_countdown_count == 13:
                    in_buy_countdown = False

    # Sell Countdown (only starts after a completed sell setup)
    # The close must be greater than or equal to the high two bars earlier
    in_sell_countdown = False
    sell_countdown_count = 0
    sell_countdown_start_index = 0

    for i in range(4, len(df)):
        # Check for a completed sell setup (9 consecutive higher closes)
        if df["sell_setup"].iloc[i] == 9 and not in_sell_countdown:
            in_sell_countdown = True
            sell_countdown_count = 0
            sell_countdown_start_index = i + 1  # Start countdown from the next bar

        # If we're in a sell countdown, check conditions
        if in_sell_countdown and i >= sell_countdown_start_index:
            # Sell countdown condition: close greater than or equal to the high two bars earlier
            if df["Close"].iloc[i] >= df["High"].iloc[i - 2]:
                sell_countdown_count += 1
                df.loc[df.index[i], "sell_countdown"] = sell_countdown_count

                # Reset after reaching 13
                if sell_countdown_count == 13:
                    in_sell_countdown = False

    # Add summary columns
    df["td_setup_direction"] = "neutral"
    df.loc[df["buy_setup"] == 9, "td_setup_direction"] = "buy"
    df.loc[df["sell_setup"] == 9, "td_setup_direction"] = "sell"

    df["td_countdown_direction"] = "neutral"
    df.loc[df["buy_countdown"] == 13, "td_countdown_direction"] = "buy"
    df.loc[df["sell_countdown"] == 13, "td_countdown_direction"] = "sell"

    return df



def plot_td_sequential(data):
    """Create a Plotly candlestick chart with TD Sequential indicators

    Places setup numbers directly on candles and countdown numbers below candles
    Highlights 9s in setups and 13s in countdowns
    """

    fig = make_subplots(rows=1, cols=1, shared_xaxes=True)

    # Add candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            name="Price",
        )
    )

    # Add buy setup numbers (green, on candles)
    buy_setup_data = data[data["buy_setup"] > 0].copy()
    if not buy_setup_data.empty:
        fig.add_trace(
            go.Scatter(
                x=buy_setup_data.index,
                y=(buy_setup_data["High"] + buy_setup_data["Low"])
                / 2,  # Middle of candle
                mode="text",
                text=buy_setup_data["buy_setup"].apply(
                    lambda x: f"<b>{x}</b>" if x == 9 else str(x)
                ),
                textposition="middle right",
                textfont=dict(
                    color="green",
                    size=buy_setup_data["buy_setup"].apply(
                        lambda x: 14 if x == 9 else 10
                    ),
                ),
                name="Buy Setup",
                hoverinfo="none",
            )
        )

    # Add sell setup numbers (red, on candles)
    sell_setup_data = data[data["sell_setup"] > 0].copy()
    if not sell_setup_data.empty:
        fig.add_trace(
            go.Scatter(
                x=sell_setup_data.index,
                y=(sell_setup_data["High"] + sell_setup_data["Low"])
                / 2,  # Middle of candle
                mode="text",
                text=sell_setup_data["sell_setup"].apply(
                    lambda x: f"<b>{x}</b>" if x == 9 else str(x)
                ),
                textposition="middle left",
                textfont=dict(
                    color="red",
                    size=sell_setup_data["sell_setup"].apply(
                        lambda x: 14 if x == 9 else 10
                    ),
                ),
                name="Sell Setup",
                hoverinfo="none",
            )
        )

    # Add buy countdown numbers (green, clearly below candles)
    buy_countdown_data = data[data["buy_countdown"] > 0].copy()
    if not buy_countdown_data.empty:
        fig.add_trace(
            go.Scatter(
                x=buy_countdown_data.index,
                # Further below the low for better visibility
                y=buy_countdown_data["Low"] - (buy_countdown_data["Low"] * 0.004),
                mode="text",
                text=buy_countdown_data["buy_countdown"].apply(
                    lambda x: f"<b>{x}</b>" if x == 13 else str(x)
                ),
                textposition="bottom center",
                textfont=dict(
                    color="green",
                    size=buy_countdown_data["buy_countdown"].apply(
                        lambda x: 14 if x == 13 else 10
                    ),
                ),
                name="Buy Countdown",
                hoverinfo="none",
            )
        )

    # Add sell countdown numbers (red, clearly below candles)
    sell_countdown_data = data[data["sell_countdown"] > 0].copy()
    if not sell_countdown_data.empty:
        fig.add_trace(
            go.Scatter(
                x=sell_countdown_data.index,
                # Further below the low for better separation from buy countdown
                y=sell_countdown_data["Low"] - (sell_countdown_data["Low"] * 0.008),
                mode="text",
                text=sell_countdown_data["sell_countdown"].apply(
                    lambda x: f"<b>{x}</b>" if x == 13 else str(x)
                ),
                textposition="bottom center",
                textfont=dict(
                    color="red",
                    size=sell_countdown_data["sell_countdown"].apply(
                        lambda x: 14 if x == 13 else 10
                    ),
                ),
                name="Sell Countdown",
                hoverinfo="none",
            )
        )

    # Add visual markers for completed setups (9)
    completed_buy_setups = data[data["buy_setup"] == 9].index
    for date in completed_buy_setups:
        # Add triangle marker for buy setup completion
        fig.add_trace(
            go.Scatter(
                x=[date],
                y=[data.loc[date, "Low"] * 0.99],
                mode="markers",
                marker=dict(
                    symbol="triangle-up",
                    size=12,
                    color="green",
                    line=dict(width=1, color="darkgreen"),
                ),
                name="Buy Setup Complete",
                legendgroup="Buy Setup Complete",
                showlegend=(
                    date == completed_buy_setups[0]
                    if len(completed_buy_setups) > 0
                    else True
                ),
                hoverinfo="text",
                hovertext=f"Buy Setup Complete on {date.strftime('%Y-%m-%d')}",
            )
        )

    completed_sell_setups = data[data["sell_setup"] == 9].index
    for date in completed_sell_setups:
        # Add triangle marker for sell setup completion
        fig.add_trace(
            go.Scatter(
                x=[date],
                y=[data.loc[date, "High"] * 1.01],
                mode="markers",
                marker=dict(
                    symbol="triangle-down",
                    size=12,
                    color="red",
                    line=dict(width=1, color="darkred"),
                ),
                name="Sell Setup Complete",
                legendgroup="Sell Setup Complete",
                showlegend=(
                    date == completed_sell_setups[0]
                    if len(completed_sell_setups) > 0
                    else True
                ),
                hoverinfo="text",
                hovertext=f"Sell Setup Complete on {date.strftime('%Y-%m-%d')}",
            )
        )

    # Add markers for completed countdowns (13)
    completed_buy_countdowns = data[data["buy_countdown"] == 13].index
    for date in completed_buy_countdowns:
        # Add star marker for buy countdown completion
        fig.add_trace(
            go.Scatter(
                x=[date],
                y=[data.loc[date, "Low"] * 0.97],
                mode="markers",
                marker=dict(
                    symbol="star",
                    size=16,
                    color="green",
                    line=dict(width=1, color="darkgreen"),
                ),
                name="Buy Countdown Complete",
                legendgroup="Buy Countdown Complete",
                showlegend=(
                    date == completed_buy_countdowns[0]
                    if len(completed_buy_countdowns) > 0
                    else True
                ),
                hoverinfo="text",
                hovertext=f"Buy Countdown Complete on {date.strftime('%Y-%m-%d')}",
            )
        )

    completed_sell_countdowns = data[data["sell_countdown"] == 13].index
    for date in completed_sell_countdowns:
        # Add star marker for sell countdown completion
        fig.add_trace(
            go.Scatter(
                x=[date],
                y=[data.loc[date, "High"] * 1.03],
                mode="markers",
                marker=dict(
                    symbol="star",
                    size=16,
                    color="red",
                    line=dict(width=1, color="darkred"),
                ),
                name="Sell Countdown Complete",
                legendgroup="Sell Countdown Complete",
                showlegend=(
                    date == completed_sell_countdowns[0]
                    if len(completed_sell_countdowns) > 0
                    else True
                ),
                hoverinfo="text",
                hovertext=f"Sell Countdown Complete on {date.strftime('%Y-%m-%d')}",
            )
        )

    # Update layout
    fig.update_layout(
        title=f"TD Sequential Indicator for {ticker}",
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        height=600,
        width=1000,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )

    return fig


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
period_options = ["1 month", "3 months", "6 months", "1 year", "Other"]
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
        td_data = calculate_td_sequential(data)

        # Plot candlestick chart with TD Sequential indicators
        fig = plot_td_sequential(td_data)
        st.plotly_chart(fig, use_container_width=True)

        # Display the dataframe
        st.subheader("Data Table")
        display_cols = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "buy_setup",
            "sell_setup",
            "buy_countdown",
            "sell_countdown",
            "buy_setup_perfected",
            "sell_setup_perfected",
            "td_setup_direction",
            "td_countdown_direction",
        ]
        st.dataframe(td_data[display_cols])
