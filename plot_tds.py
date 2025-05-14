import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, time


def plot_tdsequential(
    df,
    stock_name=None,
    window=100,
    show_support_resistance=True,
    show_setup_stop_loss=True,
    show_countdown_stop_loss=True,
    trading_hours=(time(9, 30), time(16, 0)),  # Default NYSE trading hours
    hide_non_trading_hours=True,
    hide_weekends=True,
    hide_holidays=True,
    holidays=None,  # List of holiday dates as strings 'YYYY-MM-DD' or datetime objects
):
    """
    Plot TD Sequential indicators on a candlestick chart with TDST levels and improved readability.
    Shows all setup numbers (1-9) above candlesticks and only first occurrence of countdown numbers (1-13) below candlesticks.
    Displays TDST levels, setup stop levels, and countdown stop levels as discontinuous horizontal lines.

    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with OHLC data and TD Sequential columns from calculate_tdsequential()
    stock_name : str, optional
        Name of the stock for the chart title
    window : int, optional
        Number of bars to display, default is 100
    show_support_resistance : bool, optional
        Whether to show TDST support/resistance levels, default is True
    show_setup_stop_loss : bool, optional
        Whether to show setup stop loss levels, default is True
    show_countdown_stop_loss : bool, optional
        Whether to show countdown stop loss levels, default is True
    trading_hours : tuple of datetime.time, optional
        Tuple of (start_time, end_time) for trading hours, default is (9:30, 16:00) for NYSE
    hide_non_trading_hours : bool, optional
        Whether to hide non-trading hours, default is True (only applies to datetime-indexed data)
    hide_weekends : bool, optional
        Whether to hide weekends, default is True
    hide_holidays : bool, optional
        Whether to hide holidays, default is True
    holidays : list, optional
        List of holiday dates as strings 'YYYY-MM-DD' or datetime objects

    Returns:
    --------
    plotly.graph_objects.Figure
        Plotly figure object
    """
    # Make a copy and limit to the window size
    if len(df) > window:
        plot_df = df.iloc[-window:].copy()
    else:
        plot_df = df.copy()

    # Get date column or index for x-axis and determine data type
    x, index_type = get_x_axis_values(plot_df)

    # Create a single subplot with more vertical space
    fig = make_subplots(rows=1, cols=1, vertical_spacing=0.02)

    # Add candlestick chart
    add_candlestick_chart(fig, x, plot_df)

    # Calculate price range for annotation positioning
    price_range = plot_df["high"].max() - plot_df["low"].min()
    annotation_params = calculate_annotation_parameters(price_range)

    # Dictionary to track position conflicts (avoid overlapping annotations)
    annotation_positions = {}

    # Add TDST levels as discontinuous lines with proper cancellation (if enabled)
    if show_support_resistance:
        add_tdst_levels(fig, plot_df, x)

    # Add Buy Setup Stop levels and Sell Setup Stop levels as discontinuous lines (if enabled)
    if show_setup_stop_loss:
        add_setup_stop_levels(fig, plot_df, x)

    # Add Buy Countdown Stop levels and Sell Countdown Stop levels as discontinuous lines (if enabled)
    if show_countdown_stop_loss:
        add_countdown_stop_levels(fig, plot_df, x)

    # Add Buy and Sell Setup annotations (above candlesticks)
    add_setup_annotations(fig, plot_df, x, annotation_params, annotation_positions)

    # Add Buy and Sell Countdown annotations (below candlesticks)
    add_countdown_annotations(fig, plot_df, x, annotation_params, annotation_positions)

    # Create a legend and add title
    add_legend(
        fig, show_support_resistance, show_setup_stop_loss, show_countdown_stop_loss
    )

    # Update layout with proper x-axis formatting based on index type
    update_layout(
        fig,
        stock_name,
        index_type=index_type,
        trading_hours=trading_hours,
        hide_non_trading_hours=hide_non_trading_hours,
        hide_weekends=hide_weekends,
        hide_holidays=hide_holidays,
        holidays=holidays,
    )

    return fig


