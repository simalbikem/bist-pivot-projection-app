import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
from database import create_tables, create_user, get_credentials_dict
from config import COOKIE_KEY, BIST_STOCKS, PIVOT_METHODS, TIMEFRAMES, LOW_SAMPLE_SIZE_THRESHOLD
from data_fetcher import get_stock_data, resample_to_timeframe
from pivot_calculations import calculate_all_pivots
from database import (
    get_pivot_stats, get_confluence_zones, get_last_update_time,
    screen_by_touch_probability, screen_by_confluence,
    get_user_id, create_alert, get_alerts_for_user, delete_alert,
    set_alert_active, update_telegram_chat_id, get_telegram_chat_id,
    generate_link_code, verify_telegram_link,
    is_user_admin, get_all_users_with_stats, delete_user_and_data,
)
from notifications import send_telegram_message
from charts import plot_candlestick_with_pivots, plot_confluence_zones

st.set_page_config(page_title="BIST Pivot Projection System", layout="wide")

st.markdown(
    """
    <style>
    [data-testid="stTabs"] [role="tablist"] {
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: thin;
    }
    [data-testid="stTabs"] button[role="tab"] {
        white-space: nowrap;
    }
    @media (max-width: 480px) {
        [data-testid="stTabs"] button[role="tab"] {
            padding: 6px 8px;
            min-width: unset;
        }
        [data-testid="stTabs"] button[role="tab"] p {
            font-size: 0.72rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "tables_initialized" not in st.session_state:
    create_tables()
    st.session_state["tables_initialized"] = True

@st.cache_data(ttl=60)
def cached_get_credentials_dict():
    return get_credentials_dict()


authenticator = stauth.Authenticate(
    cached_get_credentials_dict(),
    cookie_name="bist_pivot_auth",
    cookie_key=COOKIE_KEY,
    cookie_expiry_days=7,
    auto_hash=False,  # şifreler zaten create_user() ile hashlenmiş durumda
)

try:
    authenticator.login()
except stauth.LoginError:
    authenticator.cookie_controller.delete_cookie()
    st.warning(
        "Your session has expired or your account no longer exists. "
        "Please refresh this page(F5) to log in again."
    )
    st.stop()

if st.session_state.get("authentication_status") is not True:
    st.session_state.pop("pending_link_code_display", None)

if st.session_state.get("authentication_status") is False:
    st.error("Username or password is incorrect.")
    st.stop()
elif st.session_state.get("authentication_status") is None:
    st.warning("Please log in or register below if you don't have an account.")

    with st.expander("New user? Register here"):
        with st.form("register_form"):
            reg_username = st.text_input("Username")
            reg_email = st.text_input("Email")
            reg_first_name = st.text_input("First Name")
            reg_last_name = st.text_input("Last Name")
            reg_password = st.text_input("Password", type="password")
            reg_password_confirm = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Register")

            if submitted:
                if reg_password != reg_password_confirm:
                    st.error("Passwords do not match.")
                elif not all([reg_username, reg_email, reg_first_name, reg_last_name, reg_password]):
                    st.error("Please fill in all fields.")
                else:
                    success = create_user(
                        reg_username, reg_password, reg_email, reg_first_name, reg_last_name
                    )
                    if success:
                        cached_get_credentials_dict.clear()
                        st.success("Registration successful! Please log in above.")
                    else:
                        st.error("Username or email already exists.")

    st.stop()

authenticator.logout("Logout", "sidebar")
st.sidebar.write(f"Welcome, {st.session_state['name']}!")

@st.cache_data(ttl=3600)
def cached_get_stock_data(ticker: str) -> pd.DataFrame:
    """get_stock_data 1 saat boyunca önbelleğe alınır -kullanıcı sidebar'da
    farklı seçimler yaptıkça Yahoo Finance'e tekrar tekrar istek atılmasını önler."""
    return get_stock_data(ticker)

@st.cache_data(ttl=600)
def cached_get_pivot_stats(ticker: str, timeframe: str) -> pd.DataFrame:
    """get_pivot_stats'ı 10 dakika önbelleğe alır. 
    Bu veri sadece update_data.py veya alert_checker.py çalıştığında değişir 
    -kullanıcının her sekme/widget etkileşiminde Turso'ya tekrar tekrar gitmesini önler."""
    return get_pivot_stats(ticker, timeframe)

@st.cache_data(ttl=600)
def cached_get_confluence_zones(ticker: str, timeframe: str) -> pd.DataFrame:
    return get_confluence_zones(ticker, timeframe)

@st.cache_data(ttl=600)
def cached_get_last_update_time(ticker: str, timeframe: str):
    return get_last_update_time(ticker, timeframe)

@st.cache_data(ttl=600)
def cached_screen_by_touch_probability(timeframe, method, level_name, min_touch_pct):
    return screen_by_touch_probability(timeframe, method, level_name, min_touch_pct)

@st.cache_data(ttl=600)
def cached_screen_by_confluence(timeframe, min_method_count):
    return screen_by_confluence(timeframe, min_method_count)

@st.cache_data(ttl=300)
def cached_is_user_admin(username: str) -> bool:
    return is_user_admin(username)

@st.cache_data(ttl=30)
def cached_get_telegram_chat_id(username: str):
    return get_telegram_chat_id(username)

@st.cache_data(ttl=15)
def cached_get_alerts_for_user(user_id: int) -> pd.DataFrame:
    return get_alerts_for_user(user_id)

@st.cache_data(ttl=15)
def cached_get_all_users_with_stats() -> pd.DataFrame:
    return get_all_users_with_stats()

def reconstruct_zones_from_db(df_zones: pd.DataFrame) -> list:
    zones = []
    for zone_id, group in df_zones.groupby("zone_id"):
        zones.append({
            "center": group["center"].iloc[0],
            "method_count": group["method_count"].iloc[0],
            "contributors": [
                {"method": row["method"], "level": row["level_name"], "value": row["value"]}
                for _, row in group.iterrows()
            ],
        })
    zones.sort(key=lambda z: z["method_count"], reverse=True)
    return zones

# ---------------------------------------------------------
# Sidebar - kullanıcı girdileri
# ---------------------------------------------------------
st.sidebar.title("Settings")
ticker = st.sidebar.selectbox("Select Stock", BIST_STOCKS)
timeframe = st.sidebar.selectbox("Timeframe", TIMEFRAMES, format_func=str.capitalize)
method = st.sidebar.selectbox("The Pivot Method", PIVOT_METHODS, format_func=str.capitalize)
periods_to_show = st.sidebar.slider("Periods to Show in Chart", 7, 365, 180)

last_update = cached_get_last_update_time(ticker, timeframe)
if last_update:
    st.sidebar.caption(f"🕒Last updated: {last_update}")
else:
    st.sidebar.caption("🕒No backtest data yet for this stock/timeframe.")

# ---------------------------------------------------------
# Başlık - yasal uyarı
# ---------------------------------------------------------
st.title("📊BIST Pivot Point Based Stock Projection System")

st.warning(
    "⚠️ This system doesn't provide investment advice. "
    "Pivot levels are statistically calculated potential support/resistance zones; we don't guarantee specific price levels."
)

# --------------------------------------------------------------------------
# Veriyi çek, seçilen timeframe'e göre resample et, güncel pivotları hesapla
# --------------------------------------------------------------------------
raw_df = cached_get_stock_data(ticker)

if raw_df.empty or len(raw_df) < 2:
    st.error(f"{ticker}'s data was not found. Please select another stock.")
    st.stop()

# Grafik ve güncel pivot hesaplaması, seçilen timeframe'e göre resample edilmiş veriyle çalışır 
# -böylece "weekly" seçildiğinde hem mum grafiği hem pivot çizgileri haftalık olur, tutarsızlık oluşmaz.
display_df = resample_to_timeframe(raw_df, timeframe)

if display_df.empty or len(display_df) < 2:
    st.error(f"Not enough {timeframe} data available for {ticker}. Please select another stock or timeframe.")
    st.stop()

prev_row = display_df.iloc[-2]
today_row = display_df.iloc[-1]
pivots = calculate_all_pivots(
    prev_open=prev_row["Open"], prev_high=prev_row["High"],
    prev_low=prev_row["Low"], prev_close=prev_row["Close"],
    today_open=today_row["Open"],
)

# ---------------------------------------------------------
# Hızlı bakış: tüm 5 yöntemin PP değeri yan yana
# ---------------------------------------------------------
st.subheader("Quick Overview")
pp_cols = st.columns(len(pivots))
for col, (method_name, levels) in zip(pp_cols, pivots.items()):
    with col:
        st.metric(label=method_name.capitalize(), value=f"{levels['PP']:.2f}")

# ---------------------------------------------------------
# Sekmeler
# ---------------------------------------------------------
user_is_admin = cached_is_user_admin(st.session_state["username"])

tab_names = ["📈Pivot Graph", "🎯Confluence Zones", "📊Backtest Statistics", "🔍Screener", "🔔Alerts"]
if user_is_admin:
    tab_names.append("🛠️Admin")

tabs = st.tabs(tab_names)
tab1, tab2, tab3, tab4, tab5 = tabs[0], tabs[1], tabs[2], tabs[3], tabs[4]
if user_is_admin:
    tab6 = tabs[5]

with tab1:
    st.subheader(f"{ticker} - {method.capitalize()} Pivot Levels ({timeframe.capitalize()})")
    fig = plot_candlestick_with_pivots(display_df, pivots, ticker, method=method, days_to_show=periods_to_show)
    st.plotly_chart(fig, use_container_width=True)

    st.caption(f"Current Pivot Values (calculated based on the latest {timeframe} open)")
    level_df = pd.DataFrame([
        {"Level": k, "Value": round(v, 2)} for k, v in pivots[method].items()
    ])
    st.dataframe(level_df, hide_index=True, use_container_width=True)

with tab2:
    st.subheader(f"{ticker} - Confluence Zones ({timeframe.capitalize()})")
    df_zones_db = cached_get_confluence_zones(ticker, timeframe)

    if df_zones_db.empty:
        st.info(
            "No confluence data available for this stock and timeframe. "
        )
    else:
        zones = reconstruct_zones_from_db(df_zones_db)
        fig2 = plot_confluence_zones(display_df, zones, ticker, days_to_show=periods_to_show)
        st.plotly_chart(fig2, use_container_width=True)

        st.caption(f"{len(zones)} confluence zone found (ordered from strong to weak)")
        for i, zone in enumerate(zones, start=1):
            methods = ", ".join(sorted({c["method"] for c in zone["contributors"]}))
            with st.expander(f"Zone {i}: {zone['center']:.2f} — {zone['method_count']} methods"):
                st.write(f"**Contributing Methods:** {methods}")
                contrib_df = pd.DataFrame(zone["contributors"])
                st.dataframe(contrib_df, hide_index=True, use_container_width=True)

with tab3:
    st.subheader(f"{ticker} - Backtest Statistics ({timeframe.capitalize()}, Touch / Break Probabilities)")
    stats_df = cached_get_pivot_stats(ticker, timeframe)

    if stats_df.empty:
        st.info(
            "No backtest data available for this stock and timeframe. "
        )
    else:
        method_stats = stats_df[stats_df["method"] == method].copy()

        # Herhangi bir seviyenin örneklem boyutu eşiğin altındaysa, kullanıcıyı güvenilirlik konusunda bilgilendir.
        min_sample = method_stats["sample_size"].min()
        if min_sample < LOW_SAMPLE_SIZE_THRESHOLD:
            st.warning(
                f"⚠️Low sample size detected. "
                f"Statistics based on fewer than {LOW_SAMPLE_SIZE_THRESHOLD} observations may be less reliable."
            )

        for col in ["touch_probability", "break_probability", "break_up_probability", "break_down_probability"]:
            method_stats[col] = (method_stats[col] * 100).round(1)

        # Sample Size sütununda düşük değerleri görsel olarak işaretle
        method_stats["sample_size_display"] = method_stats["sample_size"].apply(
            lambda n: f"⚠️ {n}" if n < LOW_SAMPLE_SIZE_THRESHOLD else str(n)
        )

        display_cols = [
            "level_name", "touch_probability", "break_probability",
            "break_up_probability", "break_down_probability", "sample_size_display",
        ]
        st.dataframe(
            method_stats[display_cols].rename(columns={
                "level_name": "Level",
                "touch_probability": "Touch %",
                "break_probability": "Break %",
                "break_up_probability": "Break Up %",
                "break_down_probability": "Break Down %",
                "sample_size_display": "Sample Size",
            }),
            hide_index=True,
            use_container_width=True,

            column_config={
                "Level": st.column_config.TextColumn(width="small"),
                "Touch %": st.column_config.NumberColumn(width="small"),
                "Break %": st.column_config.NumberColumn(width="small"),
                "Break Up %": st.column_config.NumberColumn(width="small"),
                "Break Down %": st.column_config.NumberColumn(width="small"),
                "Sample Size": st.column_config.TextColumn(width="small"),
            },
        )

with tab4:
    st.subheader("Stock Screener")

    screener_mode = st.radio(
        "Screening Mode",
        ["Touch/Break Probability", "Confluence Strength"],
        horizontal=True,
    )

    screener_timeframe = st.selectbox(
        "Timeframe for Screening", TIMEFRAMES, format_func=str.capitalize, key="screener_tf"
    )

    if screener_mode == "Touch/Break Probability":
        col1, col2 = st.columns(2)
        with col1:
            screener_method = st.selectbox(
                "Method", PIVOT_METHODS, format_func=str.capitalize, key="screener_method"
            )
        with col2:
            screener_level = st.selectbox(
                "Level", ["PP", "R1", "R2", "R3", "S1", "S2", "S3"], key="screener_level"
            )
        min_touch = st.slider("Minimum Touch Probability (%)", 0, 100, 50, key="screener_touch") / 100

        results = cached_screen_by_touch_probability(
            screener_timeframe, screener_method, screener_level, min_touch
        )

        if results.empty:
            st.info("No stocks match this criteria. Try lowering the threshold.")
        else:
            st.success(f"{len(results)} stocks found, sorted by touch probability.")

            min_sample = results["sample_size"].min()
            if min_sample < LOW_SAMPLE_SIZE_THRESHOLD:
                st.warning(
                    f"⚠️Low sample size detected."
                    f" Results based on fewer than {LOW_SAMPLE_SIZE_THRESHOLD} observations may be less reliable."
                    f" This is expected for 'monthly' timeframe or recently listed stocks."
                )

            display = results.copy()
            for col in ["touch_probability", "break_probability", "break_up_probability", "break_down_probability"]:
                display[col] = (display[col] * 100).round(1)

            display["sample_size_display"] = display["sample_size"].apply(
                lambda n: f"⚠️ {n}" if n < LOW_SAMPLE_SIZE_THRESHOLD else str(n)
            )

            display_cols = [
                "ticker", "touch_probability", "break_probability",
                "break_up_probability", "break_down_probability", "sample_size_display",
            ]
            st.dataframe(
                display[display_cols].rename(columns={
                    "ticker": "Ticker", "touch_probability": "Touch %",
                    "break_probability": "Break %", "break_up_probability": "Break Up %",
                    "break_down_probability": "Break Down %", "sample_size_display": "Sample Size",
                }),
                hide_index=True, use_container_width=True,

                column_config={
                    "Ticker": st.column_config.TextColumn(width="small"),
                    "Touch %": st.column_config.NumberColumn(width="small"),
                    "Break %": st.column_config.NumberColumn(width="small"),
                    "Break Up %": st.column_config.NumberColumn(width="small"),
                    "Break Down %": st.column_config.NumberColumn(width="small"),
                    "Sample Size": st.column_config.TextColumn(width="small"),
                },
            )

    else:  # Confluence Strength
        min_methods = st.slider(
            "Minimum Number of Contributing Methods", 2, 5, 4, key="screener_min_methods"
        )
        st.caption(
            "Note: Lower thresholds(2-3) will match most stocks since pivot levels across methods often fall close together." 
            " Higher thresholds(4-5) yield more selective, potentially more meaningful results."
        )

        results = cached_screen_by_confluence(screener_timeframe, min_methods)

        if results.empty:
            st.info("No stocks match this criteria. Try lowering the minimum method count.")
        else:
            st.success(f"{len(results)} stocks found, sorted by confluence strength.")
            st.dataframe(
                results.rename(columns={
                    "ticker": "Ticker", "max_method_count": "Max Methods in a Zone",
                    "zone_count": "Number of Qualifying Zones",
                }),
                hide_index=True, use_container_width=True,
            )

if user_is_admin:
    with tab6:
        st.subheader("🛠️Admin Panel")
        st.caption("Manage all registered users")

        users_df = cached_get_all_users_with_stats()

        if users_df.empty:
            st.info("No users found.")
        else:
            for _, row in users_df.iterrows():
                cols = st.columns([3, 1, 1, 1])
                with cols[0]:
                    admin_badge = " 👑" if row["is_admin"] else ""
                    telegram_badge = "✅" if row["telegram_connected"] else "❌"
                    st.write(
                        f"**{row['username']}**{admin_badge} — {row['first_name']} {row['last_name']} "
                        f"({row['email']}) — {row['alert_count']} alerts — Telegram: {telegram_badge}"
                    )
                with cols[2]:
                    if row["username"] != st.session_state["username"]:
                        if st.button("Delete User", key=f"admin_delete_{row['id']}"):
                            delete_user_and_data(int(row["id"]))
                            cached_get_all_users_with_stats.clear()
                            st.success(f"Deleted user: {row['username']}")
                            st.rerun()
                    else:
                        st.caption("(You)")

with tab5:
    st.subheader("🔔My Alerts")

    if "user_id" not in st.session_state:
        st.session_state["user_id"] = get_user_id(st.session_state["username"])
    user_id = st.session_state["user_id"]

    # --- Telegram bağlantısı ---
    st.markdown("### Telegram Connection")
    current_chat_id = cached_get_telegram_chat_id(st.session_state["username"])

    if current_chat_id:
        st.success("Telegram connected ✅")

        if st.button("Send Test Message"):
            ok = send_telegram_message(current_chat_id, "🔔Test message from BIST Pivot Alert System")
            if ok:
                st.success("Test message sent! Check your Telegram.")
            else:
                st.error("Failed to send test message.")
    else:
        st.warning("Telegram not connected yet. Follow the steps below to link your account.")

        st.markdown(
            "1. Open Telegram and message our bot: **@simal_bist_alert_bot**\n"
            "2. Click **Generate Code** below, then send that exact code as a message to the bot.\n"
            "3. Click **Verify Connection**."
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Generate Code"):
                code = generate_link_code(st.session_state["username"])
                st.session_state["pending_link_code_display"] = code

        with col2:
            if st.button("Verify Connection"):
                linked = verify_telegram_link(st.session_state["username"])
                if linked:
                    cached_get_telegram_chat_id.clear()
                    st.success("Telegram connected successfully! Refresh to see updated status.")
                else:
                    st.error(
                        "Code not found yet. Make sure you sent the exact code to the bot, then try again."
                    )

        if "pending_link_code_display" in st.session_state:
            st.info(f"Your code: **{st.session_state['pending_link_code_display']}** — send this to the bot.")

    st.divider()

    # --- Hesap silme ---
    st.markdown("### Danger Zone")
    with st.expander("Delete My Account"):
        st.warning(
            "This will permanently delete your account and ALL your alerts. "
            "This action cannot be undone."
        )
        confirm_username = st.text_input(
            "Type your username to confirm deletion:", key="delete_confirm"
        )
        if st.button("Permanently Delete My Account"):
            if confirm_username == st.session_state["username"]:
                delete_user_and_data(user_id)
                st.success("Your account has been deleted. You will be logged out.")
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
            else:
                st.error("Username does not match. Account not deleted.")

    # --- Yeni alert oluşturma ---
    st.markdown("### Create New Alert")
    with st.form("new_alert_form"):
        alert_ticker = st.selectbox("Stock", BIST_STOCKS, key="alert_ticker")
        alert_timeframe = st.selectbox("Timeframe", TIMEFRAMES, format_func=str.capitalize, key="alert_timeframe")
        alert_method = st.selectbox("Method", PIVOT_METHODS, format_func=str.capitalize, key="alert_method")

        if alert_method == "demark":
            level_options = ["PP", "R1", "S1"]
        else:
            level_options = ["PP", "R1", "R2", "R3", "S1", "S2", "S3"]
        alert_level = st.selectbox("Level", level_options, key="alert_level")

        alert_condition = st.radio("Condition", ["touch", "break"], horizontal=True, key="alert_condition")

        create_submitted = st.form_submit_button("Create Alert")

        if create_submitted:
            if not cached_get_telegram_chat_id(st.session_state["username"]):
                st.error("Please link your Telegram Chat ID above before creating alerts.")
            else:
                create_alert(user_id, alert_ticker, alert_method, alert_timeframe, alert_level, alert_condition)
                cached_get_alerts_for_user.clear()
                st.success(f"Alert created: {alert_ticker} {alert_method.capitalize()} {alert_level} ({alert_condition}).")

    st.divider()

    # --- Mevcut alertler ---
    st.markdown("### My Existing Alerts")
    alerts_df = cached_get_alerts_for_user(user_id)

    if alerts_df.empty:
        st.info("You haven't created any alerts yet.")
    else:
        for _, row in alerts_df.iterrows():
            cols = st.columns([3, 1, 1])
            status = "🟢 Active" if row["active"] else "⚪ Paused"
            last_triggered = row["last_triggered_date"] or "Never"
            with cols[0]:
                st.write(
                    f"**{row['ticker']}** — {row['method'].capitalize()} {row['level_name']} "
                    f"({row['condition_type']}, {row['timeframe'].capitalize()}) — {status} — "
                    f"Last triggered: {last_triggered}"
                )
            with cols[1]:
                toggle_label = "Pause" if row["active"] else "Resume"
                if st.button(toggle_label, key=f"toggle_{row['id']}"):
                    set_alert_active(int(row["id"]), user_id, not row["active"])
                    cached_get_alerts_for_user.clear()
                    st.rerun()
            with cols[2]:
                if st.button("Delete", key=f"delete_{row['id']}"):
                    delete_alert(int(row["id"]), user_id)
                    cached_get_alerts_for_user.clear()
                    st.rerun()