import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

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

# दर ३ सेकंदांनी (३००० मिलीसेकंद) अचूक ऑटो-रिफ्रेश
st_autorefresh(interval=3000, key="bidding_counter")

ADMIN_PASSWORD = "admin123"

# चालू सर्वोच्च रक्कम
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

        st.subheader("🏆 सध्याचा विजेता (Live)")
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

    # सर्वोच्च रक्कम बॅनर
    st.info(f"### 📢 सध्या चालू असलेली सर्वोच्च बोली: **₹{current_highest}**  *(🔴 Live दर ३ सेकंदांनी ऑटो-रिफ्रेश)*")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("📝 तुमची माहिती")
        n_in = st.text_input("भाविकाचे पूर्ण नाव:", key="p_name_val", placeholder="उदा. पंकज देसाई")
        m_in = st.text_input("१० अंकी मोबाईल क्रमांक:", key="p_mob_val", placeholder="उदा. 98xxxxxxxx")

        s1 = n_in.strip()
        s2 = m_in.strip()
        if s1.isdigit() and not s2.isdigit():
            user_mob = s1
            user_name = s2
        else:
            user_name = s1
            user_mob = s2

        st.markdown("---")
        st.subheader("⚡ झटपट बोली लावा")
        st.caption("रक्कम वाढवण्यासाठी खालील बटनावर टॅप करा:")

        val_50 = current_highest + 50
        val_100 = current_highest + 100
        val_500 = current_highest + 500

        b1, b2, b3 = st.columns(3)
        add_clicked = None

        if b1.button(f"+ ₹50\n(₹{val_50})", use_container_width=True):
            add_clicked = val_50
        if b2.button(f"+ ₹100\n(₹{val_100})", use_container_width=True):
            add_clicked = val_100
        if b3.button(f"+ ₹500\n(₹{val_500})", use_container_width=True):
            add_clicked = val_500

        # झटपट बटण क्लिक
        if add_clicked is not None:
            if not user_name or len(user_mob) < 10:
                st.error("कृपया आधी तुमचे नाव आणि १० अंकी मोबाईल क्रमांक वर भरा.")
            else:
                c_conn = get_db()
                c = c_conn.cursor()
                c.execute("SELECT MAX(amount) FROM bids")
                latest = c.fetchone()[0] or 0
                if add_clicked <= latest:
                    st.error(f"दुसऱ्या भाविकाने नुकतीच बोली ₹{latest} केली आहे. कृपया पुन्हा टॅप करा.")
                    c_conn.close()
                else:
                    now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    c.execute("INSERT INTO bids (timestamp, bidder_name, mobile, amount) VALUES (?, ?, ?, ?)", (now, user_name, user_mob, add_clicked))
                    c_conn.commit()
                    c_conn.close()
                    st.toast(f"₹{add_clicked} ची बोली यशस्वीरित्या नोंदवली गेली!", icon="✅")
                    st.rerun()

        st.write("किंवा रक्कम थेट टाका:")
        min_c = current_highest + 50 if current_highest > 0 else 100
        with st.form("custom_form", clear_on_submit=True):
            custom_amt = st.number_input("इच्छित रक्कम (₹)", min_value=min_c, value=min_c, step=50)
            if st.form_submit_button("बोली निश्चित करा", type="primary"):
                if not user_name or len(user_mob) < 10:
                    st.error("कृपया आधी नाव आणि १० अंकी मोबाईल क्रमांक भरा.")
                else:
                    c_conn = get_db()
                    c = c_conn.cursor()
                    c.execute("SELECT MAX(amount) FROM bids")
                    latest = c.fetchone()[0] or 0
                    if custom_amt <= latest:
                        st.error(f"रक्कम सध्याच्या सर्वोच्च रकमेपेक्षा (₹{latest}) जास्त असावी.")
                        c_conn.close()
                    else:
                        now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                        c.execute("INSERT INTO bids (timestamp, bidder_name, mobile, amount) VALUES (?, ?, ?, ?)", (now, user_name, user_mob, custom_amt))
                        c_conn.commit()
                        c_conn.close()
                        st.toast(f"₹{custom_amt} ची बोली नोंदवली गेली!", icon="✅")
                        st.rerun()

    with col_right:
        st.subheader("📜 फक्त तुमच्या बोलींचा इतिहास")
        if user_mob and len(user_mob) >= 10:
            c_conn = get_db()
            df_my = pd.read_sql_query(
                "SELECT timestamp as वेळ, amount as रक्कम FROM bids WHERE mobile = ? ORDER BY id DESC",
                c_conn,
                params=(user_mob,)
            )
            c_conn.close()
            if not df_my.empty:
                st.dataframe(df_my, use_container_width=True, hide_index=True)
            else:
                st.info("या मोबाईल नंबरवरून अद्याप कोणतीही बोली आलेली नाही.")
        else:
            st.caption("मोबाईल क्रमांक भरल्यानंतर तुमच्या बोली येथे दिसतील.")