def get_x_axis_values(plot_df):
    """
    Extract the x-axis values from the dataframe and determine the index type

    Returns:
    --------
    tuple: (x_values, index_type)
        x_values: array-like values for the x-axis
        index_type: string indicating the type ('datetime', 'date', or 'numeric')
    """
    if isinstance(plot_df.index, pd.DatetimeIndex):
        # Check if all times are midnight (indicating date-only data)
        has_time_component = any(
            idx.time() != time(0, 0) for idx in plot_df.index if not pd.isna(idx)
        )
        if has_time_component:
            return plot_df.index, "datetime"
        else:
            return plot_df.index, "date"
    elif "date" in plot_df.columns:
        if pd.api.types.is_datetime64_any_dtype(plot_df["date"]):
            # Check if all times are midnight (indicating date-only data)
            has_time_component = any(
                idx.time() != time(0, 0) for idx in plot_df["date"] if not pd.isna(idx)
            )
            if has_time_component:
                return plot_df["date"], "datetime"
            else:
                return plot_df["date"], "date"
        return plot_df["date"], "date"
    else:
        return np.arange(len(plot_df)), "numeric"


def add_candlestick_chart(fig, x, plot_df):
    """Add candlestick chart to the figure"""
    candlestick = go.Candlestick(
        x=x,
        open=plot_df["open"],
        high=plot_df["high"],
        low=plot_df["low"],
        close=plot_df["close"],
        name="Price",
        showlegend=False,
        increasing=dict(line=dict(width=1.5), fillcolor="rgba(0,168,107,0.6)"),
        decreasing=dict(line=dict(width=1.5), fillcolor="rgba(220,39,39,0.6)"),
    )
    fig.add_trace(candlestick)


def calculate_annotation_parameters(price_range):
    """Calculate parameters for annotations based on price range"""
    return {
        "setup_offset": price_range * 0.02,
        "countdown_offset": price_range * 0.02,
        "signal_offset": price_range * 0.05,
    }


def get_adjusted_position(idx, y_position, is_above, annotation_positions):
    """Handle potential annotation overlaps"""
    key = (idx, is_above)
    if key in annotation_positions:
        # If this position is already taken, adjust by a small amount
        if is_above:
            y_position += annotation_positions.get("setup_offset", 0)
        else:
            y_position -= annotation_positions.get("countdown_offset", 0)
        annotation_positions[key] = y_position
    else:
        annotation_positions[key] = y_position
    return y_position


def add_tdst_levels(fig, plot_df, x):
    """Add TDST support and resistance levels to the figure"""
    # Process buy TDST levels (resistance)
    if "buy_tdst_level" in plot_df.columns and "buy_tdst_active" in plot_df.columns:
        add_discontinuous_levels(
            fig,
            plot_df,
            x,
            level_column="buy_tdst_level",
            active_column="buy_tdst_active",
            color="rgba(0,168,107,0.7)",
            name="Buy TDST",
        )

    # Process sell TDST levels (support)
    if "sell_tdst_level" in plot_df.columns and "sell_tdst_active" in plot_df.columns:
        add_discontinuous_levels(
            fig,
            plot_df,
            x,
            level_column="sell_tdst_level",
            active_column="sell_tdst_active",
            color="rgba(220,39,39,0.7)",
            name="Sell TDST",
        )


def add_setup_stop_levels(fig, plot_df, x):
    """Add setup stop loss levels to the figure"""
    # Process buy stop levels (support)
    if (
        "buy_setup_stop" in plot_df.columns
        and "buy_setup_stop_active" in plot_df.columns
    ):
        add_discontinuous_levels(
            fig,
            plot_df,
            x,
            level_column="buy_setup_stop",
            active_column="buy_setup_stop_active",
            color="rgba(128,0,128,0.7)",  # Purple
            name="Buy Setup Stop",
            price_column="close",
            check_price_below=True,
        )

    # Process sell stop levels (resistance)
    if (
        "sell_setup_stop" in plot_df.columns
        and "sell_setup_stop_active" in plot_df.columns
    ):
        add_discontinuous_levels(
            fig,
            plot_df,
            x,
            level_column="sell_setup_stop",
            active_column="sell_setup_stop_active",
            color="rgba(255,165,0,0.7)",  # Orange
            name="Sell Setup Stop",
            price_column="close",
            check_price_above=True,
        )


