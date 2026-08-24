
import io
import os
import sqlite3
from datetime import datetime, date

import pandas as pd
import streamlit as st

# مكتبات إنشاء الوصل العربي
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display


# =========================================================
# إعدادات البرنامج
# =========================================================

DB_NAME = "tailor_master.db"

SHOP_NAME = "صادق الخياط"
SHOP_PHONE = "07713146637"


# =========================================================
# إعداد صفحة Streamlit
# =========================================================

st.set_page_config(
    page_title="صادق الخياط - إدارة الطلبات",
    page_icon="✂️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# أدوات اللغة العربية
# =========================================================

def arabic_text(text):
    """
    تحويل النص العربي ليظهر بشكل صحيح داخل Pillow.
    """
    if text is None:
        return ""

    text = str(text)

    try:
        reshaped_text = arabic_reshaper.reshape(text)
        return get_display(reshaped_text)
    except Exception:
        return text


def get_arabic_font(size=22):
    """
    البحث عن خط يدعم اللغة العربية.
    """

    possible_fonts = [
        "assets/fonts/NotoNaskhArabic-Regular.ttf",
        "assets/fonts/Amiri-Regular.ttf",
        "fonts/NotoNaskhArabic-Regular.ttf",
        "NotoNaskhArabic-Regular.ttf",

        # خطوط محتملة في Windows
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "C:/Windows/Fonts/times.ttf",

        # خطوط محتملة في Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoNaskhArabic-Regular.ttf",
    ]

    for font_path in possible_fonts:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                pass

    return ImageFont.load_default()


# =========================================================
# قاعدة البيانات
# =========================================================

def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def init_db():
    conn = get_connection()
    c = conn.cursor()

    # جدول الزبائن
    c.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE,
            created_at TEXT
        )
    """)

    # جدول الطلبات
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            name TEXT NOT NULL,
            phone TEXT,
            item_type TEXT,
            length REAL,
            width REAL,
            shoulder REAL,
            sleeve REAL,
            collar REAL,
            cuff REAL,
            notes TEXT,
            total_price REAL DEFAULT 0,
            advance_paid REAL DEFAULT 0,
            remaining_price REAL DEFAULT 0,
            status TEXT DEFAULT 'قيد الانتظار',
            created_at TEXT,
            delivery_date TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )
    """)

    # دعم قاعدة البيانات القديمة
    if not column_exists(c, "orders", "customer_id"):
        c.execute("ALTER TABLE orders ADD COLUMN customer_id INTEGER")

    if not column_exists(c, "orders", "delivery_date"):
        c.execute("ALTER TABLE orders ADD COLUMN delivery_date TEXT")

    # جدول الدفعات
    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            amount REAL NOT NULL,
            payment_date TEXT,
            notes TEXT,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        )
    """)

    if not column_exists(c, "payments", "notes"):
        c.execute("ALTER TABLE payments ADD COLUMN notes TEXT")

    conn.commit()
    conn.close()


init_db()


# =========================================================
# دوال الزبائن
# =========================================================

def get_or_create_customer(name, phone):
    conn = get_connection()
    c = conn.cursor()

    customer = None

    if phone and phone.strip():
        c.execute(
            "SELECT * FROM customers WHERE phone = ?",
            (phone.strip(),)
        )
        customer = c.fetchone()

    if not customer:
        c.execute(
            "SELECT * FROM customers WHERE name = ? ORDER BY id DESC LIMIT 1",
            (name.strip(),)
        )
        customer = c.fetchone()

    if customer:
        customer_id = customer["id"]

        c.execute(
            """
            UPDATE customers
            SET name = ?, phone = ?
            WHERE id = ?
            """,
            (name.strip(), phone.strip(), customer_id)
        )

    else:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        c.execute(
            """
            INSERT INTO customers (name, phone, created_at)
            VALUES (?, ?, ?)
            """,
            (
                name.strip(),
                phone.strip() if phone else "",
                now
            )
        )

        customer_id = c.lastrowid

    conn.commit()
    conn.close()

    return customer_id


def get_customer_measurements(customer_id):
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT *
        FROM orders
        WHERE customer_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (customer_id,))

    result = c.fetchone()

    conn.close()

    return result


# =========================================================
# دوال الطلبات
# =========================================================

def create_order(
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
    delivery_date,
):
    customer_id = get_or_create_customer(name, phone)

    remaining = max(0, total_price - advance_paid)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        INSERT INTO orders (
            customer_id,
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
            remaining_price,
            status,
            created_at,
            delivery_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        customer_id,
        name.strip(),
        phone.strip() if phone else "",
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
        now,
        delivery_date
    ))

    order_id = c.lastrowid

    if advance_paid > 0:
        c.execute("""
            INSERT INTO payments (
                order_id,
                amount,
                payment_date,
                notes
            )
            VALUES (?, ?, ?, ?)
        """, (
            order_id,
            advance_paid,
            now,
            "عربون عند إنشاء الطلب"
        ))

    conn.commit()
    conn.close()

    return order_id, remaining


def get_all_orders():
    conn = get_connection()

    df = pd.read_sql_query(
        "SELECT * FROM orders ORDER BY id DESC",
        conn
    )

    conn.close()

    return df


def get_order(order_id):
    conn = get_connection()
    c = conn.cursor()

    c.execute(
        "SELECT * FROM orders WHERE id = ?",
        (order_id,)
    )

    result = c.fetchone()

    conn.close()

    return result


def update_order_status(order_id, new_status):
    conn = get_connection()
    c = conn.cursor()

    c.execute(
        "UPDATE orders SET status = ? WHERE id = ?",
        (new_status, order_id)
    )

    conn.commit()
    conn.close()


def delete_order(order_id):
    conn = get_connection()
    c = conn.cursor()

    c.execute(
        "DELETE FROM payments WHERE order_id = ?",
        (order_id,)
    )

    c.execute(
        "DELETE FROM orders WHERE id = ?",
        (order_id,)
    )

    conn.commit()
    conn.close()


def add_payment(order_id, amount, notes="دفعة جديدة"):
    order = get_order(order_id)

    if not order:
        return False, "الطلب غير موجود."

    remaining = float(order["remaining_price"] or 0)

    if amount <= 0:
        return False, "يجب أن يكون المبلغ أكبر من صفر."

    if amount > remaining:
        return False, "المبلغ أكبر من المبلغ المتبقي."

    new_paid = float(order["advance_paid"] or 0) + amount
    new_remaining = max(
        0,
        float(order["total_price"] or 0) - new_paid
    )

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        UPDATE orders
        SET advance_paid = ?, remaining_price = ?
        WHERE id = ?
    """, (
        new_paid,
        new_remaining,
        order_id
    ))

    c.execute("""
        INSERT INTO payments (
            order_id,
            amount,
            payment_date,
            notes
        )
        VALUES (?, ?, ?, ?)
    """, (
        order_id,
        amount,
        now,
        notes
    ))

    conn.commit()
    conn.close()

    return True, "تم تسجيل الدفعة بنجاح."


