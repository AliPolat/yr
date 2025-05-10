from datetime import datetime, timedelta
import streamlit as st
import yfinance as yf
import json
import os

from calculate_tds import calculate_tdsequential
from plot_tds import plot_tdsequential
from calculate_eqcrv import (
    calculate_performance_metrics,
    apply_simple_strategy,
    create_performance_plots,
)
from models import create_tables
from portfolio_management import display_portfolio_management


def load_translations(lang):
    """Load translations from JSON file based on selected language"""
    try:
        file_path = os.path.join("translations", f"{lang}.json")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading translations: {e}")
        # Return empty dict as fallback
        return {}


def get_stock_data(ticker, start_date, end_date, interval):
    """Download stock data using yfinance and fix column names"""
    try:
        data = yf.download(ticker, start=start_date, end=end_date, interval=interval)
        # Fix column names
        data.columns = [col[0] for col in data.columns]
        return data
    except Exception as e:
        st.error(f"Error downloading data: {e}")
        return None


# Ensure database tables are created
create_tables()

# Initialize session state for language if it doesn't exist
if "language" not in st.session_state:
    st.session_state.language = "en"  # default language is English

# Create language selector in the sidebar (before any other UI elements)
langs = {"en": "English", "tr": "Türkçe"}

# Add language selection to the very top of the sidebar
selected_lang = st.sidebar.selectbox(
    "Language / Dil",
    options=list(langs.keys()),
    format_func=lambda x: langs[x],
    index=list(langs.keys()).index(st.session_state.language),
)

# Update session state if language changed
if selected_lang != st.session_state.language:
    st.session_state.language = selected_lang
    # This will trigger a rerun with the new language

# Load translations for the selected language
t = load_translations(st.session_state.language)

# Create navigation
page_options = ["TD Sequential Indicator", "Portfolio Management"]
selected_page = st.sidebar.radio(
    t.get("navigation", "Navigation"),
    options=page_options,
    format_func=lambda x: t.get(x.lower().replace(" ", "_"), x),
)

if selected_page == "Portfolio Management":
    display_portfolio_management(t)
