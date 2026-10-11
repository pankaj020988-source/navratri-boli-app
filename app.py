import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

def get_db():
    return sqlite3.connect("navratri_bids.db", check_same_thread=False)

conn = get_db()
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS bids (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        bid_date TEXT,
        session_day TEXT,
        bidder_name TEXT,
        mobile TEXT,
        amount INTEGER
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        mobile TEXT UNIQUE,
        pin TEXT
    )
""")

try:
    cursor.execute("ALTER TABLE bids ADD COLUMN bid_date TEXT DEFAULT ''")
except Exception:
    pass

try:
    cursor.execute("ALTER TABLE bids ADD COLUMN session_day TEXT DEFAULT 'दिवस १'")
except Exception:
    pass

try:
    cursor.execute("ALTER TABLE participants ADD COLUMN pin TEXT DEFAULT ''")
except Exception:
    pass

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

st.set_page_config(page_title="देवीची पूजा व प्रार्थना बोली", layout="wide")

st_autorefresh(interval=3000, key="navratri_refresh_timer")

ADMIN_PWD = "admin123"

def get_settings():
    c_conn = get_db()
    c = c_conn.cursor()
    c.execute("SELECT current_day, is_active FROM settings WHERE id = 1")
    row = c.fetchone()
    c_conn.close()
    if row:
        return str(row[0]), bool(row[1])
    return "दिवस १", True

current_day, is_bidding_active = get_settings()

def get_highest_bid(day):
    c_conn = get_db()
    c = c_conn.cursor()
    c.execute("SELECT MAX(amount) FROM bids WHERE session_day = ?", (day,))
    val = c.fetchone()[0]
    c_conn.close()
    return int(val) if val is not None else 0

current_highest = get_highest_bid(current_day)

st.sidebar.title("🔐 प्रणाली")
role = st.sidebar.radio("भूमिका निवडा:", ["सहभागी (User)", "Admin (प्रशासक)"])

# ==========================================
# 1. ADMIN PANEL
# ==========================================
if role == "Admin (प्रशासक)":
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False

    if not st.session_state.admin_logged_in:
        st.subheader("Admin लॉगिन")
        with st.form("admin_form"):
            pwd = st.text_input("पासवर्ड प्रविष्ट करा", type="password")
            if st.form_submit_button("लॉगिन"):
                if pwd == ADMIN_PWD:
                    st.session_state.admin_logged_in = True
                    st.rerun()
                else:
                    st.error("चुकीचा पासवर्ड!")
    else:
        st.sidebar.success("Admin लॉगिन आहे")
        if st.sidebar.button("लॉगआउट"):
            st.session_state.admin_logged_in = False
            st.rerun()

        st.title("🚩 Admin नियंत्रण कक्ष")

        st.subheader("⚙️ सत्र नियंत्रण")
        c1, c2, c3 = st.columns([2, 2, 1])
        days_list = [f"दिवस {i}" for i in range(1, 11)]

        with c1:
            sel_day = st.selectbox(
                "सध्याचा दिवस निवडा:",
                days_list,
                index=days_list.index(current_day) if current_day in days_list else 0
            )

        with c2:
            st_opt = st.radio(
                "बोली स्थिती:",
                ["बोली सुरू ठेवा (Active)", "बोली बंद करा (Closed)"],
                index=0 if is_bidding_active else 1,
                horizontal=True
            )
            act_val = 1 if st_opt == "बोली सुरू ठेवा (Active)" else 0

        with c3:
            st.write("")
            st.write("")
            if st.button("सेव्ह करा", type="primary"):
                c_conn = get_db()
                c = c_conn.cursor()
                c.execute("UPDATE settings SET current_day = ?, is_active = ? WHERE id = 1", (sel_day, act_val))
                c_conn.commit()
                c_conn.close()
                st.toast("सेटिंग्ज अपडेट झाल्या!", icon="✅")
                st.rerun()

        st.markdown("---")

        c_conn = get_db()
        c = c_conn.cursor()
        c.execute("SELECT bidder_name, mobile, amount FROM bids WHERE session_day = ? ORDER BY amount DESC LIMIT 1", (current_day,))
        top = c.fetchone()
        c_conn.close()

        st.subheader(f"🏆 {current_day} चा विजेता (Live)")
        if top:
            st.metric(label=f"विजेता: {top[0]} ({top[1]})", value=f"₹{top[2]}")
        else:
            st.metric(label=f"{current_day} साठी अद्याप कोणतीही बोली नाही", value="₹0")

        st.markdown("---")

        st.subheader("📊 अहवाल आणि डाऊनलोड")
        c_conn = get_db()
        df_all = pd.read_sql_query(
            "SELECT timestamp as वेळ, bid_date as तारीख, session_day as दिवस, bidder_name as नाव, mobile as मोबाईल, amount as रक्कम FROM bids ORDER BY id DESC",
            c_conn
        )
        c_conn.close()

        if not df_all.empty:
            avail_days = sorted(list(df_all["दिवस"].dropna().unique()))
            view_day = st.selectbox("दिवस निवडा:", ["सर्व दिवस एकत्र"] + avail_days)

            if view_day == "सर्व दिवस एकत्र":
                st.dataframe(df_all, use_container_width=True, hide_index=True)
                csv_data = df_all.to_csv(index=False).encode('utf-8')
                st.download_button("सर्व डेटा CSV डाऊनलोड", data=csv_data, file_name="all_bids.csv", mime="text/csv")
            else:
                f_df = df_all[df_all["दिवस"] == view_day]
                st.dataframe(f_df, use_container_width=True, hide_index=True)
                csv_d = f_df.to_csv(index=False).encode('utf-8')
                st.download_button(f"{view_day} CSV डाऊनलोड", data=csv_d, file_name=f"{view_day}.csv", mime="text/csv")
        else:
            st.info("कोणतीही बोली नोंदवलेली नाही.")

# ==========================================
# 2. USER PANEL
# ==========================================
else:
    st.title("🚩 नवरात्र उत्सव - देवीची पूजा व प्रार्थना बोली")
    st.markdown(f"#### 🗓️ **{current_day}**")

    if not is_bidding_active:
        st.warning(f"⚠️ {current_day} साठीची बोली आता समाप्त झाली आहे.")
        if current_highest > 0:
            st.success(f"🏆 {current_day} ची अंतिम सर्वोच्च बोली: ₹{current_highest}")
    else:
        st.info(f"### 📢 {current_day} चालू सर्वोच्च बोली: **₹{current_highest}**  *(🔴 Live)*")

        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.subheader("📝 भाविकाची माहिती व गुप्त पिन")
            u_mobile = st.text_input("१० अंकी मोबाईल क्रमांक:", max_chars=10, key="u_mob", placeholder="उदा. 9876543210").strip()
            u_name = st.text_input("भाविकाचे पूर्ण नाव:", key="u_name", placeholder="उदा. पंकज देसाई").strip()
            u_pin = st.text_input("४ अंकी गुप्त पिन (PIN):", type="password", max_chars=4, key="u_pin", placeholder="उदा. 1234").strip()
            st.caption("टीप: पहिल्यांदा सेट केलेला ४ अंकी पिन पुढील प्रत्येक वेळी वापरावा लागेल.")

        with col_right:
            st.subheader("⚡ झटपट बोली लावा")
            st.write("रक्कम वाढवण्यासाठी खालील बटनावर टॅप करा:")

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

            st.write("किंवा रक्कम थेट टाका:")
            min_c = current_highest + 50 if current_highest > 0 else 100
            with st.form("custom_form", clear_on_submit=False):
                custom_amt = st.number_input("इच्छित रक्कम (₹)", min_value=min_c, value=min_c, step=50)
                submit_custom = st.form_submit_button("बोली निश्चित करा", type="primary")

        bid_to_process = None
        if add_clicked is not None:
            bid_to_process = add_clicked
        elif submit_custom:
            bid_to_process = custom_amt

        if bid_to_process is not None:
            if len(u_mobile) != 10 or not u_mobile.isdigit():
                st.error("कृपया योग्य १० अंकी मोबाईल क्रमांक टाका.")
            elif not u_name:
                st.error("कृपया भाविकाचे नाव टाका.")
            elif len(u_pin) != 4 or not u_pin.isdigit():
                st.error("कृपया बरोबर ४ अंकी गुप्त पिन प्रविष्ट करा.")
            else:
                c_conn = get_db()
                c = c_conn.cursor()

                c.execute("SELECT name, pin FROM participants WHERE mobile = ?", (u_mobile,))
                user_record = c.fetchone()

                pin_valid = False
                if user_record:
                    saved_pin = str(user_record[1])
                    if saved_pin == u_pin or saved_pin == "":
                        if saved_pin == "":
                            c.execute("UPDATE participants SET pin = ?, name = ? WHERE mobile = ?", (u_pin, u_name, u_mobile))
                            c_conn.commit()
                        pin_valid = True
                    else:
                        st.error("चुकीचा गुप्त पिन! या मोबाईल नंबरसाठी सेट केलेला खरा पिन टाका.")
                        c_conn.close()
                else:
                    c.execute("INSERT INTO participants (name, mobile, pin) VALUES (?, ?, ?)", (u_name, u_mobile, u_pin))
                    c_conn.commit()
                    pin_valid = True

                if pin_valid:
                    c.execute("SELECT MAX(amount) FROM bids WHERE session_day = ?", (current_day,))
                    latest = c.fetchone()[0] or 0

                    if bid_to_process <= latest:
                        st.error(f"दुसऱ्या भाविकाने नुकतीच बोली ₹{latest} केली आहे. कृपया पुन्हा टॅप करा.")
                        c_conn.close()
                    else:
                        now_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                        now_date = datetime.now().strftime("%d-%m-%Y")
                        c.execute(
                            "INSERT INTO bids (timestamp, bid_date, session_day, bidder_name, mobile, amount) VALUES (?, ?, ?, ?, ?, ?)",
                            (now_time, now_date, current_day, u_name, u_mobile, bid_to_process)
                        )
                        c_conn.commit()
                        c_conn.close()
                        st.success(f"अभिनंदन {u_name}! तुमची ₹{bid_to_process} ची बोली यशस्वीरित्या नोंदवली गेली आहे.")
                        st.rerun()
