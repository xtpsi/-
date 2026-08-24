import sqlite3
from datetime import datetime
import streamlit as st

# --- 1. إعداد قاعدة البيانات ---
DB_NAME = "tailor_engineer.db"


def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, phone TEXT, item_type TEXT,
            length REAL, width REAL, shoulder REAL, sleeve REAL, collar REAL, cuff REAL,
            notes TEXT, total_price REAL, advance_paid REAL, remaining_price REAL,
            status TEXT, created_at TEXT, delivery_date TEXT
        )
    """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER, amount REAL, payment_date TEXT,
            FOREIGN KEY (order_id) REFERENCES orders (id)
        )
    """
    )
    conn.commit()
    conn.close()


init_db()

# --- 2. إعداد الصفحة والتنسيقات (CSS) ---
st.set_page_config(
    page_title="صادق الخياط", page_icon="✂️", layout="wide"
)

st.markdown(
    """
    <style>
    .stApp { background-color: #F8F9FA; }
    
    section[data-testid="stSidebar"] {
        background-color: #1E293B !important;
    }
    section[data-testid="stSidebar"] * {
        color: #F8FAFC !important;
    }
    
    .main-header {
        font-size: 26px; font-weight: bold; color: #0F172A; text-align: center;
        padding: 14px; background: white; border-radius: 12px;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.05); margin-bottom: 25px;
    }

    .measure-tag {
        display: inline-block; background-color: #EFF6FF; color: #1D4ED8;
        padding: 6px 12px; margin: 3px; border-radius: 8px; font-weight: bold;
        font-size: 14px; border: 1px solid #BFDBFE;
    }

    .date-badge-late {
        background-color: #FEE2E2; color: #991B1B; padding: 4px 10px;
        border-radius: 6px; font-weight: bold; font-size: 13px;
    }

    .date-badge-today {
        background-color: #FEF3C7; color: #92400E; padding: 4px 10px;
        border-radius: 6px; font-weight: bold; font-size: 13px;
    }

    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    </style>
""",
    unsafe_allow_html=True,
)

# --- 3. القائمة الجانبية ---
st.sidebar.markdown(
    "<h2 style='text-align: center;'>✂️ صادق الخياط</h2>",
    unsafe_allow_html=True,
)
st.sidebar.markdown("---")

menu = [
    "📝 إضافة طلب جديد",
    "📋 جدول العمل والدور",
    "💵 تسديد الديون والحسابات",
    "🔍 البحث عن زبون",
    "📊 الإحصائيات والمالية",
]
choice = st.sidebar.radio("التنقل السريع:", menu)

