import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_tdsequential(df, stock_name=None, window=100):
    """
    Plot TD Sequential indicators on a candlestick chart with TDST levels and improved readability.
    Now includes setup stop loss levels (buy and sell) with distinct colors.

    Shows all setup numbers (1-9) above candlesticks and only first occurrence of countdown numbers (1-13) below candlesticks.
    Displays TDST levels and setup stop levels as discontinuous horizontal lines.

    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with OHLC data and TD Sequential columns from calculate_tdsequential()
    stock_name : str, optional
        Name of the stock for the chart title
    window : int, optional
        Number of bars to display, default is 100

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

    # Get date column or index for x-axis
    if isinstance(plot_df.index, pd.DatetimeIndex):
        x = plot_df.index
    elif "date" in plot_df.columns:
        x = plot_df["date"]
    else:
        x = np.arange(len(plot_df))

    # Create a single subplot with more vertical space
    fig = make_subplots(rows=1, cols=1, vertical_spacing=0.02)

    # Add candlestick chart
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

    # Calculate price range for annotation positioning
    price_range = plot_df["high"].max() - plot_df["low"].min()

    # Spacing for better readability
    setup_offset = price_range * 0.02
    countdown_offset = price_range * 0.02
    signal_offset = price_range * 0.05

    # Dictionary to track position conflicts (avoid overlapping annotations)
    annotation_positions = {}

    # Function to handle potential annotation overlaps
    def get_adjusted_position(idx, y_position, is_above):
        key = (idx, is_above)
        if key in annotation_positions:
            # If this position is already taken, adjust by a small amount
            if is_above:
                y_position += setup_offset
            else:
                y_position -= countdown_offset
            annotation_positions[key] = y_position
        else:
            annotation_positions[key] = y_position
        return y_position

    # Add TDST levels as discontinuous lines with proper cancellation
    if "buy_tdst_level" in plot_df.columns and "buy_tdst_active" in plot_df.columns:
        # Process buy TDST levels (resistance)
        buy_tdst_segments = []
        current_segment = None

        for i, row in plot_df.iterrows():
            if row["buy_tdst_active"]:
                if current_segment is None:
                    current_segment = {
                        "start": i,
                        "end": i,
                        "level": row["buy_tdst_level"],
                    }
                else:
                    if row["buy_tdst_level"] == current_segment["level"]:
                        current_segment["end"] = i
                    else:
                        buy_tdst_segments.append(current_segment)
                        current_segment = {
                            "start": i,
                            "end": i,
                            "level": row["buy_tdst_level"],
                        }
            else:
                if current_segment is not None:
                    buy_tdst_segments.append(current_segment)
                    current_segment = None

        if current_segment is not None:
            buy_tdst_segments.append(current_segment)

        for segment in buy_tdst_segments:
            fig.add_trace(
                go.Scatter(
                    x=[segment["start"], segment["end"]],
                    y=[segment["level"], segment["level"]],
                    mode="lines",
                    line=dict(color="rgba(0,168,107,0.7)", width=1, dash="dot"),
                    name="Buy TDST",
                    showlegend=False,
                    hoverinfo="y+name",
                )
            )

    if "sell_tdst_level" in plot_df.columns and "sell_tdst_active" in plot_df.columns:
        # Process sell TDST levels (support)
        sell_tdst_segments = []
        current_segment = None

        for i, row in plot_df.iterrows():
            if row["sell_tdst_active"]:
                if current_segment is None:
                    current_segment = {
                        "start": i,
                        "end": i,
                        "level": row["sell_tdst_level"],
                    }
                else:
                    if row["sell_tdst_level"] == current_segment["level"]:
                        current_segment["end"] = i
                    else:
                        sell_tdst_segments.append(current_segment)
                        current_segment = {
                            "start": i,
                            "end": i,
                            "level": row["sell_tdst_level"],
                        }
            else:
                if current_segment is not None:
                    sell_tdst_segments.append(current_segment)
                    current_segment = None

        if current_segment is not None:
            sell_tdst_segments.append(current_segment)

        for segment in sell_tdst_segments:
            fig.add_trace(
                go.Scatter(
                    x=[segment["start"], segment["end"]],
                    y=[segment["level"], segment["level"]],
                    mode="lines",
                    line=dict(color="rgba(220,39,39,0.7)", width=1, dash="dot"),
                    name="Sell TDST",
                    showlegend=False,
                    hoverinfo="y+name",
                )
            )

    # Add Buy Setup Stop levels as discontinuous lines (using purple)
    if (
        "buy_setup_stop" in plot_df.columns
        and "buy_setup_stop_active" in plot_df.columns
    ):
        # Process buy stop levels (support)
        buy_stop_segments = []
        current_segment = None

        for i, row in plot_df.iterrows():
            if row["buy_setup_stop_active"]:
                if current_segment is None:
                    current_segment = {
                        "start": i,
                        "end": i,
                        "level": row["buy_setup_stop"],
                    }
                else:
                    if row["buy_setup_stop"] == current_segment["level"]:
                        current_segment["end"] = i
                    else:
                        buy_stop_segments.append(current_segment)
                        current_segment = {
                            "start": i,
                            "end": i,
                            "level": row["buy_setup_stop"],
                        }
            else:
                if current_segment is not None:
                    buy_stop_segments.append(current_segment)
                    current_segment = None

        if current_segment is not None:
            buy_stop_segments.append(current_segment)

        for segment in buy_stop_segments:
            fig.add_trace(
                go.Scatter(
                    x=[segment["start"], segment["end"]],
                    y=[segment["level"], segment["level"]],
                    mode="lines",
                    line=dict(
                        color="rgba(128,0,128,0.7)", width=1, dash="dash"
                    ),  # Purple
                    name="Buy Stop",
                    showlegend=False,
                    hoverinfo="y+name",
                )
            )

    # Add Sell Setup Stop levels as discontinuous lines (using orange)
    if (
        "sell_setup_stop" in plot_df.columns
        and "sell_setup_stop_active" in plot_df.columns
    ):
        # Process sell stop levels (resistance)
        sell_stop_segments = []
        current_segment = None

        for i, row in plot_df.iterrows():
            if row["sell_setup_stop_active"]:
                if current_segment is None:
                    current_segment = {
                        "start": i,
                        "end": i,
                        "level": row["sell_setup_stop"],
                    }
                else:
                    if row["sell_setup_stop"] == current_segment["level"]:
                        current_segment["end"] = i
                    else:
                        sell_stop_segments.append(current_segment)
                        current_segment = {
                            "start": i,
                            "end": i,
                            "level": row["sell_setup_stop"],
                        }
            else:
                if current_segment is not None:
                    sell_stop_segments.append(current_segment)
                    current_segment = None

        if current_segment is not None:
            sell_stop_segments.append(current_segment)

        for segment in sell_stop_segments:
            fig.add_trace(
                go.Scatter(
                    x=[segment["start"], segment["end"]],
                    y=[segment["level"], segment["level"]],
                    mode="lines",
                    line=dict(
                        color="rgba(255,165,0,0.7)", width=1, dash="dash"
                    ),  # Orange
                    name="Sell Stop",
                    showlegend=False,
                    hoverinfo="y+name",
                )
            )

    # Add Buy Setup annotations (above candlesticks)
    for i, row in plot_df.iterrows():
        idx = x[plot_df.index.get_loc(i)] if isinstance(x, pd.DatetimeIndex) else i

        # Show all setup numbers
        if row["buy_setup"] > 0:
            y_pos = get_adjusted_position(idx, row["high"] + setup_offset, True)
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

        # Highlight perfect buy setup 9s
        if row["buy_setup"] == 9 and row.get("perfect_buy_9", 0) == 1:
            fig.add_annotation(
                x=idx,
                y=row["high"] + signal_offset,
                text="BUY 9",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor="rgb(0,168,107)",
                font=dict(color="white", size=12, family="Arial Black"),
                bgcolor="rgba(0,168,107,0.5)",  # Transparent background
                borderpad=4,
                borderwidth=0,
                opacity=0.9,
            )

    # Add Sell Setup annotations (above candlesticks)
    for i, row in plot_df.iterrows():
        idx = x[plot_df.index.get_loc(i)] if isinstance(x, pd.DatetimeIndex) else i

        # Show all setup numbers
        if row["sell_setup"] > 0:
            y_pos = get_adjusted_position(idx, row["high"] + setup_offset, True)
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

        # Highlight perfect sell setup 9s
        if row["sell_setup"] == 9 and row.get("perfect_sell_9", 0) == 1:
            fig.add_annotation(
                x=idx,
                y=row["high"] + signal_offset,
                text="SELL 9",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor="rgb(220,39,39)",
                font=dict(color="white", size=12, family="Arial Black"),
                bgcolor="rgba(220,39,39,0.5)",  # Transparent background
                borderpad=4,
                borderwidth=0,
                opacity=0.9,
            )

    # Track the last countdown numbers to detect repeats
    last_buy_countdown = None
    last_sell_countdown = None

    # Add Buy Countdown annotations (below candlesticks)
    for i, row in plot_df.iterrows():
        idx = x[plot_df.index.get_loc(i)] if isinstance(x, pd.DatetimeIndex) else i

        # Only show the first occurrence of each countdown number
        if row["buy_countdown"] > 0 and row["buy_countdown"] != last_buy_countdown:
            y_pos = get_adjusted_position(idx, row["low"] - countdown_offset, False)
            font_size = 10 + min(2, row["buy_countdown"] // 5)
            fig.add_annotation(
                x=idx,
                y=y_pos,
                text=str(int(row["buy_countdown"])),
                showarrow=False,
                font=dict(color="rgb(0,168,107)", size=font_size, family="Arial"),
                opacity=0.9,
            )

            # Highlight perfect buy countdown 13s
            if row["buy_countdown"] == 13 and row.get("perfect_buy_13", 0) == 1:
                fig.add_annotation(
                    x=idx,
                    y=row["low"] - signal_offset,
                    text="BUY 13",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor="rgb(0,168,107)",
                    font=dict(color="white", size=12, family="Arial Black"),
                    bgcolor="rgba(0,168,107,0.5)",  # Transparent background
                    borderpad=4,
                    borderwidth=0,
                    opacity=0.9,
                )

        # Update the last countdown number
        last_buy_countdown = row["buy_countdown"] if row["buy_countdown"] > 0 else None

    # Add Sell Countdown annotations (below candlesticks)
    for i, row in plot_df.iterrows():
        idx = x[plot_df.index.get_loc(i)] if isinstance(x, pd.DatetimeIndex) else i

        # Only show the first occurrence of each countdown number
        if row["sell_countdown"] > 0 and row["sell_countdown"] != last_sell_countdown:
            y_pos = get_adjusted_position(idx, row["low"] - countdown_offset, False)
            font_size = 10 + min(2, row["sell_countdown"] // 5)
            fig.add_annotation(
                x=idx,
                y=y_pos,
                text=str(int(row["sell_countdown"])),
                showarrow=False,
                font=dict(color="rgb(220,39,39)", size=font_size, family="Arial"),
                opacity=0.9,
            )

            # Highlight perfect sell countdown 13s
            if row["sell_countdown"] == 13 and row.get("perfect_sell_13", 0) == 1:
                fig.add_annotation(
                    x=idx,
                    y=row["low"] - signal_offset,
                    text="SELL 13",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor="rgb(220,39,39)",
                    font=dict(color="white", size=12, family="Arial Black"),
                    bgcolor="rgba(220,39,39,0.5)",  # Transparent background
                    borderpad=4,
                    borderwidth=0,
                    opacity=0.9,
                )

        # Update the last countdown number
        last_sell_countdown = (
            row["sell_countdown"] if row["sell_countdown"] > 0 else None
        )

    # Create a clearer legend using shapes and annotations
    fig.add_shape(
        type="rect",
        xref="paper",
        yref="paper",
        x0=0.01,
        y0=0.01,
        x1=0.3,
        y1=0.15,
        fillcolor="rgba(40,40,40,0.9)",  # Dark background for legend
        line=dict(color="#555555", width=1),
        layer="below",
    )

    # Add clearer, color-coded legend text including stop levels with new colors
    legend_texts = [
        ("BUY SETUP (1-9)", "rgb(0,168,107)", 0.025, 0.135),
        ("SELL SETUP (1-9)", "rgb(220,39,39)", 0.025, 0.115),
        ("BUY COUNTDOWN (1-13)", "rgb(0,168,107)", 0.025, 0.095),
        ("SELL COUNTDOWN (1-13)", "rgb(220,39,39)", 0.025, 0.075),
        ("BUY TDST (Resistance)", "rgba(0,168,107,0.7)", 0.025, 0.055),
        ("SELL TDST (Support)", "rgba(220,39,39,0.7)", 0.025, 0.035),
        ("BUY STOP (Support)", "rgba(128,0,128,0.7)", 0.025, 0.015),  # Purple
        ("SELL STOP (Resistance)", "rgba(255,165,0,0.7)", 0.025, -0.005),  # Orange
    ]

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

    # Update layout with dark theme styling
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

    # Customize axes for better readability in dark theme
    fig.update_xaxes(
        showgrid=True,
        gridwidth=0.5,
        gridcolor="rgba(80,80,80,0.5)",
        zeroline=False,
        title_font=dict(color="#FFFFFF"),
        tickfont=dict(color="#FFFFFF"),
    )

    fig.update_yaxes(
        title="Price",
        showgrid=True,
        gridwidth=0.5,
        gridcolor="rgba(80,80,80,0.5)",
        zeroline=False,
        title_font=dict(color="#FFFFFF"),
        tickfont=dict(color="#FFFFFF"),
    )

    return fig

