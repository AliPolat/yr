import numpy as np
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots


def td_sequential(data, high_col="High", low_col="Low", close_col="Close"):
    """
    Calculate the TD Sequential indicator for a given price series.

    Parameters:
    -----------
    data : pandas.DataFrame
        DataFrame containing price data with high, low, and close columns
    high_col : str, default='High'
        Name of the high price column
    low_col : str, default='Low'
        Name of the low price column
    close_col : str, default='Close'
        Name of the close price column

    Returns:
    --------
    pandas.DataFrame
        Original DataFrame with TD Sequential indicator columns added
    """
    # Make a copy of the input data
    df = data.copy()

    # Setup columns for TD Sequential
    df["TD_Setup"] = 0
    df["TD_Countdown"] = 0
    df["TD_Setup_Perfected"] = False
    df["TD_Buy_Setup"] = False
    df["TD_Sell_Setup"] = False
    df["TD_Buy_Countdown"] = False
    df["TD_Sell_Countdown"] = False

    # Calculate close 4 bars ago for comparison
    df["Close_4_Ago"] = df[close_col].shift(4)

    # TD Setup - Look for 9 consecutive closes greater/less than the close 4 bars ago
    setup_buy = 0
    setup_sell = 0

    for i in range(4, len(df)):
        # Reset counters if the sequence is broken
        if df.iloc[i][close_col] > df.iloc[i]["Close_4_Ago"]:
            setup_sell += 1
            setup_buy = 0
        elif df.iloc[i][close_col] < df.iloc[i]["Close_4_Ago"]:
            setup_buy += 1
            setup_sell = 0
        else:
            setup_buy = 0
            setup_sell = 0

        # Record the setup count
        if setup_buy > 0 and setup_buy <= 9:
            df.iloc[i, df.columns.get_loc("TD_Setup")] = setup_buy
            if setup_buy == 9:
                df.iloc[i, df.columns.get_loc("TD_Buy_Setup")] = True
                # Check for perfected setup (8 or 9 close is lower than the low of 6 and/or 7)
                if df.iloc[i][close_col] < min(
                    df.iloc[i - 3][low_col], df.iloc[i - 2][low_col]
                ):
                    df.iloc[i, df.columns.get_loc("TD_Setup_Perfected")] = True

        elif setup_sell > 0 and setup_sell <= 9:
            df.iloc[i, df.columns.get_loc("TD_Setup")] = setup_sell
            if setup_sell == 9:
                df.iloc[i, df.columns.get_loc("TD_Sell_Setup")] = True
                # Check for perfected setup (8 or 9 close is higher than the high of 6 and/or 7)
                if df.iloc[i][close_col] > max(
                    df.iloc[i - 3][high_col], df.iloc[i - 2][high_col]
                ):
                    df.iloc[i, df.columns.get_loc("TD_Setup_Perfected")] = True

    # TD Countdown - Begins after a completed setup
    countdown_buy = 0
    countdown_sell = 0
    in_buy_countdown = False
    in_sell_countdown = False

    for i in range(9, len(df)):
        # Check if a new setup has been completed
        if df.iloc[i]["TD_Buy_Setup"]:
            countdown_buy = 0
            in_buy_countdown = True
            in_sell_countdown = False

        if df.iloc[i]["TD_Sell_Setup"]:
            countdown_sell = 0
            in_sell_countdown = True
            in_buy_countdown = False

        # Continue existing countdown if in progress
        if in_buy_countdown and countdown_buy < 13:
            # For buy countdown, compare close to low 2 bars ago
            if df.iloc[i][close_col] < df.iloc[i - 2][low_col]:
                countdown_buy += 1
                df.iloc[i, df.columns.get_loc("TD_Countdown")] = countdown_buy

                if countdown_buy == 13:
                    df.iloc[i, df.columns.get_loc("TD_Buy_Countdown")] = True
                    in_buy_countdown = False

        if in_sell_countdown and countdown_sell < 13:
            # For sell countdown, compare close to high 2 bars ago
            if df.iloc[i][close_col] > df.iloc[i - 2][high_col]:
                countdown_sell += 1
                df.iloc[i, df.columns.get_loc("TD_Countdown")] = countdown_sell

                if countdown_sell == 13:
                    df.iloc[i, df.columns.get_loc("TD_Sell_Countdown")] = True
                    in_sell_countdown = False

    # Drop temporary column
    df = df.drop("Close_4_Ago", axis=1)

    return df