def add_countdown_stop_levels(fig, plot_df, x):
    """Add countdown stop loss levels to the figure"""
    # Process buy countdown stop levels (support)
    if (
        "buy_countdown_stop" in plot_df.columns
        and "buy_countdown_stop_active" in plot_df.columns
    ):
        add_discontinuous_levels(
            fig,
            plot_df,
            x,
            level_column="buy_countdown_stop",
            active_column="buy_countdown_stop_active",
            color="rgba(0,0,255,0.7)",  # Blue
            name="Buy Countdown Stop",
            price_column="close",
            check_price_below=True,
        )

    # Process sell countdown stop levels (resistance)
    if (
        "sell_countdown_stop" in plot_df.columns
        and "sell_countdown_stop_active" in plot_df.columns
    ):
        add_discontinuous_levels(
            fig,
            plot_df,
            x,
            level_column="sell_countdown_stop",
            active_column="sell_countdown_stop_active",
            color="rgba(0,0,255,0.7)",  # Blue
            name="Sell Countdown Stop",
            price_column="close",
            check_price_above=True,
        )


def add_discontinuous_levels(
    fig,
    plot_df,
    x,
    level_column,
    active_column,
    color,
    name,
    price_column=None,
    check_price_below=False,
    check_price_above=False,
):
    """
    Add discontinuous horizontal levels (TDST or stop levels) to the figure

    Parameters:
    -----------
    fig : plotly.graph_objects.Figure
        Figure to add levels to
    plot_df : pandas.DataFrame
        DataFrame with the data
    x : array-like
        X-axis values
    level_column : str
        Column name for the level values
    active_column : str
        Column name for the active flags
    color : str
        Color for the lines
    name : str
        Name for the hover info
    price_column : str, optional
        Column name for the price to check against the level
    check_price_below : bool, optional
        Whether to check if price is below the level
    check_price_above : bool, optional
        Whether to check if price is above the level
    """
    segments = []
    current_segment = None

    for i, row in plot_df.iterrows():
        # Skip if not active or level is NaN
        if not row[active_column] or pd.isna(row[level_column]):
            if current_segment is not None:
                segments.append(current_segment)
                current_segment = None
            continue

        # Check price conditions if specified
        if check_price_below and price_column and row[price_column] < row[level_column]:
            if current_segment is not None:
                segments.append(current_segment)
                current_segment = None
            continue

        if check_price_above and price_column and row[price_column] > row[level_column]:
            if current_segment is not None:
                segments.append(current_segment)
                current_segment = None
            continue

        # Start a new segment or continue the current one
        if current_segment is None:
            current_segment = {
                "start": i,
                "end": i,
                "level": row[level_column],
            }
        else:
            if row[level_column] == current_segment["level"]:
                current_segment["end"] = i
            else:
                segments.append(current_segment)
                current_segment = {
                    "start": i,
                    "end": i,
                    "level": row[level_column],
                }

    # Add the last segment if there is one
    if current_segment is not None:
        segments.append(current_segment)

    # Add all segments to the figure
    for segment in segments:
        # Convert index to x values if needed
        start_x = (
            x[plot_df.index.get_loc(segment["start"])]
            if isinstance(x, pd.DatetimeIndex)
            else segment["start"]
        )
        end_x = (
            x[plot_df.index.get_loc(segment["end"])]
            if isinstance(x, pd.DatetimeIndex)
            else segment["end"]
        )

        fig.add_trace(
            go.Scatter(
                x=[start_x, end_x],
                y=[segment["level"], segment["level"]],
                mode="lines",
                line=dict(color=color, width=1, dash="dash"),
                name=name,
                showlegend=False,
                hoverinfo="y+name",
            )
        )


def add_setup_annotations(fig, plot_df, x, annotation_params, annotation_positions):
    """Add Buy and Sell Setup annotations above candlesticks"""
    add_buy_setup_annotations(fig, plot_df, x, annotation_params, annotation_positions)
    add_sell_setup_annotations(fig, plot_df, x, annotation_params, annotation_positions)


