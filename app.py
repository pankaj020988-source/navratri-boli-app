import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# डेटाबेस तयार करणे व जोडणे
conn = sqlite3.connect("navratri_bids.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS bids (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        seva_type TEXT,
        bidder_name TEXT,
        mobile TEXT,
        amount INTEGER
    )
''')
conn.commit()

st.set_page_config(page_title="देवीची पूजा व प्रार्थना बोली", layout="wide")
st.title("🚩 नवरात्र उत्सव - पूजा व प्रार्थना बोली नोंदणी")

# फक्त दोनच पर्याय
seva_options = ["देवीची पूजा", "देवीची प्रार्थना व आरती"]

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("नवीन बोली नोंदवा")
    with st.form("bidding_form", clear_on_submit=True):
        seva = st.radio("सेवा निवडा:", seva_options, horizontal=True)
        name = st.text_input("भाविकाचे नाव")
        mobile = st.text_input("मोबाईल क्रमांक")
        amount = st.number_input("बोली रक्कम (₹)", min_value=100, step=50)
        submit = st.form_submit_button("बोली निश्चित करा")

        if submit:
            if not name.strip() or not mobile.strip():
                st.error("कृपया नाव आणि मोबाईल क्रमांक प्रविष्ट करा.")
            else:
                # निवडलेल्या सेवेची सर्वोच्च बोली तपासणे
                cursor.execute("SELECT MAX(amount) FROM bids WHERE seva_type = ?", (seva,))
                current_max = cursor.fetchone()[0]
                current_max = current_max if current_max is not None else 0

                if amount <= current_max:
                    st.error(f"रक्कम सध्याच्या सर्वोच्च बोलीपेक्षा (₹{current_max}) जास्त असावी.")
                else:
                    now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    cursor.execute(
                        "INSERT INTO bids (timestamp, seva_type, bidder_name, mobile, amount) VALUES (?, ?, ?, ?, ?)",
                        (now, seva, name.strip(), mobile.strip(), amount)
                    )
                    conn.commit()
                    st.success(f"{name} यांची ₹{amount} ची बोली नोंदवली गेली!")
                    st.rerun()

with col2:
    st.subheader("🏆 सध्याची सर्वोच्च बोली (Current Highest)")
    
    # दोन्ही सेवांसाठी सर्वोच्च बोली कार्ड्स स्वरूपात दाखवणे
    c1, c2 = st.columns(2)
    for idx, s_name in enumerate(seva_options):
        cursor.execute("SELECT bidder_name, amount FROM bids WHERE seva_type = ? ORDER BY amount DESC LIMIT 1", (s_name,))
        top_bid = cursor.fetchone()
        target_col = c1 if idx == 0 else c2
        with target_col:
            st.markdown(f"**{s_name}**")
            if top_bid:
                st.metric(label=f"विजेते: {top_bid[0]}", value=f"₹{top_bid[1]}")
            else:
                st.metric(label="अद्याप बोली नाही", value="₹0")

    st.markdown("---")
    st.subheader("📋 सर्व बोलींचा इतिहास")
    
    df = pd.read_sql_query("SELECT timestamp as वेळ, seva_type as सेवा, bidder_name as नाव, mobile as मोबाईल, amount as रक्कम FROM bids ORDER BY id DESC", conn)
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Excel/CSV मध्ये डेटा डाऊनलोड करा", data=csv, file_name="pooja_prarthana_bids.csv", mime="text/csv")
    else:
        st.info("अद्याप कोणतीही बोली आलेली नाही.")
