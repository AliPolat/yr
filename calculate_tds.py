import pandas as pd
import numpy as np


def calculate_tdsequential(df, stock_name="AAPL"):
    """
    Calculate TD Sequential indicators from OHLC data.

    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with columns 'open', 'high', 'low', 'close', and 'date'
    stock_name : str, optional
        Name of the stock for display purposes

    Returns:
    --------
    pandas.DataFrame
        DataFrame with added TD Sequential columns
    """
    # Make a copy to avoid modifying the original
    df = df.copy()

    # Ensure columns are lowercase
    df.columns = [col.lower() for col in df.columns]

    # Check for required columns
    required_cols = ["open", "high", "low", "close"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' not found in dataframe")

    # Ensure index is datetime if 'date' column exists
    if "date" in df.columns and not isinstance(df.index, pd.DatetimeIndex):
        df = df.set_index("date")

    # Calculate Close 4 periods ago (for setup phase)
    df["close_4_periods_ago"] = df["close"].shift(4)

    # Buy Setup: Current close less than close 4 bars earlier
    df["buy_setup_condition"] = df["close"] < df["close_4_periods_ago"]

    # Sell Setup: Current close greater than close 4 bars earlier
    df["sell_setup_condition"] = df["close"] > df["close_4_periods_ago"]

    # Initialize setup counters to 0
    df["buy_setup"] = 0
    df["sell_setup"] = 0

    # Calculate Buy and Sell Setup Phases
    for i in range(len(df)):
        if i == 0:
            continue

        # Buy Setup
        if df["buy_setup_condition"].iloc[i]:
            # Continue counting if previous bar was also part of buy setup
            if df["buy_setup"].iloc[i - 1] > 0 and df["buy_setup"].iloc[i - 1] < 9:
                df.loc[df.index[i], "buy_setup"] = df["buy_setup"].iloc[i - 1] + 1
            # Start a new count
            else:
                df.loc[df.index[i], "buy_setup"] = 1
        # Reset if condition not met
        else:
            df.loc[df.index[i], "buy_setup"] = 0

        # Sell Setup
        if df["sell_setup_condition"].iloc[i]:
            # Continue counting if previous bar was also part of sell setup
            if df["sell_setup"].iloc[i - 1] > 0 and df["sell_setup"].iloc[i - 1] < 9:
                df.loc[df.index[i], "sell_setup"] = df["sell_setup"].iloc[i - 1] + 1
            # Start a new count
            else:
                df.loc[df.index[i], "sell_setup"] = 1
        # Reset if condition not met
        else:
            df.loc[df.index[i], "sell_setup"] = 0

    # Add perfect 9 setup columns
    df["perfect_buy_9"] = 0
    df["perfect_sell_9"] = 0

    # Calculate perfect 9 setups correctly
    for i in range(2, len(df)):
        if df["buy_setup"].iloc[i] == 9:
            # Perfect Buy 9: Low of bar 9 < Low of bar 6
            if df["low"].iloc[i] < df["low"].iloc[i - 3]:
                df.loc[df.index[i], "perfect_buy_9"] = 1

        if df["sell_setup"].iloc[i] == 9:
            # Perfect Sell 9: High of bar 9 > High of bar 6
            if df["high"].iloc[i] > df["high"].iloc[i - 3]:
                df.loc[df.index[i], "perfect_sell_9"] = 1

    # Initialize countdown columns
    df["buy_countdown"] = 0
    df["sell_countdown"] = 0
    df["perfect_buy_13"] = 0
    df["perfect_sell_13"] = 0

    # Track active setups and countdowns
    active_buy_setups = []
    active_sell_setups = []
    buy_countdown_bars = []
    sell_countdown_bars = []

    # Calculate countdowns
    for i in range(9, len(df)):
        # Check for completed buy setup (9 consecutive bars)
        if df["buy_setup"].iloc[i] == 9:
            active_buy_setups.append(i)

        # Check for completed sell setup (9 consecutive bars)
        if df["sell_setup"].iloc[i] == 9:
            active_sell_setups.append(i)

        # Process Buy Countdown - must wait until after a completed setup
        if active_buy_setups and i > active_buy_setups[-1]:
            # Buy Countdown condition: Close less than or equal to low two bars earlier
            if df["close"].iloc[i] <= df["low"].iloc[i - 2]:
                buy_countdown_bars.append(i)
                current_countdown = len(buy_countdown_bars)
                df.loc[df.index[i], "buy_countdown"] = current_countdown

                # Check for perfect 13 when we reach the 13th countdown bar
                if current_countdown == 13:
                    if len(buy_countdown_bars) >= 8:
                        # Bar 8 of the countdown
                        bar_8_idx = buy_countdown_bars[7]
                        # Perfect Buy 13: Close of bar 13 ≤ Low of bar 8
                        if df["close"].iloc[i] <= df["low"].iloc[bar_8_idx]:
                            df.loc[df.index[i], "perfect_buy_13"] = 1

                    # Reset countdown after reaching 13
                    buy_countdown_bars = []
                    active_buy_setups = []

            # Check for buy countdown cancellation conditions
            if active_buy_setups and buy_countdown_bars:
                # 1. If a new buy setup starts during the countdown
                if df["buy_setup"].iloc[i] == 9:
                    # Reset and start a new countdown phase
                    buy_countdown_bars = []
                    active_buy_setups = [i]

                # 2. If price makes a new low below the low of the first bar after setup completion
                if buy_countdown_bars and i > active_buy_setups[-1] + 1:
                    first_bar_after_setup = active_buy_setups[-1] + 1
                    if df["low"].iloc[i] < df["low"].iloc[first_bar_after_setup]:
                        buy_countdown_bars = []
                        active_buy_setups = []

        # Process Sell Countdown - must wait until after a completed setup
        if active_sell_setups and i > active_sell_setups[-1]:
            # Sell Countdown condition: Close greater than or equal to high two bars earlier
            if df["close"].iloc[i] >= df["high"].iloc[i - 2]:
                sell_countdown_bars.append(i)
                current_countdown = len(sell_countdown_bars)
                df.loc[df.index[i], "sell_countdown"] = current_countdown

                # Check for perfect 13 when we reach the 13th countdown bar
                if current_countdown == 13:
                    if len(sell_countdown_bars) >= 8:
                        # Bar 8 of the countdown
                        bar_8_idx = sell_countdown_bars[7]
                        # Perfect Sell 13: Close of bar 13 ≥ High of bar 8
                        if df["close"].iloc[i] >= df["high"].iloc[bar_8_idx]:
                            df.loc[df.index[i], "perfect_sell_13"] = 1

                    # Reset countdown after reaching 13
                    sell_countdown_bars = []
                    active_sell_setups = []

            # Check for sell countdown cancellation conditions
            if active_sell_setups and sell_countdown_bars:
                # 1. If a new sell setup starts during the countdown
                if df["sell_setup"].iloc[i] == 9:
                    # Reset and start a new countdown phase
                    sell_countdown_bars = []
                    active_sell_setups = [i]

                # 2. If price makes a new high above the high of the first bar after setup completion
                if sell_countdown_bars and i > active_sell_setups[-1] + 1:
                    first_bar_after_setup = active_sell_setups[-1] + 1
                    if df["high"].iloc[i] > df["high"].iloc[first_bar_after_setup]:
                        sell_countdown_bars = []
                        active_sell_setups = []

    # Clean up intermediate columns
    df = df.drop(
        ["close_4_periods_ago", "buy_setup_condition", "sell_setup_condition"], axis=1
    )

    # Add stock name if provided
    if stock_name:
        df["stock_name"] = stock_name

    return df