'''
def calculate_support_resistance(df, high_col="High", low_col="Low", close_col="Close"):
    """
    Calculate support and resistance levels during TD Sequential setup phases.

    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with price data

    Returns:
    --------
    pandas.DataFrame
        DataFrame with additional support and resistance columns
    """
    df_copy = df.copy()

    # Buy setup support levels
    df_copy["Buy_Setup_Support"] = np.nan
    # Sell setup resistance levels
    df_copy["Sell_Setup_Resistance"] = np.nan

    # Calculate stop loss levels
    df_copy["Buy_Countdown_Stop_Loss"] = np.nan
    df_copy["Sell_Countdown_Stop_Loss"] = np.nan

    for i in range(8, len(df_copy)):
        # Potential Buy Setup occured at this point
        if df_copy.iloc[i]["TD_Buy_Setup"]:
            # Buy Setup Support: Lowest low of bars 1-4 after initial Buy Setup
            buy_support_low = df_copy.iloc[i - 8 : i][low_col].min()
            df_copy.loc[df_copy.index[i], "Buy_Setup_Support"] = buy_support_low

        # Potential Sell Setup occured at this point
        if df_copy.iloc[i]["TD_Sell_Setup"]:
            # Sell Setup Resistance: Highest high of bars 1-4 after initial Sell Setup
            sell_resistance_high = df_copy.iloc[i - 8 : i ][high_col].max()
            df_copy.loc[df_copy.index[i], "Sell_Setup_Resistance"] = sell_resistance_high
        

        # Calculate Countdown Stop Loss Levels
        # Buy Countdown Stop Loss: Lowest low during the setup phase
        if df_copy.iloc[i]["TD_Buy_Countdown"]:
            buy_stop_low = df_copy.iloc[i - 12 : i + 1][low_col].min()
            df_copy.loc[df_copy.index[i], "Buy_Countdown_Stop_Loss"] = buy_stop_low

        # Sell Countdown Stop Loss: Highest high during the setup phase
        if df_copy.iloc[i]["TD_Sell_Countdown"]:
            sell_stop_high = df_copy.iloc[i - 12 : i + 1][high_col].max()
            df_copy.loc[df_copy.index[i], "Sell_Countdown_Stop_Loss"] = sell_stop_high

    return df_copy
'''

