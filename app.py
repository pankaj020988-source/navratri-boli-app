import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# डेटाबेस जोडणी
conn = sqlite3.connect("navratri_bids.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        mobile TEXT UNIQUE
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS bids (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        bidder_name TEXT,
        mobile TEXT,
        amount INTEGER
    )
''')
conn.commit()

st.set_page_config(page_title="देवीची पूजा व प्रार्थना बोली", layout="wide")

ADMIN_PASSWORD = "admin123"

# URL Query Params द्वारे युजर टिकवणे
query_params = st.query_params

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False
if "current_user_mobile" not in st.session_state:
    saved_mob = query_params.get("user", None)
    if saved_mob:
        cursor.execute("SELECT name, mobile FROM participants WHERE mobile = ?", (saved_mob,))
        row = cursor.fetchone()
        if row:
            st.session_state.current_user_name = row[0]
            st.session_state.current_user_mobile = row[1]
        else:
            st.session_state.current_user_mobile = None
            st.session_state.current_user_name = None
    else:
        st.session_state.current_user_mobile = None
        st.session_state.current_user_name = None

# साइडबार
st.sidebar.title("🔐 प्रणाली")
selected_role = st.sidebar.radio("भूमिका निवडा:", ["सहभागी (User)", "Admin (प्रशासक)"])

# -------------------------------------------------------------
# १. ADMIN पॅनल
# -------------------------------------------------------------
if selected_role == "Admin (प्रशासक)":
    if not st.session_state.admin_logged_in:
        st.subheader("Admin लॉगिन")
        with st.form("admin_login_form"):
            pwd = st.text_input("पासवर्ड प्रविष्ट करा", type="password")
            if st.form_submit_button("लॉगिन"):
                if pwd == ADMIN_PASSWORD:
                    st.session_state.admin_logged_in = True
                    st.success("लॉगिन झाले!")
                    st.rerun()
                else:
                    st.error("चुकीचा पासवर्ड!")
    else:
        st.sidebar.success("Admin लॉगिन आहे")
        if st.sidebar.button("लॉगआउट"):
            st.session_state.admin_logged_in = False
            st.rerun()

        st.title("🚩 Admin व्यवस्थापन कक्ष")

        # Admin थेट Live View (दर ३ सेकंदांनी)
        @st.fragment(run_every="3s")
        def admin_live_view():
            cursor.execute("SELECT bidder_name, mobile, amount FROM bids ORDER BY amount DESC LIMIT 1")
