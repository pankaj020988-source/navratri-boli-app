import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# डेटाबेस जोडणी फंक्शन
def get_db_connection():
    conn = sqlite3.connect("navratri_bids.db", check_same_thread=False)
    return conn

# टेबल तयार करणे
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        mobile TEXT UNIQUE
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS bids (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        bidder_name TEXT,
        mobile TEXT,
        amount INTEGER
    )
""")
conn.commit()
conn.close()

st.set_page_config(page_title="देवीची पूजा व प्रार्थना बोली", layout="wide")

ADMIN_PASSWORD = "admin123"

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False
if "current_user_mobile" not in st.session_state:
    st.session_state.current_user_mobile = None
if "current_user_name" not in st.session_state:
    st.session_state.current_user_name = None

# सर्वोच्च बोली मिळवणारे फंक्शन
def get_highest_bid():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT MAX(amount) FROM bids")
    val = c.fetchone()[0]
    conn.close()
    return int(val) if val is not None else 0

# नवीन बोली जोडणारे सुरक्षित फंक्शन
def add_bid(bidder_name, mobile, amount):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT MAX(amount) FROM bids")
    current_max = c.fetchone()[0]
    current_max = int(current_max) if current_max is not None else 0

    if amount <= current_max:
        conn.close()
        return False, f"दुसऱ्या भाविकाने नुकतीच बोली ₹{current_max} केली आहे. कृपया पुन्हा प्रयत्न करा."
    
    now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    c.execute(
        "INSERT INTO bids (timestamp, bidder_name, mobile, amount) VALUES (?, ?, ?, ?)",
        (now, bidder_name, mobile, amount)
    )
    conn.commit()
    conn.close()
    return True, f"₹{amount} ची बोली यशस्वीरित्या नोंदवली गेली!"

st.sidebar.title("🔐 प्रणाली")
selected_role = st.sidebar.radio("भूमिका निवडा:", ["सहभागी (User)", "Admin (प्रशासक)"])

# -------------------------------------------------------------
# १. ADMIN पॅनल
# -------------------------------------------------------------
if selected_role == "Admin (प्रशासक)":
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

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT bidder_name, mobile, amount FROM bids ORDER BY amount DESC LIMIT 1")
        top_bid = c.fetchone()

        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("🏆 सध्याचा विजेता")
            if top_bid:
                st.metric(label=f"विजेता: {top_bid[0]} ({top_bid[1]})", value=f"₹{top_bid[2]}")
            else:
                st.metric(label="अद्याप कोणतीही बोली नाही", value="₹0")

        with col2:
            st.subheader("👥 नोंदणीकृत सहभागी")
            df_parts = pd.read_sql_query("SELECT id as क्र, name as नाव, mobile as मोबाईल FROM participants ORDER BY id DESC", conn)
            st.dataframe(df_parts, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("📋 सर्व बोलींचा इतिहास")
        df_all = pd.read_sql_query("SELECT timestamp as वेळ, bidder_name as नाव, mobile as मोबाईल, amount as रक्कम FROM bids ORDER BY id DESC", conn)
        conn.close()

        if not df_all.empty:
            st.dataframe(df_all, use_container_width=True, hide_index=True)
            csv = df_all.to_csv(index=False).encode('utf-8')
            st.download_button("Excel/CSV डाऊनलोड", data=csv, file_name="all_bids.csv", mime="text/csv")
        else:
            st.info("अद्याप कोणतीही बोली नाही.")

# -------------------------------------------------------------
# २. सहभागी (USER) पॅनल
# -------------------------------------------------------------
else:
    st.title("🚩 नवरात्र उत्सव - देवीची पूजा व प्रार्थना बोली")

    current_highest = get_highest_bid()

    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.info(f"### 📢 सध्या चालू असलेली सर्वोच्च बोली रक्कम: ₹{current_highest}")
    with col_btn:
        st.write("")
        if st.button("🔄 ताजी रक्कम तपासा", use_container_width=True):
            st.rerun()

    # युजर लॉगिन झालेला नसल्यास
    if not st.session_state.current_user_mobile:
        st.subheader("सहभागी होण्यासाठी माहिती भरा")
        with st.form("login_form"):
            user_mob = st.text_input("१० अंकी मोबाईल क्रमांक:", max_chars=10, placeholder="उदा. 9876543210")
            user_name_input = st.text_input("तुमचे पूर्ण नाव (पहिल्यांदाच येत असल्यास):", placeholder="उदा. राहुल शिंदे")
            if st.form_submit_button("प्रवेश करा", type="primary"):
                clean_mob = user_mob.strip()
                clean_name = user_name_input.strip()

                if len(clean_mob) < 10 or not clean_mob.isdigit():
                    st.error("कृपया योग्य १० अंकी मोबाईल क्रमांक टाका.")
                else:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("SELECT name FROM participants WHERE mobile = ?", (clean_mob,))
                    existing = c.fetchone()

                    if existing:
                        st.session_state.current_user_name = existing[0]
                        st.session_state.current_user_mobile = clean_mob
                        conn.close()
                        st.rerun()
                    else:
                        if not clean_name:
                            st.warning("पहिल्यांदा नोंदणी करताना नाव भरणे आवश्यक आहे.")
                            conn.close()
                        else:
                            c.execute("INSERT INTO participants (name, mobile) VALUES (?, ?)", (clean_name, clean_mob))
                            conn.commit()
                            conn.close()
                            st.session_state.current_user_name = clean_name
                            st.session_state.current_user_mobile = clean_mob
                            st.rerun()
    else:
        # लॉगिन झाल्यानंतर
        u_name = st.session_state.current_user_name
        u_mobile = st
