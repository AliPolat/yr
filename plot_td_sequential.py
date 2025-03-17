import plotly.graph_objects as go
from plotly.subplots import make_subplots

def plot_td_sequential(data, ticker="AAPL"):
    """Create a Plotly candlestick chart with TD Sequential indicators

    Places setup numbers above candles and countdown numbers below candles
    Highlights 9s in setups and 13s in countdowns
    Displays setup support and resistance lines
    """

    fig = make_subplots(rows=1, cols=1, shared_xaxes=True)

    # Add candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            name="Price",
        )
    )

    # Add buy setup numbers (green, above candles)
    buy_setup_data = data[data["buy_setup"] > 0].copy()
    if not buy_setup_data.empty:
        fig.add_trace(
            go.Scatter(
                x=buy_setup_data.index,
                y=buy_setup_data["High"]
                + (buy_setup_data["High"] * 0.001),  # Just above the high
                mode="text",
                text=buy_setup_data["buy_setup"].apply(
                    lambda x: f"<b>{x}</b>" if x == 9 else str(x)
                ),
                textposition="top right",
                textfont=dict(
                    color="green",
                    size=buy_setup_data["buy_setup"].apply(
                        lambda x: 14 if x == 9 else 10
                    ),
                ),
                name="Buy Setup",
                hoverinfo="none",
            )
        )

    # Add sell setup numbers (red, above candles)
    sell_setup_data = data[data["sell_setup"] > 0].copy()
    if not sell_setup_data.empty:
        fig.add_trace(
            go.Scatter(
                x=sell_setup_data.index,
                y=sell_setup_data["High"]
                + (sell_setup_data["High"] * 0.001),  # Just above the high
                mode="text",
                text=sell_setup_data["sell_setup"].apply(
                    lambda x: f"<b>{x}</b>" if x == 9 else str(x)
                ),
                textposition="top left",
                textfont=dict(
                    color="red",
                    size=sell_setup_data["sell_setup"].apply(
                        lambda x: 14 if x == 9 else 10
                    ),
                ),
                name="Sell Setup",
                hoverinfo="none",
            )
        )

    # Add buy countdown numbers (green, clearly below candles)
    buy_countdown_data = data[data["buy_countdown"] > 0].copy()
    if not buy_countdown_data.empty:
        fig.add_trace(
            go.Scatter(
                x=buy_countdown_data.index,
                # Below the low for visibility
                y=buy_countdown_data["Low"] - (buy_countdown_data["Low"] * 0.004),
                mode="text",
                text=buy_countdown_data["buy_countdown"].apply(
                    lambda x: f"<b>{x}</b>" if x == 13 else str(x)
                ),
                textposition="bottom center",
                textfont=dict(
                    color="green",
                    size=buy_countdown_data["buy_countdown"].apply(
                        lambda x: 14 if x == 13 else 10
                    ),
                ),
                name="Buy Countdown",
                hoverinfo="none",
            )
        )

    # Add sell countdown numbers (red, clearly below candles)
    sell_countdown_data = data[data["sell_countdown"] > 0].copy()
    if not sell_countdown_data.empty:
        fig.add_trace(
            go.Scatter(
                x=sell_countdown_data.index,
                # Further below the low for better separation from buy countdown
                y=sell_countdown_data["Low"] - (sell_countdown_data["Low"] * 0.008),
                mode="text",
                text=sell_countdown_data["sell_countdown"].apply(
                    lambda x: f"<b>{x}</b>" if x == 13 else str(x)
                ),
                textposition="bottom center",
                textfont=dict(
                    color="red",
                    size=sell_countdown_data["sell_countdown"].apply(
                        lambda x: 14 if x == 13 else 10
                    ),
                ),
                name="Sell Countdown",
                hoverinfo="none",
            )
        )

    # Add visual markers for completed setups (9)
    completed_buy_setups = data[data["buy_setup"] == 9].index
    for date in completed_buy_setups:
        # Add triangle marker for buy setup completion
        fig.add_trace(
            go.Scatter(
                x=[date],
                y=[data.loc[date, "Low"] * 0.99],
                mode="markers",
                marker=dict(
                    symbol="triangle-up",
                    size=12,
                    color="green",
                    line=dict(width=1, color="darkgreen"),
                ),
                name="Buy Setup Complete",
                legendgroup="Buy Setup Complete",
                showlegend=(
                    date == completed_buy_setups[0]
                    if len(completed_buy_setups) > 0
                    else True
                ),
                hoverinfo="text",
                hovertext=f"Buy Setup Complete on {date.strftime('%Y-%m-%d')}",
            )
        )

    completed_sell_setups = data[data["sell_setup"] == 9].index
    for date in completed_sell_setups:
        # Add triangle marker for sell setup completion
        fig.add_trace(
            go.Scatter(
                x=[date],
                y=[data.loc[date, "High"] * 1.01],
                mode="markers",
                marker=dict(
                    symbol="triangle-down",
                    size=12,
                    color="red",
                    line=dict(width=1, color="darkred"),
                ),
                name="Sell Setup Complete",
                legendgroup="Sell Setup Complete",
                showlegend=(
                    date == completed_sell_setups[0]
                    if len(completed_sell_setups) > 0
                    else True
                ),
                hoverinfo="text",
                hovertext=f"Sell Setup Complete on {date.strftime('%Y-%m-%d')}",
            )
        )

    # Add markers for completed countdowns (13)
    completed_buy_countdowns = data[data["buy_countdown"] == 13].index
    for date in completed_buy_countdowns:
        # Add star marker for buy countdown completion
        fig.add_trace(
            go.Scatter(
                x=[date],
                y=[data.loc[date, "Low"] * 0.97],
                mode="markers",
                marker=dict(
                    symbol="star",
                    size=16,
                    color="green",
                    line=dict(width=1, color="darkgreen"),
                ),
                name="Buy Countdown Complete",
                legendgroup="Buy Countdown Complete",
                showlegend=(
                    date == completed_buy_countdowns[0]
                    if len(completed_buy_countdowns) > 0
                    else True
                ),
                hoverinfo="text",
                hovertext=f"Buy Countdown Complete on {date.strftime('%Y-%m-%d')}",
            )
        )

    completed_sell_countdowns = data[data["sell_countdown"] == 13].index
    for date in completed_sell_countdowns:
        # Add star marker for sell countdown completion
        fig.add_trace(
            go.Scatter(
                x=[date],
                y=[data.loc[date, "High"] * 1.03],
                mode="markers",
                marker=dict(
                    symbol="star",
                    size=16,
                    color="red",
                    line=dict(width=1, color="darkred"),
                ),
                name="Sell Countdown Complete",
                legendgroup="Sell Countdown Complete",
                showlegend=(
                    date == completed_sell_countdowns[0]
                    if len(completed_sell_countdowns) > 0
                    else True
                ),
                hoverinfo="text",
                hovertext=f"Sell Countdown Complete on {date.strftime('%Y-%m-%d')}",
            )
        )

    # Add setup support lines
    setup_support_data = data[data["setup_support"].notnull()].copy()
    if not setup_support_data.empty:
        for idx, row in setup_support_data.iterrows():
            # Calculate how far to extend the support line (10 bars forward)
            extension_length = 10
            current_index_position = data.index.get_loc(idx)
            if current_index_position + extension_length < len(data.index):
                end_idx = data.index[current_index_position + extension_length]
            else:
                end_idx = data.index[-1]

            # Draw the support line
            fig.add_shape(
                type="line",
                x0=idx,
                y0=row["setup_support"],
                x1=end_idx,
                y1=row["setup_support"],
                line=dict(
                    color="green",
                    width=1.5,
                    dash="dash",
                ),
                opacity=0.7,
            )

            # Add annotation for setup support

            fig.add_annotation(
                x=idx,
                y=row["setup_support"],
                text="Support",
                showarrow=True,
                arrowhead=1,
                ax=40,
                ay=20,
                font=dict(color="green", size=10),
                bgcolor="rgba(255, 255, 255, 0.7)",
                bordercolor="green",
                borderwidth=1,
                borderpad=4,
            )

    # Add setup resistance lines
    setup_resistance_data = data[data["setup_resistance"].notnull()].copy()
    if not setup_resistance_data.empty:
        for idx, row in setup_resistance_data.iterrows():
            # Calculate how far to extend the resistance line (10 bars forward)
            extension_length = 10
            current_index_position = data.index.get_loc(idx)
            if current_index_position + extension_length < len(data.index):
                end_idx = data.index[current_index_position + extension_length]
            else:
                end_idx = data.index[-1]

            # Draw the resistance line
            fig.add_shape(
                type="line",
                x0=idx,
                y0=row["setup_resistance"],
                x1=end_idx,
                y1=row["setup_resistance"],
                line=dict(
                    color="red",
                    width=1.5,
                    dash="dash",
                ),
                opacity=0.7,
            )

            # Add annotation for setup resistance
            fig.add_annotation(
                x=idx,
                y=row["setup_resistance"],
                text="Resistance",
                showarrow=True,
                arrowhead=1,
                ax=-40,
                ay=-20,
                font=dict(color="red", size=10),
                bgcolor="rgba(255, 255, 255, 0.7)",
                bordercolor="red",
                borderwidth=1,
                borderpad=4,
            )

    # Update layout
    fig.update_layout(
        title=f"TD Sequential Indicator for {ticker}",
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        height=600,
        width=1000,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )

    return fig
