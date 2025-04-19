def _calculate_countdown_buy_stop_level(countdown_bars):
    """
    Calculate buy countdown stop level: lowest low of the countdown bars minus the range of the lowest bar.
    
    Similar to buy setup stop level, but applied to countdown qualifying bars.
    
    Parameters:
    -----------
    countdown_bars : pandas.DataFrame
        DataFrame containing all bars that qualified for the countdown
        
    Returns:
    --------
    float
        Buy countdown stop level value
    """
    # Original buy countdown stop is the lowest low of the countdown
    buy_stop = countdown_bars["low"].min()

    # Find the bar with the lowest low in the countdown
    min_low_bar = countdown_bars[countdown_bars["low"] == buy_stop].iloc[0]
    
    # Calculate the range (high - low) of that bar
    bar_range = min_low_bar["high"] - min_low_bar["low"]
    
    # Subtract this range from the original stop level
    return buy_stop - bar_range


def _calculate_countdown_sell_stop_level(countdown_bars):
    """
    Calculate sell countdown stop level: highest high of the countdown bars plus the range of the highest bar.
    
    Similar to sell setup stop level, but applied to countdown qualifying bars.
    
    Parameters:
    -----------
    countdown_bars : pandas.DataFrame
        DataFrame containing all bars that qualified for the countdown
        
    Returns:
    --------
    float
        Sell countdown stop level value
    """
    # Original sell countdown stop is the highest high of the countdown
    sell_stop = countdown_bars["high"].max()

    # Find the bar with the highest high in the countdown
    max_high_bar = countdown_bars[countdown_bars["high"] == sell_stop].iloc[0]
    
    # Calculate the range (high - low) of that bar
    bar_range = max_high_bar["high"] - max_high_bar["low"]
    
    # Add this range to the original stop level
    return sell_stop + bar_range


import pandas as pd
import numpy as np


def calculate_tdsequential(df, stock_name="AAPL"):
    """
    Calculate TD Sequential indicators with proper TDST level cancellation handling
    and setup stop loss levels.

    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with OHLC data
    stock_name : str, optional
        Name of the stock

    Returns:
    --------
    pandas.DataFrame
        DataFrame with TD Sequential indicators added
    """
    # Make a copy to avoid modifying the original
    df = df.copy()

    # Standardize and validate input data
    df = _preprocess_dataframe(df)

    # Calculate setup phases (buy and sell)
    df = _calculate_setup_phases(df)

    # Calculate TDST levels and setup stop loss levels
    df = _calculate_tdst_and_stop_levels(df)

    # Forward fill TDST levels and stop levels until cancellation or new setup
    df = _forward_fill_levels(df)

    # Identify perfect 9 setups
    df = _identify_perfect_setups(df)

    # Calculate countdown phases (buy and sell) and countdown stop levels
    df = _calculate_countdown_phases(df)

    # Identify stop loss triggers and reactivations
    df = _identify_stop_events(df)

    # Clean up intermediate columns
    df = df.drop(
        ["close_4_periods_ago", "buy_setup_condition", "sell_setup_condition"], axis=1
    )

    # Add stock name if provided
    if stock_name:
        df["stock_name"] = stock_name

    return df


def _preprocess_dataframe(df):
    """
    Standardize and validate the input dataframe.
    """
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

    # Initialize setup counters
    df["buy_setup"] = 0
    df["sell_setup"] = 0

    # Initialize TDST level columns
    df["buy_tdst_level"] = np.nan
    df["sell_tdst_level"] = np.nan
    df["buy_tdst_active"] = False
    df["sell_tdst_active"] = False

    # Initialize Setup Stop Loss columns
    df["buy_setup_stop"] = np.nan
    df["sell_setup_stop"] = np.nan
    df["buy_setup_stop_active"] = False
    df["sell_setup_stop_active"] = False

    # Initialize Countdown Stop Loss columns
    df["buy_countdown_stop"] = np.nan
    df["sell_countdown_stop"] = np.nan
    df["buy_countdown_stop_active"] = False
    df["sell_countdown_stop_active"] = False

    # Initialize countdown columns
    df["buy_countdown"] = 0
    df["sell_countdown"] = 0
    df["buy_countdown_active"] = 0
    df["sell_countdown_active"] = 0
    df["perfect_buy_13"] = 0
    df["perfect_sell_13"] = 0

    # Initialize perfect setup columns
    df["perfect_buy_9"] = 0
    df["perfect_sell_9"] = 0

    # Initialize stop loss event columns
    df["buy_stop_triggered"] = False
    df["sell_stop_triggered"] = False
    df["buy_stop_reactivated"] = False
    df["sell_stop_reactivated"] = False
    
    # Initialize countdown stop loss event columns
    df["buy_countdown_stop_triggered"] = False
    df["sell_countdown_stop_triggered"] = False
    df["buy_countdown_stop_reactivated"] = False
    df["sell_countdown_stop_reactivated"] = False

    return df


