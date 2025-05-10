import streamlit as st
import pandas as pd
from datetime import date
from models import User, StockAsset, create_tables
import json
import os


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


def display_portfolio_management(t):
    """Display the database management UI based on selected language"""
    st.title(t.get("portfolio_management_title", "Portfolio Management"))

    # Create tab for each table
    tab_user, tab_stock = st.tabs(
        [
            t.get("tab_user_management", "User Management"),
            t.get("tab_stock_management", "Stock/Asset Management"),
        ]
    )

    # User Management Tab
    with tab_user:
        display_user_management(t)

    # Stock/Asset Management Tab
    with tab_stock:
        display_stock_management(t)


def display_user_management(t):
    """Display user management UI"""
    st.header(t.get("user_management", "User Management"))

    # Get all users
    users = list(User.select())

    # Create dataframe for display
    if users:
        user_data = [
            {
                "ID": user.user_id,
                t.get("nick_name", "Nickname"): user.nick_name,
                t.get("real_name", "Real Name"): user.real_name,
                t.get("comment", "Comment"): user.comment or "",
            }
            for user in users
        ]
        st.dataframe(user_data, use_container_width=True)
    else:
        st.info(t.get("no_users", "No users found. Add a new user below."))

    # Form for adding new user
    with st.expander(t.get("add_user", "Add New User"), expanded=False):
        with st.form(key="add_user_form"):
            nick_name = st.text_input(t.get("nick_name", "Nickname"))
            real_name = st.text_input(t.get("real_name", "Real Name"))
            comment = st.text_area(t.get("comment", "Comment"))

            submit_button = st.form_submit_button(t.get("add_user_button", "Add User"))
            if submit_button:
                if nick_name and real_name:
                    User.create(
                        nick_name=nick_name, real_name=real_name, comment=comment
                    )
                    st.success(t.get("user_added", "User added successfully!"))
                    # st.experimental_rerun()
                else:
                    st.error(
                        t.get("required_fields", "Nickname and Real Name are required!")
                    )

    # Form for editing user
    with st.expander(t.get("edit_user", "Edit User"), expanded=False):
        user_options = {
            user.user_id: f"{user.nick_name} ({user.real_name})" for user in users
        }
        if user_options:
            selected_user_id = st.selectbox(
                t.get("select_user", "Select User to Edit"),
                options=list(user_options.keys()),
                format_func=lambda x: user_options[x],
            )

            selected_user = User.get_by_id(selected_user_id)

            with st.form(key="edit_user_form"):
                e_nick_name = st.text_input(
                    t.get("nick_name", "Nickname"), value=selected_user.nick_name
                )
                e_real_name = st.text_input(
                    t.get("real_name", "Real Name"), value=selected_user.real_name
                )
                e_comment = st.text_area(
                    t.get("comment", "Comment"), value=selected_user.comment or ""
                )

                col1, col2 = st.columns(2)
                with col1:
                    submit_button = st.form_submit_button(
                        t.get("update_user_button", "Update User")
                    )
                with col2:
                    delete_button = st.form_submit_button(
                        t.get("delete_user_button", "Delete User"),
                        type="primary",
                        help=t.get(
                            "delete_warning",
                            "This will delete the user and all associated assets!",
                        ),
                    )

                if submit_button:
                    if e_nick_name and e_real_name:
                        selected_user.nick_name = e_nick_name
                        selected_user.real_name = e_real_name
                        selected_user.comment = e_comment
                        selected_user.save()
                        st.success(t.get("user_updated", "User updated successfully!"))
                        # st.experimental_rerun()
                    else:
                        st.error(
                            t.get(
                                "required_fields",
                                "Nickname and Real Name are required!",
                            )
                        )

                if delete_button:
                    # Check if user has assets first
                    assets_count = (
                        StockAsset.select()
                        .where(StockAsset.user == selected_user)
                        .count()
                    )
                    if assets_count > 0:
                        st.error(
                            t.get(
                                "user_has_assets",
                                "User has assets! Please delete assets first.",
                            )
                        )
                    else:
                        selected_user.delete_instance()
                        st.success(t.get("user_deleted", "User deleted successfully!"))
                        # st.experimental_rerun()
        else:
            st.info(t.get("no_users_edit", "No users available to edit."))


