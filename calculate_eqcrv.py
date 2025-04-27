import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import yfinance as yf


def apply_simple_strategy(
    data,
    initial_capital=100000,
    strategy_type="dabak",
    fast_period=20,
    slow_period=50,
):
    """
    Apply a simple trading strategy to the data

    Parameters:
    -----------
    data : pd.DataFrame
        Stock data with OHLCV columns
    initial_capital : float
        Initial capital to start trading with
    strategy_type : str
        Type of strategy to apply (default: "sma_crossover")
    fast_period : int
        Fast moving average period
    slow_period : int
        Slow moving average period

    Returns:
    --------
    pd.DataFrame: DataFrame with trading results
    """
    # Create a copy of the dataframe to avoid modifying the original
    df = data.copy()

    # Apply strategy based on type
    if strategy_type == "sma_crossover":
        # Calculate simple moving averages
        df["SMA_Fast"] = df["close"].rolling(window=fast_period).mean()
        df["SMA_Slow"] = df["close"].rolling(window=slow_period).mean()

        # Generate signals (1 = buy, -1 = sell, 0 = hold)
        df["Signal"] = 0
        df.loc[df["SMA_Fast"] > df["SMA_Slow"], "Signal"] = 1
        df.loc[df["SMA_Fast"] < df["SMA_Slow"], "Signal"] = -1

        # Calculate position changes
        df["Position"] = df["Signal"].shift(
            1
        )  # Previous day's signal determines today's position
        df["Position"] = df["Position"].fillna(0)  # No position on first day

    elif strategy_type == "mean_reversion":
        # Simple mean reversion strategy
        lookback = fast_period
        df["SMA"] = df["close"].rolling(window=lookback).mean()
        df["SD"] = df["close"].rolling(window=lookback).std()

        # Calculate z-score
        df["ZScore"] = (df["close"] - df["SMA"]) / df["SD"]

        # Generate signals
        df["Signal"] = 0
        df.loc[df["ZScore"] < -1.5, "Signal"] = (
            1  # Buy when price is significantly below mean
        )
        df.loc[df["ZScore"] > 1.5, "Signal"] = (
            -1
        )  # Sell when price is significantly above mean

        # Calculate position changes
        df["Position"] = df["Signal"].shift(1)
        df["Position"] = df["Position"].fillna(0)

    elif strategy_type == "dabak":
        # Generate signals based on the dabak strategy rules
        df["Signal"] = 0

        # BUY conditions: Close > sell_tdst_level AND Close > sell_setup_stop AND Close > sell_countdown_stop
        buy_condition = (
            (df["close"] > df["sell_tdst_level"])
            & (df["close"] > df["sell_setup_stop"])
            & (df["close"] > df["sell_countdown_stop"])
        )

        # SELL conditions: Any of (Open, Low, High, Close) < any of (buy_tdst_level, buy_setup_stop, buy_countdown_stop)
        sell_condition_open = (
            (df["open"] < df["buy_tdst_level"])
            | (df["open"] < df["buy_setup_stop"])
            | (df["open"] < df["buy_countdown_stop"])
        )

        sell_condition_low = (
            (df["low"] < df["buy_tdst_level"])
            | (df["low"] < df["buy_setup_stop"])
            | (df["low"] < df["buy_countdown_stop"])
        )

        sell_condition_high = (
            (df["high"] < df["buy_tdst_level"])
            | (df["high"] < df["buy_setup_stop"])
            | (df["high"] < df["buy_countdown_stop"])
        )

        sell_condition_close = (
            (df["close"] < df["buy_tdst_level"])
            | (df["close"] < df["buy_setup_stop"])
            | (df["close"] < df["buy_countdown_stop"])
        )

        sell_condition = (
            sell_condition_open
            | sell_condition_low
            | sell_condition_high
            | sell_condition_close
        )

        # Apply signals
        df.loc[buy_condition, "Signal"] = 1
        df.loc[sell_condition, "Signal"] = -1

        # If both buy and sell conditions are met, prioritize sell signal
        df.loc[buy_condition & sell_condition, "Signal"] = -1

        # Calculate position changes
        df["Position"] = df["Signal"].shift(1)
        df["Position"] = df["Position"].fillna(0)

    else:
        # Default to buy and hold
        df["Position"] = 1

    # Calculate returns based on strategy
    df["Market_Return"] = df["close"].pct_change()  # Market returns
    df["Strategy_Return"] = df["Position"] * df["Market_Return"]  # Strategy returns

    # Calculate equity and P&L
    df["Equity"] = initial_capital * (1 + df["Strategy_Return"].cumsum())
    df["Daily_PnL"] = initial_capital * df["Strategy_Return"]
    df["Daily_Return"] = df["Strategy_Return"] * 100
    df["Cumulative_Return"] = (df["Equity"] / initial_capital - 1) * 100

    # Calculate drawdowns
    df["Peak"] = df["Equity"].cummax()
    df["Drawdown"] = (df["Equity"] / df["Peak"] - 1) * 100

    return df


