def calculate_td_sequential(data, ticker="AAPL"):
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

    # Add columns for setup support and resistance points
    df["setup_support"] = None
    df["setup_resistance"] = None

    # For readability, we'll use separate methods for buy and sell scenarios

    # Buy Setup (price closing LOWER than the close 4 bars earlier)
    current_buy_setup = 0
    buy_setup_start_idx = None
    for i in range(4, len(df)):
        if df["Close"].iloc[i] < df["Close"].iloc[i - 4]:  # Buy setup condition
            if current_buy_setup == 0:
                buy_setup_start_idx = i

            current_buy_setup += 1
            df.loc[df.index[i], "buy_setup"] = current_buy_setup

            # Check if the setup is perfected (low of bars 8 or 9 is lower than the low of bars 6 and 7)
            if current_buy_setup == 9:
                if (df["Low"].iloc[i] < df["Low"].iloc[i - 2]) or (
                    df["Low"].iloc[i - 1] < df["Low"].iloc[i - 3]
                ):
                    df.loc[df.index[i], "buy_setup_perfected"] = True

                # Calculate setup support level (higest high of the 9-bar setup)
                if buy_setup_start_idx is not None:
                    setup_range = df.iloc[buy_setup_start_idx : i + 1]
                    setup_support = setup_range[
                        "High"
                    ].max()  # setup_range["Low"].min()
                    df.loc[df.index[i], "setup_support"] = setup_support

        else:
            current_buy_setup = 0
            df.loc[df.index[i], "buy_setup"] = 0
            buy_setup_start_idx = None

        if current_buy_setup == 9:
            current_buy_setup = 0
            buy_setup_start_idx = None

    # Sell Setup (price closing HIGHER than the close 4 bars earlier)
    current_sell_setup = 0
    sell_setup_start_idx = None
    for i in range(4, len(df)):
        if df["Close"].iloc[i] > df["Close"].iloc[i - 4]:  # Sell setup condition
            if current_sell_setup == 0:
                sell_setup_start_idx = i

            current_sell_setup += 1
            df.loc[df.index[i], "sell_setup"] = current_sell_setup

            # Check if the setup is perfected (high of bars 8 or 9 is higher than the high of bars 6 and 7)
            if current_sell_setup == 9:
                if (df["High"].iloc[i] > df["High"].iloc[i - 2]) or (
                    df["High"].iloc[i - 1] > df["High"].iloc[i - 3]
                ):
                    df.loc[df.index[i], "sell_setup_perfected"] = True

                # Calculate setup resistance level (lowest low of the 9-bar setup)
                if sell_setup_start_idx is not None:
                    setup_range = df.iloc[sell_setup_start_idx : i + 1]
                    setup_resistance = setup_range["Low"].min()
                    df.loc[df.index[i], "setup_resistance"] = setup_resistance
        else:
            current_sell_setup = 0
            df.loc[df.index[i], "sell_setup"] = 0
            sell_setup_start_idx = None

        if current_sell_setup == 9:
            current_sell_setup = 0
            sell_setup_start_idx = None

    # Buy Countdown (only starts after a completed buy setup)
    # The close must be less than or equal to the low two bars earlier
    in_buy_countdown = False
    buy_countdown_count = 0
    buy_countdown_start_index = 0

    for i in range(4, len(df)):
        # Check for a completed buy setup (9 consecutive lower closes)
        if df["buy_setup"].iloc[i] == 9 and not in_buy_countdown:
            in_buy_countdown = True
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
                    buy_countdown_count = 0

                # Cancel the buy countdown if a new sell setup appears
                if df["sell_setup"].iloc[i] == 9:
                    in_buy_countdown = False
                    buy_countdown_count = 0

    # Sell Countdown (only starts after a completed sell setup)
    # The close must be greater than or equal to the high two bars earlier
    in_sell_countdown = False
    sell_countdown_count = 0
    sell_countdown_start_index = 0

    for i in range(4, len(df)):
        # Check for a completed sell setup (9 consecutive higher closes)
        if df["sell_setup"].iloc[i] == 9 and not in_sell_countdown:
            in_sell_countdown = True
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
                    sell_countdown_count = 0

                # Cancel the sell countdown if a new buy setup appears
                if df["buy_setup"].iloc[i] == 9:
                    in_sell_countdown = False
                    sell_countdown_count = 0

    # Add summary columns
    df["td_setup_direction"] = "neutral"
    df.loc[df["buy_setup"] == 9, "td_setup_direction"] = "buy"
    df.loc[df["sell_setup"] == 9, "td_setup_direction"] = "sell"

    df["td_countdown_direction"] = "neutral"
    df.loc[df["buy_countdown"] == 13, "td_countdown_direction"] = "buy"
    df.loc[df["sell_countdown"] == 13, "td_countdown_direction"] = "sell"

    return df