else:
    # Set the page title
    st.title(t.get("app_title", "TD Sequential Indicator"))

    # Sidebar for stock selection
    st.sidebar.header(t.get("settings", "Settings"))
    stock_options = ["AAPL", "GOLD", "BITCOIN", "Other"]
    selected_stock_option = st.sidebar.selectbox(
        t.get("select_stock", "Select Stock/Asset"), stock_options
    )

    # If "Other" is selected, let the user input a custom stock symbol
    if selected_stock_option == "BITCOIN":
        ticker = "BTC-USD"
    elif selected_stock_option == "Other":
        ticker = st.sidebar.text_input(
            t.get("enter_stock", "Enter Stock Symbol"), "MSFT"
        )
    else:
        ticker = selected_stock_option

    # Time period selection
    period_options = [
        "3 months",
        "1 day",
        "1 week",
        "1 month",
        "6 months",
        "1 year",
        "Other",
    ]
    selected_period = st.sidebar.selectbox(
        t.get("select_period", "Select Time Period"), period_options
    )

    # If "Other" is selected, let the user input a custom period
    if selected_period == "Other":
        custom_period_days = st.sidebar.number_input(
            t.get("enter_days", "Enter Number of Days"), min_value=1, value=30
        )
        end_date = datetime.now()
        start_date = end_date - timedelta(days=custom_period_days)
    else:
        end_date = datetime.now()
        period_days = {
            "1 day": 1,
            "1 week": 7,
            "1 month": 30,
            "3 months": 90,
            "6 months": 180,
            "1 year": 365,
        }
        start_date = end_date - timedelta(days=period_days.get(selected_period, 90))

    # Interval selection
    interval_options = ["1d", "5m", "15m", "1h", "4h", "1wk", "1mo"]
    interval_names = {
        "1d": "1 Day",
        "5m": "5 Minutes",
        "15m": "15 Minutes",
        "1h": "1 Hour",
        "4h": "4 Hours",
        "1wk": "1 Week",
        "1mo": "1 Month",
    }
    selected_interval = st.sidebar.selectbox(
        t.get("select_interval", "Select Interval"),
        interval_options,
        format_func=lambda x: interval_names[x],
    )

    # Add note about intraday data limitations
    if selected_interval in ["5m", "15m", "1h", "4h"]:
        st.sidebar.info(
            t.get(
                "intraday_note",
                "Note: Intraday data (minutes/hours) is typically only available for the last 60 days. For longer periods, please use daily intervals or higher.",
            )
        )

    # Add checkboxes for display options
    display_options = st.sidebar.expander(
        t.get("display_options", "Display Options"), expanded=False
    )
    show_support_resistance = display_options.checkbox(
        t.get("show_support_resistance", "Display Support/Resistance"),
        value=True,
        help=t.get(
            "show_support_resistance_help",
            "Show support and resistance levels on the chart",
        ),
    )
    show_setup_stop_loss = display_options.checkbox(
        t.get("show_setup_stop_loss", "Display Setup Stop Loss"),
        value=True,
        help=t.get(
            "show_setup_stop_loss_help",
            "Show stop loss levels for TD Sequential setups",
        ),
    )
    show_countdown_stop_loss = display_options.checkbox(
        t.get("show_countdown_stop_loss", "Display Countdown Stop Loss"),
        value=True,
        help=t.get(
            "show_countdown_stop_loss_help",
            "Show stop loss levels for TD Sequential countdowns",
        ),
    )

    # Strategy settings
    strategy_options = st.sidebar.expander(
        t.get("strategy_options", "Strategy Options"), expanded=False
    )
    initial_capital = strategy_options.number_input(
        t.get("initial_capital", "Initial Capital"), value=100000, step=10000
    )
    strategy_types = ["dabak", "sma_crossover", "mean_reversion", "other"]
    strategy_type = strategy_options.selectbox(
        t.get("strategy_type", "Strategy Type"), strategy_types
    )

    # If "other" is selected, let the user input a custom strategy name
    if strategy_type == "other":
        custom_strategy = strategy_options.text_input(
            t.get("custom_strategy", "Enter Custom Strategy Name"), "custom_strategy"
        )
        strategy_type = custom_strategy

    # Display Analysis button (renamed from Download Data)
    if st.sidebar.button(t.get("display_analysis", "Display Analysis")):
        # Load data
        data = get_stock_data(ticker, start_date, end_date, selected_interval)

        # Display data information
        if data is not None and not data.empty:
            st.header(f"{ticker} {t.get('analysis', 'Analysis')}")
            st.write(
                f"{t.get('period', 'Period')}: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            )
            st.write(
                f"{t.get('interval', 'Interval')}: {interval_names[selected_interval]}"
            )

            # Apply TD Sequential calculation
            td_data = calculate_tdsequential(data, stock_name=ticker)

            # Apply strategy
            df_strategy = apply_simple_strategy(
                td_data,
                initial_capital=initial_capital,
                strategy_type=strategy_type,
                fast_period=20,  # Could make configurable
                slow_period=50,  # Could make configurable
            )

            # Calculate metrics
            metrics = calculate_performance_metrics(
                df_strategy, initial_capital=initial_capital
            )

            # Create visualizations
            title = f"{ticker} Trading Performance: {strategy_type.replace('_', ' ').title()} Strategy"
            equity_fig, metrics_fig = create_performance_plots(
                df_strategy, metrics, title
            )

            # Plot candlestick chart with TD Sequential indicators
            td_fig = plot_tdsequential(
                td_data,
                stock_name=ticker,
                window=1000,
                show_support_resistance=show_support_resistance,
                show_setup_stop_loss=show_setup_stop_loss,
                show_countdown_stop_loss=show_countdown_stop_loss,
            )

            # Create tabs for different views
            tab1, tab2, tab3, tab4 = st.tabs(
                [
                    t.get("tab_chart", "TD Sequential Chart"),
                    t.get("tab_data", "Data Table"),
                    t.get("tab_equity", "Equity Curve"),
                    t.get("tab_metrics", "Performance Metrics"),
                ]
            )

            with tab1:
                st.plotly_chart(td_fig, use_container_width=True)

            with tab2:
                st.dataframe(df_strategy, use_container_width=True)

            with tab3:
                st.plotly_chart(equity_fig, use_container_width=True)

            with tab4:
                st.plotly_chart(metrics_fig, use_container_width=True)