def calculate_performance_metrics(df, initial_capital=None):
    """
    Calculate key performance metrics from trading results

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with trading results
    initial_capital : float, optional
        Initial capital amount. If None, will use first equity value.

    Returns:
    --------
    dict: Dictionary with performance metrics
    """
    # Extract metrics
    if initial_capital is None:
        initial_capital = df["Equity"].iloc[0]
    final_capital = df["Equity"].iloc[-1]
    total_return = ((final_capital / initial_capital) - 1) * 100
    max_drawdown = df["Drawdown"].min()
    daily_returns = df["Daily_Return"].dropna()

    # Trading days per year (approximately)
    trading_days_per_year = 252

    # Calculate annualized metrics
    annualized_return = (1 + daily_returns.mean() / 100) ** trading_days_per_year - 1
    annualized_volatility = daily_returns.std() * np.sqrt(trading_days_per_year)
    sharpe_ratio = (
        (annualized_return / annualized_volatility) if annualized_volatility != 0 else 0
    )

    # Calculate win rate
    winning_days = sum(df["Daily_PnL"] > 0)
    total_days = len(df) - 1
    win_rate = (winning_days / total_days) * 100 if total_days > 0 else 0

    # Return metrics as dictionary
    metrics = {
        "Initial Capital": f"${initial_capital:,.2f}",
        "Final Capital": f"${final_capital:,.2f}",
        "Total Return": f"{total_return:.2f}%",
        "Max Drawdown": f"{max_drawdown:.2f}%",
        "Win Rate": f"{win_rate:.2f}%",
        "Annualized Return": f"{annualized_return*100:.2f}%",
        "Annualized Volatility": f"{annualized_volatility*100:.2f}%",
        "Sharpe Ratio": f"{sharpe_ratio:.2f}",
    }

    return metrics


def create_performance_plots(df, metrics, title=None):
    """
    Create performance visualization plots

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with trading results
    metrics : dict
        Dictionary with performance metrics
    title : str
        Title for the plot

    Returns:
    --------
    tuple: (equity_fig, metrics_fig) - Plotly figure objects
    """

    # Reset index if Date is in the index
    if isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index()
        date_col = "Date"
    else:
        date_col = df.columns[0]  # Assume first column is date

    # Create figure with equity and drawdown subplots
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        subplot_titles=("Equity Curve", "Strategy Position", "Drawdown (%)"),
        row_heights=[0.5, 0.2, 0.3],
    )

    # Add equity curve trace
    fig.add_trace(
        go.Scatter(
            x=df[date_col] if date_col in df.columns else df.index,
            y=df["Equity"],
            name="Equity",
            line=dict(color="blue"),
            hovertemplate="Date: %{x}<br>Equity: $%{y:,.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # Add position trace
    fig.add_trace(
        go.Scatter(
            x=df[date_col] if date_col in df.columns else df.index,
            y=df["Position"],
            name="Position",
            line=dict(color="green"),
            hovertemplate="Date: %{x}<br>Position: %{y}<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # Add drawdown trace
    fig.add_trace(
        go.Scatter(
            x=df[date_col] if date_col in df.columns else df.index,
            y=df["Drawdown"],
            name="Drawdown",
            line=dict(color="red"),
            fill="tozeroy",
            hovertemplate="Date: %{x}<br>Drawdown: %{y:.2f}%<extra></extra>",
        ),
        row=3,
        col=1,
    )

    # Update layout
    fig.update_layout(
        title={
            "text": title or "Trading Performance: Equity Curve and Drawdown Analysis",
            "y": 0.95,
            "x": 0.5,
            "xanchor": "center",
            "yanchor": "top",
            "font": dict(size=18),
        },
        height=900,
        width=1000,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=40, t=80, b=20),
    )

    # Update axes formats
    fig.update_yaxes(
        title_text="Account Value ($)", row=1, col=1, tickprefix="$", tickformat=",.0f"
    )
    fig.update_yaxes(title_text="Position", row=2, col=1)
    fig.update_yaxes(title_text="Drawdown (%)", row=3, col=1, ticksuffix="%")

    # Create a separate figure for the metrics table
    metrics_fig = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=["<b>Metric</b>", "<b>Value</b>"],
                    font=dict(size=14, color="red"),
                    fill_color="royalblue",
                    align="center",
                    height=30,
                ),
                cells=dict(
                    values=[list(metrics.keys()), list(metrics.values())],
                    font=dict(size=13),
                    fill_color=[["blue", "red"] * int(len(metrics) / 2 + 0.5)],
                    align=["left", "right"],
                    height=25,
                ),
            )
        ]
    )

    metrics_fig.update_layout(
        title="Performance Metrics",
        height=400,
        width=600,
        margin=dict(l=20, r=20, t=40, b=20),
    )

    return fig, metrics_fig
