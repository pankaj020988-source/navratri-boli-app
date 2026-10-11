import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# डेटाबेस तयार करणे
conn = sqlite3.connect("navratri_bids.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        mobile TEXT
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

# पासवर्ड कॉन्फिगरेशन
ADMIN_PASSWORD = "admin123"  # आवश्यकतेनुसार पासवर्ड बदला

# सेशन स्टेट व्यवस्थापन
if "role" not in st.session_state:
    st.session_state.role = "सहभागी (User)"
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

# साइडबार - रोल आणि लॉगिन निवड
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
            login_btn = st.form_submit_button("लॉगिन करा")
            if login_btn:
                if pwd == ADMIN_PASSWORD:
                    st.session_state.admin_logged_in = True
                    st.success("यशस्वीरित्या लॉगिन झाले!")
                    st.rerun()
                else:
                    st.error("चुकीचा पासवर्ड!")
    else:
        # लॉगिन झाल्यानंतरचे Admin दृश्य
        st.sidebar.success("Admin म्हणून लॉगिन आहात")
        if st.sidebar.button("लॉगआउट करा"):
            st.session_state.admin_logged_in = False
            st.rerun()

        st.title("🚩 Admin व्यवस्थापन कक्ष")

        # सहभागी नोंदणी
        with st.expander("➕ नवीन सहभागी व्यक्ती जोडा", expanded=False):
            with st.form("add_p_form", clear_on_submit=True):
                p_name = st.text_input("सहभागीचे नाव")
                p_mobile = st.text_input("मोबाईल क्रमांक")
                if st.form_submit_button("सहभागी जोडा"):
                    if p_name.strip() and p_mobile.strip():
                        try:
                            cursor.execute("INSERT INTO participants (name, mobile) VALUES (?, ?)", (p_name.strip(), p_mobile.strip()))
                            conn.commit()
                            st.success(f"{p_name} यादीत जोडले गेले!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("हे नाव आधीच नोंदवलेले आहे.")
                    else:
                        st.warning("नाव आणि मोबाईल दोन्ही भरणे आवश्यक आहे.")

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
            st.subheader("👥 सर्व नोंदणीकृत सहभागी")
            df_parts = pd.read_sql_query("SELECT id as क्र, name as नाव, mobile as मोबाईल FROM participants ORDER BY id ASC", conn)
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
# २. सहभागी (USER) पॅनल
# -------------------------------------------------------------
else:
    st.title("🚩 नवरात्र उत्सव - देवीची पूजा व प्रार्थना बोली")

    # नोंदणीकृत सहभागींची यादी मिळवणे
    cursor.execute("SELECT name, mobile FROM participants ORDER BY name ASC")
    participants = cursor.fetchall()

    if not participants:
        st.warning("सध्या सहभागींची नोंदणी पूर्ण झालेली नाही. कृपया व्यवस्थापकांशी (Admin) संपर्क साधा.")
    else:
        # सध्या चालू असलेली सर्वोच्च रक्कम मिळवणे (नाव न दाखवता)
        cursor.execute("SELECT MAX(amount) FROM bids")
        max_res = cursor.fetchone()[0]
        current_highest = max_res if max_res is not None else 0

        # वर ठळकपणे सध्या चालू असलेली एकूण रक्कम दाखवणे
        st.info(f"### 📢 सध्या चालू असलेली सर्वोच्च बोली रक्कम: **₹{current_highest}**")

        col_bid, col_history = st.columns([1, 1])

        with col_bid:
            st.subheader("तुमची बोली लावा")
            user_options = [f"{p[0]} ({p[1]})" for p in participants]
            selected_user_str = st.selectbox("तुमचे नाव निवडा:", user_options)

            idx = user_options.index(selected_user_str)
            user_name = participants[idx][0]
            user_mobile = participants[idx][1]

            min_bid = current_highest + 50 if current_highest > 0 else 100
            
            with st.form("user_bid_form", clear_on_submit=True):
                bid_amount = st.number_input("बोली रक्कम (₹)", min_value=min_bid, value=min_bid, step=50)
                submit_bid = st.form_submit_button("बोली निश्चित करा", type="primary")

                if submit_bid:
                    if bid_amount <= current_highest:
                        st.error(f"रक्कम सध्या चालू असलेल्या सर्वोच्च रकमेपेक्षा (₹{current_highest}) जास्त असावी.")
                    else:
                        now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                        cursor.execute(
                            "INSERT INTO bids (timestamp, bidder_name, mobile, amount) VALUES (?, ?, ?, ?)",
                            (now, user_name, user_mobile, bid_amount)
                        )
                        conn.commit()
                        st.success(f"तुमची ₹{bid_amount} ची बोली यशस्वीरित्या नोंदवली गेली!")
                        st.rerun()

        with col_history:
            st.subheader("📜 फक्त तुमच्या बोलींचा इतिहास")
            # फक्त निवडलेल्या व्यक्तीचा इतिहास दाखवणे
            df_my_bids = pd.read_sql_query(
                "SELECT timestamp as वेळ, amount as रक्कम FROM bids WHERE bidder_name = ? AND mobile = ? ORDER BY id DESC",
                conn,
                params=(user_name, user_mobile)
            )

            if not df_my_bids.empty:
                st.dataframe(df_my_bids, use_container_width=True, hide_index=True)
            else:
                st.write("तुम्ही अद्याप कोणतीही बोली लावलेली नाही.")