def _calculate_setup_phases(df):
    """
    Calculate Buy and Sell Setup phases.
    """
    for i in range(1, len(df)):
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

    return df


def _calculate_tdst_and_stop_levels(df):
    """
    Calculate TDST levels and setup stop loss levels when setups complete.
    """
    # Track current active TDST levels and stop levels
    current_buy_tdst = None
    current_sell_tdst = None
    current_buy_stop = None
    current_sell_stop = None

    # Track inactive stop levels for potential reactivation
    inactive_buy_stop = None
    inactive_sell_stop = None

    # Flag to track if stops have been triggered
    buy_stop_triggered = False
    sell_stop_triggered = False

    for i in range(1, len(df)):
        # Check for TDST cancellation conditions before processing new setups
        if current_buy_tdst is not None and df["close"].iloc[i] > current_buy_tdst:
            current_buy_tdst = None
            df.loc[df.index[i], "buy_tdst_active"] = False

        if current_sell_tdst is not None and df["close"].iloc[i] < current_sell_tdst:
            current_sell_tdst = None
            df.loc[df.index[i], "sell_tdst_active"] = False

        # Check for stop loss cancellation conditions
        if current_buy_stop is not None and df["low"].iloc[i] <= current_buy_stop:
            inactive_buy_stop = current_buy_stop  # Store for potential reactivation
            current_buy_stop = None
            df.loc[df.index[i], "buy_setup_stop_active"] = False
            buy_stop_triggered = True

        if current_sell_stop is not None and df["high"].iloc[i] >= current_sell_stop:
            inactive_sell_stop = current_sell_stop  # Store for potential reactivation
            current_sell_stop = None
            df.loc[df.index[i], "sell_setup_stop_active"] = False
            sell_stop_triggered = True

        # Check for stop loss reactivation conditions
        if (
            inactive_buy_stop is not None
            and buy_stop_triggered
            and df["low"].iloc[i] > inactive_buy_stop
        ):
            current_buy_stop = inactive_buy_stop
            df.loc[df.index[i], "buy_setup_stop"] = current_buy_stop
            df.loc[df.index[i], "buy_setup_stop_active"] = True
            inactive_buy_stop = None
            buy_stop_triggered = False

        if (
            inactive_sell_stop is not None
            and sell_stop_triggered
            and df["high"].iloc[i] < inactive_sell_stop
        ):
            current_sell_stop = inactive_sell_stop
            df.loc[df.index[i], "sell_setup_stop"] = current_sell_stop
            df.loc[df.index[i], "sell_setup_stop_active"] = True
            inactive_sell_stop = None
            sell_stop_triggered = False

        # Calculate new levels when setup completes
        if df["buy_setup"].iloc[i] == 9:
            setup_start = max(0, i - 8)
            setup_bars = df.iloc[setup_start : i + 1]

            # TDST for buy setup is the highest high of the setup
            current_buy_tdst = setup_bars["high"].max()
            df.loc[df.index[i], "buy_tdst_level"] = current_buy_tdst
            df.loc[df.index[i], "buy_tdst_active"] = True

            # Calculate buy setup stop level
            current_buy_stop = _calculate_buy_stop_level(setup_bars)
            df.loc[df.index[i], "buy_setup_stop"] = current_buy_stop
            df.loc[df.index[i], "buy_setup_stop_active"] = True

            # Reset inactive stops and trigger flags when new setup completes
            inactive_buy_stop = None
            buy_stop_triggered = False

        if df["sell_setup"].iloc[i] == 9:
            setup_start = max(0, i - 8)
            setup_bars = df.iloc[setup_start : i + 1]

            # TDST for sell setup is the lowest low of the setup
            current_sell_tdst = setup_bars["low"].min()
            df.loc[df.index[i], "sell_tdst_level"] = current_sell_tdst
            df.loc[df.index[i], "sell_tdst_active"] = True

            # Calculate sell setup stop level
            current_sell_stop = _calculate_sell_stop_level(setup_bars)
            df.loc[df.index[i], "sell_setup_stop"] = current_sell_stop
            df.loc[df.index[i], "sell_setup_stop_active"] = True

            # Reset inactive stops and trigger flags when new setup completes
            inactive_sell_stop = None
            sell_stop_triggered = False

    return df


