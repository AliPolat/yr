import pandas as pd
import numpy as np


def calculate_tdsequential(df, stock_name="AAPL"):
    """
    Calculate TD Sequential with TDST level tracking and opposite setup cancellation.
    Stores buy_tdst_level (resistance) and sell_tdst_level (support) in DataFrame.
    """
    df = df.copy()
    df.columns = [col.lower() for col in df.columns]

    # Validate columns
    required_cols = ["open", "high", "low", "close"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # Set datetime index if 'date' exists
    if "date" in df.columns and not isinstance(df.index, pd.DatetimeIndex):
        df = df.set_index("date")

    # Setup conditions
    df["close_4_periods_ago"] = df["close"].shift(4)
    df["buy_setup_condition"] = df["close"] < df["close_4_periods_ago"]
    df["sell_setup_condition"] = df["close"] > df["close_4_periods_ago"]

    # Initialize columns
    df["buy_setup"] = 0
    df["sell_setup"] = 0
    df["perfect_buy_9"] = 0
    df["perfect_sell_9"] = 0
    df["buy_countdown"] = 0
    df["sell_countdown"] = 0
    df["buy_countdown_active"] = 0
    df["sell_countdown_active"] = 0
    df["perfect_buy_13"] = 0
    df["perfect_sell_13"] = 0
    df["buy_tdst_level"] = np.nan  # Resistance level for buy countdown
    df["sell_tdst_level"] = np.nan  # Support level for sell countdown

    # Track active countdowns
    buy_countdown_active = False
    sell_countdown_active = False
    buy_countdown_bars = []
    sell_countdown_bars = []
    current_buy_setup_idx = None
    current_sell_setup_idx = None

    for i in range(1, len(df)):
        # --- SETUP PHASE ---
        # Buy Setup
        if df["buy_setup_condition"].iloc[i]:
            df.loc[df.index[i], "buy_setup"] = (
                df["buy_setup"].iloc[i - 1] + 1
                if df["buy_setup"].iloc[i - 1] > 0
                else 1
            )

        # Sell Setup
        if df["sell_setup_condition"].iloc[i]:
            df.loc[df.index[i], "sell_setup"] = (
                df["sell_setup"].iloc[i - 1] + 1
                if df["sell_setup"].iloc[i - 1] > 0
                else 1
            )

        # Perfect Setup Checks (require at least 3 bars)
        if i >= 2:
            if (
                df["buy_setup"].iloc[i] == 9
                and df["low"].iloc[i] < df["low"].iloc[i - 3]
            ):
                df.loc[df.index[i], "perfect_buy_9"] = 1

            if (
                df["sell_setup"].iloc[i] == 9
                and df["high"].iloc[i] > df["high"].iloc[i - 3]
            ):
                df.loc[df.index[i], "perfect_sell_9"] = 1

        # --- COUNTDOWN PHASE ---
        # Buy Setup Completes (9 bars)
        if df["buy_setup"].iloc[i] == 9:
            # Cancel sell countdown if active
            if sell_countdown_active:
                sell_countdown_active = False
                sell_countdown_bars = []
                df.loc[df.index[i], "sell_countdown_active"] = 0
                df.loc[df.index[i], "sell_countdown"] = 0
                df.loc[df.index[i], "sell_tdst_level"] = np.nan

            # Start buy countdown
            buy_countdown_active = True
            buy_countdown_bars = []
            current_buy_setup_idx = i
            df.loc[df.index[i], "buy_countdown_active"] = 1

            # Set TDST level (highest high of buy setup bars)
            buy_tdst_level = df["high"].iloc[i - 8 : i + 1].max()
            df.loc[df.index[i] :, "buy_tdst_level"] = (
                buy_tdst_level  # Store in DataFrame
            )

        # Sell Setup Completes (9 bars)
        if df["sell_setup"].iloc[i] == 9:
            # Cancel buy countdown if active
            if buy_countdown_active:
                buy_countdown_active = False
                buy_countdown_bars = []
                df.loc[df.index[i], "buy_countdown_active"] = 0
                df.loc[df.index[i], "buy_countdown"] = 0
                df.loc[df.index[i], "buy_tdst_level"] = np.nan

            # Start sell countdown
            sell_countdown_active = True
            sell_countdown_bars = []
            current_sell_setup_idx = i
            df.loc[df.index[i], "sell_countdown_active"] = 1

            # Set TDST level (lowest low of sell setup bars)
            sell_tdst_level = df["low"].iloc[i - 8 : i + 1].min()
            df.loc[df.index[i] :, "sell_tdst_level"] = (
                sell_tdst_level  # Store in DataFrame
            )

        # --- COUNTDOWN PROCESSING ---
        # Buy Countdown
        if buy_countdown_active:
            # Propagate TDST level forward
            df.loc[df.index[i], "buy_tdst_level"] = buy_tdst_level

            # Check cancellation (close above TDST)
            if df["close"].iloc[i] > buy_tdst_level:
                buy_countdown_active = False
                buy_countdown_bars = []
                df.loc[df.index[i], "buy_countdown"] = 0
                df.loc[df.index[i], "buy_countdown_active"] = 0
                df.loc[df.index[i], "buy_tdst_level"] = np.nan
                continue

            # Check countdown qualification (close <= low 2 bars ago)
            if i >= 2 and df["close"].iloc[i] <= df["low"].iloc[i - 2]:
                buy_countdown_bars.append(i)
                current_count = len(buy_countdown_bars)
                df.loc[df.index[i], "buy_countdown"] = current_count

                # Perfect 13 check
                if current_count == 13 and len(buy_countdown_bars) >= 8:
                    bar_8_idx = buy_countdown_bars[7]
                    if df["close"].iloc[i] <= df["low"].iloc[bar_8_idx]:
                        df.loc[df.index[i], "perfect_buy_13"] = 1
                    buy_countdown_active = False
            else:
                if buy_countdown_bars:
                    df.loc[df.index[i], "buy_countdown"] = len(buy_countdown_bars)

        # Sell Countdown
        if sell_countdown_active:
            # Propagate TDST level forward
            df.loc[df.index[i], "sell_tdst_level"] = sell_tdst_level

            # Check cancellation (close below TDST)
            if df["close"].iloc[i] < sell_tdst_level:
                sell_countdown_active = False
                sell_countdown_bars = []
                df.loc[df.index[i], "sell_countdown"] = 0
                df.loc[df.index[i], "sell_countdown_active"] = 0
                df.loc[df.index[i], "sell_tdst_level"] = np.nan
                continue

            # Check countdown qualification (close >= high 2 bars ago)
            if i >= 2 and df["close"].iloc[i] >= df["high"].iloc[i - 2]:
                sell_countdown_bars.append(i)
                current_count = len(sell_countdown_bars)
                df.loc[df.index[i], "sell_countdown"] = current_count

                # Perfect 13 check
                if current_count == 13 and len(sell_countdown_bars) >= 8:
                    bar_8_idx = sell_countdown_bars[7]
                    if df["close"].iloc[i] >= df["high"].iloc[bar_8_idx]:
                        df.loc[df.index[i], "perfect_sell_13"] = 1
                    sell_countdown_active = False
            else:
                if sell_countdown_bars:
                    df.loc[df.index[i], "sell_countdown"] = len(sell_countdown_bars)

    # Cleanup
    df = df.drop(
        ["close_4_periods_ago", "buy_setup_condition", "sell_setup_condition"], axis=1
    )
    if stock_name:
        df["stock_name"] = stock_name

    return df
