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

# चालू सर्वोच्च रक्कम मिळवणारे फंक्शन
def get_highest_bid():
    c_conn = get_db()
    c = c_conn.cursor()
    c.execute("SELECT MAX(amount) FROM bids")
    val = c.fetchone()[0]
    c_conn.close()
    return int(val) if val is not None else 0

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

        # Admin साठी लाईव्ह ऑटो-रिफ्रेश (दर ३ सेकंदांनी)
        @st.fragment(run_every=3)
        def admin_live_dashboard():
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
            st.subheader("📋 सर्व बोलींचा संपूर्ण इतिहास (Live)")
            df_all = pd.read_sql_query("SELECT timestamp as वेळ, bidder_name as नाव, mobile as मोबाईल, amount as रक्कम FROM bids ORDER BY id DESC", c_conn)
            c_conn.close()

            if not df_all.empty:
                st.dataframe(df_all, use_container_width=True, hide_index=True)
                csv = df_all.to_csv(index=False).encode('utf-8')
                st.download_button("Excel/CSV डाऊनलोड", data=csv, file_name="all_bids.csv", mime="text/csv")
            else:
                st.info("अद्याप कोणतीही बोली नाही.")

        admin_live_dashboard()

# ==========================================
# २. सहभागी (USER) पॅनल
# ==========================================
else:
    st.title("🚩 नवरात्र उत्सव - देवीची पूजा व प्रार्थना बोली")

    # फॉर्म माहिती सेव्ह ठेवण्यासाठी session_state
    if "u_name" not in st.session_state:
        st.session_state.u_name = ""
    if "u_mob" not in st.session_state:
        st.session_state.u_mob = ""

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("📝 तुमची माहिती")
        name_input = st.text_input("भाविकाचे पूर्ण नाव:", value=st.session_state.u_name, placeholder="उदा. पंकज देसाई")
        mob_input = st.text_input("१० अंकी मोबाईल क्रमांक:", value=st.session_state.u_mob, placeholder="उदा. 98xxxxxxxx")

        # नावे व नंबर अदलाबदल झाले तरी सुधारणे
        v1 = name_input.strip()
        v2 = mob_input.strip()
        if v1.isdigit() and not v2.isdigit():
            user_mob = v1
            user_name = v2
        else:
            user_name = v1
            user_mob = v2

        st.session_state.u_name = user_name
        st.session_state.u_mob = user_mob

        st.markdown("---")

        # लाईव्ह ऑटो-रिफ्रेश होणारा बोली कक्ष (दर ३ सेकंदांनी स्वतःहून अपडेट होईल)
        @st.fragment(run_every=3)
        def live_bidding_section():
            cur_high = get_highest_bid()
            
            st.info(f"### 📢 सध्या चालू असलेली सर्वोच्च बोली: **₹{cur_high}**  *(🔴 Live)*")
            st.subheader("⚡ झटपट बोली लावा")
            st.caption("रक्कम वाढवण्यासाठी खालील बटनावर टॅप करा:")

            val_50 = cur_high + 50
            val_100 = cur_high + 100
            val_500 = cur_high + 500

            b1, b2, b3 = st.columns(3)
            clicked = None

            if b1.button(f"+ ₹50\n(₹{val_50})", use_container_width=True):
                clicked = val_50
            if b2.button(f"+ ₹100\n(₹{val_100})", use_container_width=True):
                clicked = val_100
            if b3.button(f"+ ₹500\n(₹{val_500})", use_container_width=True):
                clicked = val_500

            if clicked is not None:
                c_name = st.session_state.u_name
                c_mob = st.session_state.u_mob

                if not c_name or len(c_mob) < 10:
                    st.error("कृपया आधी तुमचे नाव आणि १० अंकी मोबाईल क्रमांक वर भरा.")
                else:
                    c_conn = get_db()
                    c = c_conn.cursor()
                    c.execute("SELECT MAX(amount) FROM bids")
                    latest = c.fetchone()[0] or 0
                    if clicked <= latest:
                        st.error(f"दुसऱ्या भाविकाने नुकतीच बोली ₹{latest} केली आहे. कृपया पुन्हा टॅप करा.")
                        c_conn.close()
                    else:
                        now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                        c.execute("INSERT INTO bids (timestamp, bidder_name, mobile, amount) VALUES (?, ?, ?, ?)", (now, c_name, c_mob, clicked))
                        c_conn.commit()
                        c_conn.close()
                        st.toast(f"₹{clicked} ची बोली यशस्वीरित्या नोंदवली गेली!", icon="✅")
                        st.rerun()

            st.write("किंवा रक्कम थेट टाईप करा:")
            min_c = cur_high + 50 if cur_high > 0 else 100
            with st.form("custom_form", clear_on_submit=True):
                custom_amt = st.number_input("इच्छित रक्कम (₹)", min_value=min_c, value=min_c, step=50)
                if st.form_submit_button("बोली निश्चित करा", type="primary"):
                    c_name = st.session_state.u_name
                    c_mob = st.session_state.u_mob

                    if not c_name or len(c_mob) < 10:
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
                            c.execute("INSERT INTO bids (timestamp, bidder_name, mobile, amount) VALUES (?, ?, ?, ?)", (now, c_name, c_mob, custom_amt))
                            c_conn.commit()
                            c_conn.close()
                            st.toast(f"₹{custom_amt} ची बोली यशस्वीरित्या नोंदवली गेली!", icon="✅")
                            st.rerun()

        live_bidding_section()

    with col_right:
        st.subheader("📜 फक्त तुमच्या बोलींचा इतिहास")
        
        # इतिहास सुद्धा दर ३ सेकंदांनी आपोआप रिफ्रेश होईल
        @st.fragment(run_every=3)
        def live_history_section():
            curr_m = st.session_state.u_mob
            if curr_m and len(curr_m) >= 10:
                c_conn = get_db()
                df_my = pd.read_sql_query(
                    "SELECT timestamp as वेळ, amount as रक्कम FROM bids WHERE mobile = ? ORDER BY id DESC",
                    c_conn,
                    params=(curr_m,)
                )
                c_conn.close()
                if not df_my.empty:
                    st.dataframe(df_my, use_container_width=True, hide_index=True)
                else:
                    st.info("या मोबाईल नंबरवरून अद्याप कोणतीही बोली आलेली