def _calculate_buy_stop_level(setup_bars):
    """
    Calculate buy setup stop level: lowest low minus the range of the lowest bar.
    """
    # Original buy setup stop is the lowest low of the setup
    buy_stop = setup_bars["low"].min()

    # Find the bar with the lowest low in the setup
    min_low_bar = setup_bars[setup_bars["low"] == buy_stop].iloc[0]
    
    # Calculate the range (high - low) of that bar
    bar_range = min_low_bar["high"] - min_low_bar["low"]
    
    # Subtract this range from the original stop level
    return buy_stop - bar_range


def _calculate_sell_stop_level(setup_bars):
    """
    Calculate sell setup stop level: highest high plus the range of the highest bar.
    """
    # Original sell setup stop is the highest high of the setup
    sell_stop = setup_bars["high"].max()

    # Find the bar with the highest high in the setup
    max_high_bar = setup_bars[setup_bars["high"] == sell_stop].iloc[0]
    
    # Calculate the range (high - low) of that bar
    bar_range = max_high_bar["high"] - max_high_bar["low"]
    
    # Add this range to the original stop level
    return sell_stop + bar_range


def _forward_fill_levels(df):
    """
    Forward fill TDST levels and stop levels until cancellation or new setup.
    """
    buy_tdst_active = False
    sell_tdst_active = False
    buy_stop_active = False
    sell_stop_active = False
    buy_countdown_stop_active = False
    sell_countdown_stop_active = False
    
    last_buy_tdst = None
    last_sell_tdst = None
    last_buy_stop = None
    last_sell_stop = None
    last_buy_countdown_stop = None
    last_sell_countdown_stop = None

    # Track inactive stop levels for potential reactivation in forward fill
    inactive_buy_stop_ff = None
    inactive_sell_stop_ff = None
    inactive_buy_countdown_stop_ff = None
    inactive_sell_countdown_stop_ff = None
    
    buy_stop_triggered_ff = False
    sell_stop_triggered_ff = False
    buy_countdown_stop_triggered_ff = False
    sell_countdown_stop_triggered_ff = False

    for i in range(len(df)):
        # Check for new TDST levels
        if not pd.isna(df["buy_tdst_level"].iloc[i]):
            buy_tdst_active = True
            last_buy_tdst = df["buy_tdst_level"].iloc[i]

        if not pd.isna(df["buy_setup_stop"].iloc[i]):
            buy_stop_active = True
            last_buy_stop = df["buy_setup_stop"].iloc[i]
            # Reset reactivation data when new stop is set
            inactive_buy_stop_ff = None
            buy_stop_triggered_ff = False

        if not pd.isna(df["sell_tdst_level"].iloc[i]):
            sell_tdst_active = True
            last_sell_tdst = df["sell_tdst_level"].iloc[i]

        if not pd.isna(df["sell_setup_stop"].iloc[i]):
            sell_stop_active = True
            last_sell_stop = df["sell_setup_stop"].iloc[i]
            # Reset reactivation data when new stop is set
            inactive_sell_stop_ff = None
            sell_stop_triggered_ff = False
            
        # Check for new countdown stop levels
        if not pd.isna(df["buy_countdown_stop"].iloc[i]):
            buy_countdown_stop_active = True
            last_buy_countdown_stop = df["buy_countdown_stop"].iloc[i]
            # Reset reactivation data when new stop is set
            inactive_buy_countdown_stop_ff = None
            buy_countdown_stop_triggered_ff = False

        if not pd.isna(df["sell_countdown_stop"].iloc[i]):
            sell_countdown_stop_active = True
            last_sell_countdown_stop = df["sell_countdown_stop"].iloc[i]
            # Reset reactivation data when new stop is set
            inactive_sell_countdown_stop_ff = None
            sell_countdown_stop_triggered_ff = False

        # Handle TDST cancellations
        if buy_tdst_active and df["close"].iloc[i] > last_buy_tdst:
            buy_tdst_active = False
            df.loc[df.index[i], "buy_tdst_active"] = False

        if sell_tdst_active and df["close"].iloc[i] < last_sell_tdst:
            sell_tdst_active = False
            df.loc[df.index[i], "sell_tdst_active"] = False

        # Handle setup stop loss cancellations
        if buy_stop_active and df["low"].iloc[i] <= last_buy_stop:
            buy_stop_active = False
            df.loc[df.index[i], "buy_setup_stop_active"] = False
            inactive_buy_stop_ff = last_buy_stop  # Store for potential reactivation
            buy_stop_triggered_ff = True

        if sell_stop_active and df["high"].iloc[i] >= last_sell_stop:
            sell_stop_active = False
            df.loc[df.index[i], "sell_setup_stop_active"] = False
            inactive_sell_stop_ff = last_sell_stop  # Store for potential reactivation
            sell_stop_triggered_ff = True
            
        # Handle countdown stop loss cancellations
        if buy_countdown_stop_active and df["low"].iloc[i] <= last_buy_countdown_stop:
            buy_countdown_stop_active = False
            df.loc[df.index[i], "buy_countdown_stop_active"] = False
            inactive_buy_countdown_stop_ff = last_buy_countdown_stop  # Store for potential reactivation
            buy_countdown_stop_triggered_ff = True

        if sell_countdown_stop_active and df["high"].iloc[i] >= last_sell_countdown_stop:
            sell_countdown_stop_active = False
            df.loc[df.index[i], "sell_countdown_stop_active"] = False
            inactive_sell_countdown_stop_ff = last_sell_countdown_stop  # Store for potential reactivation
            sell_countdown_stop_triggered_ff = True

        # Handle setup stop loss reactivation
        if (
            inactive_buy_stop_ff is not None
            and buy_stop_triggered_ff
            and df["low"].iloc[i] > inactive_buy_stop_ff
        ):
            buy_stop_active = True
            last_buy_stop = inactive_buy_stop_ff
            df.loc[df.index[i], "buy_setup_stop"] = last_buy_stop
            df.loc[df.index[i], "buy_setup_stop_active"] = True
            inactive_buy_stop_ff = None
            buy_stop_triggered_ff = False

        if (
            inactive_sell_stop_ff is not None
            and sell_stop_triggered_ff
            and df["high"].iloc[i] < inactive_sell_stop_ff
        ):
            sell_stop_active = True
            last_sell_stop = inactive_sell_stop_ff
            df.loc[df.index[i], "sell_setup_stop"] = last_sell_stop
            df.loc[df.index[i], "sell_setup_stop_active"] = True
            inactive_sell_stop_ff = None
            sell_stop_triggered_ff = False
            
        # Handle countdown stop loss reactivation
        if (
            inactive_buy_countdown_stop_ff is not None
            and buy_countdown_stop_triggered_ff
            and df["low"].iloc[i] > inactive_buy_countdown_stop_ff
        ):
            buy_countdown_stop_active = True
            last_buy_countdown_stop = inactive_buy_countdown_stop_ff
            df.loc[df.index[i], "buy_countdown_stop"] = last_buy_countdown_stop
            df.loc[df.index[i], "buy_countdown_stop_active"] = True
            df.loc[df.index[i], "buy_countdown_stop_reactivated"] = True
            inactive_buy_countdown_stop_ff = None
            buy_countdown_stop_triggered_ff = False

        if (
            inactive_sell_countdown_stop_ff is not None
            and sell_countdown_stop_triggered_ff
            and df["high"].iloc[i] < inactive_sell_countdown_stop_ff
        ):
            sell_countdown_stop_active = True
            last_sell_countdown_stop = inactive_sell_countdown_stop_ff
            df.loc[df.index[i], "sell_countdown_stop"] = last_sell_countdown_stop
            df.loc[df.index[i], "sell_countdown_stop_active"] = True
            df.loc[df.index[i], "sell_countdown_stop_reactivated"] = True
            inactive_sell_countdown_stop_ff = None
            sell_countdown_stop_triggered_ff = False

        # Forward fill active TDST levels
        if buy_tdst_active:
            df.loc[df.index[i], "buy_tdst_level"] = last_buy_tdst
            df.loc[df.index[i], "buy_tdst_active"] = True

        if sell_tdst_active:
            df.loc[df.index[i], "sell_tdst_level"] = last_sell_tdst
            df.loc[df.index[i], "sell_tdst_active"] = True

        # Forward fill active setup stop levels
        if buy_stop_active:
            df.loc[df.index[i], "buy_setup_stop"] = last_buy_stop
            df.loc[df.index[i], "buy_setup_stop_active"] = True

        if sell_stop_active:
            df.loc[df.index[i], "sell_setup_stop"] = last_sell_stop
            df.loc[df.index[i], "sell_setup_stop_active"] = True
            
        # Forward fill active countdown stop levels
        if buy_countdown_stop_active:
            df.loc[df.index[i], "buy_countdown_stop"] = last_buy_countdown_stop
            df.loc[df.index[i], "buy_countdown_stop_active"] = True

        if sell_countdown_stop_active:
            df.loc[df.index[i], "sell_countdown_stop"] = last_sell_countdown_stop
            df.loc[df.index[i], "sell_countdown_stop_active"] = True

    return df


