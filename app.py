import sqlite3
from datetime import datetime, date
import pandas as pd
import streamlit as st

# ==========================================
# 1. إعداد الصفحة والتصميم الجمالي الخشبي والقماشي
# ==========================================
st.set_page_config(page_title="صادق الخياط", page_icon="🧵", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    section[data-testid="stSidebar"], button[aria-label="Toggle sidebar"] {
        display: none !important;
    }
    .stApp {
        background-color: #fcf8f2;
        direction: rtl;
        text-align: right;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .main .block-container {
        padding-top: 1.5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }
    /* تصميم التبويبات بمظهر قماشي وخشبي */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #e5d3b3;
        padding: 8px;
        border-radius: 12px;
        border: 2px solid #b89768;
        display: flex;
        justify-content: space-around;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        border-radius: 8px;
        background-color: #d4b886;
        color: #4a2c11;
        font-weight: bold;
        border: 1px solid #a67c52;
        flex-grow: 1;
        text-align: center;
        font-size: 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #8b5a2b !important;
        color: #ffffff !important;
        border-color: #5c3a17 !important;
        box-shadow: 0px 3px 6px rgba(0,0,0,0.2);
    }
    /* تصميم البطاقات والخانات */
    div[data-testid="stVerticalBlock"] > div {
        background-color: #ffffff;
        border-radius: 14px;
        border: 1px dashed #b89768;
        padding: 1.2rem;
        margin-bottom: 0.8rem;
        box-shadow: 0 2px 5px rgba(139, 90, 43, 0.05);
    }
    .stTextInput input, .stSelectbox select, .stTextArea textarea, .stDateInput input {
        border-radius: 8px !important;
        border: 1px solid #cbb292 !important;
        background-color: #faf6f0 !important;
    }
    .stButton > button {
        background-color: #8b5a2b !important;
        color: white !important;
        border-radius: 10px !important;
        border: 1px solid #5c3a17 !important;
        font-weight: bold;
        width: 100%;
        padding: 0.6rem !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.15);
    }
    .stButton > button:hover {
        background-color: #6d441f !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. إعدادات قاعدة البيانات والتحديث التلقائي
# ==========================================
DB_NAME = "tailor_master.db"
SHOP_NAME = "مشغل صادق الخياط 🧵🪡"
STATUSES = ["قيد الانتظار", "جاري القص ✂️", "جاري التفصيل 🧵", "جاري الكي 🧺", "جاهز للاستلام 🛍️", "تم التسليم ✅"]

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
            sizes TEXT DEFAULT '',
            delivery_date TEXT DEFAULT '',
            total_price REAL DEFAULT 0,
            paid_amount REAL DEFAULT 0,
            remaining_amount REAL DEFAULT 0,
            created_at TEXT DEFAULT ''
        )
    """)
    conn.commit()

    c.execute("PRAGMA table_info(orders)")
    columns = [col[1] for col in c.fetchall()]
    
    missing_columns = {
        'sizes': "TEXT DEFAULT ''",
        'remaining_amount': 'REAL DEFAULT 0',
        'paid_amount': 'REAL DEFAULT 0',
        'total_price': 'REAL DEFAULT 0',
        'delivery_date': "TEXT DEFAULT ''",
        'item_type': "TEXT DEFAULT ''",
        'status': "TEXT DEFAULT 'قيد الانتظار'",
        'notes': "TEXT DEFAULT ''",
        'phone': "TEXT DEFAULT ''",
        'customer_name': "TEXT DEFAULT ''"
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
# 3. الهيدر والواجهة الرئيسية
# ==========================================
st.markdown(f"<h1 style='text-align: center; color: #5c3a17; margin-bottom: 0px;'>🪵 {SHOP_NAME} 🪵</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8b5a2b; font-size: 15px; font-weight: bold;'>نظام إدارة تفصيل الخياطة والقياسات والحسابات</p>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🪵 لوحة التحكم",
    "➕ إضافة طلب",
    "🧵 إدارة الطلبات",
    "💵 الديون",
    "🔍 البحث",
    "💾 النسخ الاحتياطي"
])

# ------------------------------------------
# التبويب الأول: لوحة التحكم
# ------------------------------------------
with tab1:
    conn = get_connection()
    df_orders = pd.read_sql_query("SELECT * FROM orders", conn)
    conn.close()

    col1, col2, col3 = st.columns(3)
    col1.metric("📦 إجمالي الطلبات", len(df_orders))
    
    pending_count = len(df_orders[df_orders['status'].astype(str).str.contains('قيد الانتظار|القص|التفصيل')]) if ('status' in df_orders.columns and not df_orders.empty) else 0
    ready_count = len(df_orders[df_orders['status'].astype(str).str.contains('جاهز')]) if ('status' in df_orders.columns and not df_orders.empty) else 0
    
    col2.metric("⏳ قيد العمل", pending_count)
    col3.metric("🛍️ جاهز للاستلام", ready_count)

# ------------------------------------------
# التبويب الثاني: إضافة طلب + القياسات
# ------------------------------------------
with tab2:
    st.subheader("➕ إضافة طلب جديد وتفاصيل القياس")
    with st.form("add_order_form", clear_on_submit=True):
        st.markdown("##### 👤 بيانات الزبون")
        c_name = st.text_input("اسم الزبون*")
        c_phone = st.text_input("رقم الهاتف")
        item_type = st.selectbox("نوع القماش / القطعة", ["دشداشة رجالي", "دشداشة ولادي", "بنطال", "قميص", "بدلة", "آخر"])
        status = st.selectbox("حالة الطلب Initial", STATUSES)
        
        st.markdown("##### 📐 جدول قياسات الخياطة (سم)")
        col_s1, col_s2, col_s3 = st.columns(3)
        size_length = col_s1.text_input("الطول")
        size_shoulder = col_s2.text_input("الكتف")
        size_sleeve = col_s3.text_input("الردن / الكم")
        
        col_s4, col_s5, col_s6 = st.columns(3)
        size_chest = col_s4.text_input("الصدر")
        size_neck = col_s5.text_input("الرقبة")
        size_waist = col_s6.text_input("الخصر / العرض")

        st.markdown("##### 💰 الحساب المالي والحجز")
        delivery_d = st.date_input("تاريخ التسليم المتوقع", date.today())
        total_p = st.number_input("المبلغ الإجمالي (د.ع)", min_value=0.0, step=1000.0)
        paid_p = st.number_input("المبلغ المدفوع عربون (د.ع)", min_value=0.0, step=1000.0)
        notes = st.text_area("ملاحظات إضافية على الخياطة")

        submitted = st.form_submit_button("💾 حفظ الطلب والقياسات")
        if submitted:
            if c_name.strip():
                try:
                    conn = get_connection()
                    c = conn.cursor()
                    rem_p = total_p - paid_p
                    
                    sizes_text = f"طول: {size_length} | كتف: {size_shoulder} | ردن: {size_sleeve} | صدر: {size_chest} | رقبة: {size_neck} | خصر: {size_waist}"
                    
                    c.execute("""
                        INSERT INTO orders (customer_name, phone, item_type, status, notes, sizes, delivery_date, total_price, paid_amount, remaining_amount, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (c_name, c_phone, item_type, status, notes, sizes_text, str(delivery_d), total_p, paid_p, rem_p, str(date.today())))
                    conn.commit()
                    conn.close()
                    st.success("✅ تم حفظ الطلب والقياسات بنجاح!")
                    st.rerun()
                except Exception as e:
                    st.error(f"حدث خطأ أثناء الحفظ: {e}")
            else:
                st.warning("⚠️ يرجى كتابة اسم الزبون.")

