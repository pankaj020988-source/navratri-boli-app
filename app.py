import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# डेटाबेस जोडणी आणि सुरक्षित स्कीमा अपडेट
def get_db():
    return sqlite3.connect("navratri_bids.db", check_same_thread=False)

conn = get_db()
cursor = conn.cursor()

# मूळ टेबल तयार करणे (नसल्यास)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS bids (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        bidder_name TEXT,
        mobile TEXT,
        amount INTEGER
    )
""")

# जुन्या टेबलमध्ये नवीन कॉलम नसल्यास सुरक्षितपणे जोडणे
cursor.execute("PRAGMA table_info(bids)")
columns = [info[1] for info in cursor.fetchall()]

if "bid_date" not in columns:
    cursor.execute("ALTER TABLE bids ADD COLUMN bid_date TEXT DEFAULT ''")
if "session_day" not in columns:
    cursor.execute("ALTER TABLE bids ADD COLUMN session_day TEXT DEFAULT 'दिवस १'")

# सिस्टीम सेटिंग्ज टेबल
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

# दर ३ सेकंदांनी ऑटो-रिफ्रेश
st_autorefresh(interval=3000, key="bidding_counter")

ADMIN_PASSWORD = "admin123"

# चालू सेटिंग्ज मिळवणे
def get_settings():
    c_conn = get_db()
    c = c_conn.cursor()
    c.execute("SELECT current_day, is_active FROM settings WHERE id = 1")
    res = c.fetchone()
    c_conn.close()
    if res:
        return res[0], bool(res[1])
    return "दिवस १", True

current_day, is_bidding_active = get_settings()

# चालू दिवसाची सर्वोच्च बोली
def get_highest_bid_for_day(day):
    c_conn = get_db()
    c = c_conn.cursor()
    c.execute("SELECT MAX(amount) FROM bids WHERE session_day = ?", (day,))
    val = c.fetchone()[0]
    c_conn.close()
    return int(val) if val is not None else 0

current_highest = get_highest_bid_for_day(current_day)

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

        st.title("🚩 Admin व्यवस्थापन व नियंत्रण कक्ष")

        # दिवस आणि चालू/बंद नियंत्रण
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

        # चालू दिवसाचा विजेता
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
        
        # मागील सर्व दिवसांचा कायमस्वरूपी डेटा
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
# २. सहभागी (USER) पॅनल
# ==========================================
else:
    st.title("🚩 नवरात्र उत्सव - देवीची पूजा व प्रार्थना बोली")
    st.markdown(f"#### 🗓️ **{current_day}**")

    # जर बोली बंद असेल तर
    if not is_bidding_active:
        st.warning(f"⚠️ **{current_day} साठीची बोली आता समाप्त झाली आहे.** पुढील सत्रासाठी कृपया व्यवस्थापनाशी संपर्क साधा.")
        if current_highest > 0:
            st.success(f"🏆 {current_day} ची अंतिम सर्वोच्च बोली: **₹{current_highest}**")
    else:
        st.info(f"### 📢 {current_day} चालू सर्वोच्च बोली: **₹{current_highest}**  *(🔴 Live दर ३ सेकंदांनी ऑटो-रिफ्रेश)*")

        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.subheader("📝 तुमची माहिती")
            n_in = st.text_input("भाविकाचे पूर्ण नाव:", key="p_name_val", placeholder="उदा. पंकज देसाई")
            m_in = st.text_input("१० अंकी मोबाईल क्रमांक:", key="p_mob_val", placeholder="उदा. 98xxxxxxxx")

            s1 = n_in.strip()
            s2 = m_in.strip()
            if s1.isdigit() and not s2.isdigit():
