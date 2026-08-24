import sqlite3
from datetime import datetime, date
import pandas as pd
import streamlit as st

# ==========================================
# 1. إعداد الصفحة وتلغية القائمة الجانبية
# ==========================================
st.set_page_config(page_title="صادق الخياط", page_icon="✂️", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    section[data-testid="stSidebar"], button[aria-label="Toggle sidebar"] {
        display: none !important;
    }
    .stApp {
        background-color: #f8fafc;
        direction: rtl;
        text-align: right;
    }
    .main .block-container {
        padding-top: 1.5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #ffffff;
        padding: 6px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        display: flex;
        justify-content: space-around;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        border-radius: 8px;
        background-color: #f1f5f9;
        color: #334155;
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
    div[data-testid="stVerticalBlock"] > div {
        background-color: #ffffff;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }
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
# 2. إعدادات قاعدة البيانات والتحديث الآلي
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
            customer_name TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            item_type TEXT DEFAULT '',
            status TEXT DEFAULT 'قيد الانتظار',
            notes TEXT DEFAULT '',
            delivery_date TEXT DEFAULT '',
            total_price REAL DEFAULT 0,
            paid_amount REAL DEFAULT 0,
            remaining_amount REAL DEFAULT 0,
            created_at TEXT DEFAULT ''
        )
    """)
    conn.commit()

    # تحديث أعمدة قاعدة البيانات القديمة آلياً لتفادي DatabaseError
    c.execute("PRAGMA table_info(orders)")
    columns = [col[1] for col in c.fetchall()]
    
    missing_columns = {
        'remaining_amount': 'REAL DEFAULT 0',
        'paid_amount': 'REAL DEFAULT 0',
        'total_price': 'REAL DEFAULT 0',
        'delivery_date': "TEXT DEFAULT ''",
        'item_type': "TEXT DEFAULT ''",
        'status': "TEXT DEFAULT 'قيد الانتظار'",
        'notes': "TEXT DEFAULT ''"
    }

    for col_name, col_type in missing_columns.items():
        if col_name not in columns:
            try:
                c.execute(f"ALTER TABLE orders ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass

    conn.commit()
    conn.close()

init_db()

# ==========================================
# 3. الواجهة الرئيسية
# ==========================================
st.markdown(f"<h2 style='text-align: center; color: #1e293b; margin-bottom: 0px;'>✂️ {SHOP_NAME}</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; font-size: 14px;'>نظام إدارة الطلبات والقياسات والحسابات</p>", unsafe_allow_html=True)

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
    
    pending_count = len(df_orders[df_orders['status'] == 'قيد الانتظار']) if ('status' in df_orders.columns and not df_orders.empty) else 0
    ready_count = len(df_orders[df_orders['status'] == 'جاهز للاستلام']) if ('status' in df_orders.columns and not df_orders.empty) else 0
    
    col2.metric("قيد الانتظار", pending_count)
    col3.metric("جاهز للاستلام", ready_count)

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
                st.rerun()
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
            order_id = row.get('id', idx)
            cust_name = row.get('customer_name', 'غير محدد')
            i_type = row.get('item_type', 'غير محدد')
            st_val = row.get('status', 'غير محدد')
            phone_val = row.get('phone', '-')
            d_val = safe_parse_date(row.get('delivery_date', ''))
            tot_p = row.get('total_price', 0)
            p_p = row.get('paid_amount', 0)
            rem_p = row.get('remaining_amount', 0)
            nts = row.get('notes', '-')

            with st.expander(f"#{order_id} | {cust_name} | {i_type} ({st_val})"):
                st.write(f"**رقم الهاتف:** {phone_val}")
                st.write(f"**تاريخ الاستلام:** {d_val}")
                st.write(f"**المبلغ الكلي:** {tot_p} | **المدفوع:** {p_p} | **المتبقي:** {rem_p}")
                st.write(f"**ملاحظات:** {nts}")
    else:
        st.info("لا توجد طلبات مسجلة حالياً.")

# ------------------------------------------
# التبويب الرابع: الدفعات والديون (استعلام آمن)
# ------------------------------------------
with tab4:
    st.subheader("الحسابات والديون")
    conn = get_connection()
    df_all = pd.read_sql_query("SELECT * FROM orders", conn)
    conn.close()

    if not df_all.empty and 'remaining_amount' in df_all.columns:
        df_debts = df_all[df_all['remaining_amount'] > 0]
        if not df_debts.empty:
            show_df = df_debts[['customer_name', 'phone', 'remaining_amount']].rename(columns={
                'customer_name': 'اسم الزبون',
                'phone': 'رقم الهاتف',
                'remaining_amount': 'المبلغ المتبقي'
            })
            st.dataframe(show_df, use_container_width=True)
        else:
            st.success("لا يوجد ديون متبقية على الزبائن!")
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
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("لم يتم العثور على نتائج مطابقة.")
