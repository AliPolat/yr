import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_tdsequential(df, stock_name=None, window=100):
    """
    Plot TD Sequential with BREAKING TDST lines (discontinuous when levels change)
    - Buy TDST (resistance) = Red dashed line (breaks when level changes/inactive)
    - Sell TDST (support) = Green dashed line (breaks when level changes/inactive)
    """
    # Data preparation
    plot_df = df.iloc[-window:] if len(df) > window else df.copy()

    # Create figure with dark theme
    fig = make_subplots(rows=1, cols=1)
    fig.update_layout(template="plotly_dark")

    # Add candlesticks
    fig.add_trace(
        go.Candlestick(
            x=plot_df.index,
            open=plot_df["open"],
            high=plot_df["high"],
            low=plot_df["low"],
            close=plot_df["close"],
            name="Price",
        )
    )

    # --- DISCONTINUOUS TDST LEVELS ---
    def create_breaking_segments(series):
        """Create line segments that break when value changes or becomes NaN"""
        segments = []
        current_segment = []
        prev_val = None

        for idx, val in series.items():
            # Break conditions:
            # 1. Value changed
            # 2. Became NaN (inactive)
            # 3. Previous was NaN (new activation)
            if (
                (val != prev_val and not (pd.isna(val) and pd.isna(prev_val)))
                or (pd.isna(val) and not pd.isna(prev_val))
                or (not pd.isna(val) and pd.isna(prev_val))
            ):
                if current_segment:
                    segments.append(current_segment)
                current_segment = []

            if not pd.isna(val):
                current_segment.append((idx, val))
            prev_val = val

        if current_segment:
            segments.append(current_segment)

        return segments

    # Buy TDST (resistance) - Red dashed
    if "buy_tdst_level" in plot_df:
        buy_segments = create_breaking_segments(plot_df["buy_tdst_level"])
        for seg_num, segment in enumerate(buy_segments):
            x_vals, y_vals = zip(*segment)
            fig.add_trace(
                go.Scatter(
                    x=x_vals,
                    y=y_vals,
                    mode="lines",
                    line=dict(color="rgba(255, 80, 80, 0.8)", width=1.5, dash="dot"),
                    name="Buy TDST" if seg_num == 0 else None,
                    showlegend=seg_num == 0,
                    hoverinfo="y",
                    hovertemplate="Resistance: %{y:.2f}<extra></extra>",
                )
            )

    # Sell TDST (support) - Green dashed
    if "sell_tdst_level" in plot_df:
        sell_segments = create_breaking_segments(plot_df["sell_tdst_level"])
        for seg_num, segment in enumerate(sell_segments):
            x_vals, y_vals = zip(*segment)
            fig.add_trace(
                go.Scatter(
                    x=x_vals,
                    y=y_vals,
                    mode="lines",
                    line=dict(color="rgba(80, 255, 80, 0.8)", width=1.5, dash="dot"),
                    name="Sell TDST" if seg_num == 0 else None,
                    showlegend=seg_num == 0,
                    hoverinfo="y",
                    hovertemplate="Support: %{y:.2f}<extra></extra>",
                )
            )

    # --- TD Sequential Annotations ---
    price_range = plot_df["high"].max() - plot_df["low"].min()
    setup_offset = price_range * 0.02
    countdown_offset = price_range * 0.02
    signal_offset = price_range * 0.05

    # Track last countdown to avoid duplicates
    last_buy_countdown = None
    last_sell_countdown = None

    for i, row in plot_df.iterrows():
        # Setup Numbers (all shown)
        if row["buy_setup"] > 0:
            fig.add_annotation(
                x=i,
                y=row["high"] + setup_offset,
                text=str(int(row["buy_setup"])),
                font=dict(color="lime", size=10 + min(2, row["buy_setup"] - 1)),
                showarrow=False,
            )
            if row["buy_setup"] == 9 and row.get("perfect_buy_9", 0) == 1:
                fig.add_annotation(
                    x=i,
                    y=row["high"] + signal_offset,
                    text="BUY 9",
                    bgcolor="rgba(0,168,107,0.5)",
                    font=dict(color="white", size=12),
                    showarrow=True,
                    arrowhead=2,
                )

        if row["sell_setup"] > 0:
            fig.add_annotation(
                x=i,
                y=row["high"] + setup_offset,
                text=str(int(row["sell_setup"])),
                font=dict(color="red", size=10 + min(2, row["sell_setup"] - 1)),
                showarrow=False,
            )
            if row["sell_setup"] == 9 and row.get("perfect_sell_9", 0) == 1:
                fig.add_annotation(
                    x=i,
                    y=row["high"] + signal_offset,
                    text="SELL 9",
                    bgcolor="rgba(220,39,39,0.5)",
                    font=dict(color="white", size=12),
                    showarrow=True,
                    arrowhead=2,
                )

        # Countdown Numbers (first occurrence only)
        if row["buy_countdown"] > 0 and row["buy_countdown"] != last_buy_countdown:
            fig.add_annotation(
                x=i,
                y=row["low"] - countdown_offset,
                text=str(int(row["buy_countdown"])),
                font=dict(color="lime", size=10 + min(2, row["buy_countdown"] // 5)),
                showarrow=False,
            )
            if row["buy_countdown"] == 13 and row.get("perfect_buy_13", 0) == 1:
                fig.add_annotation(
                    x=i,
                    y=row["low"] - signal_offset,
                    text="BUY 13",
                    bgcolor="rgba(0,168,107,0.5)",
                    font=dict(color="white", size=12),
                    showarrow=True,
                    arrowhead=2,
                )
            last_buy_countdown = row["buy_countdown"]

        if row["sell_countdown"] > 0 and row["sell_countdown"] != last_sell_countdown:
            fig.add_annotation(
                x=i,
                y=row["low"] - countdown_offset,
                text=str(int(row["sell_countdown"])),
                font=dict(color="red", size=10 + min(2, row["sell_countdown"] // 5)),
                showarrow=False,
            )
            if row["sell_countdown"] == 13 and row.get("perfect_sell_13", 0) == 1:
                fig.add_annotation(
                    x=i,
                    y=row["low"] - signal_offset,
                    text="SELL 13",
                    bgcolor="rgba(220,39,39,0.5)",
                    font=dict(color="white", size=12),
                    showarrow=True,
                    arrowhead=2,
                )
            last_sell_countdown = row["sell_countdown"]

    # Layout enhancements
    fig.update_layout(
        title=f"TD Sequential {' - ' + stock_name if stock_name else ''}",
        height=800,
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, itemsizing="constant"),
    )

    return fig
