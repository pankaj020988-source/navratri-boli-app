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

# URL वरून युजर ओळखणे
query_params = st.query_params

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

if "current_user_mobile" not in st.session_state:
    st.session_state.current_user_mobile = None
    st.session_state.current_user_name = None

saved_mob = query_params.get("user", None)
if saved_mob and not st.session_state.current_user_mobile:
    cursor.execute("SELECT name, mobile FROM participants WHERE mobile = ?", (str(saved_mob).strip(),))
    found = cursor.fetchone()
    if found:
        st.session_state.current_user_name = found[0]
        st.session_state.current_user_mobile = found[1]

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

        cursor.execute("SELECT bidder_name, mobile, amount FROM bids ORDER BY amount DESC LIMIT 1")
        top_bid = cursor.fetchone()

        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("🏆 सध्याचा विजेता")
            if top_bid:
                st.metric(label="विजेता: " + str(top_bid[0]) + " (" + str(top_bid[1]) + ")", value="₹" + str(top_bid[2]))
            else:
                st.metric(label="अद्याप कोणतीही बोली नाही", value="₹0")

        with col2:
            st.subheader("👥 सर्व नोंदणीकृत सहभागी")
            df_parts = pd.read_sql_query("SELECT id as क्र, name as नाव, mobile as मोबाईल FROM participants ORDER BY id DESC", conn)
            st.dataframe(df_parts, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("📋 सर्व बोलींचा संपूर्ण इतिहास")
        df_all = pd.read_sql_query("SELECT timestamp as वेळ, bidder_name as नाव, mobile as मोबाईल, amount as रक्कम FROM bids ORDER BY id DESC", conn)
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

    # चालू सर्वोच्च रक्कम मिळवणे
    cursor.execute("SELECT MAX(amount) FROM bids")
    max_res = cursor.fetchone()[0]
    current_highest = int(max_res) if max_res is not None else 0

    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.info("### 📢 सध्या चालू असलेली सर्वोच्च बोली रक्कम: ₹" + str(current_highest))
    with col_btn:
        st.write("")
        if st.button("🔄 ताजी रक्कम तपासा", use_container_width=True):
            st.rerun()

    # जर युजर लॉगिन नसेल तर
    if not st.session_state.current_user_mobile:
        st.subheader("सहभागी होण्यासाठी माहिती भरा")
        with st.form("auto_login_form"):
            user_mob = st.text_input("१० अंकी मोबाईल क्रमांक:", max_chars=10, placeholder="उदा. 9876543210")
            user_name_input = st.text_input("तुमचे पूर्ण नाव (पहिल्यांदाच येत असल्यास):", placeholder="उदा. राहुल शिंदे")
            submit_login = st.form_submit_button("प्रवेश करा", type="primary")

            if submit_login:
                clean_mob = user_mob.strip()
                clean_name = user_name_input.strip()

                if len(clean_mob) < 10 or not clean_mob.isdigit():
                    st.error("कृपया योग्य १० अंकी मोबाईल क्रमांक टाका.")
                else:
                    cursor.execute("SELECT name FROM participants WHERE mobile = ?", (clean_mob,))
                    existing = cursor.fetchone()

                    if existing:
                        st.session_state.current_user_name = existing[0]
                        st.session_state.current_user_mobile = clean_mob
                        st.query_params["user"] = clean_mob
                        st.rerun()
                    else:
                        if not clean_name:
                            st.warning("पहिल्यांदा नोंदणी करताना नाव भरणे आवश्यक आहे.")
                        else:
                            cursor.execute("INSERT INTO participants (name, mobile) VALUES (?, ?)", (clean_name, clean_mob))
                            conn.commit()
                            st.session_state.current_user_name = clean_name
                            st.session_state.
