import io
import os
import sqlite3
from datetime import datetime, date

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display


# =========================
# إعدادات عامة
# =========================
DB_NAME = "tailor_master.db"
SHOP_NAME = "صادق الخياط"
SHOP_PHONE = "07713146637"

STATUSES = [
    "قيد الانتظار",
    "جارٍ القص",
    "جارٍ التفصيل",
    "جارٍ الكي",
    "جاهز للاستلام",
    "تم التسليم",
    "ملغي",
]

st.set_page_config(
    page_title=f"{SHOP_NAME} - إدارة الطلبات",
    page_icon="✂️",
    layout="wide",
)


# =========================
# أدوات اللغة العربية
# =========================
def rtl(text):
    if text is None:
        return ""
    try:
        return get_display(arabic_reshaper.reshape(str(text)))
    except Exception:
        return str(text)


def get_font(size):
    paths = [
        "assets/fonts/NotoNaskhArabic-Regular.ttf",
        "assets/fonts/Amiri-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoNaskhArabic-Regular.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


# =========================
# قاعدة البيانات
# =========================
def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_columns(conn, table):
    return [row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def ensure_column(conn, table, column, definition):
    if column not in get_columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            created_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            name TEXT NOT NULL,
            phone TEXT,
            item_type TEXT,
            length REAL DEFAULT 0,
            width REAL DEFAULT 0,
            shoulder REAL DEFAULT 0,
            sleeve REAL DEFAULT 0,
            collar REAL DEFAULT 0,
            cuff REAL DEFAULT 0,
            notes TEXT,
            total_price REAL DEFAULT 0,
            advance_paid REAL DEFAULT 0,
            remaining_price REAL DEFAULT 0,
            status TEXT DEFAULT 'قيد الانتظار',
            created_at TEXT,
            delivery_date TEXT
        )
    """)

    # دعم قواعد البيانات القديمة
    ensure_column(conn, "orders", "customer_id", "INTEGER")
    ensure_column(conn, "orders", "delivery_date", "TEXT")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            amount REAL NOT NULL,
            payment_date TEXT,
            notes TEXT
        )
    """)

    ensure_column(conn, "payments", "notes", "TEXT")

    conn.commit()
    conn.close()


init_db()


# =========================
# دوال البيانات
# =========================
def get_or_create_customer(name, phone):
    conn = get_connection()
    phone = (phone or "").strip()
    name = name.strip()

    customer = None
    if phone:
        customer = conn.execute(
            "SELECT * FROM customers WHERE phone = ? ORDER BY id DESC LIMIT 1",
            (phone,)
        ).fetchone()

    if customer is None:
        customer = conn.execute(
            "SELECT * FROM customers WHERE name = ? ORDER BY id DESC LIMIT 1",
            (name,)
        ).fetchone()

    if customer:
        customer_id = customer["id"]
        conn.execute(
            "UPDATE customers SET name = ?, phone = ? WHERE id = ?",
            (name, phone, customer_id)
        )
    else:
        customer_id = conn.execute(
            "INSERT INTO customers (name, phone, created_at) VALUES (?, ?, ?)",
            (name, phone, datetime.now().strftime("%Y-%m-%d %H:%M"))
        ).lastrowid

    conn.commit()
    conn.close()
    return customer_id