# ------------------------------------------
# التبويب الثالث: إدارة الطلبات والتعديل والوصل
# ------------------------------------------
with tab3:
    st.subheader("🧵 قائمة الطلبات الحالية")
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
    conn.close()

    if not df.empty:
        for idx, row in df.iterrows():
            order_id = row.get('id', idx)
            cust_name = row.get('customer_name', 'غير محدد')
            i_type = row.get('item_type', 'غير محدد')
            st_val = row.get('status', 'قيد الانتظار')
            phone_val = row.get('phone', '-')
            d_val = safe_parse_date(row.get('delivery_date', ''))
            tot_p = row.get('total_price', 0.0)
            p_p = row.get('paid_amount', 0.0)
            rem_p = row.get('remaining_amount', 0.0)
            nts = row.get('notes', '')
            szs = row.get('sizes', '')

            with st.expander(f"📦 طلب #{order_id} | الزبون: {cust_name} | {i_type} [{st_val}]"):
                st.write(f"📞 **رقم الهاتف:** {phone_val}")
                st.info(f"📐 **القياسات:** {szs if szs else 'لم تُسجل قياسات'}")
                st.write(f"📅 **تاريخ الاستلام:** {d_val}")
                st.write(f"💵 **الإجمالي:** {tot_p:,} | **العربون:** {p_p:,} | **المتبقي:** {rem_p:,} د.ع")
                st.write(f"📝 **الملاحظات:** {nts if nts else '-'}")
                
                col_b1, col_b2, col_b3 = st.columns(3)
                
                # تعديل الطلب
                with col_b1:
                    with st.popover("✏️ تعديل الطلب"):
                        with st.form(key=f"edit_form_{order_id}"):
                            new_status = st.selectbox("الحالة الحالية", STATUSES, index=0)
                            new_sizes = st.text_area("تعديل القياسات", value=str(szs))
                            new_total = st.number_input("المبلغ الإجمالي", value=float(tot_p), step=1000.0)
                            new_paid = st.number_input("المبلغ المدفوع", value=float(p_p), step=1000.0)
                            new_notes = st.text_area("تعديل الملاحظات", value=str(nts))
                            
                            if st.form_submit_button("حفظ التحديثات"):
                                conn = get_connection()
                                c = conn.cursor()
                                new_rem = new_total - new_paid
                                c.execute("""
                                    UPDATE orders 
                                    SET status=?, sizes=?, total_price=?, paid_amount=?, remaining_amount=?, notes=?
                                    WHERE id=?
                                """, (new_status, new_sizes, new_total, new_paid, new_rem, new_notes, order_id))
                                conn.commit()
                                conn.close()
                                st.success("تم التعديل بنجاح!")
                                st.rerun()

                # تنزيل الوصل
                with col_b2:
                    receipt_text = f"""
================================
         وصل خياطة الزبون
         مشغل صادق الخياط 🧵
================================
رقم الطلب: #{order_id}
اسم الزبون: {cust_name}
رقم الهاتف: {phone_val}
نوع القطعة: {i_type}
التاريخ: {d_val}
--------------------------------
القياسات:
{szs}
--------------------------------
المبلغ الكلي: {tot_p} د.ع
المبلغ المدفوع: {p_p} د.ع
المبلغ المتبقي: {rem_p} د.ع
--------------------------------
شكراً لزيارتكم مشغل صادق الخياط!
================================
"""
                    st.download_button(
                        label="📄 تنزيل الوصل",
                        data=receipt_text,
                        file_name=f"receipt_order_{order_id}.txt",
                        mime="text/plain",
                        key=f"dl_rec_{order_id}"
                    )

                # حذف الطلب
                with col_b3:
                    if st.button("🗑️ حذف الطلب", key=f"del_{order_id}"):
                        conn = get_connection()
                        c = conn.cursor()
                        c.execute("DELETE FROM orders WHERE id=?", (order_id,))
                        conn.commit()
                        conn.close()
                        st.warning("تم حذف الطلب.")
                        st.rerun()
    else:
        st.info("لا توجد طلبات مسجلة حالياً.")

