import streamlit as st
import time
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from fake_news_detector import FakeNewsDetector

st.set_page_config(
    page_title="سامانه حقیقت‌یاب هوشمند",
    page_icon="⚖️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .main {direction: rtl; font-family: 'Vazir', sans-serif;}
    h1, h2, h3 {text-align: center; color: #2E86C1;}
    .stAlert {direction: rtl; text-align: right;}
    .stTextInput > div > div > input {direction: rtl; text-align: right;}
    div[data-testid="stMarkdownContainer"] {direction: rtl; text-align: right;}
    .reportview-container .main .block-container{padding-top: 2rem;}
    .stCheckbox {direction: rtl; text-align: right;}
</style>
""", unsafe_allow_html=True)

st.title("⚖️ سامانه تشخیص اخبار جعلی")
st.markdown("---")

if 'detector' not in st.session_state:
    with st.spinner('در حال بارگذاری مدل‌های هوش مصنوعی...'):
        st.session_state['detector'] = FakeNewsDetector()
    st.success("سیستم آماده است!")

query = st.text_area("خبر یا ادعای مورد نظر را وارد کنید:", height=100, placeholder="مثال: قیمت بنزین فردا ۵۰۰۰ تومان می‌شود...")

col1, col2 = st.columns([1, 3])
with col2:
    use_llm = st.checkbox("استفاده از هوش مصنوعی (LLM) برای تحلیل عمیق", value=True, help="در صورت غیرفعال کردن، سیستم فقط بر اساس آمار و گراف نظر می‌دهد (سریع‌تر).")

if st.button("بررسی حقیقت 🔍"):
    if not query:
        st.warning("لطفاً متنی وارد کنید.")
    else:
        status_placeholder = st.empty()
        status_placeholder.info("⏳ در حال جستجو در پایگاه داده و تحلیل محتوا...")
        
        start_time = time.time()
        
        real_connection_status = st.session_state['detector'].is_connected
        
        if not use_llm:
            st.session_state['detector'].is_connected = False
        
        try:
            result = st.session_state['detector'].verify(query)
        finally:
            st.session_state['detector'].is_connected = real_connection_status

        end_time = time.time()
        duration = end_time - start_time
        
        status_placeholder.empty()

        if result:
            verdict = result.get("status", "Unknown")
            confidence = result.get("confidence", 0)
            reasoning = result.get("reasoning", "")
            
            if verdict == "Verified":
                st.success(f"✅ **تایید شده (واقعی)** - اطمینان: {confidence}%")
            elif verdict == "Fake":
                st.error(f"⛔ **جعلی (Fake)** - اطمینان: {confidence}%")
            else:
                st.warning(f"⚠️ **مشکوک / غیرقابل تایید** - اطمینان: {confidence}%")
            
            st.markdown("### 🧠 استدلال سیستم:")
            st.info(reasoning)
            
            st.markdown("---")
            st.markdown(f"⏱️ زمان پردازش: {duration:.2f} ثانیه")
            
            evidence_docs = st.session_state['detector'].search_engine.search(query, top_k=3)
            
            if evidence_docs:
                st.markdown("### 📄 مستندات یافت شده:")
                for i, doc in enumerate(evidence_docs, 1):
                    with st.expander(f"سند {i}: {doc.get('title', 'بدون عنوان')}"):
                        source = doc.get('source', 'نامشخص')
                        score = doc.get('score', 0)
                        
                        tag = "⭐ منبع معتبر (High Authority)" if doc.get('graph_score', 0) > 0.001 else "منبع معمولی"
                        
                        st.markdown(f"**منبع:** {source} | {tag}")
                        st.markdown(f"**امتیاز نهایی:** `{score:.4f}`")
                        st.markdown(f"**تاریخ:** {doc.get('publish_date', '-')}")
                        st.markdown(f"**خلاصه متن:** {doc.get('content', '')[:300]}...")
                        if doc.get('url'):
                            st.markdown(f"[مشاهده لینک اصلی]({doc.get('url')})")
            else:
                st.write("هیچ سند مشابهی در پایگاه داده یافت نشد.")
                
        else:
            st.error("خطا در پردازش. لطفاً مجدد تلاش کنید.")