def get_order_payments(order_id):
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT *
        FROM payments
        WHERE order_id = ?
        ORDER BY id DESC
    """, (order_id,))

    results = c.fetchall()

    conn.close()

    return results


# =========================================================
# إنشاء وصل عربي احترافي
# =========================================================

def generate_receipt_image(order):
    """
    إنشاء وصل PNG يدعم اللغة العربية.
    """

    WIDTH = 1000
    HEIGHT = 1450

    img = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (250, 250, 250)
    )

    draw = ImageDraw.Draw(img)

    font_title = get_arabic_font(48)
    font_large = get_arabic_font(34)
    font_body = get_arabic_font(28)
    font_small = get_arabic_font(23)

    # خلفية رأس الوصل
    draw.rectangle(
        [30, 30, WIDTH - 30, 210],
        fill=(30, 41, 59)
    )

    # إطار
    draw.rectangle(
        [20, 20, WIDTH - 20, HEIGHT - 20],
        outline=(30, 41, 59),
        width=4
    )

    def draw_right_text(text, y, font, fill=(20, 20, 20), margin=70):
        shaped = arabic_text(text)

        bbox = draw.textbbox(
            (0, 0),
            shaped,
            font=font
        )

        text_width = bbox[2] - bbox[0]

        x = WIDTH - margin - text_width

        draw.text(
            (x, y),
            shaped,
            font=font,
            fill=fill
        )

    # الرأس
    draw_right_text(
        SHOP_NAME,
        60,
        font_title,
        fill=(255, 255, 255),
        margin=80
    )

    draw_right_text(
        f"الهاتف: {SHOP_PHONE}",
        130,
        font_large,
        fill=(230, 230, 230),
        margin=80
    )

    # معلومات الطلب
    y = 260

    draw_right_text(
        "وصل استلام طلب",
        y,
        font_title
    )

    y += 90

    lines = [
        f"رقم الطلب: #{order['id']}",
        f"تاريخ التسجيل: {order['created_at']}",
        f"تاريخ التسليم المتوقع: {order['delivery_date'] or 'غير محدد'}",
        f"اسم الزبون: {order['name']}",
        f"رقم الهاتف: {order['phone'] or 'غير محدد'}",
        f"نوع التفصيل: {order['item_type']}",
    ]

    for line in lines:
        draw_right_text(
            line,
            y,
            font_body
        )

        y += 55

    # خط فاصل
    draw.line(
        [70, y, WIDTH - 70, y],
        fill=(120, 120, 120),
        width=2
    )

    y += 35

    draw_right_text(
        "القياسات بالسنتيمتر",
        y,
        font_large
    )

    y += 70

    measurements = [
        f"الطول: {order['length']}",
        f"العرض: {order['width']}",
        f"عرض الكتاف: {order['shoulder']}",
        f"طول الردان: {order['sleeve']}",
        f"الياخة: {order['collar']}",
        f"البزمة: {order['cuff']}",
    ]

    for line in measurements:
        draw_right_text(
            line,
            y,
            font_body
        )

        y += 50

    draw.line(
        [70, y, WIDTH - 70, y],
        fill=(120, 120, 120),
        width=2
    )

    y += 35

    draw_right_text(
        "الحساب",
        y,
        font_large
    )

    y += 70

    financial_lines = [
        f"السعر الكلي: {float(order['total_price'] or 0):,.0f} د.ع",
        f"المبلغ المدفوع: {float(order['advance_paid'] or 0):,.0f} د.ع",
        f"المبلغ المتبقي: {float(order['remaining_price'] or 0):,.0f} د.ع",
    ]

    for line in financial_lines:
        draw_right_text(
            line,
            y,
            font_body
        )

        y += 55

    # الملاحظات
    draw.line(
        [70, y, WIDTH - 70, y],
        fill=(120, 120, 120),
        width=2
    )

    y += 35

    draw_right_text(
        f"الحالة: {order['status']}",
        y,
        font_body
    )

    y += 60

    notes = order["notes"] or "لا توجد ملاحظات"

    draw_right_text(
        f"ملاحظات: {notes}",
        y,
        font_small
    )

    # أسفل الوصل
    footer_y = HEIGHT - 130

    draw.line(
        [70, footer_y - 30, WIDTH - 70, footer_y - 30],
        fill=(120, 120, 120),
        width=2
    )

    draw_right_text(
        "شكراً لتعاملكم معنا",
        footer_y,
        font_large
    )

    draw_right_text(
        f"{SHOP_NAME} - {SHOP_PHONE}",
        footer_y + 50,
        font_small
    )

    buffer = io.BytesIO()

    img.save(
        buffer,
        format="PNG",
        quality=95
    )

    buffer.seek(0)

    return buffer.getvalue()


# =========================================================
# الواجهة الرئيسية
# =========================================================

st.title("✂️ صادق الخياط")
st.caption("نظام احترافي لإدارة الطلبات والقياسات والحسابات")

st.divider()


# =========================================================
# القائمة الجانبية
# =========================================================

menu = st.sidebar.radio(
    "القائمة الرئيسية",
    [
        "🏠 لوحة التحكم",
        "➕ إضافة طلب جديد",
        "📋 جميع الطلبات",
        "💵 الدفعات والديون",
        "👥 الزبائن",
        "🔍 البحث",
        "📊 الإحصائيات",
        "💾 النسخ الاحتياطي",
    ]
)


# =========================================================
# لوحة التحكم
# =========================================================

if menu == "🏠 لوحة التحكم":

    df = get_all_orders()

    if df.empty:

        st.info("لا توجد طلبات مسجلة حتى الآن.")

    else:

        total_orders = len(df)

        total_sales = df["total_price"].fillna(0).sum()

        total_paid = df["advance_paid"].fillna(0).sum()

        total_due = df["remaining_price"].fillna(0).sum()

        ready_orders = len(
            df[
                df["status"].isin([
                    "جاهز للاستلام",
                    "تم التسليم"
                ])
            ]
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "إجمالي الطلبات",
            total_orders
        )

        c2.metric(
            "إجمالي المبيعات",
            f"{total_sales:,.0f} د.ع"
        )

        c3.metric(
            "المبالغ المستلمة",
            f"{total_paid:,.0f} د.ع"
        )

        c4.metric(
            "الديون المتبقية",
            f"{total_due:,.0f} د.ع"
        )

        st.divider()

        st.subheader("📌 آخر الطلبات")

        display_columns = [
            "id",
            "name",
            "phone",
            "item_type",
            "status",
            "delivery_date",
            "remaining_price"
        ]

        st.dataframe(
            df[display_columns],
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# إضافة طلب جديد
# =========================================================

elif menu == "➕ إضافة طلب جديد":

    st.subheader("➕ تسجيل طلب جديد")

    with st.form(
        "new_order_form",
        clear_on_submit=True
    ):

        st.markdown("### 👤 معلومات الزبون")

        c1, c2 = st.columns(2)

        with c1:
            name = st.text_input(
                "اسم الزبون *"
            )

        with c2:
            phone = st.text_input(
                "رقم الهاتف"
            )

        st.markdown("### 👔 تفاصيل الطلب")

        c1, c2 = st.columns(2)

        with c1:

            item_type = st.selectbox(
                "نوع التفصيل",
                [
                    "دشداشة",
                    "قميص",
                    "بنطلون",
                    "بدلة كاملة",
                    "عباءة",
                    "تفصيل آخر"
                ]
            )

        with c2:

            delivery_date = st.date_input(
                "تاريخ التسليم المتوقع",
                value=date.today()
            )

        st.markdown("### 📐 القياسات بالسنتيمتر")

        m1, m2, m3 = st.columns(3)

        with m1:
            length = st.number_input(
                "الطول",
                min_value=0.0,
                step=0.5
            )

            width = st.number_input(
                "العرض",
                min_value=0.0,
                step=0.5
            )

        with m2:
            shoulder = st.number_input(
                "عرض الكتاف",
                min_value=0.0,
                step=0.5
            )

            sleeve = st.number_input(
                "طول الردان",
                min_value=0.0,
                step=0.5
            )

        with m3:
            collar = st.number_input(
                "الياخة",
                min_value=0.0,
                step=0.5
            )

            cuff = st.number_input(
                "البزمة",
                min_value=0.0,
                step=0.5
            )

        notes = st.text_area(
            "ملاحظات",
            placeholder="نوع القماش، اللون، الموديل أو أي ملاحظات أخرى..."
        )

        st.markdown("### 💰 الحساب")

        p1, p2 = st.columns(2)

        with p1:

            total_price = st.number_input(
                "السعر الكلي د.ع",
                min_value=0.0,
                step=1000.0
            )

        with p2:

            advance_paid = st.number_input(
                "المبلغ المدفوع د.ع",
                min_value=0.0,
                step=1000.0
            )

        submitted = st.form_submit_button(
            "💾 حفظ الطلب",
            use_container_width=True
        )

        if submitted:

            if not name.strip():

                st.error(
                    "يرجى إدخال اسم الزبون."
                )

            elif advance_paid > total_price:

                st.error(
                    "المبلغ المدفوع لا يمكن أن يكون أكبر من السعر الكلي."
                )

            else:

                order_id, remaining = create_order(
                    name=name,
                    phone=phone,
                    item_type=item_type,
                    length=length,
                    width=width,
                    shoulder=shoulder,
                    sleeve=sleeve,
                    collar=collar,
                    cuff=cuff,
                    notes=notes,
                    total_price=total_price,
                    advance_paid=advance_paid,
                    delivery_date=str(delivery_date),
                )

                st.success(
                    f"تم حفظ الطلب رقم #{order_id} بنجاح."
                )

                st.info(
                    f"المبلغ المتبقي: {remaining:,.0f} د.ع"
                )


# =========================================================
# جميع الطلبات
# =========================================================

elif menu == "📋 جميع الطلبات":

    st.subheader("📋 إدارة جميع الطلبات")

    df = get_all_orders()

    if df.empty:

        st.info("لا توجد طلبات.")

    else:

        status_filter = st.multiselect(
            "فلترة حسب الحالة",
            options=[
                "قيد الانتظار",
                "جارٍ القص",
                "جارٍ التفصيل",
                "جارٍ الكي",
                "جاهز للاستلام",
                "تم التسليم",
                "ملغي",
            ]
        )

        if status_filter:

            df = df[
                df["status"].isin(status_filter)
            ]

        st.write(
            f"عدد الطلبات المعروضة: {len(df)}"
        )

        for _, row in df.iterrows():

            order_id = int(row["id"])

            title = (
                f"#{order_id} | "
                f"{row['name']} | "
                f"{row['item_type']} | "
                f"{row['status']}"
            )

            with st.expander(title):

                c1, c2, c3 = st.columns(3)

                with c1:

                    st.markdown("### 👤 الزبون")

                    st.write(
                        f"**الاسم:** {row['name']}"
                    )

                    st.write(
                        f"**الهاتف:** {row['phone'] or 'غير محدد'}"
                    )

                    st.write(
                        f"**تاريخ التسجيل:** {row['created_at']}"
                    )

                    st.write(
                        f"**التسليم المتوقع:** {row['delivery_date'] or 'غير محدد'}"
                    )

                with c2:

                    st.markdown("### 📐 القياسات")

                    st.write(
                        f"الطول: {row['length']}"
                    )

                    st.write(
                        f"العرض: {row['width']}"
                    )

                    st.write(
                        f"الكتاف: {row['shoulder']}"
                    )

                    st.write(
                        f"الردان: {row['sleeve']}"
                    )

                    st.write(
                        f"الياخة: {row['collar']}"
                    )

                    st.write(
                        f"البزمة: {row['cuff']}"
                    )

                with c3:

                    st.markdown("### 💰 الحساب")

                    st.write(
                        f"**السعر الكلي:** {float(row['total_price']):,.0f} د.ع"
                    )

                    st.write(
                        f"**المدفوع:** {float(row['advance_paid']):,.0f} د.ع"
                    )

                    st.error(
                        f"المتبقي: {float(row['remaining_price']):,.0f} د.ع"
                    )

                st.divider()

                order = get_order(order_id)

                new_status = st.selectbox(
                    "تغيير حالة الطلب",
                    [
                        "قيد الانتظار",
                        "جارٍ القص",
                        "جارٍ التفصيل",
                        "جارٍ الكي",
                        "جاهز للاستلام",
                        "تم التسليم",
                        "ملغي",
                    ],
                    index=[
                        "قيد الانتظار",
                        "جارٍ القص",
                        "جارٍ التفصيل",
                        "جارٍ الكي",
                        "جاهز للاستلام",
                        "تم التسليم",
                        "ملغي",
                    ].index(order["status"]),
                    key=f"status_{order_id}"
                )

                b1, b2, b3 = st.columns(3)

                with b1:

                    if st.button(
                        "💾 تحديث الحالة",
                        key=f"update_{order_id}"
                    ):

                        update_order_status(
                            order_id,
                            new_status
                        )

                        st.success(
                            "تم تحديث الحالة."
                        )

                        st.rerun()

                with b2:

                    receipt = generate_receipt_image(
                        order
                    )

                    st.download_button(
                        "🖼️ تنزيل الوصل PNG",
                        data=receipt,
                        file_name=f"وصل_صادق_الخياط_{order_id}.png",
                        mime="image/png",
                        key=f"receipt_{order_id}",
                        use_container_width=True
                    )

                with b3:

                    if st.button(
                        "🗑️ حذف الطلب",
                        key=f"delete_{order_id}"
                    ):

                        delete_order(
                            order_id
                        )

                        st.success(
                            "تم حذف الطلب."
                        )

                        st.rerun()

                st.divider()

                st.write(
                    f"**الملاحظات:** {order['notes'] or 'لا توجد ملاحظات'}"
                )


# =========================================================
# الدفعات والديون
# =========================================================

elif menu == "💵 الدفعات والديون":

    st.subheader("💵 تسديد الديون والدفعات")

    df = get_all_orders()

    debtors = df[
        df["remaining_price"] > 0
    ]

    if debtors.empty:

        st.success(
            "🎉 لا توجد مبالغ متبقية."
        )

    else:

        total_debt = debtors[
            "remaining_price"
        ].sum()

        st.metric(
            "إجمالي الديون",
            f"{total_debt:,.0f} د.ع"
        )

        for _, row in debtors.iterrows():

            order_id = int(row["id"])

            with st.expander(
                f"#{order_id} | {row['name']} | المتبقي: {float(row['remaining_price']):,.0f} د.ع"
            ):

                st.write(
                    f"الهاتف: {row['phone']}"
                )

                st.write(
                    f"نوع الطلب: {row['item_type']}"
                )

                amount = st.number_input(
                    "مبلغ الدفعة",
                    min_value=0.0,
                    max_value=float(
                        row["remaining_price"]
                    ),
                    step=1000.0,
                    key=f"payment_{order_id}"
                )

                payment_notes = st.text_input(
                    "ملاحظات الدفعة",
                    value="دفعة جديدة",
                    key=f"payment_notes_{order_id}"
                )

                if st.button(
                    "💵 تسجيل الدفعة",
                    key=f"pay_{order_id}"
                ):

                    success, message = add_payment(
                        order_id,
                        amount,
                        payment_notes
                    )

                    if success:

                        st.success(message)

                        st.rerun()

                    else:

                        st.error(message)


# =========================================================
# الزبائن
# =========================================================

elif menu == "👥 الزبائن":

    st.subheader("👥 قاعدة بيانات الزبائن")

    conn = get_connection()

    customers = pd.read_sql_query(
        """
        SELECT *
        FROM customers
        ORDER BY id DESC
        """,
        conn
    )

    conn.close()

    if customers.empty:

        st.info(
            "لا توجد بيانات زبائن."
        )

    else:

        st.dataframe(
            customers,
            use_container_width=True,
            hide_index=True
        )

        selected_name = st.selectbox(
            "اختر زبوناً لعرض طلباته",
            customers["name"].tolist()
        )

        customer = customers[
            customers["name"] == selected_name
        ].iloc[0]

        conn = get_connection()

        customer_orders = pd.read_sql_query(
            """
            SELECT *
            FROM orders
            WHERE customer_id = ?
            ORDER BY id DESC
            """,
            conn,
            params=(int(customer["id"]),)
        )

        conn.close()

        st.subheader(
            f"طلبات الزبون: {selected_name}"
        )

        st.dataframe(
            customer_orders,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# البحث
# =========================================================

elif menu == "🔍 البحث":

    st.subheader("🔍 البحث عن طلب أو زبون")

    search = st.text_input(
        "اكتب اسم الزبون أو رقم الهاتف أو رقم الطلب"
    )

    if search:

        conn = get_connection()

        query = """
            SELECT *
            FROM orders
            WHERE
                name LIKE ?
                OR phone LIKE ?
                OR CAST(id AS TEXT) LIKE ?
            ORDER BY id DESC
        """

        results = pd.read_sql_query(
            query,
            conn,
            params=(
                f"%{search}%",
                f"%{search}%",
                f"%{search}%"
            )
        )

        conn.close()

        if results.empty:

            st.warning(
                "لم يتم العثور على نتائج."
            )

        else:

            st.success(
                f"تم العثور على {len(results)} نتيجة."
            )

            st.dataframe(
                results,
                use_container_width=True,
                hide_index=True
            )


# =========================================================
# الإحصائيات
# =========================================================

elif menu == "📊 الإحصائيات":

    st.subheader("📊 الإحصائيات المالية")

    df = get_all_orders()

    if df.empty:

        st.info(
            "لا توجد بيانات للإحصائيات."
        )

    else:

        total_orders = len(df)

        total_price = df[
            "total_price"
        ].fillna(0).sum()

        total_paid = df[
            "advance_paid"
        ].fillna(0).sum()

        total_remaining = df[
            "remaining_price"
        ].fillna(0).sum()

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "عدد الطلبات",
            total_orders
        )

        c2.metric(
            "إجمالي المبيعات",
            f"{total_price:,.0f} د.ع"
        )

        c3.metric(
            "المقبوض",
            f"{total_paid:,.0f} د.ع"
        )

        c4.metric(
            "الديون",
            f"{total_remaining:,.0f} د.ع"
        )

        st.divider()

        st.subheader(
            "📌 عدد الطلبات حسب الحالة"
        )

        status_counts = (
            df["status"]
            .value_counts()
            .reset_index()
        )

        status_counts.columns = [
            "الحالة",
            "عدد الطلبات"
        ]

        st.dataframe(
            status_counts,
            use_container_width=True,
            hide_index=True
        )

        st.bar_chart(
            status_counts.set_index("الحالة")
        )


# =========================================================
# النسخ الاحتياطي
# =========================================================

elif menu == "💾 النسخ الاحتياطي":

    st.subheader("💾 النسخ الاحتياطي")

    st.write(
        "يمكنك تنزيل نسخة من قاعدة البيانات والاحتفاظ بها في مكان آمن."
    )

    if os.path.exists(DB_NAME):

        with open(
            DB_NAME,
            "rb"
        ) as file:

            db_data = file.read()

        st.download_button(
            "⬇️ تنزيل النسخة الاحتياطية",
            data=db_data,
            file_name=f"backup_tailor_{datetime.now().strftime('%Y%m%d_%H%M')}.db",
            mime="application/octet-stream",
            use_container_width=True
        )

    st.divider()

    st.subheader(
        "♻️ استعادة نسخة احتياطية"
    )

    uploaded_backup = st.file_uploader(
        "اختر ملف قاعدة بيانات محفوظ سابقاً",
        type=["db"]
    )

    if uploaded_backup:

        st.warning(
            "سيتم استبدال قاعدة البيانات الحالية بالنسخة التي رفعتها."
        )

        confirm_restore = st.checkbox(
            "أوافق على استبدال البيانات الحالية"
        )

        if confirm_restore:

            if st.button(
                "♻️ استعادة النسخة الاحتياطية"
            ):

                with open(
                    DB_NAME,
                    "wb"
                ) as file:

                    file.write(
                        uploaded_backup.getbuffer()
                    )

                st.success(
                    "تمت استعادة النسخة الاحتياطية بنجاح."
                )

                st.rerun()
```
