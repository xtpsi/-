import sqlite3
from datetime import datetime
import streamlit as st

# --- 1. إعداد قاعدة البيانات بترميز UTF-8 ---
DB_NAME = "tailor_utf8.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    # إجبار الاتصال على استقبال وإرسال النصوص بترميز UTF-8
    conn.text_factory = str
    return conn


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
            status TEXT,
            created_at TEXT
        )
    """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            amount REAL,
            payment_date TEXT,
            FOREIGN KEY (order_id) REFERENCES orders (id)
        )
    """
    )
    conn.commit()
    conn.close()


init_db()

# --- 2. إعداد الواجهة ---
st.set_page_config(
    page_title="خياطة الفيحاء - إدارة الطلبات والمحاسبة",
    page_icon="✂️",
    layout="wide",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    html, body, [class*="css"], div, span, p {
        font-family: 'Cairo', sans-serif !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("✂️ نظام إدارة الخياطة والمحاسبة الذكي")

menu = [
    "📝 إضافة طلب جديد",
    "📋 جدول العمل والدور",
    "💵 تسديد الديون والحسابات",
    "🔍 البحث عن زبون",
    "📊 الإحصائيات والمالية",
]
choice = st.sidebar.radio("القائمة الرئيسية:", menu)

# --- 3. إضافة طلب جديد ---
if choice == "📝 إضافة طلب جديد":
    st.subheader("تسجيل طلب وقياسات وحساب جديد")

    with st.form("add_order_form", clear_on_submit=True):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            name = st.text_input("اسم الزبون *")
        with col_c2:
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

        notes = st.text_area("ملاحظات (نوع القماش، اللون، الموديل)")

        st.markdown("---")
        st.markdown("**💰 التفاصيل المالية:**")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            total_price = st.number_input(
                "السعر الكلي (د.ع)", min_value=0.0, step=1000.0
            )
        with col_p2:
            advance_paid = st.number_input(
                "العربون المدفوع (د.ع)", min_value=0.0, step=1000.0
            )

        submit = st.form_submit_button("حفظ الطلب والحساب")

        if submit:
            if not name.strip():
                st.error("يرجى إدخال اسم الزبون!")
            else:
                remaining = max(0.0, total_price - advance_paid)
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                conn = get_connection()
                c = conn.cursor()
                c.execute(
                    """
                    INSERT INTO orders (
                        name, phone, item_type, length, width, shoulder, sleeve, collar, cuff,
                        notes, total_price, advance_paid, remaining_price, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        now_str,
                    ),
                )
                order_id = c.lastrowid
                if advance_paid > 0:
                    c.execute(
                        "INSERT INTO payments (order_id, amount, payment_date) VALUES (?, ?, ?)",
                        (order_id, advance_paid, now_str),
                    )
                conn.commit()
                conn.close()
                st.success(
                    f"تم حفظ الطلب بنجاح! المتبقي على الزبون: {remaining:,.0f} د.ع"
                )

# --- 4. تسديد الديون والحسابات ---
elif choice == "💵 تسديد الديون والحسابات":
    st.subheader("💵 تسديد المبالغ المتبقية والديون")

    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, name, phone, item_type, total_price, advance_paid, remaining_price FROM orders WHERE remaining_price > 0 ORDER BY id DESC"
    )
    debtors = c.fetchall()
    conn.close()

    if debtors:
        st.write(f"عدد الزبائن الذين عليهم مبالغ متبقية: **{len(debtors)}**")
        for debtor in debtors:
            d_id, d_name, d_phone, d_item, d_total, d_paid, d_rem = debtor
            with st.expander(
                f"👤 {d_name} | {d_item} | المتبقي عليه: [{d_rem:,.0f} د.ع]"
            ):
                st.write(f"**رقم الهاتف:** {d_phone}")
                st.write(
                    f"**السعر الكلي:** {d_total:,.0f} د.ع | **الواصل:** {d_paid:,.0f} د.ع | **المتبقي:** :red[{d_rem:,.0f} د.ع]"
                )

                col_pay1, col_pay2 = st.columns([2, 1])
                with col_pay1:
                    pay_amount = st.number_input(
                        "المبلغ المستلم الآن (د.ع):",
                        min_value=0.0,
                        max_value=float(d_rem),
                        step=1000.0,
                        key=f"pay_input_{d_id}",
                    )
                with col_pay2:
                    st.write(" ")
                    st.write(" ")
                    if st.button("تأكيد استلام المبلغ 💵", key=f"pay_btn_{d_id}"):
                        if pay_amount > 0:
                            new_paid = d_paid + pay_amount
                            new_rem = d_total - new_paid
                            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

                            conn = get_connection()
                            c = conn.cursor()
                            c.execute(
                                "UPDATE orders SET advance_paid = ?, remaining_price = ? WHERE id = ?",
                                (new_paid, new_rem, d_id),
                            )
                            c.execute(
                                "INSERT INTO payments (order_id, amount, payment_date) VALUES (?, ?, ?)",
                                (d_id, pay_amount, now_str),
                            )
                            conn.commit()
                            conn.close()

                            st.success(
                                f"تم تسجيل دفعة بقيمة {pay_amount:,.0f} د.ع بنجاح!"
                            )
                            st.rerun()
                        else:
                            st.warning("أدخل مبلغاً أكبر من صفر.")
    else:
        st.success("🎉 ممتاز! لا توجد ديون أو مبالغ متبقية على أي زبون.")

# --- 5. جدول العمل والدور ---
elif choice == "📋 جدول العمل والدور":
    st.subheader("📋 متابعة الدور وحالة التفصيل")

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
                o_date,
            ) = row

            with st.expander(
                f"📌 #{o_id} | الزبون: {o_name} | {o_item} | الحالة: [{o_status}]"
            ):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.write(f"**الهاتف:** {o_phone}")
                    st.write(f"**التاريخ:** {o_date}")
                    st.write(f"**الملاحظات:** {o_notes}")
                with c2:
                    st.write("**القياسات (سم):**")
                    st.write(
                        f"طول: {o_len} | عرض: {o_wid} | كتاف: {o_sh}\nردان: {o_slv} | ياخة: {o_col} | بزمة: {o_cuf}"
                    )
                with c3:
                    st.write("**الحساب:**")
                    st.write(
                        f"الكلي: {o_total:,.0f} د.ع | الواصل: {o_paid:,.0f} د.ع"
                    )
                    st.write(f"**المتبقي:** :red[{o_rem:,.0f} د.ع]")

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
                        c.execute(
                            "DELETE FROM payments WHERE order_id = ?", (o_id,)
                        )
                        conn.commit()
                        conn.close()
                        st.rerun()
    else:
        st.info("لا توجد طلبات مسجلة حالياً.")

# --- 6. البحث عن زبون ---
elif choice == "🔍 البحث عن زبون":
    st.subheader("🔍 البحث عن قياسات وسجل دفعات زبون")
    search = st.text_input("أدخل اسم الزبون أو رقم الهاتف:")

    if search:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "SELECT * FROM orders WHERE name LIKE ? OR phone LIKE ?",
            (f"%{search}%", f"%{search}%"),
        )
        results = c.fetchall()

        if results:
            for r in results:
                st.success(f"الزبون: {r[1]} ({r[3]}) - الهاتف: {r[2]}")
                st.write(
                    f"**القياسات:** طول {r[4]} | عرض {r[5]} | كتاف {r[6]} | ردان {r[7]} | ياخة {r[8]} | بزمة {r[9]}"
                )
                st.write(
                    f"**المالية:** الكلي: {r[11]:,.0f} د.ع | الواصل: {r[12]:,.0f} د.ع | المتبقي: {r[13]:,.0f} د.ع"
                )

                c.execute(
                    "SELECT amount, payment_date FROM payments WHERE order_id = ? ORDER BY id DESC",
                    (r[0],),
                )
                pays = c.fetchall()
                if pays:
                    st.write("**سجل الدفعات المقبوضة:**")
                    for p in pays:
                        st.caption(
                            f"• تم تسديد {p[0]:,.0f} د.ع بتاريخ {p[1]}"
                        )
                st.markdown("---")
        else:
            st.warning("لم يتم العثور على زبون مطابق.")
        conn.close()

# --- 7. الإحصائيات والمالية ---
elif choice == "📊 الإحصائيات والمالية":
    st.subheader("📊 ملخص الأرباح والديون")

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
    m2.metric("إجمالي المبالغ", f"{total_income:,.0f} د.ع")
    m3.metric("الواصل المقبوض", f"{total_paid:,.0f} د.ع")
    m4.metric("إجمالي الديون", f"{total_due:,.0f} د.ع")
