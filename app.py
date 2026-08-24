import sqlite3
import streamlit as st

# --- 1. إدارة قاعدة البيانات ---
DB_NAME = "tailor_full.db"


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
            total_price REAL,
            advance_paid REAL,
            remaining_price REAL,
            status TEXT
        )
    """
    )
    conn.commit()
    conn.close()


init_db()

# --- 2. إعداد الواجهة ---
st.set_page_config(
    page_title="نظام إدارة الخياطة والمحاسبة", page_icon="✂️", layout="wide"
)
st.title("✂️ نظام إدارة محل الخياطة والمحاسبة الشامل")

menu = [
    "📝 إضافة طلب جديد",
    "📋 جدول العمل والدور",
    "🔍 البحث عن زبون",
    "📊 الإحصائيات والمالية",
]
choice = st.sidebar.radio("القائمة الرئيسية:", menu)

# --- 3. إضافة طلب جديد مع المحاسبة ---
if choice == "📝 إضافة طلب جديد":
    st.subheader("تسجيل طلب وقياسات وحساب جديد")

    with st.form("full_order_form", clear_on_submit=True):
        col_cust1, col_cust2 = st.columns(2)
        with col_cust1:
            name = st.text_input("اسم الزبون *")
        with col_cust2:
            phone = st.text_input("رقم الهاتف")

        item_type = st.selectbox(
            "نوع التفصال", ["دشداشة", "قميص", "بنطلون", "بدلة كاملة"]
        )

        st.markdown("---")
        st.markdown("**📐 القياسات (بالسم):**")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            length = st.number_input("الطول الكلي", min_value=0.0, step=0.5)
            width = st.number_input("العرض (الصدر)", min_value=0.0, step=0.5)
            shoulder = st.number_input("عرض الكتاف", min_value=0.0, step=0.5)
        with col_m2:
            sleeve = st.number_input("طول الردان", min_value=0.0, step=0.5)
            collar = st.number_input("الياخة", min_value=0.0, step=0.5)
            cuff = st.number_input("البزمة", min_value=0.0, step=0.5)

        notes = st.text_area("ملاحظات تفصيلية (نوع القماش، اللون، النقشة...)")

        st.markdown("---")
        st.markdown("**💰 التفاصيل المالية:**")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            total_price = st.number_input("السعر الكلي", min_value=0.0, step=1.0)
        with col_p2:
            advance_paid = st.number_input(
                "العربون (المبلغ المدفوع)", min_value=0.0, step=1.0
            )

        submit = st.form_submit_button("حفظ الطلب والحساب")

        if submit:
            if not name.strip():
                st.error("يرجى إدخال اسم الزبون!")
            else:
                remaining = max(0.0, total_price - advance_paid)
                conn = get_connection()
                c = conn.cursor()
                c.execute(
                    """
                    INSERT INTO orders (
                        name, phone, item_type, length, width, shoulder, sleeve, 
                        collar, cuff, notes, total_price, advance_paid, remaining_price, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        total_price,
                        advance_paid,
                        remaining,
                        "قيد الانتظار",
                    ),
                )
                conn.commit()
                conn.close()
                st.success(
                    f"تم حفظ طلب الزبون {name} بنجاح! المتبقي عليه: {remaining}"
                )

# --- 4. جدول العمل والدور ---
elif choice == "📋 جدول العمل والدور":
    st.subheader("📋 متابعة الدور والطلبات")

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
                o_total,
                o_paid,
                o_rem,
                o_status,
            ) = row

            with st.expander(
                f"📌 #{o_id} | الزبون: {o_name} | {o_item} | الحالة: [{o_status}]"
            ):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.write(f"**الهاتف:** {o_phone}")
                    st.write(f"**الملاحظات:** {o_notes}")
                with c2:
                    st.write("**القياسات:**")
                    st.write(
                        f"طول: {o_len} | عرض: {o_wid} | كتاف: {o_sh}\nردان: {o_slv} | ياخة: {o_col} | بزمة: {o_cuf}"
                    )
                with c3:
                    st.write("**الحساب:**")
                    st.write(f"الكلي: {o_total} | الواصل: {o_paid}")
                    st.write(f"**المتبقي:** :red[{o_rem}]")

                st.markdown("---")
                col_st, col_del = st.columns([3, 1])
                with col_st:
                    new_st = st.selectbox(
                        "تغيير الحالة:",
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
                        ].index(o_status),
                        key=f"st_{o_id}",
                    )
                    if st.button("تحديث الحالة", key=f"btn_st_{o_id}"):
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
                    if st.button("حذف الطلب ❌", key=f"del_{o_id}"):
                        conn = get_connection()
                        c = conn.cursor()
                        c.execute("DELETE FROM orders WHERE id = ?", (o_id,))
                        conn.commit()
                        conn.close()
                        st.rerun()
    else:
        st.info("لا توجد طلبات مسجلة حالياً.")

# --- 5. البحث عن زبون ---
elif choice == "🔍 البحث عن زبون":
    st.subheader("🔍 البحث عن قياسات أو حساب زبون")
    search = st.text_input("أدخل اسم الزبون أو رقم الهاتف:")

    if search:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "SELECT * FROM orders WHERE name LIKE ? OR phone LIKE ?",
            (f"%{search}%", f"%{search}%"),
        )
        results = c.fetchall()
        conn.close()

        if results:
            for r in results:
                st.success(f"تم العثور على الزبون: {r[1]} ({r[3]})")
                st.write(
                    f"**القياسات:** طول {r[4]} | عرض {r[5]} | كتاف {r[6]} | ردان {r[7]} | ياخة {r[8]} | بزمة {r[9]}"
                )
                st.write(
                    f"**المالية:** السعر الكلي: {r[11]} | المدفوع: {r[12]} | المتبقي: {r[13]}"
                )
                st.markdown("---")
        else:
            st.warning("لم يتم العثور على أي زبون بهذه البيانات.")

# --- 6. الإحصائيات والمالية ---
elif choice == "📊 الإحصائيات والمالية":
    st.subheader("📊 ملخص الحسابات والعمليات")

    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT SUM(total_price), SUM(advance_paid), SUM(remaining_price), COUNT(id) FROM orders"
    )
    stats = c.fetchone()
    conn.close()

    total_income = stats[0] or 0.0
    total_paid = stats[1] or 0.0
    total_due = stats[2] or 0.0
    total_orders = stats[3] or 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("إجمالي الطلبات", total_orders)
    m2.metric("إجمالي المبالغ", f"{total_income}")
    m3.metric("الواصل (المقبوض)", f"{total_paid}")
    m4.metric("الديون المتأخرة (المتبقي)", f"{total_due}")