def add_buy_setup_annotations(fig, plot_df, x, annotation_params, annotation_positions):
    """Add Buy Setup annotations above candlesticks"""
    setup_offset = annotation_params["setup_offset"]
    signal_offset = annotation_params["signal_offset"]

    for i, row in plot_df.iterrows():
        idx = x[plot_df.index.get_loc(i)] if isinstance(x, pd.DatetimeIndex) else i

        # Show all setup numbers
        if row["buy_setup"] > 0:
            y_pos = get_adjusted_position(
                idx, row["high"] + setup_offset, True, annotation_positions
            )
            # Make higher numbers more prominent
            font_size = 10 + min(2, row["buy_setup"] - 1)
            fig.add_annotation(
                x=idx,
                y=y_pos,
                text=str(int(row["buy_setup"])),
                showarrow=False,
                font=dict(color="rgb(0,168,107)", size=font_size, family="Arial"),
                opacity=0.9,
            )

        # Add annotations for normal buy setup 9s
        if row["buy_setup"] == 9 and row.get("perfect_buy_9", 0) != 1:
            fig.add_annotation(
                x=idx,
                y=row["high"] + signal_offset,
                text="BUY 9",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor="rgb(0,168,107)",
                font=dict(color="white", size=9, family="Arial"),  # Smaller font
                bgcolor="rgba(0,168,107,0.4)",  # More transparent
                borderpad=3,
                borderwidth=0,
                opacity=0.7,  # More transparent
            )

        # Highlight perfect buy setup 9s with "BUY M9" text
        if row["buy_setup"] == 9 and row.get("perfect_buy_9", 0) == 1:
            fig.add_annotation(
                x=idx,
                y=row["high"] + signal_offset,
                text="BUY M9",  # Changed text format to BUY M9
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor="rgb(0,168,107)",
                font=dict(color="white", size=9, family="Arial"),  # Smaller font
                bgcolor="rgba(0,168,107,0.4)",  # More transparent
                borderpad=3,
                borderwidth=0,
                opacity=0.7,  # More transparent
            )


def add_sell_setup_annotations(
    fig, plot_df, x, annotation_params, annotation_positions
):
    """Add Sell Setup annotations above candlesticks"""
    setup_offset = annotation_params["setup_offset"]
    signal_offset = annotation_params["signal_offset"]

    for i, row in plot_df.iterrows():
        idx = x[plot_df.index.get_loc(i)] if isinstance(x, pd.DatetimeIndex) else i

        # Show all setup numbers
        if row["sell_setup"] > 0:
            y_pos = get_adjusted_position(
                idx, row["high"] + setup_offset, True, annotation_positions
            )
            # Make higher numbers more prominent
            font_size = 10 + min(2, row["sell_setup"] - 1)
            fig.add_annotation(
                x=idx,
                y=y_pos,
                text=str(int(row["sell_setup"])),
                showarrow=False,
                font=dict(color="rgb(220,39,39)", size=font_size, family="Arial"),
                opacity=0.9,
            )

        # Add annotations for normal sell setup 9s
        if row["sell_setup"] == 9 and row.get("perfect_sell_9", 0) != 1:
            fig.add_annotation(
                x=idx,
                y=row["high"] + signal_offset,
                text="SELL 9",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor="rgb(220,39,39)",
                font=dict(color="white", size=9, family="Arial"),  # Smaller font
                bgcolor="rgba(220,39,39,0.4)",  # More transparent
                borderpad=3,
                borderwidth=0,
                opacity=0.7,  # More transparent
            )

        # Highlight perfect sell setup 9s with "SELL M9" text
        if row["sell_setup"] == 9 and row.get("perfect_sell_9", 0) == 1:
            fig.add_annotation(
                x=idx,
                y=row["high"] + signal_offset,
                text="SELL M9",  # Changed text format to SELL M9
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor="rgb(220,39,39)",
                font=dict(color="white", size=9, family="Arial"),  # Smaller font
                bgcolor="rgba(220,39,39,0.4)",  # More transparent
                borderpad=3,
                borderwidth=0,
                opacity=0.7,  # More transparent
            )


def add_countdown_annotations(fig, plot_df, x, annotation_params, annotation_positions):
    """Add Buy and Sell Countdown annotations below candlesticks"""
    add_buy_countdown_annotations(
        fig, plot_df, x, annotation_params, annotation_positions
    )
    add_sell_countdown_annotations(
        fig, plot_df, x, annotation_params, annotation_positions
    )