def display_stock_management(t):
    """Display stock/asset management UI"""
    st.header(t.get("stock_management", "Stock/Asset Management"))

    # Get all users for selection
    users = list(User.select())

    if not users:
        st.warning(t.get("create_user_first", "Please create a user first!"))
        return

    # User selector
    user_options = {
        user.user_id: f"{user.nick_name} ({user.real_name})" for user in users
    }
    selected_user_id = st.selectbox(
        t.get("select_user_assets", "Select User to View Assets"),
        options=list(user_options.keys()),
        format_func=lambda x: user_options[x],
    )

    # Get assets for the selected user
    assets = list(StockAsset.select().where(StockAsset.user_id == selected_user_id))

    # Create dataframe for display
    if assets:
        asset_data = [
            {
                "ID": asset.stock_asset_id,
                t.get("code", "Code"): asset.stock_asset_code,
                t.get("name", "Name"): asset.stock_asset_name,
                t.get("buy_date", "Buy Date"): asset.buy_date.strftime("%Y-%m-%d"),
                t.get("buy_price", "Buy Price"): float(asset.buy_price),
                t.get("sell_date", "Sell Date"): (
                    asset.sell_date.strftime("%Y-%m-%d") if asset.sell_date else "-"
                ),
                t.get("sell_price", "Sell Price"): (
                    float(asset.sell_price) if asset.sell_price else "-"
                ),
                t.get("status", "Status"): asset.status,
            }
            for asset in assets
        ]
        st.dataframe(asset_data, use_container_width=True)
    else:
        st.info(
            t.get("no_assets", "No assets found for this user. Add a new asset below.")
        )

    # Form for adding new asset
    with st.expander(t.get("add_asset", "Add New Asset"), expanded=False):
        with st.form(key="add_asset_form"):
            stock_code = st.text_input(t.get("asset_code", "Asset Code"))
            stock_name = st.text_input(t.get("asset_name", "Asset Name"))
            buy_date = st.date_input(t.get("buy_date", "Buy Date"), value=date.today())
            buy_price = st.number_input(
                t.get("buy_price", "Buy Price"), min_value=0.01, value=0.01, step=0.01
            )
            sell_date = st.date_input(
                t.get("sell_date", "Sell Date (optional)"), value=None
            )
            sell_price = st.number_input(
                t.get("sell_price", "Sell Price (optional)"),
                min_value=0.0,
                value=0.0,
                step=0.01,
            )

            status_options = ["Position", "Cash"]
            status = st.selectbox(
                t.get("status", "Status"),
                options=status_options,
                index=0 if sell_date == None else 1,
            )

            submit_button = st.form_submit_button(
                t.get("add_asset_button", "Add Asset")
            )
            if submit_button:
                if stock_code and stock_name and buy_price > 0:
                    # Convert empty sell date and price to None
                    sell_date_value = (
                        sell_date if sell_date and sell_date > buy_date else None
                    )
                    sell_price_value = sell_price if sell_price > 0 else None

                    # Set status based on sell information
                    if sell_date_value and sell_price_value:
                        status = "Cash"

                    # Create the asset
                    StockAsset.create(
                        user_id=selected_user_id,
                        stock_asset_code=stock_code,
                        stock_asset_name=stock_name,
                        buy_date=buy_date,
                        buy_price=buy_price,
                        sell_date=sell_date_value,
                        sell_price=sell_price_value,
                        status=status,
                    )

                    st.success(t.get("asset_added", "Asset added successfully!"))
                    # st.experimental_rerun()
                else:
                    st.error(
                        t.get(
                            "required_asset_fields",
                            "Code, Name, and Buy Price are required!",
                        )
                    )

    # Form for editing/deleting asset
    if assets:
        with st.expander(t.get("edit_asset", "Edit/Delete Asset"), expanded=False):
            asset_options = {
                asset.stock_asset_id: f"{asset.stock_asset_code} - {asset.stock_asset_name}"
                for asset in assets
            }
            selected_asset_id = st.selectbox(
                t.get("select_asset", "Select Asset to Edit"),
                options=list(asset_options.keys()),
                format_func=lambda x: asset_options[x],
            )

            selected_asset = StockAsset.get_by_id(selected_asset_id)

            with st.form(key="edit_asset_form"):
                e_stock_code = st.text_input(
                    t.get("asset_code", "Asset Code"),
                    value=selected_asset.stock_asset_code,
                )
                e_stock_name = st.text_input(
                    t.get("asset_name", "Asset Name"),
                    value=selected_asset.stock_asset_name,
                )
                e_buy_date = st.date_input(
                    t.get("buy_date", "Buy Date"), value=selected_asset.buy_date
                )
                e_buy_price = st.number_input(
                    t.get("buy_price", "Buy Price"),
                    min_value=0.01,
                    value=float(selected_asset.buy_price),
                    step=0.01,
                )
                e_sell_date = st.date_input(
                    t.get("sell_date", "Sell Date (optional)"),
                    value=selected_asset.sell_date,
                )
                e_sell_price = st.number_input(
                    t.get("sell_price", "Sell Price (optional)"),
                    min_value=0.0,
                    value=(
                        float(selected_asset.sell_price)
                        if selected_asset.sell_price
                        else 0.0
                    ),
                    step=0.01,
                )

                status_options = ["Position", "Cash"]
                e_status = st.selectbox(
                    t.get("status", "Status"),
                    options=status_options,
                    index=status_options.index(selected_asset.status),
                )

                col1, col2 = st.columns(2)
                with col1:
                    update_button = st.form_submit_button(
                        t.get("update_asset_button", "Update Asset")
                    )
                with col2:
                    delete_button = st.form_submit_button(
                        t.get("delete_asset_button", "Delete Asset"), type="primary"
                    )

                if update_button:
                    if e_stock_code and e_stock_name and e_buy_price > 0:
                        # Convert empty sell date and price to None
                        e_sell_date_value = (
                            e_sell_date
                            if e_sell_date and e_sell_date > e_buy_date
                            else None
                        )
                        e_sell_price_value = e_sell_price if e_sell_price > 0 else None

                        # Set status based on sell information
                        if (
                            e_sell_date_value
                            and e_sell_price_value
                            and e_status == "Position"
                        ):
                            e_status = "Cash"
                        elif (
                            not e_sell_date_value
                            and not e_sell_price_value
                            and e_status == "Cash"
                        ):
                            e_status = "Position"

                        # Update the asset
                        selected_asset.stock_asset_code = e_stock_code
                        selected_asset.stock_asset_name = e_stock_name
                        selected_asset.buy_date = e_buy_date
                        selected_asset.buy_price = e_buy_price
                        selected_asset.sell_date = e_sell_date_value
                        selected_asset.sell_price = e_sell_price_value
                        selected_asset.status = e_status
                        selected_asset.save()

                        st.success(
                            t.get("asset_updated", "Asset updated successfully!")
                        )
                        # st.experimental_rerun()
                    else:
                        st.error(
                            t.get(
                                "required_asset_fields",
                                "Code, Name, and Buy Price are required!",
                            )
                        )

                if delete_button:
                    selected_asset.delete_instance()
                    st.success(t.get("asset_deleted", "Asset deleted successfully!"))
                    # st.experimental_rerun()
