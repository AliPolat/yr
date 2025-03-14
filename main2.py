import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime, timedelta


# Function to calculate TD Sequential
def calculate_td_sequential(df):
    # Initialize columns for TD Setup and Countdown
    df["TD_Sell_Setup"] = 0
    df["TD_Buy_Setup"] = 0
    df["TD_Sell_Countdown"] = 0
    df["TD_Buy_Countdown"] = 0

    # Setup phase
    for i in range(4, len(df)):
        # Sell Setup - price closes higher than the close 4 bars earlier
        if df["Close"].iloc[i] > df["Close"].iloc[i - 4]:
            if df["TD_Sell_Setup"].iloc[i - 1] == 9:
                df.loc[df.index[i], "TD_Sell_Setup"] = 1
            else:
                df.loc[df.index[i], "TD_Sell_Setup"] = (
                    df["TD_Sell_Setup"].iloc[i - 1] + 1
                )
        else:
            df.loc[df.index[i], "TD_Sell_Setup"] = 0

        # Buy Setup - price closes lower than the close 4 bars earlier
        if df["Close"].iloc[i] < df["Close"].iloc[i - 4]:
            if df["TD_Buy_Setup"].iloc[i - 1] == 9:
                df.loc[df.index[i], "TD_Buy_Setup"] = 1
            else:
                df.loc[df.index[i], "TD_Buy_Setup"] = df["TD_Buy_Setup"].iloc[i - 1] + 1
        else:
            df.loc[df.index[i], "TD_Buy_Setup"] = 0

    # Find setup completion points (when TD_Setup reaches 9)
    sell_setups = []
    buy_setups = []

    for i in range(len(df)):
        if df["TD_Sell_Setup"].iloc[i] == 9:
            sell_setups.append(i)
        if df["TD_Buy_Setup"].iloc[i] == 9:
            buy_setups.append(i)

    # Countdown phase
    # For a sell countdown, we need a sell setup completion first
    for setup_idx in sell_setups:
        if setup_idx + 2 >= len(df):
            continue

        countdown = 0
        for i in range(setup_idx + 2, len(df)):
            if countdown >= 13:
                break
            # Sell Countdown: Close > High two bars earlier
            if df["Close"].iloc[i] > df["High"].iloc[i - 2]:
                countdown += 1
                df.loc[df.index[i], "TD_Sell_Countdown"] = countdown

    # For a buy countdown, we need a buy setup completion first
    for setup_idx in buy_setups:
        if setup_idx + 2 >= len(df):
            continue

        countdown = 0
        for i in range(setup_idx + 2, len(df)):
            if countdown >= 13:
                break
            # Buy Countdown: Close < Low two bars earlier
            if df["Close"].iloc[i] < df["Low"].iloc[i - 2]:
                countdown += 1
                df.loc[df.index[i], "TD_Buy_Countdown"] = countdown

    # Calculate Support and Resistance points for each setup
    df["Support"] = np.nan
    df["Resistance"] = np.nan

    # Support/Resistance at Setup completion
    for i in sell_setups:
        # For sell setup, low of candle 9 is resistance
        df.loc[df.index[i], "Resistance"] = df["Low"].iloc[i]

    for i in buy_setups:
        # For buy setup, high of candle 9 is support
        df.loc[df.index[i], "Support"] = df["High"].iloc[i]

    # Calculate Buy and Sell Stop points
    df["Buy_Stop"] = np.nan
    df["Sell_Stop"] = np.nan

    for i in sell_setups:
        # Sell stop for sell setup is below the low of the bar with the lowest low in bars 1-9
        lowest_low = min(df["Low"].iloc[i - 8 : i + 1])
        df.loc[df.index[i], "Sell_Stop"] = lowest_low * 0.99  # 1% below lowest low

    for i in buy_setups:
        # Buy stop for buy setup is above the high of the bar with the highest high in bars 1-9
        highest_high = max(df["High"].iloc[i - 8 : i + 1])
        df.loc[df.index[i], "Buy_Stop"] = highest_high * 1.01  # 1% above highest high

    # Calculate Stop Loss points
    df["Setup_Stop_Loss"] = np.nan
    df["Countdown_Stop_Loss"] = np.nan

    for i in sell_setups:
        # Stop loss for sell setup is above the highest high of setup phase
        highest_high = max(df["High"].iloc[i - 8 : i + 1])
        df.loc[df.index[i], "Setup_Stop_Loss"] = (
            highest_high * 1.02
        )  # 2% above highest high

    for i in buy_setups:
        # Stop loss for buy setup is below the lowest low of setup phase
        lowest_low = min(df["Low"].iloc[i - 8 : i + 1])
        df.loc[df.index[i], "Setup_Stop_Loss"] = (
            lowest_low * 0.98
        )  # 2% below lowest low

    # Stop loss for countdown completions (TD_Countdown = 13)
    for i in range(len(df)):
        if df["TD_Sell_Countdown"].iloc[i] == 13:
            # Countdown stop loss for sell is above the high of 13th bar
            df.loc[df.index[i], "Countdown_Stop_Loss"] = (
                df["High"].iloc[i] * 1.02
            )  # 2% above high

        if df["TD_Buy_Countdown"].iloc[i] == 13:
            # Countdown stop loss for buy is below the low of 13th bar
            df.loc[df.index[i], "Countdown_Stop_Loss"] = (
                df["Low"].iloc[i] * 0.98
            )  # 2% below low

    return df