def _identify_perfect_setups(df):
    """
    Identify perfect 9 setups for both buy and sell.
    """
    for i in range(2, len(df)):
        if df["buy_setup"].iloc[i] == 9:
            # Perfect Buy 9: Low of bar 9 < Low of bar 6
            if df["low"].iloc[i] < df["low"].iloc[i - 3]:
                df.loc[df.index[i], "perfect_buy_9"] = 1

        if df["sell_setup"].iloc[i] == 9:
            # Perfect Sell 9: High of bar 9 > High of bar 6
            if df["high"].iloc[i] > df["high"].iloc[i - 3]:
                df.loc[df.index[i], "perfect_sell_9"] = 1

    return df


def _calculate_countdown_phases(df):
    """
    Calculate TD Sequential countdown phases for both buy and sell.
    """
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
    
    # First pass - Calculate countdown values
    for i in range(9, len(df)):
        # Process buy side setup completion
        if df["buy_setup"].iloc[i] == 9:
            df, buy_countdown_active, buy_countdown_bars, buy_tdst_level, sell_countdown_active, \
            sell_countdown_bars, current_buy_setup_idx, current_sell_setup_idx, \
            sell_tdst_level = _handle_buy_setup_completion(
                df, i, buy_countdown_active, buy_countdown_bars, buy_tdst_level, 
                sell_countdown_active, sell_countdown_bars, current_buy_setup_idx, 
                current_sell_setup_idx, sell_tdst_level
            )

        # Process sell side setup completion
        if df["sell_setup"].iloc[i] == 9:
            df, buy_countdown_active, buy_countdown_bars, buy_tdst_level, sell_countdown_active, \
            sell_countdown_bars, current_buy_setup_idx, current_sell_setup_idx, \
            sell_tdst_level = _handle_sell_setup_completion(
                df, i, buy_countdown_active, buy_countdown_bars, buy_tdst_level, 
                sell_countdown_active, sell_countdown_bars, current_buy_setup_idx, 
                current_sell_setup_idx, sell_tdst_level
            )

        # Process Buy Countdown
        if buy_countdown_active:
            df, buy_countdown_active, buy_countdown_bars = _process_buy_countdown(
                df, i, buy_countdown_active, buy_countdown_bars, buy_tdst_level
            )

        # Process Sell Countdown
        if sell_countdown_active:
            df, sell_countdown_active, sell_countdown_bars = _process_sell_countdown(
                df, i, sell_countdown_active, sell_countdown_bars, sell_tdst_level
            )
    
    # Second pass - Calculate countdown stop levels
    # Find all buy countdown completions (where countdown = 13)
    buy_completion_indices = [i for i in range(len(df)) if df["buy_countdown"].iloc[i] == 13]
    sell_completion_indices = [i for i in range(len(df)) if df["sell_countdown"].iloc[i] == 13]
    
    # Process each buy countdown completion
    for completion_index in buy_completion_indices:
        # Look back to find the sequence of bars that formed this countdown
        countdown_bars_indices = []
        current_count = 0
        
        # Look back up to 30 bars to find the 13 qualifying bars
        for j in range(completion_index, max(0, completion_index - 30), -1):
            if df["buy_countdown"].iloc[j] > 0:
                current_count += 1
                countdown_bars_indices.insert(0, j)  # Insert at beginning to maintain order
                if current_count >= 13:
                    break
        
        # If we found enough bars, calculate the stop level
        if len(countdown_bars_indices) == 13:
            countdown_bars = df.iloc[countdown_bars_indices]
            buy_countdown_stop = _calculate_countdown_buy_stop_level(countdown_bars)
            
            # Apply the stop level from the completion point forward until canceled
            active = True
            for i in range(completion_index, len(df)):
                # Check if the stop should be deactivated
                if active and df["low"].iloc[i] <= buy_countdown_stop:
                    active = False
                    df.loc[df.index[i], "buy_countdown_stop_triggered"] = True
                
                # Set the stop level and active status
                df.loc[df.index[i], "buy_countdown_stop"] = buy_countdown_stop
                df.loc[df.index[i], "buy_countdown_stop_active"] = active
                
                # If we reach another completion point, break this loop
                if i > completion_index and df["buy_countdown"].iloc[i] == 13:
                    break
    
    # Process each sell countdown completion
    for completion_index in sell_completion_indices:
        # Look back to find the sequence of bars that formed this countdown
        countdown_bars_indices = []
        current_count = 0
        
        # Look back up to 30 bars to find the 13 qualifying bars
        for j in range(completion_index, max(0, completion_index - 30), -1):
            if df["sell_countdown"].iloc[j] > 0:
                current_count += 1
                countdown_bars_indices.insert(0, j)  # Insert at beginning to maintain order
                if current_count >= 13:
                    break
        
        # If we found enough bars, calculate the stop level
        if len(countdown_bars_indices) == 13:
            countdown_bars = df.iloc[countdown_bars_indices]
            sell_countdown_stop = _calculate_countdown_sell_stop_level(countdown_bars)
            
            # Apply the stop level from the completion point forward until canceled
            active = True
            for i in range(completion_index, len(df)):
                # Check if the stop should be deactivated
                if active and df["high"].iloc[i] >= sell_countdown_stop:
                    active = False
                    df.loc[df.index[i], "sell_countdown_stop_triggered"] = True
                
                # Set the stop level and active status
                df.loc[df.index[i], "sell_countdown_stop"] = sell_countdown_stop
                df.loc[df.index[i], "sell_countdown_stop_active"] = active
                
                # If we reach another completion point, break this loop
                if i > completion_index and df["sell_countdown"].iloc[i] == 13:
                    break
    
    # Now handle reactivation
    for i in range(1, len(df)):
        # Buy countdown stop reactivation
        if (i > 0 and 
            not df["buy_countdown_stop_active"].iloc[i-1] and 
            not pd.isna(df["buy_countdown_stop"].iloc[i]) and
            df["buy_countdown_stop_triggered"].iloc[i-1] and
            df["low"].iloc[i] > df["buy_countdown_stop"].iloc[i]):
            
            # Reactivate from this point until next cancellation
            reactivation_level = df["buy_countdown_stop"].iloc[i]
            df.loc[df.index[i], "buy_countdown_stop_active"] = True
            df.loc[df.index[i], "buy_countdown_stop_reactivated"] = True
            
            # Continue forward until canceled again
            for j in range(i+1, len(df)):
                if df["low"].iloc[j] <= reactivation_level:
                    df.loc[df.index[j], "buy_countdown_stop_active"] = False
                    df.loc[df.index[j], "buy_countdown_stop_triggered"] = True
                    break
                else:
                    df.loc[df.index[j], "buy_countdown_stop_active"] = True
        
        # Sell countdown stop reactivation
        if (i > 0 and 
            not df["sell_countdown_stop_active"].iloc[i-1] and 
            not pd.isna(df["sell_countdown_stop"].iloc[i]) and
            df["sell_countdown_stop_triggered"].iloc[i-1] and
            df["high"].iloc[i] < df["sell_countdown_stop"].iloc[i]):
            
            # Reactivate from this point until next cancellation
            reactivation_level = df["sell_countdown_stop"].iloc[i]
            df.loc[df.index[i], "sell_countdown_stop_active"] = True
            df.loc[df.index[i], "sell_countdown_stop_reactivated"] = True
            
            # Continue forward until canceled again
            for j in range(i+1, len(df)):
                if df["high"].iloc[j] >= reactivation_level:
                    df.loc[df.index[j], "sell_countdown_stop_active"] = False
                    df.loc[df.index[j], "sell_countdown_stop_triggered"] = True
                    break
                else:
                    df.loc[df.index[j], "sell_countdown_stop_active"] = True
    
    return df


