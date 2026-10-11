import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# डेटाबेस जोडणी
conn = sqlite3.connect("navratri_bids.db", check_same_thread=False)
cursor = conn.cursor()

# सहभागी व्यक्तींचा टेबल
cursor.execute('''
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        mobile TEXT
    )
''')

# बोलींचा टेबल
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
st.title("🚩 नवरात्र उत्सव - देवीची पूजा व प्रार्थना बोली")

# डाव्या बाजूला साइडबारमध्ये सहभागी जोडण्याची सोय
with st.sidebar:
    st.header("👥 सहभागी व्यवस्थापन")
    with st.form("add_participant_form", clear_on_submit=True):
        p_name = st.text_input("सहभागीचे नाव")
        p_mobile = st.text_input("मोबाईल क्रमांक")
        add_btn = st.form_submit_button("सहभागी जोडा")

        if add_btn:
            if p_name.strip() and p_mobile.strip():
                try:
                    cursor.execute("INSERT INTO participants (name, mobile) VALUES (?, ?)", (p_name.strip(), p_mobile.strip()))
                    conn.commit()
                    st.success(f"{p_name} यादीत जोडले गेले!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("हे नाव आधीच यादीत नोंदवलेले आहे.")
            else:
                st.warning("नाव आणि मोबाईल दोन्ही भरा.")

    # सध्या नोंदवलेले सहभागी
    cursor.execute("SELECT name, mobile FROM participants ORDER BY id ASC")
    all_participants = cursor.fetchall()
    st.write(f"एकूण नोंदणीकृत सहभागी: **{len(all_participants)}**")
    if all_participants:
        df_p = pd.DataFrame(all_participants, columns=["नाव", "मोबाईल"])
        st.dataframe(df_p, use_container_width=True, hide_index=True)

# सध्याची सर्वोच्च बोली शोधणे
cursor.execute("SELECT bidder_name, amount FROM bids ORDER BY amount DESC LIMIT 1")
top_bid = cursor.fetchone()
current_max = top_bid[1] if top_bid else 0
current_winner = top_bid[0] if top_bid else "अद्याप कोणी नाही"

col1, col2 = st.columns([1, 1])

# उजव्या बाजूला / मुख्य स्क्रीनवर बोली लावणे
with col1:
    st.subheader("⚡ थेट बोली लावा")

    if not all_participants:
        st.info("👈 कृपया आधी डाव्या बाजूच्या मेनूमधून सहभागींची नावे नोंदवा.")
    else:
        participant_names = [p[0] for p in all_participants]
        selected_name = st.selectbox("सहभागी निवडा:", participant_names)

        # निवडलेल्या सहभागीचा मोबाईल नंबर मिळवणे
        selected_mobile = next(p[1] for p in all_participants if p[0] == selected_name)

        st.info(f"सध्याची सर्वोच्च बोली: **₹{current_max}**")

        # झटपट रक्कम वाढवण्यासाठी पर्याय
        st.write("रक्कम वाढवण्यासाठी निवडा किंवा थेट टाईप करा:")
        
        c_btn1, c_btn2, c_btn3 = st.columns(3)
        add_amount = 0
        
        bid_amount = st.number_input(
            "बोली रक्कम (₹)",
            min_value=current_max + 50,
            value=current_max + 50,
            step=50
        )

        # झटपट वाढीव रक्कम टाकण्यासाठी बटणे
        if c_btn1.button(f"+ ₹100 (₹{current_max + 100})"):
            bid_amount = current_max + 100
        if c_btn2.button(f"+ ₹200 (₹{current_max + 200})"):
            bid_amount = current_max + 200
        if c_btn3.button(f"+ ₹500 (₹{current_max + 500})"):
            bid_amount = current_max + 500

        if st.button("🔴 बोली निश्चित करा (Confirm Bid)", type="primary", use_container_width=True):
            if bid_amount <= current_max:
                st.error(f"रक्कम सध्याच्या सर्वोच्च बोलीपेक्षा (₹{current_max}) जास्त असावी.")
            else:
                now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                cursor.execute(
                    "INSERT INTO bids (timestamp, bidder_name, mobile, amount) VALUES (?, ?, ?, ?)",
                    (now, selected_name, selected_mobile, bid_amount)
                )
                conn.commit()
                st.success(f"{selected_name} यांची ₹{bid_amount} ची बोली नोंदवली गेली!")
                st.rerun()

with col2:
    st.subheader("🏆 सध्याचा विजेता")
    st.metric(label=f"विजेते: {current_winner}", value=f"₹{current_max}")

    st.markdown("---")
    st.subheader("📋 बोलींचा इतिहास")

    df_bids = pd.read_sql_query(
        "SELECT timestamp as वेळ, bidder_name as नाव, mobile as मोबाईल, amount as रक्कम FROM bids ORDER BY id DESC",
        conn
    )

    if not df_bids.empty:
        st.dataframe(df_bids, use_container_width=True, hide_index=True)
        csv = df_bids.to_csv(index=False).encode('utf-8')
        st.download_button("Excel/CSV मध्ये डाऊनलोड करा", data=csv, file_name="devi_pooja_prarthana_bids.csv", mime="text/csv")
    else:
        st.info("अद्याप कोणतीही बोली आलेली नाही.")