def create_order(data):
    customer_id = get_or_create_customer(data["name"], data["phone"])
    remaining = max(0.0, data["total_price"] - data["advance_paid"])
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = get_connection()
    order_id = conn.execute("""
        INSERT INTO orders (
            customer_id, name, phone, item_type,
            length, width, shoulder, sleeve, collar, cuff,
            notes, total_price, advance_paid, remaining_price,
            status, created_at, delivery_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        customer_id,
        data["name"].strip(),
        (data["phone"] or "").strip(),
        data["item_type"],
        data["length"],
        data["width"],
        data["shoulder"],
        data["sleeve"],
        data["collar"],
        data["cuff"],
        data["notes"],
        data["total_price"],
        data["advance_paid"],
        remaining,
        "قيد الانتظار",
        now,
        str(data["delivery_date"]),
    )).lastrowid

    if data["advance_paid"] > 0:
        conn.execute(
            "INSERT INTO payments (order_id, amount, payment_date, notes) VALUES (?, ?, ?, ?)",
            (order_id, data["advance_paid"], now, "عربون عند تسجيل الطلب")
        )

    conn.commit()
    conn.close()
    return order_id, remaining


def get_orders():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
    conn.close()
    return df


def get_order(order_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    return row


def update_status(order_id, status):
    conn = get_connection()
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()


def delete_order(order_id):
    conn = get_connection()
    conn.execute("DELETE FROM payments WHERE order_id = ?", (order_id,))
    conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()


def add_payment(order_id, amount, notes):
    order = get_order(order_id)
    if order is None:
        return False, "الطلب غير موجود."

    amount = float(amount)
    remaining = float(order["remaining_price"] or 0)

    if amount <= 0:
        return False, "أدخل مبلغًا أكبر من صفر."

    if amount > remaining:
        return False, "المبلغ أكبر من المبلغ المتبقي."

    new_paid = float(order["advance_paid"] or 0) + amount
    new_remaining = max(0.0, float(order["total_price"] or 0) - new_paid)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = get_connection()
    conn.execute(
        "UPDATE orders SET advance_paid = ?, remaining_price = ? WHERE id = ?",
        (new_paid, new_remaining, order_id)
    )
    conn.execute(
        "INSERT INTO payments (order_id, amount, payment_date, notes) VALUES (?, ?, ?, ?)",
        (order_id, amount, now, notes or "دفعة جديدة")
    )
    conn.commit()
    conn.close()
    return True, "تم تسجيل الدفعة بنجاح."


def get_payments(order_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM payments WHERE order_id = ? ORDER BY id DESC",
        (order_id,)
    ).fetchall()
    conn.close()
    return rows


# =========================
# إنشاء الوصل كصورة PNG
# =========================
def generate_receipt(order):
    width, height = 1100, 1550
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    title_font = get_font(52)
    big_font = get_font(38)
    body_font = get_font(29)
    small_font = get_font(24)

    draw.rectangle((20, 20, width - 20, height - 20), outline=(35, 55, 75), width=5)
    draw.rectangle((25, 25, width - 25, 220), fill=(35, 55, 75))

    def right(text, y, font, fill=(20, 20, 20), margin=70):
        shaped = rtl(text)
        box = draw.textbbox((0, 0), shaped, font=font)
        x = width - margin - (box[2] - box[0])
        draw.text((x, y), shaped, font=font, fill=fill)

    right(SHOP_NAME, 55, title_font, "white")
    right(f"الهاتف: {SHOP_PHONE}", 135, big_font, (230, 235, 240))

    y = 270
    right("وصل استلام طلب", y, title_font)
    y += 95

    info = [
        f"رقم الطلب: #{order['id']}",
        f"تاريخ التسجيل: {order['created_at'] or ''}",
        f"تاريخ التسليم: {order['delivery_date'] or 'غير محدد'}",
        f"اسم الزبون: {order['name']}",
        f"رقم الهاتف: {order['phone'] or 'غير محدد'}",
        f"نوع التفصيل: {order['item_type'] or ''}",
    ]

    for line in info:
        right(line, y, body_font)
        y += 58

    draw.line((70, y, width - 70, y), fill=(160, 160, 160), width=2)
    y += 30
    right("القياسات (سم)", y, big_font)
    y += 65

    measurements = [
        f"الطول: {order['length']}",
        f"العرض: {order['width']}",
        f"الكتاف: {order['shoulder']}",
        f"طول الردان: {order['sleeve']}",
        f"الياخة: {order['collar']}",
        f"البزمة: {order['cuff']}",
    ]

    for line in measurements:
        right(line, y, body_font)
        y += 50

    draw.line((70, y, width - 70, y), fill=(160, 160, 160), width=2)
    y += 30
    right("الحساب", y, big_font)
    y += 65

    finance = [
        f"السعر الكلي: {float(order['total_price'] or 0):,.0f} د.ع",
        f"المبلغ المدفوع: {float(order['advance_paid'] or 0):,.0f} د.ع",
        f"المبلغ المتبقي: {float(order['remaining_price'] or 0):,.0f} د.ع",
        f"الحالة: {order['status'] or ''}",
    ]

    for line in finance:
        right(line, y, body_font)
        y += 58

    draw.line((70, y, width - 70, y), fill=(160, 160, 160), width=2)
    y += 30
    right("ملاحظات", y, big_font)
    y += 60

    notes = order["notes"] or "لا توجد ملاحظات"
    # قص الملاحظات الطويلة إلى عدة أسطر
    words = str(notes).split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if len(test) > 55:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    for line in lines[:5]:
        right(line, y, small_font)
        y += 42

    footer_y = height - 130
    draw.line((70, footer_y - 25, width - 70, footer_y - 25), fill=(160, 160, 160), width=2)
    right("شكراً لتعاملكم معنا", footer_y, big_font)
    right(SHOP_NAME, footer_y + 55, small_font)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()


# =========================
# الواجهة
# =========================
st.title("✂️ صادق الخياط")
st.caption("نظام إدارة الطلبات والقياسات والحسابات")

menu = st.sidebar.radio(
    "القائمة الرئيسية",
    [
        "🏠 لوحة التحكم",
        "➕ إضافة طلب",
        "📋 إدارة الطلبات",
        "💵 الدفعات والديون",
        "👥 الزبائن",
        "🔍 البحث",
        "📊 الإحصائيات",
        "💾 النسخ الاحتياطي",
    ],
)


# لوحة التحكم
if menu == "🏠 لوحة التحكم":
    df = get_orders()

    if df.empty:
        st.info("لا توجد طلبات مسجلة حتى الآن.")
    else:
        total_orders = len(df)
        total_price = df["total_price"].fillna(0).sum()
        total_paid = df["advance_paid"].fillna(0).sum()
        total_due = df["remaining_price"].fillna(0).sum()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("إجمالي الطلبات", total_orders)
        c2.metric("إجمالي المبيعات", f"{total_price:,.0f} د.ع")
        c3.metric("المقبوض", f"{total_paid:,.0f} د.ع")
        c4.metric("المتبقي", f"{total_due:,.0f} د.ع")

        st.subheader("آخر الطلبات")
        show = df[["id", "name", "phone", "item_type", "status", "delivery_date", "remaining_price"]].copy()
        show.columns = ["رقم", "الزبون", "الهاتف", "الطلب", "الحالة", "التسليم", "المتبقي"]
        st.dataframe(show, use_container_width=True, hide_index=True)


# إضافة طلب
elif menu == "➕ إضافة طلب":
    st.subheader("تسجيل طلب جديد")

    with st.form("new_order", clear_on_submit=True):
        st.markdown("### معلومات الزبون")
        c1, c2 = st.columns(2)
        name = c1.text_input("اسم الزبون *")
        phone = c2.text_input("رقم الهاتف")

        st.markdown("### تفاصيل الطلب")
        c1, c2 = st.columns(2)
        item_type = c1.selectbox(
            "نوع التفصيل",
            ["دشداشة", "قميص", "بنطلون", "بدلة كاملة", "عباءة", "تفصيل آخر"]
        )
        delivery_date = c2.date_input("تاريخ التسليم المتوقع", value=date.today())

        st.markdown("### القياسات بالسنتيمتر")
        a, b, c = st.columns(3)
        length = a.number_input("الطول", min_value=0.0, step=0.5)
        width = a.number_input("العرض", min_value=0.0, step=0.5)
        shoulder = b.number_input("عرض الكتاف", min_value=0.0, step=0.5)
        sleeve = b.number_input("طول الردان", min_value=0.0, step=0.5)
        collar = c.number_input("الياخة", min_value=0.0, step=0.5)
        cuff = c.number_input("البزمة", min_value=0.0, step=0.5)

        notes = st.text_area("ملاحظات", placeholder="القماش، اللون، الموديل...")

        st.markdown("### الحساب")
        p1, p2 = st.columns(2)
        total_price = p1.number_input("السعر الكلي (د.ع)", min_value=0.0, step=1000.0)
        advance_paid = p2.number_input("المبلغ المدفوع (د.ع)", min_value=0.0, step=1000.0)

        submitted = st.form_submit_button("💾 حفظ الطلب", use_container_width=True)

        if submitted:
            if not name.strip():
                st.error("يرجى إدخال اسم الزبون.")
            elif advance_paid > total_price:
                st.error("المبلغ المدفوع لا يمكن أن يكون أكبر من السعر الكلي.")
            else:
                order_id, remaining = create_order({
                    "name": name,
                    "phone": phone,
                    "item_type": item_type,
                    "length": length,
                    "width": width,
                    "shoulder": shoulder,
                    "sleeve": sleeve,
                    "collar": collar,
                    "cuff": cuff,
                    "notes": notes,
                    "total_price": total_price,
                    "advance_paid": advance_paid,
                    "delivery_date": delivery_date,
                })
                st.success(f"تم حفظ الطلب رقم #{order_id} بنجاح.")
                st.info(f"المبلغ المتبقي: {remaining:,.0f} د.ع")


# إدارة الطلبات
elif menu == "📋 إدارة الطلبات":
    st.subheader("إدارة الطلبات")
    df = get_orders()

    if df.empty:
        st.info("لا توجد طلبات.")
    else:
        selected_statuses = st.multiselect("فلترة حسب الحالة", STATUSES)
        if selected_statuses:
            df = df[df["status"].isin(selected_statuses)]

        st.caption(f"عدد الطلبات: {len(df)}")

        for _, row in df.iterrows():
            order_id = int(row["id"])
            with st.expander(
                f"#{order_id} | {row['name']} | {row['item_type']} | {row['status']}"
            ):
                a, b, c = st.columns(3)

                with a:
                    st.write(f"**الزبون:** {row['name']}")
                    st.write(f"**الهاتف:** {row['phone'] or 'غير محدد'}")
                    st.write(f"**التسجيل:** {row['created_at']}")
                    st.write(f"**التسليم:** {row['delivery_date'] or 'غير محدد'}")

                with b:
                    st.write("**القياسات**")
                    st.write(f"الطول: {row['length']}")
                    st.write(f"العرض: {row['width']}")
                    st.write(f"الكتاف: {row['shoulder']}")
                    st.write(f"الردان: {row['sleeve']}")
                    st.write(f"الياخة: {row['collar']}")
                    st.write(f"البزمة: {row['cuff']}")

                with c:
                    st.write(f"**السعر:** {float(row['total_price'] or 0):,.0f} د.ع")
                    st.write(f"**المدفوع:** {float(row['advance_paid'] or 0):,.0f} د.ع")
                    st.write(f"**المتبقي:** {float(row['remaining_price'] or 0):,.0f} د.ع")

                st.write(f"**الملاحظات:** {row['notes'] or 'لا توجد ملاحظات'}")

                order = get_order(order_id)
                current_status = order["status"] if order else "قيد الانتظار"
                status_index = STATUSES.index(current_status) if current_status in STATUSES else 0

                new_status = st.selectbox(
                    "حالة الطلب",
                    STATUSES,
                    index=status_index,
                    key=f"status_{order_id}",
                )

                x1, x2, x3 = st.columns(3)

                if x1.button("💾 تحديث الحالة", key=f"update_{order_id}"):
                    update_status(order_id, new_status)
                    st.success("تم تحديث الحالة.")
                    st.rerun()

                receipt = generate_receipt(order)
                x2.download_button(
                    "🖼️ تنزيل الوصل PNG",
                    data=receipt,
                    file_name=f"receipt_{order_id}.png",
                    mime="image/png",
                    key=f"receipt_{order_id}",
                    use_container_width=True,
                )

                if x3.button("🗑️ حذف الطلب", key=f"delete_{order_id}"):
                    delete_order(order_id)
                    st.success("تم حذف الطلب.")
                    st.rerun()

                payments = get_payments(order_id)
                if payments:
                    st.write("**سجل الدفعات:**")
                    payment_df = pd.DataFrame(
                        [dict(p) for p in payments]
                    )[["amount", "payment_date", "notes"]]
                    payment_df.columns = ["المبلغ", "التاريخ", "ملاحظات"]
                    st.dataframe(payment_df, use_container_width=True, hide_index=True)


# الدفعات والديون
elif menu == "💵 الدفعات والديون":
    st.subheader("الدفعات والديون")
    df = get_orders()

    if df.empty:
        st.info("لا توجد بيانات.")
    else:
        debtors = df[df["remaining_price"].fillna(0) > 0]

        if debtors.empty:
            st.success("🎉 لا توجد مبالغ متبقية.")
        else:
            total_debt = debtors["remaining_price"].sum()
            st.metric("إجمالي الديون", f"{total_debt:,.0f} د.ع")

            for _, row in debtors.iterrows():
                order_id = int(row["id"])
                with st.expander(
                    f"#{order_id} | {row['name']} | المتبقي {float(row['remaining_price']):,.0f} د.ع"
                ):
                    amount = st.number_input(
                        "المبلغ المستلم",
                        min_value=0.0,
                        max_value=float(row["remaining_price"]),
                        step=1000.0,
                        key=f"amount_{order_id}",
                    )
                    note = st.text_input(
                        "ملاحظات",
                        value="دفعة جديدة",
                        key=f"note_{order_id}",
                    )
                    if st.button("💵 تسجيل الدفعة", key=f"pay_{order_id}"):
                        ok, message = add_payment(order_id, amount, note)
                        if ok:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)


# الزبائن
elif menu == "👥 الزبائن":
    st.subheader("قاعدة بيانات الزبائن")
    conn = get_connection()
    customers = pd.read_sql_query(
        "SELECT id, name, phone, created_at FROM customers ORDER BY id DESC",
        conn
    )
    conn.close()

    if customers.empty:
        st.info("لا توجد بيانات زبائن.")
    else:
        view = customers.copy()
        view.columns = ["رقم", "الاسم", "الهاتف", "تاريخ الإضافة"]
        st.dataframe(view, use_container_width=True, hide_index=True)

        customer_id = st.selectbox(
            "اختر زبونًا لعرض طلباته",
            customers["id"].tolist(),
            format_func=lambda x: (
                f"{customers.loc[customers['id'] == x, 'name'].iloc[0]}"
                f" - {customers.loc[customers['id'] == x, 'phone'].iloc[0]}"
            ),
        )

        conn = get_connection()
        orders = pd.read_sql_query(
            "SELECT * FROM orders WHERE customer_id = ? ORDER BY id DESC",
            conn,
            params=(int(customer_id),),
        )
        conn.close()

        if orders.empty:
            st.info("لا توجد طلبات لهذا الزبون.")
        else:
            st.dataframe(orders, use_container_width=True, hide_index=True)


# البحث
elif menu == "🔍 البحث":
    st.subheader("البحث")
    search = st.text_input("ابحث بالاسم أو رقم الهاتف أو رقم الطلب")

    if search.strip():
        conn = get_connection()
        results = pd.read_sql_query(
            """
            SELECT * FROM orders
            WHERE name LIKE ?
               OR phone LIKE ?
               OR CAST(id AS TEXT) LIKE ?
            ORDER BY id DESC
            """,
            conn,
            params=(f"%{search}%", f"%{search}%", f"%{search}%"),
        )
        conn.close()

        if results.empty:
            st.warning("لم يتم العثور على نتائج.")
        else:
            st.success(f"تم العثور على {len(results)} نتيجة.")
            st.dataframe(results, use_container_width=True, hide_index=True)


# الإحصائيات
elif menu == "📊 الإحصائيات":
    st.subheader("الإحصائيات")
    df = get_orders()

    if df.empty:
        st.info("لا توجد بيانات للإحصائيات.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("عدد الطلبات", len(df))
        c2.metric("إجمالي المبيعات", f"{df['total_price'].fillna(0).sum():,.0f} د.ع")
        c3.metric("المقبوض", f"{df['advance_paid'].fillna(0).sum():,.0f} د.ع")
        c4.metric("الديون", f"{df['remaining_price'].fillna(0).sum():,.0f} د.ع")

        st.subheader("الطلبات حسب الحالة")
        counts = df["status"].value_counts()
        st.bar_chart(counts)


# النسخ الاحتياطي
elif menu == "💾 النسخ الاحتياطي":
    st.subheader("النسخ الاحتياطي")

    if os.path.exists(DB_NAME):
        with open(DB_NAME, "rb") as f:
            st.download_button(
                "⬇️ تنزيل نسخة احتياطية",
                data=f.read(),
                file_name=f"tailor_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.db",
                mime="application/octet-stream",
                use_container_width=True,
            )

    st.divider()
    st.subheader("استعادة نسخة احتياطية")
    backup = st.file_uploader("اختر ملف النسخة الاحتياطية", type=["db"])

    if backup is not None:
        confirm = st.checkbox("أفهم أن البيانات الحالية سيتم استبدالها.")

        if confirm and st.button("♻️ استعادة النسخة"):
            with open(DB_NAME, "wb") as f:
                f.write(backup.getbuffer())

            init_db()
            st.success("تمت استعادة النسخة الاحتياطية بنجاح.")
            st.rerun()