def _handle_buy_setup_completion(
    df, i, buy_countdown_active, buy_countdown_bars, buy_tdst_level, 
    sell_countdown_active, sell_countdown_bars, current_buy_setup_idx, 
    current_sell_setup_idx, sell_tdst_level
):
    """
    Handle the completion of a buy setup (9 consecutive bars).
    """
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
    
    return (
        df, buy_countdown_active, buy_countdown_bars, buy_tdst_level, 
        sell_countdown_active, sell_countdown_bars, current_buy_setup_idx, 
        current_sell_setup_idx, sell_tdst_level
    )


def _handle_sell_setup_completion(
    df, i, buy_countdown_active, buy_countdown_bars, buy_tdst_level, 
    sell_countdown_active, sell_countdown_bars, current_buy_setup_idx, 
    current_sell_setup_idx, sell_tdst_level
):
    """
    Handle the completion of a sell setup (9 consecutive bars).
    """
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
    
    return (
        df, buy_countdown_active, buy_countdown_bars, buy_tdst_level, 
        sell_countdown_active, sell_countdown_bars, current_buy_setup_idx, 
        current_sell_setup_idx, sell_tdst_level
    )


def _process_buy_countdown(df, i, buy_countdown_active, buy_countdown_bars, buy_tdst_level):
    """
    Process buy countdown at the current bar.
    """
    # Mark countdown as active in dataframe
    df.loc[df.index[i], "buy_countdown_active"] = 1

    # Check for countdown cancel condition (close above TDST)
    if buy_tdst_level is not None and df["close"].iloc[i] > buy_tdst_level:
        # Cancel the buy countdown
        buy_countdown_active = False
        buy_countdown_bars = []
        df.loc[df.index[i], "buy_countdown"] = 0  # Reset buy_countdown
        return df, buy_countdown_active, buy_countdown_bars

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
                    
            # Calculate buy countdown stop level when countdown completes
            countdown_bars = df.iloc[buy_countdown_bars]
            buy_countdown_stop = _calculate_countdown_buy_stop_level(countdown_bars)
            df.loc[df.index[i], "buy_countdown_stop"] = buy_countdown_stop
            df.loc[df.index[i], "buy_countdown_stop_active"] = True

            # Reset countdown after reaching 13
            buy_countdown_active = False
    else:
        # Bar doesn't qualify, but countdown continues
        # Keep the previous countdown value
        if buy_countdown_bars:
            df.loc[df.index[i], "buy_countdown"] = len(buy_countdown_bars)

    return df, buy_countdown_active, buy_countdown_bars


