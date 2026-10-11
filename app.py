import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# डेटाबेस जोडणी
def get_db():
    return sqlite3.connect("navratri_bids.db", check_same_thread=False)

conn = get_db()
cursor = conn.cursor()
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

# चालू सर्वोच्च बोली मिळवणे
def get_highest_bid():
    c_conn = get_db()
    c = c_conn.cursor()
    c.execute("SELECT MAX(amount) FROM bids")
    val = c.fetchone()[0]
    c_conn.close()
    return int(val) if val is not None else 0

current_highest = get_highest_bid()

# साइडबार
st.sidebar.title("🔐 प्रणाली")
role = st.sidebar.radio("भूमिका निवडा:", ["सहभागी (User)", "Admin (प्रशासक)"])

# ==========================================
# १. ADMIN पॅनल
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

        c_conn = get_db()
        c = c_conn.cursor()
        c.execute("SELECT bidder_name, mobile, amount FROM bids ORDER BY amount DESC LIMIT 1")
        top_bid = c.fetchone()

        st.subheader("🏆 सध्याचा विजेता")
        if top_bid:
            st.metric(label=f"विजेता: {top_bid[0]} ({top_bid[1]})", value=f"₹{top_bid[2]}")
        else:
            st.metric(label="अद्याप कोणतीही बोली नाही", value="₹0")

        st.markdown("---")
        st.subheader("📋 सर्व बोलींचा संपूर्ण इतिहास")
        df_all = pd.read_sql_query("SELECT timestamp as वेळ, bidder_name as नाव, mobile as मोबाईल, amount as रक्कम FROM bids ORDER BY id DESC", c_conn)
        c_conn.close()

        if not df_all.empty:
            st.dataframe(df_all, use_container_width=True, hide_index=True)
            csv = df_all.to_csv(index=False).encode('utf-8')
            st.download_button("Excel/CSV डाऊनलोड", data=csv, file_name="all_bids.csv", mime="text/csv")
        else:
            st.info("अद्याप कोणतीही बोली नाही.")

# ==========================================
# २. सहभागी (USER) पॅनल
# ==========================================
else:
    st.title("🚩 नवरात्र उत्सव - देवीची पूजा व प्रार्थना बोली")

    # सर्वोच्च रक्कम आणि रिफ्रेश बटण
    col_banner, col_refresh = st.columns([4, 1])
    with col_banner:
        st.info(f"### 📢 सध्या चालू असलेली सर्वोच्च बोली रक्कम: **₹{current_highest}**")
    with col_refresh:
        st.write("")
        if st.button("🔄 ताजी रक्कम तपासा", use_container_width=True):
            st.rerun()

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("📝 तुमची माहिती")
        name = st.text_input("भाविकाचे पूर्ण नाव:", key="user_name_input", placeholder="उदा. राहुल शिंदे")
        mobile = st.text_input("१० अंकी मोबाईल क्रमांक:", max_chars=10, key="user_mobile_input", placeholder="उदा. 9876543210")

        st.markdown("---")
        st.subheader("⚡ झटपट बोली लावा")
        st.caption("रक्कम वाढवण्यासाठी खालील बटनावर टॅप करा:")

        val_50 = current_highest + 50
        val_100 = current_highest + 100
        val_500 = current_highest + 500

        b1, b2, b3 = st.columns(3)
        clicked_val = None

        if b1.button(f"+ ₹50\n(₹{val_50})", use_container_width=True):
            clicked_val = val_50
        if b2.button(f"+ ₹100\n(₹{val_100})", use_container_width=True):
            clicked_val = val_100
        if b3.button(f"+ ₹500\n(₹{val_500})", use_container_width=True):
            clicked_val = val_500

        # बटनावर क्लिक झाल्यावर लगेच सेव्ह करणे
        if clicked_val is not None:
            clean_name = name.strip()
            clean_mob = mobile.strip()

            if not clean_name or len(clean_mob) < 10 or not clean_mob.isdigit():
                st.error("कृपया आधी तुमचे नाव आणि १० अंकी मोबाईल क्रमांक वर भरा.")
            else:
                c_conn = get_db()
                c = c_conn.cursor()
                c.execute("SELECT MAX(amount) FROM bids")
                latest = c.fetchone()[0] or 0
                if clicked_val <= latest:
                    st.error(f"कोणीतरी नुकतीच बोली ₹{latest} केली आहे. कृपया पुन्हा टॅप करा.")
                    c_conn.close()
                else:
                    now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    c.execute("INSERT INTO bids (timestamp, bidder_name, mobile, amount) VALUES (?, ?, ?, ?)", (now, clean_name, clean_mob, clicked_val))
                    c_conn.commit()
                    c_conn.close()
                    st.toast(f"₹{clicked_val} ची बोली यशस्वीरित्या नोंदवली गेली!", icon="✅")
                    st.rerun()

        st.write("किंवा रक्कम थेट टाईप करा:")
        min_custom = current_highest + 50 if current_highest > 0 else 100
        with st.form("custom_bid_form", clear_on_submit=True):
            custom_amount = st.number_input("इच्छित रक्कम (₹)", min_value=min_custom, value=min_custom, step=50)
            if st.form_submit_button("बोली निश्चित करा", type="primary"):
                clean_name = name.strip()
                clean_mob = mobile.strip()

                if not clean_name or len(clean_mob) < 10 or not clean_mob.isdigit():
                    st.error("कृपया तुमचे नाव आणि १० अंकी मोबाईल क्रमांक भरा.")
                else:
                    c_conn = get_db()
                    c = c_conn.cursor()
                    c.execute("SELECT MAX(amount) FROM bids")
                    latest = c.fetchone()[0] or 0
                    if custom_amount <= latest:
                        st.error(f"रक्कम सध्याच्या सर्वोच्च रकमेपेक्षा (₹{latest}) जास्त असावी.")
                        c_conn.close()
                    else:
                        now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                        c.execute("INSERT INTO bids (timestamp, bidder_name, mobile, amount) VALUES (?, ?, ?, ?)", (now, clean_name, clean_mob, custom_amount))
                        c_conn.commit()
                        c_conn.close()
                        st.toast(f"₹{custom_amount} ची बोली नोंदवली गेली!", icon="✅")
                        st.rerun()

    with col_right:
        st.subheader("📜 फक्त तुमच्या बोलींचा इतिहास")
        if mobile.strip() and len(mobile.strip()) == 10:
            c_conn = get_db()
            df_my = pd.read_sql_query(
                "SELECT timestamp as वेळ, amount as रक्कम FROM bids WHERE mobile = ? ORDER BY id DESC",
                c_conn,
                params=(mobile.strip(),)
            )
            c_conn.close()
            if not df_my.empty:
                st.dataframe(df_my, use_container_width=True, hide_index=True)
            else:
                st.info("या मोबाईल नंबरवरून अद्याप कोणतीही बोली आलेली नाही.")
        else:
            st.caption("डाव्या बाजूला मोबाईल क्रमांक टाकल्यावर तुमच्या जुन्या बोली येथे दिसतील.")
