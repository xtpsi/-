import io
import os
import sqlite3
import urllib.parse
from datetime import datetime, date

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# 1. إعداد الصفحة وتلغية القائمة الجانبية بالكامل
# ==========================================
st.set_page_config(page_title="صادق الخياط", page_icon="✂️", layout="wide", initial_sidebar_state="collapsed")

# إخفاء القائمة الجانبية وتنسيق الواجهة الرئيسية للجوال والحاسبة
st.markdown("""
    <style>
    /* إخفاء القائمة الجانبية وأزرار التحكم بها */
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    button[aria-label="Toggle sidebar"] {
        display: none !important;
    }
    
    /* اتجاه وخلفية الصفحة */
    .stApp {
        background-color: #f8fafc;
        direction: rtl;
        text-align: right;
    }
    
    /* تقليل المسافات العلوية للـ Mobile */
    .main .block-container {
        padding-top: 1.5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }

    /* تحسين شكل التبويبات الرئيسية (Tabs) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #ffffff;
        padding: 8px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        display: flex;
        justify-content: space-around;
        overflow-x: auto;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        border-radius: 8px;
        background-color: #f1f5f9;
        color: #334155;
        font-size: 15px;
        font-weight: bold;
        border: 1px solid #cbd5e1;
        flex-grow: 1;
        text-align: center;
    }

    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: white !important;
        border-color: #2563eb !important;
    }

    /* تصميم البطاقات وحاويات البيانات */
    div[data-testid="stVerticalBlock"] > div {
        background-color: #ffffff;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }

    /* تصميم الأزرار وحقول الإدخال */
    .stTextInput input, .stSelectbox select, .stTextArea textarea, .stDateInput input {
        border-radius: 8px !important;
        border: 1px solid #cbd5e1 !important;
    }

    .stButton > button {
        background-color: #2563eb !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: bold;
        width: 100%;
        padding: 0.6rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. إعدادات قاعدة البيانات والدوال
# ==========================================
DB_NAME = "tailor_master.db"
SHOP_NAME = "صادق الخياط"

STATUSES = ["قيد الانتظار", "جاري القص", "جاري التفصيل", "جاري الكي", "جاهز للاستلام", "تم التسليم"]

def safe_parse_date(date_val):
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

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            phone TEXT,
            item_type TEXT,
            status TEXT,
            notes TEXT,
            delivery_date TEXT,
            total_price REAL DEFAULT 0,
            paid_amount REAL DEFAULT 0,
            remaining_amount REAL DEFAULT 0,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 3. الهيدر الرئيسي للتطبيق
# ==========================================
st.markdown(f"<h2 style='text-align: center; color: #1e293b; margin-bottom: 0px;'>✂️ {SHOP_NAME}</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; font-size: 14px;'>نظام إدارة الطلبات والقياسات والحسابات</p>", unsafe_allow_html=True)

# ==========================================
# 4. القائمة الرئيسية على شكل أيقونات/تبويبات علوية
# ==========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 التحكم",
    "➕ إضافة",
    "📑 الطلبات",
    "💵 الديون",
    "🔍 البحث"
])

# ------------------------------------------
# التبويب الأول: لوحة التحكم
# ------------------------------------------
with tab1:
    conn = get_connection()
    df_orders = pd.read_sql_query("SELECT * FROM orders", conn)
    conn.close()

    col1, col2, col3 = st.columns(3)
    col1.metric("إجمالي الطلبات", len(df_orders))
    col2.metric("قيد الانتظار", len(df_orders[df_orders['status'] == 'قيد الانتظار']) if not df_orders.empty else 0)
    col3.metric("جاهز للاستلام", len(df_orders[df_orders['status'] == 'جاهز للاستلام']) if not df_orders.empty else 0)

# ------------------------------------------
# التبويب الثاني: إضافة طلب
# ------------------------------------------
with tab2:
    st.subheader("إضافة طلب جديد")
    with st.form("add_order_form"):
        c_name = st.text_input("اسم الزبون")
        c_phone = st.text_input("رقم الهاتف")
        item_type = st.selectbox("نوع القماش / القطعة", ["دشداشة", "بنطال", "قميص", "بدلة"])
        status = st.selectbox("حالة الطلب", STATUSES)
        delivery_d = st.date_input("تاريخ الاستلام المتوقع", date.today())
        total_p = st.number_input("المبلغ الإجمالي", min_value=0.0, step=1000.0)
        paid_p = st.number_input("المبلغ المدفوع", min_value=0.0, step=1000.0)
        notes = st.text_area("ملاحظات / قياسات")

        submitted = st.form_submit_button("حفظ الطلب")
        if submitted:
            if c_name:
                conn = get_connection()
                c = conn.cursor()
                rem_p = total_p - paid_p
                c.execute("""
                    INSERT INTO orders (customer_name, phone, item_type, status, notes, delivery_date, total_price, paid_amount, remaining_amount, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (c_name, c_phone, item_type, status, notes, str(delivery_d), total_p, paid_p, rem_p, str(date.today())))
                conn.commit()
                conn.close()
                st.success("تم حفظ الطلب بنجاح!")
            else:
                st.error("يرجى إدخال اسم الزبون.")

# ------------------------------------------
# التبويب الثالث: إدارة الطلبات
# ------------------------------------------
with tab3:
    st.subheader("إدارة الطلبات")
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
    conn.close()

    if not df.empty:
        for idx, row in df.iterrows():
            d_val = safe_parse_date(row["delivery_date"])
            with st.expander(f"#{row['id']} | {row['customer_name']} | {row['item_type']} ({row['status']})"):
                st.write(f"**رقم الهاتف:** {row['phone']}")
                st.write(f"**تاريخ الاستلام:** {d_val}")
                st.write(f"**المبلغ الكلي:** {row['total_price']} | **المدفوع:** {row['paid_amount']} | **المتبقي:** {row['remaining_amount']}")
                st.write(f"**ملاحظات:** {row['notes']}")
    else:
        st.info("لا توجد طلبات مسجلة حالياً.")

# ------------------------------------------
# التبويب الرابع: الدفعات والديون
# ------------------------------------------
with tab4:
    st.subheader("الحسابات والديون")
    conn = get_connection()
    df = pd.read_sql_query("SELECT customer_name, phone, remaining_amount FROM orders WHERE remaining_amount > 0", conn)
    conn.close()

    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.success("لا يوجد ديون متبقية على الزبائن!")

# ------------------------------------------
# التبويب الخامس: البحث
# ------------------------------------------
with tab5:
    st.subheader("البحث عن طلب")
    search_query = st.text_input("أدخل اسم الزبون أو رقم الهاتف:")
    if search_query:
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM orders WHERE customer_name LIKE ? OR phone LIKE ?", conn, params=(f"%{search_query}%", f"%{search_query}%"))
        conn.close()
        st.dataframe(df, use_container_width=True)