def _process_sell_countdown(df, i, sell_countdown_active, sell_countdown_bars, sell_tdst_level):
    """
    Process sell countdown at the current bar.
    """
    # Mark countdown as active in dataframe
    df.loc[df.index[i], "sell_countdown_active"] = 1

    # Check for countdown cancel condition (close below TDST)
    if sell_tdst_level is not None and df["close"].iloc[i] < sell_tdst_level:
        # Cancel the sell countdown
        sell_countdown_active = False
        sell_countdown_bars = []
        df.loc[df.index[i], "sell_countdown"] = 0  # Reset sell_countdown
        return df, sell_countdown_active, sell_countdown_bars

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
                    
            # Calculate sell countdown stop level when countdown completes
            countdown_bars = df.iloc[sell_countdown_bars]
            sell_countdown_stop = _calculate_countdown_sell_stop_level(countdown_bars)
            df.loc[df.index[i], "sell_countdown_stop"] = sell_countdown_stop
            df.loc[df.index[i], "sell_countdown_stop_active"] = True

            # Reset countdown after reaching 13
            sell_countdown_active = False
    else:
        # Bar doesn't qualify, but countdown continues
        # Keep the previous countdown value
        if sell_countdown_bars:
            df.loc[df.index[i], "sell_countdown"] = len(sell_countdown_bars)

    return df, sell_countdown_active, sell_countdown_bars