def plot_td_sequential_plotly(df, symbol):
    # Create figure with secondary y-axis
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(
            f"{symbol} Price with TD Sequential Support/Resistance",
            "TD Sequential Indicator",
        ),
        row_heights=[0.7, 0.3],
    )

    # Add candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=symbol,
        ),
        row=1,
        col=1,
    )

    # Add support levels
    support_df = df[~df["Support"].isna()]
    if not support_df.empty:
        for idx, row in support_df.iterrows():
            # Calculate end date (20 bars forward or end of dataframe)
            end_idx = min(df.index.get_loc(idx) + 20, len(df) - 1)
            end_date = df.index[end_idx]

            fig.add_trace(
                go.Scatter(
                    x=[idx, end_date],
                    y=[row["Support"], row["Support"]],
                    mode="lines",
                    line=dict(color="green", width=2, dash="dash"),
                    name="Support",
                ),
                row=1,
                col=1,
            )

    # Add resistance levels
    resistance_df = df[~df["Resistance"].isna()]
    if not resistance_df.empty:
        for idx, row in resistance_df.iterrows():
            # Calculate end date (20 bars forward or end of dataframe)
            end_idx = min(df.index.get_loc(idx) + 20, len(df) - 1)
            end_date = df.index[end_idx]

            fig.add_trace(
                go.Scatter(
                    x=[idx, end_date],
                    y=[row["Resistance"], row["Resistance"]],
                    mode="lines",
                    line=dict(color="red", width=2, dash="dash"),
                    name="Resistance",
                ),
                row=1,
                col=1,
            )

    # Add Buy Stop points
    buy_stop_df = df[~df["Buy_Stop"].isna()]
    if not buy_stop_df.empty:
        fig.add_trace(
            go.Scatter(
                x=buy_stop_df.index,
                y=buy_stop_df["Buy_Stop"],
                mode="markers",
                marker=dict(symbol="triangle-up", size=10, color="blue"),
                name="Buy Stop",
            ),
            row=1,
            col=1,
        )

    # Add Sell Stop points
    sell_stop_df = df[~df["Sell_Stop"].isna()]
    if not sell_stop_df.empty:
        fig.add_trace(
            go.Scatter(
                x=sell_stop_df.index,
                y=sell_stop_df["Sell_Stop"],
                mode="markers",
                marker=dict(symbol="triangle-down", size=10, color="purple"),
                name="Sell Stop",
            ),
            row=1,
            col=1,
        )

    # NEW CODE: Add Setup Stop Loss lines
    setup_sl_df = df[~df["Setup_Stop_Loss"].isna()]
    if not setup_sl_df.empty:
        # First add the markers as before
        fig.add_trace(
            go.Scatter(
                x=setup_sl_df.index,
                y=setup_sl_df["Setup_Stop_Loss"],
                mode="markers",
                marker=dict(symbol="x", size=10, color="orange"),
                name="Setup Stop Loss",
            ),
            row=1,
            col=1,
        )
        
        # Now add horizontal lines for each Setup Stop Loss
        for idx, row in setup_sl_df.iterrows():
            # Calculate end date (10 bars forward or end of dataframe)
            end_idx = min(df.index.get_loc(idx) + 10, len(df) - 1)
            end_date = df.index[end_idx]
            
            fig.add_trace(
                go.Scatter(
                    x=[idx, end_date],
                    y=[row["Setup_Stop_Loss"], row["Setup_Stop_Loss"]],
                    mode="lines",
                    line=dict(color="orange", width=1.5, dash="dot"),
                    showlegend=False,
                ),
                row=1,
                col=1,
            )

    # NEW CODE: Add Countdown Stop Loss lines
    countdown_sl_df = df[~df["Countdown_Stop_Loss"].isna()]
    if not countdown_sl_df.empty:
        # First add the markers as before
        fig.add_trace(
            go.Scatter(
                x=countdown_sl_df.index,
                y=countdown_sl_df["Countdown_Stop_Loss"],
                mode="markers",
                marker=dict(symbol="x", size=10, color="magenta"),
                name="Countdown Stop Loss",
            ),
            row=1,
            col=1,
        )
        
        # Now add horizontal lines for each Countdown Stop Loss
        for idx, row in countdown_sl_df.iterrows():
            # Calculate end date (10 bars forward or end of dataframe)
            end_idx = min(df.index.get_loc(idx) + 10, len(df) - 1)
            end_date = df.index[end_idx]
            
            fig.add_trace(
                go.Scatter(
                    x=[idx, end_date],
                    y=[row["Countdown_Stop_Loss"], row["Countdown_Stop_Loss"]],
                    mode="lines",
                    line=dict(color="magenta", width=1.5, dash="dot"),
                    showlegend=False,
                ),
                row=1,
                col=1,
            )

    # TD Sequential numbers on candlestick chart
    # TD Sell Setup numbers above candles
    for i, row in df.iterrows():
        if row["TD_Sell_Setup"] > 0:
            # Position above the high price with a small offset
            position = row["High"] * 1.005  # 0.5% above the high
            
            fig.add_trace(
                go.Scatter(
                    x=[i],
                    y=[position],
                    mode="text",
                    text=str(int(row["TD_Sell_Setup"])),
                    textposition="top center",
                    textfont=dict(
                        color="red",
                        size=9 if row["TD_Sell_Setup"] != 9 else 12,
                        family="Arial",
                    ),
                    showlegend=False,
                    hoverinfo="text",
                    hovertext=f'Sell Setup: {int(row["TD_Sell_Setup"])}',
                    name="Sell Setup" if row["TD_Sell_Setup"] == 1 else "",
                ),
                row=1,
                col=1,
            )

    # TD Buy Setup numbers below candles
    for i, row in df.iterrows():
        if row["TD_Buy_Setup"] > 0:
            # Position below the low price with a small offset
            position = row["Low"] * 0.995  # 0.5% below the low
            
            fig.add_trace(
                go.Scatter(
                    x=[i],
                    y=[position],
                    mode="text",
                    text=str(int(row["TD_Buy_Setup"])),
                    textposition="bottom center",
                    textfont=dict(
                        color="green",
                        size=9 if row["TD_Buy_Setup"] != 9 else 12,
                        family="Arial",
                    ),
                    showlegend=False,
                    hoverinfo="text",
                    hovertext=f'Buy Setup: {int(row["TD_Buy_Setup"])}',
                    name="Buy Setup" if row["TD_Buy_Setup"] == 1 else "",
                ),
                row=1,
                col=1,
            )

    # TD Sell Countdown numbers above candles but higher than sell setup
    for i, row in df.iterrows():
        if row["TD_Sell_Countdown"] > 0:
            # Position above the high price with a larger offset than the setup
            position = row["High"] * 1.01  # 1% above the high
            
            fig.add_trace(
                go.Scatter(
                    x=[i],
                    y=[position],
                    mode="text",
                    text=str(int(row["TD_Sell_Countdown"])),
                    textposition="top center",
                    textfont=dict(
                        color="darkred",
                        size=8 if row["TD_Sell_Countdown"] != 13 else 11,
                        family="Arial Bold",
                    ),
                    showlegend=False,
                    hoverinfo="text",
                    hovertext=f'Sell Countdown: {int(row["TD_Sell_Countdown"])}',
                    name="Sell Countdown" if row["TD_Sell_Countdown"] == 1 else "",
                ),
                row=1,
                col=1,
            )

    # TD Buy Countdown numbers below candles but lower than buy setup
    for i, row in df.iterrows():
        if row["TD_Buy_Countdown"] > 0:
            # Position below the low price with a larger offset than the setup
            position = row["Low"] * 0.99  # 1% below the low
            
            fig.add_trace(
                go.Scatter(
                    x=[i],
                    y=[position],
                    mode="text",
                    text=str(int(row["TD_Buy_Countdown"])),
                    textposition="bottom center",
                    textfont=dict(
                        color="darkgreen",
                        size=8 if row["TD_Buy_Countdown"] != 13 else 11,
                        family="Arial Bold",
                    ),
                    showlegend=False,
                    hoverinfo="text",
                    hovertext=f'Buy Countdown: {int(row["TD_Buy_Countdown"])}',
                    name="Buy Countdown" if row["TD_Buy_Countdown"] == 1 else "",
                ),
                row=1,
                col=1,
            )

    # Create TD Sequential indicators for the bottom chart
    # TD Sell Setup
    sell_setup_traces = []
    for i, row in df.iterrows():
        if row["TD_Sell_Setup"] > 0:
            sell_setup_traces.append(
                go.Scatter(
                    x=[i],
                    y=[0.75],
                    mode="text",
                    text=str(int(row["TD_Sell_Setup"])),
                    textposition="middle center",
                    textfont=dict(
                        color="red",
                        size=10 if row["TD_Sell_Setup"] != 9 else 14,
                        family="Arial",
                    ),
                    showlegend=False,
                    hoverinfo="text",
                    hovertext=f'Sell Setup: {int(row["TD_Sell_Setup"])}',
                )
            )

    # TD Buy Setup
    buy_setup_traces = []
    for i, row in df.iterrows():
        if row["TD_Buy_Setup"] > 0:
            buy_setup_traces.append(
                go.Scatter(
                    x=[i],
                    y=[0.25],
                    mode="text",
                    text=str(int(row["TD_Buy_Setup"])),
                    textposition="middle center",
                    textfont=dict(
                        color="green",
                        size=10 if row["TD_Buy_Setup"] != 9 else 14,
                        family="Arial",
                    ),
                    showlegend=False,
                    hoverinfo="text",
                    hovertext=f'Buy Setup: {int(row["TD_Buy_Setup"])}',
                )
            )

    # TD Sell Countdown
    sell_countdown_traces = []
    for i, row in df.iterrows():
        if row["TD_Sell_Countdown"] > 0:
            sell_countdown_traces.append(
                go.Scatter(
                    x=[i],
                    y=[0.85],
                    mode="text",
                    text=str(int(row["TD_Sell_Countdown"])),
                    textposition="middle center",
                    textfont=dict(
                        color="darkred",
                        size=8 if row["TD_Sell_Countdown"] != 13 else 14,
                        family="Arial",
                    ),
                    showlegend=False,
                    hoverinfo="text",
                    hovertext=f'Sell Countdown: {int(row["TD_Sell_Countdown"])}',
                )
            )

    # TD Buy Countdown
    buy_countdown_traces = []
    for i, row in df.iterrows():
        if row["TD_Buy_Countdown"] > 0:
            buy_countdown_traces.append(
                go.Scatter(
                    x=[i],
                    y=[0.15],
                    mode="text",
                    text=str(int(row["TD_Buy_Countdown"])),
                    textposition="middle center",
                    textfont=dict(
                        color="darkgreen",
                        size=8 if row["TD_Buy_Countdown"] != 13 else 14,
                        family="Arial",
                    ),
                    showlegend=False,
                    hoverinfo="text",
                    hovertext=f'Buy Countdown: {int(row["TD_Buy_Countdown"])}',
                )
            )

    # Add all TD Sequential traces to the second subplot
    for trace in (
        sell_setup_traces
        + buy_setup_traces
        + sell_countdown_traces
        + buy_countdown_traces
    ):
        fig.add_trace(trace, row=2, col=1)

    # Add horizontal lines and indicator labels in the second subplot
    fig.add_trace(
        go.Scatter(
            x=[df.index[0], df.index[-1]],
            y=[0.5, 0.5],
            mode="lines",
            line=dict(color="gray", width=1, dash="dot"),
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    # Add indicator labels
    fig.add_annotation(
        x=df.index[0],
        y=0.75,
        text="Sell Setup",
        showarrow=False,
        xanchor="left",
        yanchor="middle",
        font=dict(color="red"),
        row=2,
        col=1,
    )

    fig.add_annotation(
        x=df.index[0],
        y=0.25,
        text="Buy Setup",
        showarrow=False,
        xanchor="left",
        yanchor="middle",
        font=dict(color="green"),
        row=2,
        col=1,
    )

    fig.add_annotation(
        x=df.index[0],
        y=0.85,
        text="Sell Countdown",
        showarrow=False,
        xanchor="left",
        yanchor="middle",
        font=dict(color="darkred"),
        row=2,
        col=1,
    )

    fig.add_annotation(
        x=df.index[0],
        y=0.15,
        text="Buy Countdown",
        showarrow=False,
        xanchor="left",
        yanchor="middle",
        font=dict(color="darkgreen"),
        row=2,
        col=1,
    )

    # Add legend for the main chart to explain the TD Sequential numbers
    fig.add_annotation(
        x=df.index[0],
        y=df["High"].max() * 1.03,
        text="Red: Sell Setup | Dark Red: Sell Countdown | Green: Buy Setup | Dark Green: Buy Countdown",
        showarrow=False,
        xanchor="left",
        yanchor="middle",
        font=dict(size=10),
        row=1,
        col=1,
    )

    # Update y-axis range for the indicator subplot
    fig.update_yaxes(range=[0, 1], showticklabels=False, row=2, col=1)

    # Update layout
    fig.update_layout(
        title=f"TD Sequential Analysis for {symbol}",
        yaxis_title="Price ($)",
        xaxis_rangeslider_visible=False,
        height=800,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
    )

    return fig


# Set page title and configuration
st.set_page_config(
    page_title="TD Sequential Indicator Dashboard", page_icon="📈", layout="wide"
)

# App title and description
st.title("TD Sequential Indicator Dashboard")
st.markdown(
    """
This app calculates and displays the TD Sequential indicator for any stock.
It shows setup and countdown phases, support/resistance levels, buy/sell stop points, and stop loss levels.
"""
)

# Sidebar inputs for stock selection and parameters
with st.sidebar:
    st.header("Settings")

    # Stock symbol input
    stock_symbol = st.text_input("Stock Symbol", "AAPL").upper()

    # Time period selection
    period_options = {
        "1 Month": 30,
        "3 Months": 90,
        "6 Months": 180,
        "1 Year": 365,
        "2 Years": 730,
        "5 Years": 1825,
    }
    selected_period = st.selectbox("Time Period", list(period_options.keys()))
    days = period_options[selected_period]

    # Interval selection
    interval_options = ["1d", "1h", "15m", "5m"]
    interval = st.selectbox(
        "Interval",
        interval_options,
        help="Note: Smaller intervals may only be available for shorter time periods",
    )

    # Calculate button
    calculate_button = st.button("Calculate TD Sequential")

# Main app logic
if calculate_button or "data" in st.session_state:
    try:
        # Display loading message
        with st.spinner(f"Downloading data for {stock_symbol}..."):
            # Calculate dates
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Download data
            data = yf.download(
                stock_symbol, start=start_date, end=end_date, interval=interval
            )

            # Drop multiline column names and make one word
            data.columns = [col[0] for col in data.columns]
            st.write(data)

            # Check if data is empty
            if data.empty:
                st.error(
                    f"No data found for {stock_symbol}. Please check the symbol and try again."
                )
            else:
                # Store data in session state
                st.session_state.data = data
                st.session_state.symbol = stock_symbol

                # Calculate TD Sequential
                with st.spinner("Calculating TD Sequential..."):
                    td_data = calculate_td_sequential(data)

                    # Display stock info
                    stock_info = yf.Ticker(stock_symbol).info
                    company_name = stock_info.get("longName", stock_symbol)

                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader(company_name)
                        current_price = data["Close"].iloc[-1]
                        st.metric(
                            "Current Price",
                            f"${current_price:.2f}",
                            f"{(data['Close'].iloc[-1] - data['Close'].iloc[-2]) / data['Close'].iloc[-2] * 100:.2f}%",
                        )

                    with col2:
                        # Get some basic stats
                        price_change = (
                            (data["Close"].iloc[-1] - data["Close"].iloc[0])
                            / data["Close"].iloc[0]
                            * 100
                        )
                        highest_price = data["High"].max()
                        lowest_price = data["Low"].min()

                        st.metric("Period Change", f"{price_change:.2f}%")
                        st.metric(
                            "Highest/Lowest",
                            f"${highest_price:.2f} / ${lowest_price:.2f}",
                        )

                    # Create and display the chart
                    fig = plot_td_sequential_plotly(td_data, stock_symbol)
                    st.plotly_chart(fig, use_container_width=True)

                    # Display statistics
                    st.subheader("TD Sequential Statistics")

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric(
                            "Sell Setup Completions",
                            len(td_data[td_data["TD_Sell_Setup"] == 9]),
                        )
                    with col2:
                        st.metric(
                            "Buy Setup Completions",
                            len(td_data[td_data["TD_Buy_Setup"] == 9]),
                        )
                    with col3:
                        st.metric(
                            "Sell Countdown Completions",
                            len(td_data[td_data["TD_Sell_Countdown"] == 13]),
                        )
                    with col4:
                        st.metric(
                            "Buy Countdown Completions",
                            len(td_data[td_data["TD_Buy_Countdown"] == 13]),
                        )

                    # Show recent TD Sequential values
                    st.subheader("Recent TD Sequential Values")

                    # Select columns to show
                    display_cols = [
                        "Close",
                        "TD_Sell_Setup",
                        "TD_Buy_Setup",
                        "TD_Sell_Countdown",
                        "TD_Buy_Countdown",
                        "Support",
                        "Resistance",
                        "Buy_Stop",
                        "Sell_Stop",
                    ]

                    # Format the dataframe
                    display_df = td_data[display_cols].tail(10).copy()

                    # Format numeric columns
                    for col in display_df.columns:
                        if col in [
                            "TD_Sell_Setup",
                            "TD_Buy_Setup",
                            "TD_Sell_Countdown",
                            "TD_Buy_Countdown",
                        ]:
                            display_df[col] = display_df[col].apply(
                                lambda x: int(x) if not np.isnan(x) else ""
                            )
                        else:
                            display_df[col] = display_df[col].apply(
                                lambda x: f"{x:.2f}" if not np.isnan(x) else ""
                            )

                    st.dataframe(display_df, use_container_width=True)

                    # Add explanation
                    with st.expander("TD Sequential Explanation"):
                        st.markdown(
                            """
                        ## TD Sequential Indicator

                        The TD Sequential indicator is a technical analysis tool developed by Tom DeMark to identify potential price exhaustion points and trend reversals.

                        ### Components:

                        #### 1. Setup Phase
                        - **Buy Setup**: Occurs when price closes lower than the close 4 bars earlier for 9 consecutive bars.
                        - **Sell Setup**: Occurs when price closes higher than the close 4 bars earlier for 9 consecutive bars.

                        #### 2. Countdown Phase
                        - **Buy Countdown**: Initiated after a Buy Setup completion. Counts 13 instances where the close is lower than the low 2 bars earlier.
                        - **Sell Countdown**: Initiated after a Sell Setup completion. Counts 13 instances where the close is higher than the high 2 bars earlier.

                        #### 3. Support/Resistance Levels
                        - Support levels are drawn at the high of bar 9 of a Buy Setup.
                        - Resistance levels are drawn at the low of bar 9 of a Sell Setup.

                        #### 4. Buy/Sell Stop Points
                        - Buy Stop: Placed above the highest high of the Buy Setup phase.
                        - Sell Stop: Placed below the lowest low of the Sell Setup phase.

                        #### 5. Stop Loss Levels
                        - Setup Stop Loss: Based on the price extremes during the Setup phase.
                        - Countdown Stop Loss: Derived from the price at Countdown completion (bar 13).
                        """
                        )

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.error("Please check your inputs and try again.")

# Add footer with information
st.markdown("---")
st.markdown("TD Sequential Indicator Dashboard © 2025 | Data provided by Yahoo Finance")
st.markdown(
    "*Disclaimer: This app is for educational purposes only. Not financial advice.*"
)
