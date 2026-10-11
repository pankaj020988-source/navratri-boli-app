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

# बोलींचा टेबल
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

# सहभागी भाविक आणि त्यांचा गुप्त पिन
cursor.execute("""
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        mobile TEXT UNIQUE,
        pin TEXT
    )
""")

# कॉलम तपासणी
cursor.execute("PRAGMA table_info(bids)")
cols = [col[1] for col in cursor.fetchall()]
if "bid_date" not in cols:
    cursor.execute("ALTER TABLE bids ADD COLUMN bid_date TEXT DEFAULT ''")
if "session_day" not in cols:
    cursor.execute("ALTER TABLE bids ADD COLUMN session_day TEXT DEFAULT 'दिवस १'")

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

st.set_page_config(page_title="देवीची पूजा व प्रार्थना बोली", layout="centered")

# दर ३ सेकंदांनी रिफ्रेश
st_autorefresh(interval=3000, key="auto_refresher")

ADMIN_PASSWORD = "admin123"

def get_settings():
    c_conn = get_db()
    c = c_conn.cursor()
    c.execute("SELECT current_day, is_active FROM settings WHERE id = 1")
    res = c.fetchone()
    c_conn.close()
    if res:
        return str(res[0]), bool(res[1])
    return "दिवस १", True

current_day, is_bidding_active = get_settings()

def get_highest_bid_for_day(day):
    c_conn = get_db()
    c = c_conn.cursor()
    c.execute("SELECT MAX(amount) FROM bids WHERE session_day = ?", (day,))
    val = c.fetchone()[0]
    c_conn.close()
    return int(val) if val is not None else 0

current_highest = get_highest_bid_for_day(current_day)

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

        st.title("🚩 Admin व्यवस्थापन व नियंत्रण कक्ष")

        st.subheader("⚙️ बोली सत्र नियंत्रण")
        ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 2, 1])

        days_list = [f"दिवस {i}" for i in range(1, 11)]

        with ctrl_col1:
            selected_new_day = st.selectbox(
                "सध्याचा दिवस निवडा (बोलीसाठी):",
                days_list,
                index=days_list.index(current_day) if current_day in days_list else 0
            )

        with ctrl_col2:
            new_status = st.radio(
                "बोली स्थिती:",
                ["बोली सुरू ठेवा (Active)", "बोली बंद करा (Closed)"],
                index=0 if is_bidding_active else 1,
                horizontal=True
            )
            status_val = 1 if new_status == "बोली सुरू ठेवा (Active)" else 0

        with ctrl_col3:
            st.write("")
            st.write("")
            if st.button("सेटिंग्ज सेव्ह करा", type="primary"):
                c_conn = get_db()
                c = c_conn.cursor()
                c.execute("UPDATE settings SET current_day = ?, is_active = ? WHERE id = 1", (selected_new_day, status_val))
                c_conn.commit()
                c_conn.close()
                st.toast("सेटिंग्ज अपडेट झाल्या!", icon="✅")
                st.rerun()

        st.markdown("---")

        c_conn = get_db()
        c = c_conn.cursor()
        c.execute("SELECT bidder_name, mobile, amount FROM bids WHERE session_day = ? ORDER BY amount DESC LIMIT 1", (current_day,))
        top_bid = c.fetchone()
        c_conn.close()

        st.subheader(f"🏆 {current_day} चा विजेता (Live)")
        if top_bid:
            st.metric(label=f"विजेता: {top_bid[0]} ({top_bid[1]})", value=f"₹{top_bid[2]}")
        else:
            st.metric(label=f"{current_day} साठी अद्याप कोणतीही बोली नाही", value="₹0")

        st.markdown("---")

        st.subheader("📊 अहवाल आणि डेटा डाऊनलोड")
        c_conn = get_db()
        df_all = pd.read_sql_query(
            "SELECT timestamp as वेळ, bid_date as तारीख, session_day as दिवस, bidder_name as नाव, mobile as मोबाईल, amount as रक्कम FROM bids ORDER BY id DESC",
            c_conn
        )
        c_conn.close()

        if not df_all.empty:
            avail_days = sorted(list(df_all["दिवस"].dropna().unique()))
            view_day = st.selectbox("कोणत्या दिवसाचा अहवाल पाहायचा आहे?", ["सर्व दिवस एकत्र"] + avail_days)

            if view_day == "सर्व दिवस एकत्र":
                st.dataframe(df_all, use_container_width=True, hide_index=True)
                csv = df_all.to_csv(index=False).encode('utf-8')
                st.download_button("सर्व दिवसांचा डेटा (CSV) डाऊनलोड करा", data=csv, file_name="all_navratri_bids.csv", mime="text/csv")
            else:
                filtered_df = df_all[df_all["दिवस"] == view_day]
                st.dataframe(filtered_df, use_container_width=True, hide_index=True)
                csv_day = filtered_df.to_csv(index=False).encode('utf-8')
                st.download_button(f"{view_day} चा डेटा (CSV) डाऊनलोड करा", data=csv_day, file_name=f"{view_day}_bids.csv", mime="text/csv")
        else:
            st.info("अद्याप कोणतीही बोली नोंदवलेली नाही.")

