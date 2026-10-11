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
        bidder_name TEXT,
        mobile TEXT,
        amount INTEGER
    )
''')
conn.commit()

st.set_page_config(page_title="देवीची पूजा व प्रार्थना - बोली", layout="wide")
st.title("🚩 नवरात्र उत्सव - देवीची पूजा व प्रार्थना बोली नोंदणी")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("नवीन बोली नोंदवा")
    with st.form("bidding_form", clear_on_submit=True):
        st.markdown("🎯 **सेवा:** देवीची पूजा व प्रार्थना")
        name = st.text_input("भाविकाचे नाव")
        mobile = st.text_input("मोबाईल क्रमांक")
        amount = st.number_input("बोली रक्कम (₹)", min_value=100, step=50)
        submit = st.form_submit_button("बोली निश्चित करा")

        if submit:
            if not name.strip() or not mobile.strip():
                st.error("कृपया नाव आणि मोबाईल क्रमांक प्रविष्ट करा.")
            else:
                # सध्याची सर्वोच्च बोली तपासणे
                cursor.execute("SELECT MAX(amount) FROM bids")
                current_max = cursor.fetchone()[0]
                current_max = current_max if current_max is not None else 0

                if amount <= current_max:
                    st.error(f"रक्कम सध्याच्या सर्वोच्च बोलीपेक्षा (₹{current_max}) जास्त असावी.")
                else:
                    now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    cursor.execute(
                        "INSERT INTO bids (timestamp, bidder_name, mobile, amount) VALUES (?, ?, ?, ?)",
                        (now, name.strip(), mobile.strip(), amount)
                    )
                    conn.commit()
                    st.success(f"{name} यांची ₹{amount} ची बोली यशस्वीरित्या नोंदवली गेली!")
                    st.rerun()

with col2:
    st.subheader("🏆 सध्याची सर्वोच्च बोली")
    cursor.execute("SELECT bidder_name, amount FROM bids ORDER BY amount DESC LIMIT 1")
    top_bid = cursor.fetchone()

    if top_bid:
        st.metric(label=f"सध्याचे विजेते: {top_bid[0]}", value=f"₹{top_bid[1]}")
    else:
        st.metric(label="अद्याप कोणतीही बोली नाही", value="₹0")

    st.markdown("---")
    st.subheader("📋 बोलींचा इतिहास")
    
    df = pd.read_sql_query("SELECT timestamp as वेळ, bidder_name as नाव, mobile as मोबाईल, amount as रक्कम FROM bids ORDER BY id DESC", conn)
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        csv