def _identify_stop_events(df):
    """
    Identify where stop loss levels were triggered and reactivated.
    """
    for i in range(1, len(df)):
        # Detect setup stop triggering
        if (
            df["buy_setup_stop_active"].iloc[i - 1] == True
            and df["buy_setup_stop_active"].iloc[i] == False
            and not pd.isna(df["buy_setup_stop"].iloc[i - 1])
        ):
            df.loc[df.index[i], "buy_stop_triggered"] = True

        if (
            df["sell_setup_stop_active"].iloc[i - 1] == True
            and df["sell_setup_stop_active"].iloc[i] == False
            and not pd.isna(df["sell_setup_stop"].iloc[i - 1])
        ):
            df.loc[df.index[i], "sell_stop_triggered"] = True

        # Detect setup stop reactivation
        if (
            df["buy_setup_stop_active"].iloc[i - 1] == False
            and df["buy_setup_stop_active"].iloc[i] == True
            and df["buy_setup"].iloc[i] != 9
        ):  # Not a new setup
            df.loc[df.index[i], "buy_stop_reactivated"] = True

        if (
            df["sell_setup_stop_active"].iloc[i - 1] == False
            and df["sell_setup_stop_active"].iloc[i] == True
            and df["sell_setup"].iloc[i] != 9
        ):  # Not a new setup
            df.loc[df.index[i], "sell_stop_reactivated"] = True
            
        # Detect countdown stop triggering
        if (
            df["buy_countdown_stop_active"].iloc[i - 1] == True
            and df["buy_countdown_stop_active"].iloc[i] == False
            and not pd.isna(df["buy_countdown_stop"].iloc[i - 1])
        ):
            df.loc[df.index[i], "buy_countdown_stop_triggered"] = True

        if (
            df["sell_countdown_stop_active"].iloc[i - 1] == True
            and df["sell_countdown_stop_active"].iloc[i] == False
            and not pd.isna(df["sell_countdown_stop"].iloc[i - 1])
        ):
            df.loc[df.index[i], "sell_countdown_stop_triggered"] = True

        # Detect countdown stop reactivation (if not already marked in calculation phase)
        if (
            df["buy_countdown_stop_active"].iloc[i - 1] == False
            and df["buy_countdown_stop_active"].iloc[i] == True
            and df["buy_countdown"].iloc[i] != 13
            and not df["buy_countdown_stop_reactivated"].iloc[i]
        ):  # Not a new countdown completion and not already marked
            df.loc[df.index[i], "buy_countdown_stop_reactivated"] = True

        if (
            df["sell_countdown_stop_active"].iloc[i - 1] == False
            and df["sell_countdown_stop_active"].iloc[i] == True
            and df["sell_countdown"].iloc[i] != 13
            and not df["sell_countdown_stop_reactivated"].iloc[i]
        ):  # Not a new countdown completion and not already marked
            df.loc[df.index[i], "sell_countdown_stop_reactivated"] = True

    return df