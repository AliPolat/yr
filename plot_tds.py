import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_tdsequential(df, stock_name=None, window=100):
    """
    Plot TD Sequential with TDST levels (buy=resistance, sell=support)
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

    # --- TDST LEVELS ---
    # Buy TDST (resistance) - Red dashed line
    if "buy_tdst_level" in plot_df:
        fig.add_trace(
            go.Scatter(
                x=plot_df.index,
                y=plot_df["buy_tdst_level"],
                mode="lines",
                line=dict(color="rgba(255, 0, 0, 0.5)", width=1, dash="dot"),
                name="Buy TDST (Resistance)",
                hoverinfo="y",
            )
        )

    # Sell TDST (support) - Green dashed line
    if "sell_tdst_level" in plot_df:
        fig.add_trace(
            go.Scatter(
                x=plot_df.index,
                y=plot_df["sell_tdst_level"],
                mode="lines",
                line=dict(color="rgba(0, 255, 0, 0.5)", width=1, dash="dot"),
                name="Sell TDST (Support)",
                hoverinfo="y",
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
