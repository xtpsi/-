import streamlit as st
from datetime import datetime, date

# =========================================================
# 1. تحسين واجهة المستخدم وقوائم التنقل (Tailwind & CSS)
# =========================================================
st.set_page_config(page_title="صادق الخياط", page_icon="✂️", layout="wide")

st.markdown("""
    <!-- استدعاء Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    
    <style>
    /* الاتجاه العام والخلفيات */
    .stApp {
        background-color: #f8fafc;
        direction: rtl;
        text-align: right;
    }
    
    /* 2. تحسين القائمة الجانبية (Sidebar) */
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-left: 1px solid #e2e8f0;
        box-shadow: 2px 0 10px rgba(0,0,0,0.03);
    }
    
    section[data-testid="stSidebar"] .stRadio > div {
        gap: 8px;
    }
    
    /* تنسيق خيارات القائمة الجانبية كبطاقات عصرية */
    section[data-testid="stSidebar"] label {
        background-color: #f1f5f9;
        border-radius: 10px;
        padding: 10px 14px !important;
        border: 1px solid #e2e8f0;
        transition: all 0.2s ease;
        cursor: pointer;
        font-weight: 600;
        color: #334155 !important;
    }
    
    section[data-testid="stSidebar"] label:hover {
        background-color: #e2e8f0;
        border-color: #cbd5e1;
    }

    /* 3. ترتيب البطاقات الرئيسية والحقول */
    div[data-testid="stVerticalBlock"] > div {
        background-color: #ffffff;
        border-radius: 14px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03);
        padding: 1.25rem;
        margin-bottom: 0.5rem;
    }
    
    /* تجاوب الواجهة مع شاشات الجوال */
    @media (max-width: 768px) {
        .main .block-container {
            padding: 1rem !important;
        }
        div[data-testid="stVerticalBlock"] > div {
            padding: 0.85rem;
        }
    }

    /* 4. تصميم أزرار وحقول الإدخال */
    .stTextInput input, .stSelectbox select, .stTextArea textarea, .stDateInput input {
        border-radius: 8px !important;
        border: 1px solid #cbd5e1 !important;
        padding: 0.6rem 0.8rem !important;
        background-color: #fafafa !important;
    }
    
    .stTextInput input:focus, .stSelectbox select:focus {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 3px #bfdbfe !important;
    }

    .stButton > button {
        background-color: #2563eb !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        background-color: #1d4ed8 !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
    }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# 2. كود دالة تحويل التاريخ الآمنة (لحل خطأ TypeError)
# =========================================================
def safe_parse_date(date_val):
    """دالة لضمان معالجة وتدقيق التاريخ بدون أخطاء"""
    if isinstance(date_val, date):
        return date_val
    elif isinstance(date_val, datetime):
        return date_val.date()
    elif isinstance(date_val, str) and date_val.strip():
        try:
            return datetime.strptime(date_val.strip(), "%Y-%m-%d").date()
        except ValueError:
            return date.today()
    return date.today()

# مثال لاستخدام الدالة عند استخراج delivery_date في الكود لديك:
# d_val = safe_parse_date(row["delivery_date"])