# ==========================================
# २. सहभागी (USER) पॅनल (४ अंकी गुप्त पिन सुरक्षा)
# ==========================================
else:
    st.title("🚩 नवरात्र उत्सव - देवीची पूजा व प्रार्थना बोली")
    st.markdown(f"#### 🗓️ **{current_day}**")

    if not is_bidding_active:
        st.warning(f"⚠️ {current_day} साठीची बोली आता समाप्त झाली आहे. पुढील सत्रासाठी कृपया व्यवस्थापनाशी संपर्क साधा.")
        if current_highest > 0:
            st.success(f"🏆 {current_day} ची अंतिम सर्वोच्च बोली: ₹{current_highest}")
    else:
        st.info(f"### 📢 {current_day} चालू सर्वोच्च बोली: **₹{current_highest}**  *(🔴 Live)*")

        st.subheader("📝 तुमची माहिती व सुरक्षित पिन")
        u_mobile = st.text_input("१० अंकी मोबाईल क्रमांक:", max_chars=10, key="mob_key", placeholder="उदा. 9876543210").strip()

        # मोबाईल नंबरवरून युजर आधी नोंदणीकृत आहे का ते तपासणे
        existing_user = None
        if len(u_mobile) == 10 and u_mobile.isdigit():
            c_conn = get_db()
            c = c_conn.cursor()
            c.execute("SELECT name, pin FROM participants WHERE mobile = ?", (u_mobile,))
            existing_user = c.fetchone()
            c_conn.close()

        if existing_user:
            st.info(f"नोंदणीकृत नाव: **{existing_user[0]}**")
            u_name = existing_user[0]
            u_pin = st.text_input("तुमचा ४ अंकी गुप्त पिन टाका:", type="password", max_chars=4, key="pin_exist_key", placeholder="****").strip()
            is_new = False
        else:
            u_name = st.text_input("भाविकाचे पूर्ण नाव:", key="name_new_key", placeholder="उदा. पंकज देसाई").strip()
            u_pin = st.text_input("स्वतःचा नवीन ४ अंकी गुप्त पिन तयार करा:", type="password", max_chars=4, key="pin_new_key", placeholder="उदा. 1234").strip()
            is_new = True

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

        # बोली सुरक्षित सबमिट करण्याचे अंतर्गत फंक्शन
        def process_user_bid(amount_to_bid):
            if len(u_mobile) < 10 or not u_mobile.isdigit():
                st.error("कृपया योग्य १० अंकी मोबाईल क्रमांक टाका.")
                return
            if not u_name:
                st.error("कृपया तुमचे नाव टाका.")
                return
            if len(u_pin) != 4 or not u_pin.isdigit():
                st.error("कृपया बरोबर ४ अंकी गुप्त पिन प्रविष्ट करा.")
                return

            c_conn = get_db()
            c = c_conn.cursor()

            # पिन पडताळणी
            if not is_new:
                if str(existing_user[1]) != str(u_pin):
                    st.error("❌ चुकीचा गुप्त पिन! दुसऱ्याच्या मोबाईल नंबरवरून बोली लावता येणार नाही.")
                    c_conn.close()
                    return
            else:
                # नवीन युजर नोंदणी
                c.execute("INSERT OR REPLACE INTO participants (name, mobile, pin) VALUES (?, ?, ?)", (u_name, u_mobile, u_pin))
                c_conn.commit()

            # बोली रक्कम तपासणी
            c.execute("SELECT MAX(amount) FROM bids WHERE session_day = ?", (current_day,))
            latest = c.fetchone()[0] or 0
            if amount_to_bid <= latest:
                st.error(f"दुसऱ्या भाविकाने नुकतीच बोली ₹{latest} केली आहे. कृपया पुन्हा टॅप करा.")
                c_conn.close()
                return

            now_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            now_date = datetime.now().strftime("%d-%m-%Y")
            c.execute(
                "INSERT INTO bids (timestamp, bid_date, session_day, bidder_name, mobile, amount) VALUES (?, ?, ?, ?, ?, ?)",
                (now_time, now_date, current_day, u_name, u_mobile, amount_to_bid)
            )
            c_conn.commit()
            c_conn.close()
            st.success(f"✅ अभिनंदन {u_name}! तुमची ₹{amount_to_bid} ची बोली यशस्वीरित्या नोंदवली गेली आहे.")
            st.rerun()

        if add_clicked is not None:
            process_user_bid(add_clicked)

        st.write("किंवा रक्कम थेट टाका:")
        min_c = current_highest + 50 if current_highest > 0 else 100
        with st.form("custom_form", clear_on_submit=True):
            custom_amt = st.number_input("इच्छित रक्कम (₹)", min_value=min_c, value=min_c, step=50)
            if st.form_submit_button("बोली निश्चित करा", type="primary"):
                process_user_bid(custom_amt)