def add_buy_countdown_annotations(
    fig, plot_df, x, annotation_params, annotation_positions
):
    """Add Buy Countdown annotations below candlesticks"""
    countdown_offset = annotation_params["countdown_offset"]
    signal_offset = annotation_params["signal_offset"]

    # Track the last countdown numbers to detect repeats
    last_buy_countdown = None

    for i, row in plot_df.iterrows():
        idx = x[plot_df.index.get_loc(i)] if isinstance(x, pd.DatetimeIndex) else i

        # Only show the first occurrence of each countdown number
        if row["buy_countdown"] > 0 and row["buy_countdown"] != last_buy_countdown:
            y_pos = get_adjusted_position(
                idx, row["low"] - countdown_offset, False, annotation_positions
            )
            font_size = 10 + min(2, row["buy_countdown"] // 5)
            fig.add_annotation(
                x=idx,
                y=y_pos,
                text=str(int(row["buy_countdown"])),
                showarrow=False,
                font=dict(color="rgb(0,168,107)", size=font_size, family="Arial"),
                opacity=0.9,
            )

            # Add annotations for normal buy countdown 13s
            if row["buy_countdown"] == 13 and row.get("perfect_buy_13", 0) != 1:
                fig.add_annotation(
                    x=idx,
                    y=row["low"] - signal_offset,
                    text="BUY 13",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor="rgb(0,168,107)",
                    font=dict(color="white", size=9, family="Arial"),  # Smaller font
                    bgcolor="rgba(0,168,107,0.4)",  # More transparent
                    borderpad=3,
                    borderwidth=0,
                    opacity=0.7,  # More transparent
                )

            # Highlight perfect buy countdown 13s with "BUY M13" text
            if row["buy_countdown"] == 13 and row.get("perfect_buy_13", 0) == 1:
                fig.add_annotation(
                    x=idx,
                    y=row["low"] - signal_offset,
                    text="BUY M13",  # Changed text format to BUY M13
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor="rgb(0,168,107)",
                    font=dict(color="white", size=9, family="Arial"),  # Smaller font
                    bgcolor="rgba(0,168,107,0.4)",  # More transparent
                    borderpad=3,
                    borderwidth=0,
                    opacity=0.7,  # More transparent
                )

        # Update the last countdown number
        last_buy_countdown = row["buy_countdown"] if row["buy_countdown"] > 0 else None


def add_sell_countdown_annotations(
    fig, plot_df, x, annotation_params, annotation_positions
):
    """Add Sell Countdown annotations below candlesticks"""
    countdown_offset = annotation_params["countdown_offset"]
    signal_offset = annotation_params["signal_offset"]

    # Track the last countdown numbers to detect repeats
    last_sell_countdown = None

    for i, row in plot_df.iterrows():
        idx = x[plot_df.index.get_loc(i)] if isinstance(x, pd.DatetimeIndex) else i

        # Only show the first occurrence of each countdown number
        if row["sell_countdown"] > 0 and row["sell_countdown"] != last_sell_countdown:
            y_pos = get_adjusted_position(
                idx, row["low"] - countdown_offset, False, annotation_positions
            )
            font_size = 10 + min(2, row["sell_countdown"] // 5)
            fig.add_annotation(
                x=idx,
                y=y_pos,
                text=str(int(row["sell_countdown"])),
                showarrow=False,
                font=dict(color="rgb(220,39,39)", size=font_size, family="Arial"),
                opacity=0.9,
            )

            # Add annotations for normal sell countdown 13s
            if row["sell_countdown"] == 13 and row.get("perfect_sell_13", 0) != 1:
                fig.add_annotation(
                    x=idx,
                    y=row["low"] - signal_offset,
                    text="SELL 13",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor="rgb(220,39,39)",
                    font=dict(color="white", size=9, family="Arial"),  # Smaller font
                    bgcolor="rgba(220,39,39,0.4)",  # More transparent
                    borderpad=3,
                    borderwidth=0,
                    opacity=0.7,  # More transparent
                )

            # Highlight perfect sell countdown 13s with "SELL M13" text
            if row["sell_countdown"] == 13 and row.get("perfect_sell_13", 0) == 1:
                fig.add_annotation(
                    x=idx,
                    y=row["low"] - signal_offset,
                    text="SELL M13",  # Changed text format to SELL M13
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor="rgb(220,39,39)",
                    font=dict(color="white", size=9, family="Arial"),  # Smaller font
                    bgcolor="rgba(220,39,39,0.4)",  # More transparent
                    borderpad=3,
                    borderwidth=0,
                    opacity=0.7,  # More transparent
                )

        # Update the last countdown number
        last_sell_countdown = (
            row["sell_countdown"] if row["sell_countdown"] > 0 else None
        )


def add_legend(
    fig, show_support_resistance, show_setup_stop_loss, show_countdown_stop_loss
):
    """Add a legend to the figure"""
    # Create a clearer legend using shapes and annotations
    fig.add_shape(
        type="rect",
        xref="paper",
        yref="paper",
        x0=0.01,
        y0=0.01,
        x1=0.3,
        y1=0.19,  # Increased height to accommodate additional legend items
        fillcolor="rgba(40,40,40,0.9)",  # Dark background for legend
        line=dict(color="#555555", width=1),
        layer="below",
    )

    # Add clearer, color-coded legend text
    legend_texts = [
        ("BUY SETUP (1-9)", "rgb(0,168,107)", 0.025, 0.175),
        ("SELL SETUP (1-9)", "rgb(220,39,39)", 0.025, 0.155),
        ("BUY COUNTDOWN (1-13)", "rgb(0,168,107)", 0.025, 0.135),
        ("SELL COUNTDOWN (1-13)", "rgb(220,39,39)", 0.025, 0.115),
    ]

    # Only add TDST levels to legend if enabled
    if show_support_resistance:
        legend_texts.extend(
            [
                ("BUY TDST (Resistance)", "rgba(0,168,107,0.7)", 0.025, 0.095),
                ("SELL TDST (Support)", "rgba(220,39,39,0.7)", 0.025, 0.075),
            ]
        )

    # Only add setup stop levels to legend if enabled
    if show_setup_stop_loss:
        legend_texts.extend(
            [
                (
                    "BUY SETUP STOP (Support)",
                    "rgba(128,0,128,0.7)",
                    0.025,
                    0.055,
                ),  # Purple
                (
                    "SELL SETUP STOP (Resistance)",
                    "rgba(255,165,0,0.7)",
                    0.025,
                    0.035,
                ),  # Orange
            ]
        )

    # Only add countdown stop levels to legend if enabled
    if show_countdown_stop_loss:
        legend_texts.extend(
            [
                (
                    "BUY COUNTDOWN STOP (Support)",
                    "rgba(0,0,255,0.7)",
                    0.025,
                    0.015,
                ),  # Blue
                (
                    "SELL COUNTDOWN STOP (Resistance)",
                    "rgba(0,0,255,0.7)",
                    0.025,
                    -0.005,
                ),  # Blue
            ]
        )

    for text, color, x, y in legend_texts:
        fig.add_annotation(
            x=x,
            y=y,
            xref="paper",
            yref="paper",
            text=text,
            showarrow=False,
            font=dict(size=11, color=color, family="Arial"),
            align="left",
            bgcolor="rgba(0,0,0,0)",
        )


def is_holiday(date, holidays):
    """Check if a given date is a holiday"""
    if holidays is None:
        return False

    # Convert date to string format for comparison if it's a datetime
    if isinstance(date, (pd.Timestamp, datetime)):
        date_str = date.strftime("%Y-%m-%d")
    else:
        date_str = date

    # Convert all holidays to string format if they aren't already
    holiday_strs = []
    for holiday in holidays:
        if isinstance(holiday, (pd.Timestamp, datetime)):
            holiday_strs.append(holiday.strftime("%Y-%m-%d"))
        else:
            holiday_strs.append(holiday)

    return date_str in holiday_strs


def is_weekend(date):
    """Check if a given date is a weekend (Saturday or Sunday)"""
    if isinstance(date, (pd.Timestamp, datetime)):
        return date.weekday() >= 5  # 5 = Saturday, 6 = Sunday
    return False


def is_trading_time(timestamp, trading_hours):
    """Check if a given timestamp is within trading hours"""
    if not isinstance(timestamp, (pd.Timestamp, datetime)):
        return True

    start_time, end_time = trading_hours
    timestamp_time = timestamp.time()

    return start_time <= timestamp_time <= end_time


def update_layout(
    fig,
    stock_name,
    index_type="numeric",
    trading_hours=(time(9, 30), time(16, 0)),
    hide_non_trading_hours=True,
    hide_weekends=True,
    hide_holidays=True,
    holidays=None,
):
    """
    Update the figure layout with dark theme styling and appropriate x-axis formatting

    Parameters:
    -----------
    fig : plotly.graph_objects.Figure
        Figure to update
    stock_name : str, optional
        Name of the stock for the chart title
    index_type : str, optional
        Type of index ('datetime', 'date', or 'numeric')
    trading_hours : tuple of datetime.time, optional
        Tuple of (start_time, end_time) for trading hours
    hide_non_trading_hours : bool, optional
        Whether to hide non-trading hours
    hide_weekends : bool, optional
        Whether to hide weekends
    hide_holidays : bool, optional
        Whether to hide holidays
    holidays : list, optional
        List of holiday dates
    """
    title = f"TD Sequential Analysis{' - ' + stock_name if stock_name else ''}"
    fig.update_layout(
        title=dict(text=title, font=dict(size=24, family="Arial", color="#FFFFFF")),
        height=800,
        width=1200,
        margin=dict(l=50, r=50, t=100, b=100),
        xaxis_rangeslider_visible=False,
        template="plotly_dark",  # Use dark template
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="#121212",  # Dark background
        paper_bgcolor="#121212",  # Dark paper
        hovermode="x unified",
        font=dict(family="Arial", color="#FFFFFF"),  # Light text for dark background
    )

    # Configure x-axis based on index type
    x_axis_config = {
        "showgrid": True,
        "gridwidth": 0.5,
        "gridcolor": "rgba(80,80,80,0.5)",
        "zeroline": False,
        "title_font": dict(color="#FFFFFF"),
        "tickfont": dict(color="#FFFFFF"),
    }

    # Add specific configurations for datetime or date indices
    if index_type == "datetime":
        # For datetime data, show date and time
        x_axis_config.update(
            {
                "title": "Date & Time",
                "tickformat": "%Y-%m-%d %H:%M",
                "type": "date",
                "rangeslider": dict(visible=False),
            }
        )

        # Configure rangebreaks to hide non-trading hours, weekends, and holidays
        rangebreaks = []

        # Hide non-trading hours if requested
        if hide_non_trading_hours:
            start_time, end_time = trading_hours
            rangebreaks.append(
                dict(
                    bounds=[end_time.strftime("%H:%M"), start_time.strftime("%H:%M")],
                    pattern="hour",
                )
            )

        # Hide weekends if requested
        if hide_weekends:
            rangebreaks.append(dict(bounds=["sat", "mon"], pattern="day of week"))

        # Add rangebreaks to x-axis config if there are any
        if rangebreaks:
            x_axis_config["rangebreaks"] = rangebreaks

    elif index_type == "date":
        # For date-only data, show just the date
        x_axis_config.update(
            {
                "title": "Date",
                "tickformat": "%Y-%m-%d",
                "type": "date",
                "rangeslider": dict(visible=False),
            }
        )

        # Configure rangebreaks to hide weekends and holidays
        rangebreaks = []

        # Hide weekends if requested
        if hide_weekends:
            rangebreaks.append(dict(bounds=["sat", "mon"], pattern="day of week"))

        # Add rangebreaks to x-axis config if there are any
        if rangebreaks:
            x_axis_config["rangebreaks"] = rangebreaks
    else:
        # For numeric data, leave as is
        x_axis_config["title"] = "Bar Number"

    fig.update_xaxes(**x_axis_config)

    fig.update_yaxes(
        title="Price",
        showgrid=True,
        gridwidth=0.5,
        gridcolor="rgba(80,80,80,0.5)",
        zeroline=False,
        title_font=dict(color="#FFFFFF"),
        tickfont=dict(color="#FFFFFF"),
    )
