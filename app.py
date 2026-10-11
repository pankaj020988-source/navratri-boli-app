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

        # Admin साठी दर ३ सेकंदांनी आपोआप अपडेट होणारा भाग
        @st.fragment(run_every="3s")
        def admin_live_view():
            cursor.execute("SELECT bidder_name, mobile, amount FROM bids ORDER BY amount DESC LIMIT 1")
            top_bid = cursor.fetchone()

            col1, col2 = st.columns([1, 2])
            with col1:
                st.subheader("🏆 सध्याचा विजेता (Live)")
                if top_bid:
                    st.metric(label=f"विजेता: {top_bid[0]} ({top_bid[1]})", value=f"₹{top_bid[2]}")
                else:
                    st.metric(label="अद्याप कोणतीही बोली नाही", value="₹0")

            with col2:
                st.subheader("👥 सर्व नोंदणीकृत सहभागी")
                df_parts = pd.read_sql_query("SELECT id as क्र, name as नाव, mobile as मोबाईल FROM participants ORDER BY id DESC", conn)
                st.dataframe(df_parts, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("📋 सर्व बोलींचा संपूर्ण इतिहास (Live)")
            df_all = pd.read_sql_query("SELECT timestamp as वेळ, bidder_name as नाव, mobile as मोबाईल, amount as रक्कम FROM bids ORDER BY id DESC", conn)
            if not df_all.empty:
                st.dataframe(df_all, use_container_width=True, hide_index=True)
            else:
                st.info("अद्याप कोणतीही बोली नाही.")

        admin_live_view()

# -------------------------------------------------------------
# २. सहभागी (USER) पॅनल
# -------------------------------------------------------------
else:
    st.title("🚩 नवरात्र उत्सव - देवीची पूजा व प्रार्थना बोली")

    # दर ३ सेकंदांनी सर्वोच्च रक्कम आणि बॅनर आपोआप अपडेट करणारे फंक्शन
    @st.fragment(run_every="3s")
    def show_live_banner():
        cursor.execute("SELECT MAX(amount) FROM bids")
        max_r = cursor.fetchone()[0]
        cur_high = max_r if max_r is not None else 0
        st.info(f"### 📢 सध्या चालू असलेली सर्वोच्च बोली रक्कम: **₹{cur_high}**  *(🔴 Live दर ३ सेकंदांनी अपडेट होत आहे)*")

    show_live_banner()

    # युजर लॉगिन झालेला नसल्यास (फक्त पहिल्यांदाच)
    if not st.session_state.current_user_mobile:
        st.subheader("सहभागी होण्यासाठी एकदाच माहिती भरा")
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
                            st.warning("पहिल्यांदा नोंदणी करताना नाव आवश्यक आहे.")
                        else:
                            cursor.execute("INSERT INTO participants (name, mobile) VALUES (?, ?)", (clean_name, clean_mob))
                            conn.commit()
                            st.session_state.current_user_name = clean_name
                            st.session_state.current_user_mobile = clean_mob
                            st.query_params["user"] = clean_mob
                            st.rerun()
    else:
        # लॉगिन झाल्यानंतर
        u_name = st.session_state.current_user_name
        u_mobile = st.session_state.current_user_mobile

        top_col1, top_col2 = st.columns([3, 1])
        with top_col1:
            st.success(f"👤 स्वागत आहे: **{u_name}** ({u_mobile})")
        with top_col2:
            if st.button("बाहेर पडा (Logout)"):
                st.session_state.current_user_mobile = None
                st.session_state.current_user_name = None
                st.query_params.clear()
                st.rerun()

        # सध्याची सर्वोच्च रक्कम मिळवणे
        cursor.execute("SELECT MAX(amount) FROM bids")
        max_res = cursor.fetchone()[0]
        current_highest = max_res if max_res is not None else 0

        col_bid, col_history = st.columns([1, 1])

        with col_bid:
            st.subheader("⚡ झटपट बोली लावा")
            st.caption("रक्कम वाढवण्यासाठी खालील बटनावर टॅप करा:")
            b_col1, b_col2, b_col3 = st.columns(3)
            
            clicked_add = None
            if b_col1.button(f"+ ₹50\n(₹{current_highest + 50})", use_container_width=True):
                clicked_add = current_highest + 50
            if b_col2.button(f"+ ₹100\n(₹{current_highest + 100})", use_container_width=True):
                clicked_add = current_highest + 100
            if b_col3.button(f"+ ₹500\n(₹{current_highest + 500})", use_container_width=True):
                clicked_add = current_highest + 500

            if clicked_add:
                # पुन्हा तपासा की कोणी त्या सेकंदात वाढवले नाही ना
                cursor.execute("SELECT MAX(amount) FROM bids")
                latest_val = cursor.fetchone()[0] or 0
                if clicked_add <= latest_val:
                    st.error(f"दुसऱ्या भाविकाने नुकतीच बोली ₹{latest_val} पर्यंत वाढवली आहे. कृपया पुन्हा प्रयत्न करा.")
                else:
                    now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    cursor.execute(
                        "INSERT INTO bids (timestamp, bidder_name, mobile, amount) VALUES (?, ?, ?, ?)",
                        (now, u_name, u_mobile, clicked_add)
                    )
                    conn.commit()
                    st.success(f"₹{clicked_add} ची बोली यशस्वीरित्या नोंदवली गेली!")
                    st.rerun()

            st.write("किंवा इच्छित रक्कम टाईप करा:")
            min_bid = current_highest + 50 if current_highest > 0 else 100
            with st.form("custom_bid_form", clear_on_submit=True):
                bid_amount = st.number_input("इच्छित रक्कम (₹)", min_value=min_bid, value=min_bid, step=50)
                submit_custom = st.form_submit_button("बोली निश्चित करा", type="primary")

                if submit_custom:
                    cursor.execute("SELECT MAX(amount) FROM bids")
                    latest_val = cursor.fetchone()[0] or 0
                    if bid_amount <= latest_val:
                        st.error(f"रक्कम सध्याच्या सर्वोच्च रकमेपेक्षा (₹{latest_val}) जास्त असावी.")
                    else:
                        now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                        cursor.execute(
                            "INSERT INTO bids (timestamp, bidder_name, mobile, amount) VALUES (?,
