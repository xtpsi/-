from datetime import datetime
import sqlite3
import streamlit as st

# --- 1. إعداد قاعدة البيانات وتحديث الجداول ---
conn = sqlite3.connect("", check_same_thread=False)
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
        total_price REAL,
        paid_amount REAL,
        remaining_amount REAL,
        order_date TEXT,
        delivery_date TEXT,
        notes TEXT, 
        status TEXT
    )
"""
)
conn.commit()

# --- 2. إعدادات الواجهة ---
st.set_page_config(
    page_title="نظام الخياطة والمحاسبة", page_icon="✂️", layout="wide"
)
st.title("✂️ نظام إدارة المحل والمحاسبة الشامل")

menu = ["إضافة زبون جديد", "جدول الدور والطلبات", "التقرير المالي والمحاسبة"]
choice = st.sidebar.radio("القائمة الرئيسية:", menu)

# --- الصفحة الأولى: إضافة زبون وحساب المبالغ ---
if choice == "إضافة زبون جديد":
    st.subheader("📝 تسجيل طلب وقياسات جديدة")

    with st.form("add_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("اسم الزبون *")
            phone = st.text_input("رقم الهاتف")
            item_type = st.selectbox(
                "نوع التفصال", ["دشداشة", "قميص", "بنطلون", "بدلة"]
            )
            order_date = st.date_input("تاريخ الطلب", datetime.now()).strftime(
                "%Y-%m-%d"
            )
            delivery_date = st.date_input(
                "موعد التسليم المتوقع"
            ).strftime("%Y-%m-%d")

        with col2:
            st.markdown("**الحسابات المالية:**")
            total_price = st.number_input(
                "السعر الكلي (د.ع)", min_value=0.0, step=1000.0
            )
            paid_amount = st.number_input(
                "المبلغ المدفوع (العربون)", min_value=0.0, step=1000.0
            )
            remaining_amount = total_price - paid_amount
            st.info(f"المبلغ المتبقي: **{remaining_amount:,.0f} د.ع**")

        st.markdown("---")
        st.markdown("**القياسات (بالسم):**")
        q1, q2, q3 = st.columns(3)
        with q1:
            length = st.number_input("الطول الكلي", min_value=0.0)
            width = st.number_input("العرض (الصدر)", min_value=0.0)
        with q2:
            shoulder = st.number_input("عرض الكتاف", min_value=0.0)
            sleeve = st.number_input("طول الردان", min_value=0.0)
        with q3:
            collar = st.number_input("الياخة", min_value=0.0)
            cuff = st.number_input("البزمة", min_value=0.0)

        notes = st.text_area("ملاحظات تفصيلية (نوع القماش، التفاصيل)")
        submit = st.form_submit_button("حفظ الطلب")

        if submit:
            if name:
                c.execute(
                    """
                    INSERT INTO orders (
                        name, phone, item_type, length, width, shoulder, sleeve, collar, cuff,
                        total_price, paid_amount, remaining_amount, order_date, delivery_date, notes, status
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
                        total_price,
                        paid_amount,
                        remaining_amount,
                        order_date,
                        delivery_date,
                        notes,
                        "قيد الانتظار",
                    ),
                )
                conn.commit()
                st.success(f"تم حفظ طلب الزبون {name} بنجاح!")
            else:
                st.error("يرجى إدخال اسم الزبون.")

# --- الصفحة الثانية: متابعة الدور وتحديث الحسابات ---
elif choice == "جدول الدور والطلبات":
    st.subheader("📋 جدول العمل والدور")

    c.execute("SELECT * FROM orders ORDER BY id DESC")
    rows = c.fetchall()

    if rows:
        for row in rows:
            with st.expander(
                f"طلب #{row[0]} | الزبون: {row[1]} | النوع: {row[3]} | التسليم: {row[14]} | الحالة: [{row[16]}]"
            ):
                col_a, col_b = st.columns(2)

                with col_a:
                    st.write(f"**الهاتف:** {row[2]}")
                    st.write(f"**تاريخ الطلب:** {row[13]}")
                    st.write(f"**موعد التسليم:** {row[14]}")
                    st.write(
                        f"**القياسات:** طول: {row[4]} | عرض: {row[5]} | كتاف: {row[6]} | ردان: {row[7]} | ياخة: {row[8]} | بزمة: {row[9]}"
                    )
                    st.write(f"**الملاحظات:** {row[15]}")

                with col_b:
                    st.write(f"**السعر الكلي:** {row[10]:,.0f} د.ع")
                    st.write(f"**المدفوع:** {row[11]:,.0f} د.ع")
                    st.write(f"**المتبقي:** {row[12]:,.0f} د.ع")

                    # تحديث الدفع والحالة
                    new_status = st.selectbox(
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
                        ].index(row[16]),
                        key=f"st_{row[0]}",
                    )

                    if st.button("تحديث البيانات", key=f"btn_{row[0]}"):
                        c.execute(
                            "UPDATE orders SET status = ? WHERE id = ?",
                            (new_status, row[0]),
                        )
                        conn.commit()
                        st.rerun()
    else:
        st.info("لا توجد طلبات.")

# --- الصفحة الثالثة: التقرير المالي والمحاسبة ---
elif choice == "التقرير المالي والمحاسبة":
    st.subheader("💰 التقرير المالي والإحصائيات")

    c.execute(
        "SELECT SUM(total_price), SUM(paid_amount), SUM(remaining_amount) FROM orders"
    )
    financials = c.fetchone()

    total_income = financials[0] if financials[0] else 0.0
    total_paid = financials[1] if financials[1] else 0.0
    total_remaining = financials[2] if financials[2] else 0.0

    m1, m2, m3 = st.columns(3)
    m1.metric("إجمالي حجم الأعمال", f"{total_income:,.0f} د.ع")
    m2.metric("إجمالي المبالغ المستلمة", f"{total_paid:,.0f} د.ع")
    m3.metric("إجمالي الديون (المتبقي)", f"{total_remaining:,.0f} د.ع")

    st.markdown("---")
    st.write("### 🚨 زبائن عليهم مبالغ متبقية:")

    c.execute(
        "SELECT name, phone, remaining_amount, delivery_date FROM orders WHERE remaining_amount > 0"
    )
    debtors = c.fetchall()

    if debtors:
        for d in debtors:
            st.warning(
                f"**الزبون:** {d[0]} | **الهاتف:** {d[1]} | **المبلغ المتبقي:** {d[2]:,.0f} د.ع | **موعد التسليم:** {d[3]}"
            )
    else:
        st.success("لا توجد أي مبالغ متبقية على الزبائن!")