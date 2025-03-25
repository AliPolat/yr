import pandas as pd
import numpy as np


def calculate_tdsequential(df, stock_name="AAPL"):
    """
    Calculate TD Sequential indicators with proper TDST level cancellation handling.
    TDST levels are cancelled when:
    1. For buy setups: When price closes above the buy TDST level
    2. For sell setups: When price closes below the sell TDST level
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

    # Initialize TDST level columns
    df["buy_tdst_level"] = np.nan
    df["sell_tdst_level"] = np.nan
    df["buy_tdst_active"] = False
    df["sell_tdst_active"] = False

    # Track current active TDST levels
    current_buy_tdst = None
    current_sell_tdst = None

    # Calculate Buy and Sell Setup Phases with TDST levels
    for i in range(len(df)):
        if i == 0:
            continue

        # Check for TDST cancellation conditions before processing new setups
        if current_buy_tdst is not None and df["close"].iloc[i] > current_buy_tdst:
            current_buy_tdst = None
            df.loc[df.index[i], "buy_tdst_active"] = False

        if current_sell_tdst is not None and df["close"].iloc[i] < current_sell_tdst:
            current_sell_tdst = None
            df.loc[df.index[i], "sell_tdst_active"] = False

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

        # Calculate TDST levels when setup completes
        if df["buy_setup"].iloc[i] == 9:
            # TDST for buy setup is the highest high of the setup
            setup_start = max(0, i - 8)
            current_buy_tdst = df["high"].iloc[setup_start : i + 1].max()
            df.loc[df.index[i], "buy_tdst_level"] = current_buy_tdst
            df.loc[df.index[i], "buy_tdst_active"] = True

        if df["sell_setup"].iloc[i] == 9:
            # TDST for sell setup is the lowest low of the setup
            setup_start = max(0, i - 8)
            current_sell_tdst = df["low"].iloc[setup_start : i + 1].min()
            df.loc[df.index[i], "sell_tdst_level"] = current_sell_tdst
            df.loc[df.index[i], "sell_tdst_active"] = True

    # Forward fill TDST levels until cancellation or new setup
    buy_tdst_active = False
    sell_tdst_active = False
    last_buy_tdst = None
    last_sell_tdst = None

    for i in range(len(df)):
        # Check for new TDST levels
        if not pd.isna(df["buy_tdst_level"].iloc[i]):
            buy_tdst_active = True
            last_buy_tdst = df["buy_tdst_level"].iloc[i]

        if not pd.isna(df["sell_tdst_level"].iloc[i]):
            sell_tdst_active = True
            last_sell_tdst = df["sell_tdst_level"].iloc[i]

        # Check cancellation conditions
        if buy_tdst_active and df["close"].iloc[i] > last_buy_tdst:
            buy_tdst_active = False
            df.loc[df.index[i], "buy_tdst_active"] = False

        if sell_tdst_active and df["close"].iloc[i] < last_sell_tdst:
            sell_tdst_active = False
            df.loc[df.index[i], "sell_tdst_active"] = False

        # Forward fill active TDST levels
        if buy_tdst_active:
            df.loc[df.index[i], "buy_tdst_level"] = last_buy_tdst
            df.loc[df.index[i], "buy_tdst_active"] = True

        if sell_tdst_active:
            df.loc[df.index[i], "sell_tdst_level"] = last_sell_tdst
            df.loc[df.index[i], "sell_tdst_active"] = True

    # [Rest of the function remains the same...]
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
    df["buy_countdown_active"] = 0
    df["sell_countdown_active"] = 0
    df["perfect_buy_13"] = 0
    df["perfect_sell_13"] = 0

    # Store indices of setup and countdown bars
    buy_countdown_bars = []
    sell_countdown_bars = []

    # Track active countdowns
    buy_countdown_active = False
    sell_countdown_active = False

    # Setup that initiated current countdown
    current_buy_setup_idx = None
    current_sell_setup_idx = None

    # TDST levels for buy and sell countdowns
    buy_tdst_level = None
    sell_tdst_level = None

    # Calculate countdowns
    for i in range(9, len(df)):
        # Process buy side
        # Check if this bar completes a buy setup (9 consecutive bars)
        if df["buy_setup"].iloc[i] == 9:
            # If sell countdown is active, reset it and start buy countdown
            if sell_countdown_active:
                sell_countdown_active = False
                sell_countdown_bars = []
                current_sell_setup_idx = None
                sell_tdst_level = None
                df.loc[df.index[i], "sell_countdown_active"] = 0
                df.loc[df.index[i], "sell_countdown"] = 0

            # Start a new buy countdown
            buy_countdown_active = True
            buy_countdown_bars = []
            current_buy_setup_idx = i
            df.loc[df.index[i], "buy_countdown_active"] = 1

            # Set TDST level for buy countdown (highest high of the buy setup)
            buy_tdst_level = df["high"].iloc[i - 8 : i + 1].max()

        # Process sell side
        # Check if this bar completes a sell setup (9 consecutive bars)
        if df["sell_setup"].iloc[i] == 9:
            # If buy countdown is active, reset it and start sell countdown
            if buy_countdown_active:
                buy_countdown_active = False
                buy_countdown_bars = []
                current_buy_setup_idx = None
                buy_tdst_level = None
                df.loc[df.index[i], "buy_countdown_active"] = 0
                df.loc[df.index[i], "buy_countdown"] = 0

            # Start a new sell countdown
            sell_countdown_active = True
            sell_countdown_bars = []
            current_sell_setup_idx = i
            df.loc[df.index[i], "sell_countdown_active"] = 1

            # Set TDST level for sell countdown (lowest low of the sell setup)
            sell_tdst_level = df["low"].iloc[i - 8 : i + 1].min()

        # Process Buy Countdown
        if buy_countdown_active:
            # Mark countdown as active in dataframe
            df.loc[df.index[i], "buy_countdown_active"] = 1

            # Check for countdown cancel condition (close above TDST)
            if buy_tdst_level is not None and df["close"].iloc[i] > buy_tdst_level:
                # Cancel the buy countdown
                buy_countdown_active = False
                buy_countdown_bars = []
                df.loc[df.index[i], "buy_countdown"] = 0  # Reset buy_countdown
                continue

            # Check for countdown qualifying bar: Close <= Low of 2 bars earlier
            if i >= 2 and df["close"].iloc[i] <= df["low"].iloc[i - 2]:
                # Add this bar to qualifying bars
                buy_countdown_bars.append(i)

                # Update countdown count
                current_count = len(buy_countdown_bars)
                df.loc[df.index[i], "buy_countdown"] = current_count

                # Check for perfect 13 when we reach the 13th bar
                if current_count == 13:
                    # Get bar 8 of the countdown
                    if len(buy_countdown_bars) >= 8:
                        bar_8_idx = buy_countdown_bars[7]  # 8th bar (0-indexed)

                        # Perfect Buy 13: Close of bar 13 ≤ Low of bar 8
                        if df["close"].iloc[i] <= df["low"].iloc[bar_8_idx]:
                            df.loc[df.index[i], "perfect_buy_13"] = 1

                    # Reset countdown after reaching 13
                    buy_countdown_active = False
            else:
                # Bar doesn't qualify, but countdown continues
                # Keep the previous countdown value
                if buy_countdown_bars:
                    df.loc[df.index[i], "buy_countdown"] = len(buy_countdown_bars)

        # Process Sell Countdown
        if sell_countdown_active:
            # Mark countdown as active in dataframe
            df.loc[df.index[i], "sell_countdown_active"] = 1

            # Check for countdown cancel condition (close below TDST)
            if sell_tdst_level is not None and df["close"].iloc[i] < sell_tdst_level:
                # Cancel the sell countdown
                sell_countdown_active = False
                sell_countdown_bars = []
                df.loc[df.index[i], "sell_countdown"] = 0  # Reset sell_countdown
                continue

            # Check for countdown qualifying bar: Close >= High of 2 bars earlier
            if i >= 2 and df["close"].iloc[i] >= df["high"].iloc[i - 2]:
                # Add this bar to qualifying bars
                sell_countdown_bars.append(i)

                # Update countdown count
                current_count = len(sell_countdown_bars)
                df.loc[df.index[i], "sell_countdown"] = current_count

                # Check for perfect 13 when we reach the 13th bar
                if current_count == 13:
                    # Get bar 8 of the countdown
                    if len(sell_countdown_bars) >= 8:
                        bar_8_idx = sell_countdown_bars[7]  # 8th bar (0-indexed)

                        # Perfect Sell 13: Close of bar 13 ≥ High of bar 8
                        if df["close"].iloc[i] >= df["high"].iloc[bar_8_idx]:
                            df.loc[df.index[i], "perfect_sell_13"] = 1

                    # Reset countdown after reaching 13
                    sell_countdown_active = False
            else:
                # Bar doesn't qualify, but countdown continues
                # Keep the previous countdown value
                if sell_countdown_bars:
                    df.loc[df.index[i], "sell_countdown"] = len(sell_countdown_bars)

    # Clean up intermediate columns
    df = df.drop(
        ["close_4_periods_ago", "buy_setup_condition", "sell_setup_condition"], axis=1
    )

    # Add stock name if provided
    if stock_name:
        df["stock_name"] = stock_name

    return df

