import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# Database connection
def get_db():
    return sqlite3.connect("navratri_bids.db", check_same_thread=False)

conn = get_db()
cursor = conn.cursor()

# Bids table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS bids (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        bidder_name TEXT,
        mobile TEXT,
        amount INTEGER
    )
""")

# Participants table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        mobile TEXT UNIQUE,
        pin TEXT
    )
""")

# Bids table madhye columns check karne
cursor.execute("PRAGMA table_info(bids)")
bids_cols = [col[1] for col in cursor.fetchall()]
if "bid_date" not in bids_cols:
    cursor.execute("ALTER TABLE bids ADD COLUMN bid_date TEXT DEFAULT ''")
if "session_day" not in bids_cols:
    cursor.execute("ALTER TABLE bids ADD COLUMN session_day TEXT DEFAULT 'दिवस १'")

# Participants table madhye PIN column check karne (Auto Fix)
cursor.execute("PRAGMA table_info(participants)")
parts_cols = [col[1] for col in cursor.fetchall()]
if "pin" not in parts_cols:
    cursor.execute("ALTER TABLE participants ADD COLUMN pin TEXT DEFAULT ''")

# Settings table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY,
        current_day TEXT,
        is_active INTEGER
    )
""")
cursor.execute("INSERT OR IGNORE INTO settings (id, current_day, is_active) VALUES (1, 'दिवस १', 1)")
conn.commit()
conn.close()

st.set_page_config(page_title="देवीची पूजा व प्रार्थना बोली", layout="centered")

# Auto-refresh every 3 seconds
st_autorefresh(interval=3000, key="auto_refresher")

ADMIN_PASSWORD = "admin123"

def get_settings():
    c_conn = get_db()
    c = c_conn.cursor()
    c.execute("SELECT current_day, is_active FROM settings WHERE id = 1")
    res = c.fetchone()
    c_conn.close()
    if res:
        return str(res[0]), bool(res[1])
    return "दिवस १", True

current_day, is_bidding_active = get_settings()

def get_highest_bid_for_day(day):
    c_conn = get_db()
    c = c_conn.cursor()
    c.execute("SELECT MAX(amount) FROM bids WHERE session_day = ?", (day,))
    val = c.fetchone()[0]
    c_conn.close()
    return int(val) if val is not None else 0

current_highest = get_highest_bid_for_day(current_day)

st.sidebar.title("🔐 प्रणाली")
role = st.sidebar.radio("भूमिका निवडा:", ["सहभागी (User)", "Admin (प्रशासक)"])

# ==========================================
# १. ADMIN PANEL
# ==========================================
if role == "Admin (प्रशासक)":
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False

    if not st.session_state.admin_logged_in:
        st.subheader("Admin लॉगिन")
        with st.form("admin_form"):
            pwd = st.text_input("पासवर्ड प्रविष्ट करा", type="password")
            if st.form_submit_button("लॉगिन"):
                if pwd == ADMIN_PASSWORD:
                    st.session_state.admin_logged_in = True
                    st.rerun()
                else:
                    st.error("चुकीचा पासवर्ड!")
    else:
        st.sidebar.success("Admin लॉगिन आहे")
        if st.sidebar.button("लॉगआउट"):
            st.session_state.admin_logged_in = False
            st.rerun()

        st.title("🚩 Admin व्यवस्थापन कक्ष")

        st.subheader("⚙️ बोली सत्र नियंत्रण")
        ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 2, 1])

        days_list = [f"दिवस {i}" for i in range(1, 11)]

        with ctrl_col1:
            selected_new_day = st.selectbox(
                "सध्याचा दिवस निवडा (बोलीसाठी):",
                days_list,
                index=days_list.index(current_day) if current_day in days_list else 0
            )

        with ctrl_col2:
            new_status = st.radio(
                "बोली स्थिती:",
                ["बोली सुरू ठेवा (Active)", "बोली बंद करा (Closed)"],
                index=0 if is_bidding_active else 1,
                horizontal=True
            )
            status_val = 1 if new_status == "बोली सुरू ठेवा (Active)" else 0

        with ctrl_col3:
            st.write("")
            st.write("")
            if st.button("सेटिंग्ज सेव्ह करा", type="primary"):
                c_conn = get_db()
                c = c_conn.cursor()
                c.execute("UPDATE settings SET current_day = ?, is_active = ? WHERE id = 1", (selected_new_day, status_val))
                c_conn.commit()
                c_conn.close()
                st.toast("सेटिंग्ज अपडेट झाल्या!", icon="✅")
                st.rerun()

        st.markdown("---")

        c_conn = get_db()
        c = c_conn.cursor()
        c.execute("SELECT bidder_name, mobile, amount FROM bids WHERE session_day = ? ORDER BY amount DESC LIMIT 1", (current_day,))
        top_bid = c.fetchone()
        c_conn.close()

        st.subheader(f"🏆 {current_day} चा विजेता (Live)")
        if top_bid:
            st.metric(label=f"विजेता: {top_bid[0]} ({top_bid[1]})", value=f"₹{top_bid[2]}")
        else:
            st.metric(label=f"{current_day} साठी अद्याप कोणतीही बोली नाही", value="₹0")

        st.markdown("---")

        st.subheader("📊 अहवाल आणि डेटा डाऊनलोड")
        c_conn = get_db()
        df_all = pd.read_sql_query(
            "SELECT timestamp as वेळ, bid_date as तारीख, session_day as दिवस, bidder_name as नाव, mobile as मोबाईल, amount as रक्कम FROM bids ORDER BY id DESC",
            c_conn
        )
        c_conn.close()

        if not df_all.empty:
            avail_days = sorted(list(df_all["दिवस"].dropna().unique()))
            view_day = st.selectbox("कोणत्या दिवसाचा अहवाल पाहायचा आहे?", ["सर्व दिवस एकत्र"] + avail_days)

            if view_day == "सर्व दिवस एकत्र":
                st.dataframe(