def calculate_support_resistance_stop_loss(
    df, high_col="High", low_col="Low", close_col="Close"
):
    """
    Calculate TD Sequential support, resistance and stop loss levels.

    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with price data and TD Sequential indicators
    high_col : str
        Name of high price column
    low_col : str
        Name of low price column
    close_col : str
        Name of close price column

    Returns:
    --------
    pandas.DataFrame
        DataFrame with additional support, resistance and stop loss columns
    """
    df_copy = df.copy()

    # Setup phase levels
    df_copy["Buy_Setup_Support"] = np.nan
    df_copy["Sell_Setup_Resistance"] = np.nan
    df_copy["Buy_Setup_Stop_Loss"] = np.nan
    df_copy["Sell_Setup_Stop_Loss"] = np.nan

    # Add this with other column initializations
    df_copy["Buy_Setup_Stop_Loss_Bar"] = np.nan
    df_copy["Sell_Setup_Stop_Loss_Bar"] = np.nan

    # Countdown phase levels
    df_copy["Buy_Countdown_Stop_Loss"] = np.nan
    df_copy["Sell_Countdown_Stop_Loss"] = np.nan

    for i in range(8, len(df_copy)):
        # Buy Setup calculations
        if df_copy.iloc[i]["TD_Buy_Setup"]:
            buy_support = df_copy.iloc[i - 8 : i ][high_col].max()
            df_copy.loc[df_copy.index[i], "Buy_Setup_Support"] = buy_support

            # Setup Stop Loss: highest high of entire setup phase (bars 1-9)
            # Find both the max value and its index
            buy_setup_values = df_copy.iloc[i - 8 : i][high_col]
            buy_setup_max = buy_setup_values.max()
            buy_setup_max_idx = buy_setup_values.idxmax()

            # Store both the stop loss value and the bar number where it occurred
            df_copy.loc[df_copy.index[i], "Buy_Setup_Stop_Loss"] = (buy_setup_max)

        # Sell Setup calculations
        if df_copy.iloc[i]["TD_Sell_Setup"]:
            # Resistance: Highest high of bars 1-9 of setup
            sell_resistance = df_copy.iloc[i - 8 : i][low_col].min()
            df_copy.loc[df_copy.index[i], "Sell_Setup_Resistance"] = sell_resistance

            # Setup Stop Loss: Find both the min value and its index
            sell_setup_values = df_copy.iloc[i - 8 : i][low_col]
            sell_setup_min = sell_setup_values.min()
            sell_setup_min_idx = sell_setup_values.idxmin()

            # Store both the stop loss value and the bar number where it occurred
            df_copy.loc[df_copy.index[i], "Sell_Setup_Stop_Loss"] = sell_setup_min  

        # Countdown Stop Loss calculations
        if df_copy.iloc[i]["TD_Buy_Countdown"]:
            # Buy Countdown Stop Loss: Lowest low during countdown phase
            buy_countdown_stop = df_copy.iloc[i - 12 : i + 1][low_col].min()
            df_copy.loc[df_copy.index[i], "Buy_Countdown_Stop_Loss"] = (
                buy_countdown_stop
            )

        if df_copy.iloc[i]["TD_Sell_Countdown"]:
            # Sell Countdown Stop Loss: Highest high during countdown phase
            sell_countdown_stop = df_copy.iloc[i - 12 : i + 1][high_col].max()
            df_copy.loc[df_copy.index[i], "Sell_Countdown_Stop_Loss"] = (
                sell_countdown_stop
            )

    return df_copy


