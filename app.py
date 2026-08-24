import sqlite3
import streamlit as st

# --- 1. إنشاء/اتصال قاعدة البيانات ---
DB_NAME = "tailor.db"


def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            item_type TEXT,
            length REAL,
            width REAL,
            shoulder REAL,
            sleeve REAL,
            collar REAL,
            cuff REAL,
            notes TEXT,
            status TEXT
        )
    """
    )
    conn.commit()
    conn.close()


init_db()

# --- 2. إعداد واجهة الموقع ---
st.set_page_config(
    page_title="نظام إدارة محل الخياطة", page_icon="✂️", layout="wide"
)
st.title("✂️ نظام إدارة المحل والمحاسبة الشامل")

page = st.sidebar.radio(
    "القائمة الرئيسية:", ["إضافة طلب جديد", "جدول العمل والدور"]
)

# --- 3. صفحة إضافة طلب جديد ---
if page == "إضافة طلب جديد":
    st.subheader("📝 تسجيل طلب وقياسات جديدة")

    with st.form("add_order_form", clear_on_submit=True):
        name = st.text_input("اسم الزبون *")
        phone = st.text_input("رقم الهاتف")
        item_type = st.selectbox(
            "نوع التفصال", ["دشداشة", "قميص", "بنطلون", "بدلة"]
        )

        st.markdown("**القياسات (بالسم):**")
        col1, col2 = st.columns(2)
        with col1:
            length = st.number_input("الطول الكلي", min_value=0.0, step=0.5)
            width = st.number_input("العرض (الصدر)", min_value=0.0, step=0.5)
            shoulder = st.number_input("عرض الكتاف", min_value=0.0, step=0.5)
        with col2:
            sleeve = st.number_input("طول الردان", min_value=0.0, step=0.5)
            collar = st.number_input("الياخة", min_value=0.0, step=0.5)
            cuff = st.number_input("البزمة", min_value=0.0, step=0.5)

        notes = st.text_area("ملاحظات تفصيلية (نوع القماش، التفاصيل)")
        submit = st.form_submit_button("حفظ الطلب")

        if submit:
            if name.strip() == "":
                st.error("يرجى إدخال اسم الزبون!")
            else:
                conn = get_connection()
                c = conn.cursor()
                c.execute(
                    """
                    INSERT INTO orders (name, phone, item_type, length, width, shoulder, sleeve, collar, cuff, notes, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        name,
                        phone,
                        item_type,
                        length,
                        width,
                        shoulder,
                        sleeve,
                        collar,
                        cuff,
                        notes,
                        "قيد الانتظار",
                    ),
                )
                conn.commit()
                conn.close()

                st.success(f"تم حفظ طلب الزبون {name} بنجاح!")

# --- 4. صفحة جدول العمل والدور ---
elif page == "جدول العمل والدور":
    st.subheader("📋 جدول العمل والدور")

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM orders ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    if rows:
        for row in rows:
            (
                o_id,
                o_name,
                o_phone,
                o_item,
                o_len,
                o_wid,
                o_sh,
                o_slv,
                o_col,
                o_cuf,
                o_notes,
                o_status,
            ) = row

            with st.expander(
                f"📌 #{o_id} | الزبون: {o_name} | {o_item} | الحالة: [{o_status}]"
            ):
                st.write(f"**رقم الهاتف:** {o_phone}")
                st.write(
                    f"**القياسات:** طول: {o_len} | عرض: {o_wid} | كتاف: {o_sh} | ردان: {o_slv} | ياخة: {o_col} | بزمة: {o_cuf}"
                )
                st.write(f"**الملاحظات:** {o_notes}")

                col_stat, col_del = st.columns([2, 1])
                with col_stat:
                    new_st = st.selectbox(
                        "تحديث الحالة:",
                        [
                            "قيد الانتظار",
                            "جارِ التفصيل",
                            "جاهز للتسليم",
                            "تم التسليم",
                        ],
                        index=[
                            "قيد الانتظار",
                            "جارِ التفصيل",
                            "جاهز للتسليم",
                            "تم التسليم",
                        ].index(
                            o_status
                            if o_status
                            in [
                                "قيد الانتظار",
                                "جارِ التفصيل",
                                "جاهز للتسليم",
                                "تم التسليم",
                            ]
                            else "قيد الانتظار"
                        ),
                        key=f"status_select_{o_id}",
                    )
                    if st.button("حفظ التغيير", key=f"btn_update_{o_id}"):
                        conn = get_connection()
                        c = conn.cursor()
                        c.execute(
                            "UPDATE orders SET status = ? WHERE id = ?",
                            (new_st, o_id),
                        )
                        conn.commit()
                        conn.close()
                        st.rerun()

                with col_del:
                    if st.button("حذف الطلب ❌", key=f"btn_del_{o_id}"):
                        conn = get_connection()
                        c = conn.cursor()
                        c.execute("DELETE FROM orders WHERE id = ?", (o_id,))
                        conn.commit()
                        conn.close()
                        st.rerun()
    else:
        st.info("لا توجد طلبات مسجلة حالياً.")