# ------------------------------------------
# التبويب الرابع: الدفعات والديون
# ------------------------------------------
with tab4:
    st.subheader("💵 قائمة الديون والذمم المتبقية")
    conn = get_connection()
    df_all = pd.read_sql_query("SELECT * FROM orders", conn)
    conn.close()

    if not df_all.empty and 'remaining_amount' in df_all.columns:
        df_debts = df_all[df_all['remaining_amount'] > 0]
        if not df_debts.empty:
            show_df = df_debts[['customer_name', 'phone', 'item_type', 'remaining_amount']].rename(columns={
                'customer_name': 'اسم الزبون',
                'phone': 'رقم الهاتف',
                'item_type': 'نوع القطعة',
                'remaining_amount': 'المبلغ المتبقي (د.ع)'
            })
            st.dataframe(show_df, use_container_width=True)
        else:
            st.success("🎉 ممتاز! لا توجد ديون متبقية على الزبائن.")
    else:
        st.success("🎉 لا توجد ديون متبقية.")

# ------------------------------------------
# التبويب الخامس: البحث
# ------------------------------------------
with tab5:
    st.subheader("🔍 البحث السريع")
    search_query = st.text_input("أدخل اسم الزبون أو رقم الهاتف للبحث:")
    if search_query:
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM orders WHERE customer_name LIKE ? OR phone LIKE ?", conn, params=(f"%{search_query}%", f"%{search_query}%"))
        conn.close()
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("لم يتم العثور على أي نتائج.")

# ------------------------------------------
# التبويب السادس: النسخ الاحتياطي لقاعدة البيانات
# ------------------------------------------
with tab6:
    st.subheader("💾 النسخ الاحتياطي وحفظ البيانات")
    st.write("يمكنك تنزيل نسخة احتياطية من قاعدة البيانات بالكامل لحفظها على جهازك وتفادي ضياع البيانات:")
    
    try:
        with open(DB_NAME, "rb") as fp:
            st.download_button(
                label="📥 تنزيل نسخة احتياطية من قاعدة البيانات (tailor_master.db)",
                data=fp,
                file_name=f"backup_tailor_{date.today()}.db",
                mime="application/octet-stream"
            )
    except Exception as e:
        st.error("لم يتم العثور على ملف قاعدة البيانات بعد.")