def plot_td_sequential(
    df, window=1000, draw_suport_resitantce=False, draw_count_stop_points=False
):
    """
    Create an interactive Plotly chart for TD Sequential analysis with TD_Setup and TD_Countdown values.

    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with price data and TD Sequential indicators
    window : int, default=100
        Number of bars to display in the chart
    """

    plot_df = df.tail(window).copy()

    # Create subplot with two rows
    fig = make_subplots(rows=1, cols=1)

    # Candlestick chart (same as before)
    fig.add_trace(
        go.Candlestick(
            x=plot_df.index,
            open=plot_df["Open"],
            high=plot_df["High"],
            low=plot_df["Low"],
            close=plot_df["Close"],
            name="Price",
        ),
        row=1,
        col=1,
    )

    # Buy Setup signals
    buy_setups = plot_df[plot_df["TD_Buy_Setup"] == True]
    fig.add_trace(
        go.Scatter(
            x=buy_setups.index,
            y=buy_setups["Close"],
            mode="markers",
            marker=dict(symbol="triangle-up", size=10, color="green"),
            name="Buy Setup (9)",
        ),
        row=1,
        col=1,
    )

    # Sell Setup signals
    sell_setups = plot_df[plot_df["TD_Sell_Setup"] == True]
    fig.add_trace(
        go.Scatter(
            x=sell_setups.index,
            y=sell_setups["Close"],
            mode="markers",
            marker=dict(symbol="triangle-down", size=10, color="red"),
            name="Sell Setup (9)",
        ),
        row=1,
        col=1,
    )

    # Buy Countdown signals
    buy_countdown = plot_df[plot_df["TD_Buy_Countdown"] == True]
    fig.add_trace(
        go.Scatter(
            x=buy_countdown.index,
            y=buy_countdown["Close"],
            mode="markers",
            marker=dict(symbol="star", size=15, color="green"),
            name="Buy Countdown (13)",
        ),
        row=1,
        col=1,
    )

    # Sell Countdown signals
    sell_countdown = plot_df[plot_df["TD_Sell_Countdown"] == True]
    fig.add_trace(
        go.Scatter(
            x=sell_countdown.index,
            y=sell_countdown["Close"],
            mode="markers",
            marker=dict(symbol="star", size=15, color="red"),
            name="Sell Countdown (13)",
        ),
        row=1,
        col=1,
    )

    if draw_suport_resitantce:
        # Buy Setup Support Levels
        '''
        fig.add_trace(
            go.Scatter(
                x=plot_df.index,
                y=plot_df["Buy_Setup_Support"].ffill(),  # Fill NaN for visualization
                mode="lines",
                line=dict(color="blue", width=1, dash="dash"),
                name="Buy Setup Support",
            ),
            row=1,
            col=1,
        )
        '''
        
        # Sell Setup Resistance Levels
        fig.add_trace(
            go.Scatter(
                x=plot_df.index,
                y=plot_df[
                    "Sell_Setup_Resistance"
                ].ffill(),  # Fill NaN for visualization
                mode="lines",
                line=dict(color="orange", width=1, dash="dash"),
                name="Sell Setup Resistance",
            ),
            row=1,
            col=1,
        )

    if False:    
        # Buy Setup Support Levels
        fig.add_trace(
            go.Scatter(
                x=plot_df.index,
                y=plot_df["Buy_Setup_Stop_Loss"].ffill(),  # Fill NaN for visualization
                mode="lines",
                line=dict(color="blue", width=1, dash="dash"),
                name="Buy Setup Stop Loss",
            ),
            row=1,
            col=1,
        )

        # Sell Setup Stop Loss
        fig.add_trace(
            go.Scatter(
                x=plot_df.index,
                y=plot_df["Sell_Setup_Stop_Loss"].ffill(),  # Fill NaN for visualization
                mode="lines",
                line=dict(color="orange", width=1, dash="dash"),
                name="Sell Setup Stop Loss",
            ),
            row=1,
            col=1,
        )

    if draw_count_stop_points:
        # Buy Countdown Stop Loss Levels
        fig.add_trace(
            go.Scatter(
                x=plot_df.index,
                y=plot_df[
                    "Buy_Countdown_Stop_Loss"
                ].ffill(),  # Fill NaN for visualization
                mode="lines",
                line=dict(color="purple", width=1, dash="dash"),
                name="Buy Countdown Stop Loss",
            ),
            row=1,
            col=1,
        )

        # Sell Countdown Stop Loss Levels
        fig.add_trace(
            go.Scatter(
                x=plot_df.index,
                y=plot_df[
                    "Sell_Countdown_Stop_Loss"
                ].ffill(),  # Fill NaN for visualization
                mode="lines",
                line=dict(color="brown", width=1, dash="dash"),
                name="Sell Countdown Stop Loss",
            ),
            row=1,
            col=1,
        )

    # Add TD_Setup and TD_Countdown values as text annotations
    for i, row in plot_df.iterrows():
        fig.add_annotation(
            x=i,
            y=row["High"] + 0.3,  # Adjust the vertical position as needed
            text=f" {row['TD_Setup']}" if row["TD_Setup"] else "",
            showarrow=False,
            font=dict(size=8),
            row=1,
            col=1,
        )

        fig.add_annotation(
            x=i,
            y=row["Low"] - 0.3,  # Adjust the vertical position as needed
            text=f" {row['TD_Countdown']}" if row["TD_Countdown"] else "",
            showarrow=False,
            font=dict(size=8),
            row=1,
            col=1,
        )

    # Customize layout
    fig.update_layout(
        title="TD Sequential Analysis",
        xaxis_rangeslider_visible=False,
        height=800,
        width=1200,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    # Set y-axis titles
    fig.update_yaxes(title_text="Price", row=1, col=1)

    return fig  # fig.show()
