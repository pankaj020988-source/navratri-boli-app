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

ADMIN_PASSWORD = "admin123"  # Admin पासवर्ड

# सेशन स्टेट व्हेरिएबल्स
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False
if "current_user_mobile" not in st.session_state:
    st.session_state.current_user_mobile = None
if "current_user_name" not in st.session_state:
    st.session_state.current_user_name = None

# साइडबार - रोल निवड
st.sidebar.title("🔐 प्रणाली प्रवेश")
selected_role = st.sidebar.radio("तुमची भूमिका निवडा:", ["सहभागी (User)", "Admin (प्रशासक)"])

# -------------------------------------------------------------
# १. ADMIN पॅनल
# -------------------------------------------------------------
if selected_role == "Admin (प्रशासक)":
    if not st.session_state.admin_logged_in:
        st.subheader("प्रशासक लॉगिन (Admin Login)")
        with st.form("admin_login_form"):
            pwd = st.text_input("Admin पासवर्ड प्रविष्ट करा", type="password")
            if st.form_submit_button("लॉगिन करा"):
                if pwd == ADMIN_PASSWORD:
                    st.session_state.admin_logged_in = True
                    st.success("यशस्वीरित्या लॉगिन झाले!")
                    st.rerun()
                else:
                    st.error("चुकीचा पासवर्ड!")
    else:
        st.sidebar.success("Admin लॉगिन आहे")
        if st.sidebar.button("लॉगआउट करा"):
            st.session_state.admin_logged_in = False
            st.rerun()

        st.title("🚩 Admin व्यवस्थापन कक्ष")

        # सर्वोच्च बोली
        cursor.execute("SELECT bidder_name, mobile, amount FROM bids ORDER BY amount DESC LIMIT 1")
        top_bid = cursor.fetchone()

        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("🏆 सध्याचा विजेता")
            if top_bid:
                st.metric(label=f"विजेता: {top_bid[0]} ({top_bid[1]})", value=f"₹{top_bid[2]}")
            else:
                st.metric(label="अद्याप कोणतीही बोली नाही", value="₹0")

        with col2:
            st.subheader("👥 स्वयं-नोंदणी झालेले सर्व सहभागी")
            df_parts = pd.read_sql_query("SELECT id as क्र, name as नाव, mobile as मोबाईल FROM participants ORDER BY id DESC", conn)
            st.dataframe(df_parts, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("📋 सर्व बोलींचा संपूर्ण इतिहास (केवळ Admin साठी)")
        df_all_bids = pd.read_sql_query("SELECT timestamp as वेळ, bidder_name as नाव, mobile as मोबाईल, amount as रक्कम FROM bids ORDER BY id DESC", conn)
        
        if not df_all_bids.empty:
            st.dataframe(df_all_bids, use_container_width=True, hide_index=True)
            csv = df_all_bids.to_csv(index=False).encode('utf-8')
            st.download_button("Excel/CSV मध्ये डेटा डाऊनलोड करा", data=csv, file_name="all_navratri_bids.csv", mime="text/csv")
        else:
            st.info("अद्याप कोणतीही बोली आलेली नाही.")

# -------------------------------------------------------------
# २. सहभागी (USER) पॅनल - ऑटो/स्वयं नोंदणी
# -------------------------------------------------------------
else:
    st.title("🚩 नवरात्र उत्सव - देवीची पूजा व प्रार्थना बोली")

    # सध्या चालू असलेली सर्वोच्च रक्कम मिळवणे
    cursor.execute("SELECT MAX(amount) FROM bids")
    max_res = cursor.fetchone()[0]
    current_highest = max_res if max_res is not None else 0

    st.info(f"### 📢 सध्या चालू असलेली सर्वोच्च बोली रक्कम: **₹{current_highest}**")

    # युजर लॉगिन / स्वयं नोंदणी
    if not st.session_state.current_user_mobile:
        st.subheader("सहभागी होण्यासाठी मोबाईल नंबर टाका")
        with st.form("auto_login_form"):
            user_mob = st.text_input("तुमचा १० अंकी मोबाईल क्रमांक:", max_chars=10, placeholder="उदा. 9876543210")
            user_name_input = st.text_input("तुमचे पूर्ण नाव (पहिल्यांदाच येत असल्यास भरा):", placeholder="उदा. राहुल शिंदे")
            submit_login = st.form_submit_button("प्रवेश करा")

            if submit_login:
                clean_mob = user_mob.strip()
                clean_name = user_name_input.strip()

                if len(clean_mob) < 10 or not clean_mob.isdigit():
                    st.error("कृपया योग्य १० अंकी मोबाईल क्रमांक टाका.")
                else:
                    # जुना सदस्य आहे का तपासणे
                    cursor.execute("SELECT name FROM participants WHERE mobile = ?", (clean_mob,))
                    existing = cursor.fetchone()

                    if existing:
                        st.session_state.current_user_name = existing[0]
                        st.session_state.current_user_mobile = clean_mob
                        st.rerun()
                    else:
                        # नवीन सदस्य असल्यास नाव आवश्यक
                        if not clean_name:
                            st.warning("तुम्ही पहिल्यांदाच येत आहात, कृपया तुमचे नाव प्रविष्ट करा.")
                        else:
                            cursor.execute("INSERT INTO participants (name, mobile) VALUES (?, ?)", (clean_name, clean_mob))
                            conn.commit()
                            st.session_state.current_user_name = clean_name
                            st.session_state.current_user_mobile = clean_mob
                            st.rerun()
    else:
        # लॉगिन झाल्यानंतरचे बोली पेज
        u_name = st.session_state.current_user_name
        u_mobile = st.session_state.current_user_mobile

        top_col1, top_col2 = st.columns([3, 1])
        with top_col1:
            st.success(f"👤 स्वागत आहे: **{u_name}** ({u_mobile})")
        with top_col2:
            if st.button("बाहेर पडा (Logout)"):
                st.session_state.current_user_mobile = None
                st.session_state.current_user_name = None
                st.rerun()

        col_bid, col_history = st.columns([1, 1])

        with col_bid:
            st.subheader("तुमची नवीन बोली लावा")
            min_bid = current_highest + 50 if current_highest > 0 else 100

            with st.form("user_bid_form", clear_on_submit=True):
                bid_amount = st.number_input("बोली रक्कम (₹)", min_value=min_bid, value=min_bid, step=50)
                submit_bid = st.form_submit_button("बोली निश्चित करा", type="primary")

                if submit_bid:
                    if bid_amount <= current_highest:
                        st.error(f"रक्कम सध्याच्या सर्वोच्च रकमेपेक्षा (₹{current_highest}) जास्त असावी.")
                    else:
                        now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                        cursor.execute(
                            "INSERT INTO bids (timestamp, bidder_name, mobile, amount) VALUES (?, ?, ?, ?)",
                            (now, u_name, u_mobile, bid_amount)
                        )
                        conn.commit()
                        st.success(f"तुमची ₹{bid_amount} ची बोली यशस्वीरित्या नोंदवली गेली!")
                        st.rerun()

        with col_history:
            st.subheader("📜 फक्त तुमच्या बोलींचा इतिहास")
            df_my_bids = pd.read_sql_query(
                "SELECT timestamp as वेळ, amount as रक्कम FROM bids WHERE mobile = ? ORDER BY id DESC",
                conn,
                params=(u_mobile,)
            )

            if not df_my_bids.empty:
                st.dataframe(df_my_bids, use_container_width=True, hide_index=True)
            else:
                st.write("तुम्ही अद्याप कोणतीही बोली लावलेली नाही.")