# --- 4. إضافة طلب جديد ---
if choice == "📝 إضافة طلب جديد":
    st.markdown(
        "<div class='main-header'>📝 تسجيل طلب وقياسات جديدة - خياطة مهندس وأولاده</div>",
        unsafe_allow_html=True,
    )

    with st.form("add_order_form", clear_on_submit=True):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            name = st.text_input("👤 اسم الزبون *")
            phone = st.text_input("📞 رقم الهاتف")
        with col_c2:
            item_type = st.selectbox(
                "🧵 نوع التفصال", ["دشداشة", "قميص", "بنطلون", "بدلة كاملة"]
            )
            delivery_date = st.date_input(
                "📅 موعد التسليم المتوقع", datetime.now()
            ).strftime("%Y-%m-%d")

        st.markdown("---")
        st.markdown("### 📐 القياسات (بالسنتيمتر)")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            length = st.number_input("📏 الطول الكلي", min_value=0.0, step=0.5)
            width = st.number_input(
                "↔️ العرض (الصدر)", min_value=0.0, step=0.5
            )
            shoulder = st.number_input(
                "📐 عرض الكتاف", min_value=0.0, step=0.5
            )
        with col_m2:
            sleeve = st.number_input("🦾 طول الردان", min_value=0.0, step=0.5)
            collar = st.number_input("👔 الياخة", min_value=0.0, step=0.5)
            cuff = st.number_input("🔘 البزمة", min_value=0.0, step=0.5)

        notes = st.text_area("📝 ملاحظات تفصيلية (نوع القماش، اللون، الموديل)")

        st.markdown("---")
        st.markdown("### 💰 التفاصيل المالية")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            total_price = st.number_input(
                "💵 السعر الكلي", min_value=0.0, step=1.0
            )
        with col_p2:
            advance_paid = st.number_input(
                "💳 العربون المدفوع", min_value=0.0, step=1.0
            )

        submit = st.form_submit_button("✅ حفظ الطلب والقياسات")

        if submit:
            if not name.strip():
                st.error("⚠️ يرجى إدخال اسم الزبون!")
            else:
                remaining = max(0.0, total_price - advance_paid)
                now_str = datetime.now().strftime("%Y-%m-%d")
                conn = get_connection()
                c = conn.cursor()
                c.execute(
                    """
                    INSERT INTO orders (
                        name, phone, item_type, length, width, shoulder, sleeve, collar, cuff,
                        notes, total_price, advance_paid, remaining_price, status, created_at, delivery_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        delivery_date,
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
                    f"🎉 تم حفظ الطلب بنجاح! موعد التسليم: {delivery_date} | المتبقي: {remaining:,.0f}"
                )

# --- 5. جدول العمل والدور ---
elif choice == "📋 جدول العمل والدور":
    st.markdown(
        "<div class='main-header'>📋 جدول العمل والدور ومواعيد التسليم</div>",
        unsafe_allow_html=True,
    )

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM orders ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    today_str = datetime.now().strftime("%Y-%m-%d")

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
                o_deliv,
            ) = row

            # تنبيه موعد التسليم
            date_status_html = ""
            if o_status != "تم التسليم":
                if o_deliv < today_str:
                    date_status_html = f"<span class='date-badge-late'>⚠️ متأخر (موعده: {o_deliv})</span>"
                elif o_deliv == today_str:
                    date_status_html = f"<span class='date-badge-today'>🔔 تسليم اليوم ({o_deliv})</span>"
                else:
                    date_status_html = f"📅 التسليم: {o_deliv}"
            else:
                date_status_html = f"📅 التسليم: {o_deliv}"

            with st.expander(
                f"📌 #{o_id} | 👤 {o_name} | 🧵 {o_item} | 🏷️ [{o_status}]"
            ):
                st.markdown(f"**حالة الموعد:** {date_status_html}", unsafe_allow_html=True)
                st.write(" ")

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.write(f"📞 **الهاتف:** {o_phone}")
                    st.write(f"📅 **تاريخ الطلب:** {o_date}")
                    st.write(f"📝 **الملاحظات:** {o_notes}")
                with c2:
                    st.write("**📐 القياسات:**")
                    st.markdown(
                        f"""
                    <span class='measure-tag'>طول: {o_len}</span>
                    <span class='measure-tag'>عرض: {o_wid}</span>
                    <span class='measure-tag'>كتف: {o_sh}</span>
                    <br>
                    <span class='measure-tag'>ردان: {o_slv}</span>
                    <span class='measure-tag'>ياخة: {o_col}</span>
                    <span class='measure-tag'>بزمة: {o_cuf}</span>
                    """,
                        unsafe_allow_html=True,
                    )
                with c3:
                    st.write("**💰 الحساب:**")
                    st.write(f"الكلي: {o_total:,.0f} | الواصل: {o_paid:,.0f}")
                    st.write(f"**المتبقي:** :red[{o_rem:,.0f}]")

                st.markdown("---")
                col_st, col_del = st.columns([3, 1])
                with col_st:
                    new_st = st.selectbox(
                        "تغيير حالة الدور:",
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
                    if st.button("🔄 تحديث الحالة", key=f"btn_st_{o_id}"):
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
                    if st.button("🗑️ حذف الطلب", key=f"del_{o_id}"):
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
        st.info("💡 لا توجد طلبات مسجلة حتى الآن.")

# --- 6. تسديد الديون والحسابات ---
elif choice == "💵 تسديد الديون والحسابات":
    st.markdown(
        "<div class='main-header'>💵 تسديد المبالغ المتبقية والديون</div>",
        unsafe_allow_html=True,
    )

    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, name, phone, item_type, total_price, advance_paid, remaining_price FROM orders WHERE remaining_price > 0 ORDER BY id DESC"
    )
    debtors = c.fetchall()
    conn.close()

    if debtors:
        st.info(f"📌 عدد الزبائن المتبقي عليهم مبالغ: **{len(debtors)}**")
        for debtor in debtors:
            d_id, d_name, d_phone, d_item, d_total, d_paid, d_rem = debtor
            with st.expander(
                f"👤 {d_name} | {d_item} | المتبقي: ⚠️ [{d_rem:,.0f}]"
            ):
                st.write(f"📞 **الهاتف:** {d_phone}")
                st.write(
                    f"💰 **السعر الكلي:** {d_total:,.0f} | **الواصل:** {d_paid:,.0f} | **المتبقي:** :red[{d_rem:,.0f}]"
                )

                col_pay1, col_pay2 = st.columns([2, 1])
                with col_pay1:
                    pay_amount = st.number_input(
                        "المبلغ المستلم الان:",
                        min_value=0.0,
                        max_value=float(d_rem),
                        step=1.0,
                        key=f"pay_input_{d_id}",
                    )
                with col_pay2:
                    st.write(" ")
                    st.write(" ")
                    if st.button("💵 تأكيد الاستلام", key=f"pay_btn_{d_id}"):
                        if pay_amount > 0:
                            new_paid = d_paid + pay_amount
                            new_rem = d_total - new_paid
                            now_str = datetime.now().strftime("%Y-%m-%d")

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
                                f"✅ تم تسديد مبلغ {pay_amount:,.0f} بنجاح!"
                            )
                            st.rerun()
    else:
        st.success("🎉 ممتاز! لا توجد مبالغ متبقية على أي زبون حالياً.")

# --- 7. البحث عن زبون ---
elif choice == "🔍 البحث عن زبون":
    st.markdown(
        "<div class='main-header'>🔍 البحث عن قياسات وسجل زبون</div>",
        unsafe_allow_html=True,
    )
    search = st.text_input("🔎 أدخل اسم الزبون أو رقم الهاتف:")

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
                st.success(f"👤 الزبون: {r[1]} ({r[3]}) - 📞 {r[2]}")
                st.write(f"📅 **تاريخ التسليم المتوقع:** {r[16]}")
                st.markdown(
                    f"""
                <span class='measure-tag'>طول: {r[4]}</span>
                <span class='measure-tag'>عرض: {r[5]}</span>
                <span class='measure-tag'>كتف: {r[6]}</span>
                <span class='measure-tag'>ردان: {r[7]}</span>
                <span class='measure-tag'>ياخة: {r[8]}</span>
                <span class='measure-tag'>بزمة: {r[9]}</span>
                """,
                    unsafe_allow_html=True,
                )
                st.write(
                    f"💵 **المالية:** الكلي: {r[11]:,.0f} | الواصل: {r[12]:,.0f} | المتبقي: :red[{r[13]:,.0f}]"
                )

                c.execute(
                    "SELECT amount, payment_date FROM payments WHERE order_id = ? ORDER BY id DESC",
                    (r[0],),
                )
                pays = c.fetchall()
                if pays:
                    st.caption("🧾 **سجل الدفعات المقبوضة:**")
                    for p in pays:
                        st.caption(f"• تم تسديد {p[0]:,.0f} بتاريخ {p[1]}")
                st.markdown("---")
        else:
            st.warning("⚠️ لم يتم العثور على زبون مطابق.")
        conn.close()

# --- 8. الإحصائيات والمالية ---
elif choice == "📊 الإحصائيات والمالية":
    st.markdown(
        "<div class='main-header'>📊 ملخص الأرباح والديون العامة - خياطة مهندس وأولاده</div>",
        unsafe_allow_html=True,
    )

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
    m1.metric("📋 إجمالي الطلبات", total_orders)
    m2.metric("💰 إجمالي المبالغ", f"{total_income:,.0f}")
    m3.metric("✅ المقبوض فعلياً", f"{total_paid:,.0f}")
    m4.metric("⚠️ الديون المتبقية", f"{total_due:,.0f}")
