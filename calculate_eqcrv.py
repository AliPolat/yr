import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


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
        Type of strategy to apply (default: "dabak")
    fast_period : int
        Fast moving average period (used for SMA and mean reversion strategies)
    slow_period : int
        Slow moving average period (used for SMA strategy)

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

        # Generate raw signals (1 = buy, -1 = sell, 0 = hold)
        df["Raw_Signal"] = 0
        df.loc[df["SMA_Fast"] > df["SMA_Slow"], "Raw_Signal"] = 1
        df.loc[df["SMA_Fast"] < df["SMA_Slow"], "Raw_Signal"] = -1

    elif strategy_type == "mean_reversion":
        # Simple mean reversion strategy
        lookback = fast_period
        df["SMA"] = df["close"].rolling(window=lookback).mean()
        df["SD"] = df["close"].rolling(window=lookback).std()

        # Calculate z-score
        df["ZScore"] = (df["close"] - df["SMA"]) / df["SD"]

        # Generate raw signals
        df["Raw_Signal"] = 0
        df.loc[df["ZScore"] < -1.5, "Raw_Signal"] = (
            1  # Buy when price is significantly below mean
        )
        df.loc[df["ZScore"] > 1.5, "Raw_Signal"] = (
            -1
        )  # Sell when price is significantly above mean

    elif strategy_type == "dabak":
        # Check if required columns exist in the dataframe
        required_columns = [
            "sell_tdst_level",
            "sell_setup_stop",
            "sell_countdown_stop",
            "buy_tdst_level",
            "buy_setup_stop",
            "buy_countdown_stop",
        ]
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Required column '{col}' not found in dataframe")

        # Create filled versions of threshold columns (using previous day's values)
        # This prevents look-ahead bias when generating signals
        for col in required_columns:
            df[f"{col}_filled"] = df[col].shift(1).fillna(0)

        # Generate raw signals for dabak strategy
        df["Raw_Signal"] = 0

        # BUY conditions: Close must be above ALL sell thresholds
        # Only consider non-zero thresholds to avoid false positives
        buy_condition = (
            (df["close"] > df["buy_tdst_level_filled"])
            & (df["close"] > df["sell_setup_stop_filled"])
            & (df["close"] > df["sell_countdown_stop_filled"])
            & (
                (df["buy_tdst_level_filled"] > 0)
                | (df["sell_setup_stop_filled"] > 0)
                | (df["sell_countdown_stop_filled"] > 0)
            )
        )

        # SELL conditions: Any price point (open, high, low, close) breaking
        # below ANY buy threshold will trigger a sell
        sell_condition_close = (
            (df["close"] < df["sell_tdst_level_filled"])
            | (df["close"] < df["buy_setup_stop_filled"])
            | (df["close"] < df["buy_countdown_stop_filled"])
        )

        sell_condition_open = (
            (df["open"] < df["sell_tdst_level_filled"])
            | (df["open"] < df["buy_setup_stop_filled"])
            | (df["open"] < df["buy_countdown_stop_filled"])
        )

        sell_condition_low = (
            (df["low"] < df["sell_tdst_level_filled"])
            | (df["low"] < df["buy_setup_stop_filled"])
            | (df["low"] < df["buy_countdown_stop_filled"])
        )

        sell_condition_high = (
            (df["high"] < df["sell_tdst_level_filled"])
            | (df["high"] < df["buy_setup_stop_filled"])
            | (df["high"] < df["buy_countdown_stop_filled"])
        )

        # Final sell condition - any price point breaking below ANY threshold
        sell_condition = (
            sell_condition_open
            | sell_condition_low
            | sell_condition_high
            | sell_condition_close
        )

        # Apply raw signals - these are the daily buy/sell signals without position holding
        df.loc[buy_condition, "Raw_Signal"] = 1
        df.loc[sell_condition, "Raw_Signal"] = -1

        # If both buy and sell conditions are met, prioritize sell signal
        df.loc[buy_condition & sell_condition, "Raw_Signal"] = -1

    else:
        # Default to buy and hold
        df["Raw_Signal"] = 1

    # === NEW CODE: Implement position holding until opposite signal ===
    # This applies to all strategy types

    # Initialize columns for position tracking
    df["Signal"] = 0  # Final signal after position holding logic
    df["Position"] = 0  # Position based on signals (1 = long, -1 = short/flat)

    # Loop through the dataframe to implement position holding
    # Starting with -1 position (flat/cash) as per requirement
    current_position = -1  # Start with flat position (cash)

    for i in range(len(df)):
        raw_signal = df.iloc[i]["Raw_Signal"]

        # Only change position when we get an opposite signal or when we have no position
        if (raw_signal == 1 and current_position == -1) or (
            raw_signal == -1 and current_position == 1
        ):
            current_position = raw_signal
            df.iloc[i, df.columns.get_loc("Signal")] = raw_signal

        # Update position for this row
        df.iloc[i, df.columns.get_loc("Position")] = current_position

    # Calculate market returns
    df["Market_Return"] = df["close"].pct_change()  # Market returns

    # Calculate strategy returns - when position is 1, apply market returns, when -1 (flat/cash), returns are 0
    df["Strategy_Return"] = 0.0  # Initialize with zeros (cash position)
    df.loc[df["Position"] == 1, "Strategy_Return"] = df.loc[
        df["Position"] == 1, "Market_Return"
    ]
    # Note: When Position is -1, Strategy_Return remains 0 (cash position, no market exposure)

    # Calculate equity and P&L
    df["Equity"] = initial_capital * (1 + df["Strategy_Return"].cumsum())
    df["Daily_PnL"] = initial_capital * df["Strategy_Return"]
    df["Daily_Return"] = df["Strategy_Return"] * 100
    df["Cumulative_Return"] = (df["Equity"] / initial_capital - 1) * 100

    # Calculate drawdowns
    df["Peak"] = df["Equity"].cummax()
    df["Drawdown"] = (df["Equity"] / df["Peak"] - 1) * 100

    # Clean up temporary columns if needed
    # df.drop([col for col in df.columns if col.endswith('_filled')], axis=1, inplace=True)

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
