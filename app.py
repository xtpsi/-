import io
import os
import sqlite3
from datetime import datetime, date, timedelta
import time

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# =========================
# إعدادات المحل (يمكنك تعديلها هنا)
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

@st.cache_resource
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
# إدارة قاعدة البيانات
# =========================
class DatabaseManager:
    _instance = None
    _conn = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    def get_connection(self):
        if self._conn is None:
            self._conn = sqlite3.connect(DB_NAME, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn
    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
    def execute(self, query, params=None):
        conn = self.get_connection()
        try:
            if params:
                return conn.execute(query, params)
            return conn.execute(query)
        except sqlite3.Error as e:
            st.error(f"خطأ في قاعدة البيانات: {e}")
            return None
    def commit(self):
        if self._conn:
            self._conn.commit()

db = DatabaseManager()

def get_columns(table):
    conn = db.get_connection()
    return [row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]

def ensure_column(table, column, definition):
    if column not in get_columns(table):
        conn = db.get_connection()
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        db.commit()

def init_db():
    conn = db.get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            created_at TEXT,
            last_order_date TEXT
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
            delivery_date TEXT,
            updated_at TEXT
        )
    """)
    ensure_column("orders", "customer_id", "INTEGER")
    ensure_column("orders", "delivery_date", "TEXT")
    ensure_column("orders", "updated_at", "TEXT")
    ensure_column("customers", "last_order_date", "TEXT")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            amount REAL NOT NULL,
            payment_date TEXT,
            notes TEXT
        )
    """)
    ensure_column("payments", "notes", "TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at)")
    db.commit()

init_db()

# =========================
# دوال البيانات
# =========================
@st.cache_data(ttl=60)
def get_customers():
    conn = db.get_connection()
    return pd.read_sql_query("SELECT * FROM customers ORDER BY id DESC", conn)

@st.cache_data(ttl=30)
def get_orders():
    conn = db.get_connection()
    return pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)

def get_order(order_id):
    conn = db.get_connection()
    return conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()

def get_payments(order_id):
    conn = db.get_connection()
    return conn.execute("SELECT * FROM payments WHERE order_id = ? ORDER BY id DESC", (order_id,)).fetchall()

def get_or_create_customer(name, phone):
    conn = db.get_connection()
    phone = (phone or "").strip()
    name = name.strip()
    customer = None
    if phone:
        customer = conn.execute("SELECT * FROM customers WHERE phone = ? ORDER BY id DESC LIMIT 1", (phone,)).fetchone()
    if customer is None:
        customer = conn.execute("SELECT * FROM customers WHERE name = ? ORDER BY id DESC LIMIT 1", (name,)).fetchone()
    if customer:
        customer_id = customer["id"]
        conn.execute("UPDATE customers SET name = ?, phone = ?, last_order_date = ? WHERE id = ?",
                     (name, phone, datetime.now().strftime("%Y-%m-%d %H:%M"), customer_id))
    else:
        customer_id = conn.execute(
            "INSERT INTO customers (name, phone, created_at, last_order_date) VALUES (?, ?, ?, ?)",
            (name, phone, datetime.now().strftime("%Y-%m-%d %H:%M"), datetime.now().strftime("%Y-%m-%d %H:%M"))
        ).lastrowid
    db.commit()
    return customer_id

def create_order(data):
    try:
        customer_id = get_or_create_customer(data["name"], data["phone"])
        remaining = max(0.0, data["total_price"] - data["advance_paid"])
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn = db.get_connection()
        order_id = conn.execute("""
            INSERT INTO orders (
                customer_id, name, phone, item_type,
                length, width, shoulder, sleeve, collar, cuff,
                notes, total_price, advance_paid, remaining_price,
                status, created_at, delivery_date, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            now
        )).lastrowid
        if data["advance_paid"] > 0:
            conn.execute("INSERT INTO payments (order_id, amount, payment_date, notes) VALUES (?, ?, ?, ?)",
                         (order_id, data["advance_paid"], now, "عربون عند تسجيل الطلب"))
        db.commit()
        st.cache_data.clear()
        return order_id, remaining, None
    except Exception as e:
        return None, None, str(e)

def update_status(order_id, status):
    try:
        conn = db.get_connection()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn.execute("UPDATE orders SET status = ?, updated_at = ? WHERE id = ?", (status, now, order_id))
        db.commit()
        st.cache_data.clear()
        return True, None
    except Exception as e:
        return False, str(e)

def delete_order(order_id):
    try:
        conn = db.get_connection()
        conn.execute("DELETE FROM payments WHERE order_id = ?", (order_id,))
        conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
        db.commit()
        st.cache_data.clear()
        return True, None
    except Exception as e:
        return False, str(e)

def add_payment(order_id, amount, notes):
    try:
        order = get_order(order_id)
        if order is None:
            return False, "الطلب غير موجود."
        amount = float(amount)
        remaining = float(order["remaining_price"] or 0)
        if amount <= 0:
            return False, "أدخل مبلغًا أكبر من صفر."
        if amount > remaining:
            return False, f"المبلغ أكبر من المبلغ المتبقي ({remaining:,.0f} د.ع)."
        new_paid = float(order["advance_paid"] or 0) + amount
        new_remaining = max(0.0, float(order["total_price"] or 0) - new_paid)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn = db.get_connection()
        conn.execute("UPDATE orders SET advance_paid = ?, remaining_price = ?, updated_at = ? WHERE id = ?",
                     (new_paid, new_remaining, now, order_id))
        conn.execute("INSERT INTO payments (order_id, amount, payment_date, notes) VALUES (?, ?, ?, ?)",
                     (order_id, amount, now, notes or "دفعة جديدة"))
        db.commit()
        st.cache_data.clear()
        return True, "تم تسجيل الدفعة بنجاح."
    except Exception as e:
        return False, str(e)

def get_monthly_report():
    df = get_orders()
    if df.empty:
        return pd.DataFrame()
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['month'] = df['created_at'].dt.to_period('M')
    monthly = df.groupby('month').agg({
        'total_price': 'sum',
        'advance_paid': 'sum',
        'id': 'count'
    }).reset_index()
    monthly.columns = ['الشهر', 'إجمالي المبيعات', 'المقبوض', 'عدد الطلبات']
    return monthly

def get_overdue_orders():
    df = get_orders()
    if df.empty:
        return df
    df['delivery_date'] = pd.to_datetime(df['delivery_date']).dt.date
    today = date.today()
    return df[(df['delivery_date'] < today) & (df['status'] != 'تم التسليم') & (df['status'] != 'ملغي')]

def get_status_counts():
    df = get_orders()
    if df.empty:
        return pd.Series()
    return df['status'].value_counts()

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
# الواجهة الرئيسية (بدون مصادقة)
# =========================
def main():
    st.title("✂️ صادق الخياط")
    st.caption("نظام إدارة الطلبات والقياسات والحسابات - نسخة مبسطة بدون كلمة مرور")

    overdue = get_overdue_orders()
    if not overdue.empty:
        st.warning(f"⚠️ هناك {len(overdue)} طلباً متأخراً عن موعد التسليم!")

    menu = st.sidebar.radio(
        "القائمة الرئيسية",
        [
            "🏠 لوحة التحكم",
            "➕ إضافة طلب",
            "📋 إدارة الطلبات",
            "💵 الدفعات والديون",
            "👥 الزبائن",
            "🔍 البحث المتقدم",
            "📊 الإحصائيات والتقارير",
            "💾 النسخ الاحتياطي",
        ],
    )

    # ---------- لوحة التحكم ----------
    if menu == "🏠 لوحة التحكم":
        st.subheader("📊 لوحة التحكم")
        df = get_orders()
        if df.empty:
            st.info("لا توجد طلبات مسجلة حتى الآن.")
            return

        total_orders = len(df)
        total_revenue = df["total_price"].fillna(0).sum()
        total_paid = df["advance_paid"].fillna(0).sum()
        total_due = df["remaining_price"].fillna(0).sum()
        completed = len(df[df["status"] == "تم التسليم"])
        completion_rate = (completed / total_orders * 100) if total_orders > 0 else 0

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("📦 إجمالي الطلبات", total_orders)
        col2.metric("💰 إجمالي المبيعات", f"{total_revenue:,.0f} د.ع")
        col3.metric("💵 المقبوض", f"{total_paid:,.0f} د.ع")
        col4.metric("📉 المتبقي", f"{total_due:,.0f} د.ع", delta=f"{total_due/total_revenue*100:.1f}%" if total_revenue > 0 else "0%")
        col5.metric("✅ نسبة الإنجاز", f"{completion_rate:.1f}%")

        # رسوم بيانية باستخدام Streamlit Charts (بدون matplotlib)
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("توزيع الطلبات حسب الحالة")
            status_counts = get_status_counts()
            if not status_counts.empty:
                st.bar_chart(status_counts)

        with col2:
            st.subheader("المبيعات الشهرية")
            monthly = get_monthly_report()
            if not monthly.empty:
                # نرسم المبيعات الشهرية كخط أو عمود
                st.area_chart(monthly.set_index('الشهر')['إجمالي المبيعات'])

        st.subheader("📋 آخر الطلبات")
        show = df.head(10)[["id", "name", "phone", "item_type", "status", "delivery_date", "remaining_price"]].copy()
        show.columns = ["رقم", "الزبون", "الهاتف", "الطلب", "الحالة", "التسليم", "المتبقي"]
        st.dataframe(show, use_container_width=True, hide_index=True)

    # ---------- إضافة طلب ----------
    elif menu == "➕ إضافة طلب":
        st.subheader("➕ تسجيل طلب جديد")
        with st.form("new_order", clear_on_submit=True):
            col1, col2 = st.columns(2)
            name = col1.text_input("اسم الزبون *", placeholder="أدخل اسم الزبون")
            phone = col2.text_input("رقم الهاتف", placeholder="أدخل رقم الهاتف")
            col1, col2 = st.columns(2)
            item_type = col1.selectbox("نوع التفصيل", ["دشداشة", "قميص", "بنطلون", "بدلة كاملة", "عباءة", "جاكيت", "تفصيل آخر"])
            delivery_date = col2.date_input("تاريخ التسليم المتوقع", value=date.today() + timedelta(days=7))
            st.markdown("### 📏 القياسات بالسنتيمتر")
            col1, col2, col3 = st.columns(3)
            length = col1.number_input("الطول", min_value=0.0, step=0.5, format="%.1f")
            width = col1.number_input("العرض", min_value=0.0, step=0.5, format="%.1f")
            shoulder = col2.number_input("عرض الكتاف", min_value=0.0, step=0.5, format="%.1f")
            sleeve = col2.number_input("طول الردان", min_value=0.0, step=0.5, format="%.1f")
            collar = col3.number_input("الياخة", min_value=0.0, step=0.5, format="%.1f")
            cuff = col3.number_input("البزمة", min_value=0.0, step=0.5, format="%.1f")
            notes = st.text_area("📝 ملاحظات", placeholder="القماش، اللون، الموديل...")
            col1, col2 = st.columns(2)
            total_price = col1.number_input("السعر الكلي (د.ع)", min_value=0.0, step=1000.0, format="%.0f")
            advance_paid = col2.number_input("المبلغ المدفوع (د.ع)", min_value=0.0, step=1000.0, format="%.0f")
            submitted = st.form_submit_button("💾 حفظ الطلب", use_container_width=True, type="primary")
            if submitted:
                if not name.strip():
                    st.error("⚠️ يرجى إدخال اسم الزبون.")
                elif advance_paid > total_price:
                    st.error("⚠️ المبلغ المدفوع لا يمكن أن يكون أكبر من السعر الكلي.")
                else:
                    with st.spinner('جاري حفظ الطلب...'):
                        order_id, remaining, error = create_order({
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
                        if error:
                            st.error(f"❌ حدث خطأ: {error}")
                        else:
                            st.success(f"✅ تم حفظ الطلب رقم #{order_id} بنجاح.")
                            st.info(f"💵 المبلغ المتبقي: {remaining:,.0f} د.ع")
                            st.balloons()

    # ---------- إدارة الطلبات ----------
    elif menu == "📋 إدارة الطلبات":
        st.subheader("📋 إدارة الطلبات")
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_status = st.selectbox("فلترة حسب الحالة", ["الكل"] + STATUSES)
        with col2:
            search_text = st.text_input("بحث في الأسماء", placeholder="ابحث باسم الزبون")
        with col3:
            date_filter = st.date_input("فلترة حسب تاريخ التسليم", value=None)
        df = get_orders()
        if df.empty:
            st.info("لا توجد طلبات.")
            return
        if selected_status != "الكل":
            df = df[df["status"] == selected_status]
        if search_text:
            df = df[df["name"].str.contains(search_text, case=False, na=False)]
        if date_filter:
            df = df[pd.to_datetime(df["delivery_date"]).dt.date == date_filter]
        st.caption(f"📊 عدد الطلبات: {len(df)}")
        for _, row in df.iterrows():
            order_id = int(row["id"])
            status_icon = {"قيد الانتظار":"🟡","جارٍ القص":"🔵","جارٍ التفصيل":"🟣","جارٍ الكي":"🟠","جاهز للاستلام":"🟢","تم التسليم":"✅","ملغي":"❌"}.get(row["status"], "📌")
            with st.expander(f"{status_icon} #{order_id} | {row['name']} | {row['item_type']} | {row['status']}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**👤 الزبون:** {row['name']}")
                    st.write(f"**📞 الهاتف:** {row['phone'] or 'غير محدد'}")
                    st.write(f"**📅 التسجيل:** {row['created_at']}")
                    st.write(f"**📆 التسليم:** {row['delivery_date'] or 'غير محدد'}")
                with col2:
                    st.write("**📏 القياسات**")
                    st.write(f"الطول: {row['length']} سم")
                    st.write(f"العرض: {row['width']} سم")
                    st.write(f"الكتاف: {row['shoulder']} سم")
                    st.write(f"الردان: {row['sleeve']} سم")
                    st.write(f"الياخة: {row['collar']} سم")
                    st.write(f"البزمة: {row['cuff']} سم")
                with col3:
                    st.write(f"**💰 السعر:** {float(row['total_price'] or 0):,.0f} د.ع")
                    st.write(f"**💵 المدفوع:** {float(row['advance_paid'] or 0):,.0f} د.ع")
                    st.write(f"**📉 المتبقي:** {float(row['remaining_price'] or 0):,.0f} د.ع")
                    if float(row['remaining_price'] or 0) == 0:
                        st.success("✅ تم السداد بالكامل")
                st.write(f"**📝 الملاحظات:** {row['notes'] or 'لا توجد ملاحظات'}")
                order = get_order(order_id)
                if order:
                    current_status = order["status"]
                    status_index = STATUSES.index(current_status) if current_status in STATUSES else 0
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        new_status = st.selectbox("الحالة", STATUSES, index=status_index, key=f"status_{order_id}")
                        if st.button("💾 تحديث", key=f"update_{order_id}", use_container_width=True):
                            success, error = update_status(order_id, new_status)
                            if success:
                                st.success("✅ تم تحديث الحالة.")
                                st.rerun()
                            else:
                                st.error(f"❌ خطأ: {error}")
                    with col2:
                        receipt = generate_receipt(order)
                        st.download_button("🖼️ تنزيل الوصل", data=receipt, file_name=f"receipt_{order_id}.png", mime="image/png", key=f"receipt_{order_id}", use_container_width=True)
                    with col3:
                        if st.button("🗑️ حذف", key=f"delete_{order_id}", use_container_width=True):
                            confirm = st.checkbox(f"تأكيد حذف الطلب #{order_id}", key=f"confirm_{order_id}")
                            if confirm:
                                success, error = delete_order(order_id)
                                if success:
                                    st.success("✅ تم حذف الطلب.")
                                    st.rerun()
                                else:
                                    st.error(f"❌ خطأ: {error}")
                payments = get_payments(order_id)
                if payments:
                    st.write("**💳 سجل الدفعات:**")
                    payment_df = pd.DataFrame([dict(p) for p in payments])[["amount", "payment_date", "notes"]]
                    payment_df.columns = ["المبلغ", "التاريخ", "ملاحظات"]
                    st.dataframe(payment_df, use_container_width=True, hide_index=True)

    # ---------- الدفعات والديون ----------
    elif menu == "💵 الدفعات والديون":
        st.subheader("💵 الدفعات والديون")
        df = get_orders()
        if df.empty:
            st.info("لا توجد بيانات.")
        else:
            debtors = df[df["remaining_price"].fillna(0) > 0]
            if debtors.empty:
                st.success("🎉 لا توجد مبالغ متبقية! جميع الطلبات مدفوعة.")
            else:
                total_debt = debtors["remaining_price"].sum()
                col1, col2 = st.columns(2)
                col1.metric("📉 إجمالي الديون", f"{total_debt:,.0f} د.ع")
                col2.metric("👥 عدد المدينين", len(debtors))
                for _, row in debtors.iterrows():
                    order_id = int(row["id"])
                    with st.expander(f"#{order_id} | {row['name']} | المتبقي {float(row['remaining_price']):,.0f} د.ع"):
                        col1, col2 = st.columns(2)
                        with col1:
                            amount = st.number_input("المبلغ المستلم", min_value=0.0, max_value=float(row["remaining_price"]), step=1000.0, key=f"amount_{order_id}")
                        with col2:
                            note = st.text_input("ملاحظات", value="دفعة جديدة", key=f"note_{order_id}")
                        if st.button("💵 تسجيل الدفعة", key=f"pay_{order_id}"):
                            ok, message = add_payment(order_id, amount, note)
                            if ok:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)

    # ---------- الزبائن ----------
    elif menu == "👥 الزبائن":
        st.subheader("👥 قاعدة بيانات الزبائن")
        customers = get_customers()
        if customers.empty:
            st.info("لا توجد بيانات زبائن.")
        else:
            view = customers.copy()
            view.columns = ["رقم", "الاسم", "الهاتف", "تاريخ الإضافة", "آخر طلب"]
            st.dataframe(view, use_container_width=True, hide_index=True)
            customer_id = st.selectbox("اختر زبونًا لعرض طلباته", customers["id"].tolist(),
                                       format_func=lambda x: f"{customers.loc[customers['id']==x, 'name'].iloc[0]} - {customers.loc[customers['id']==x, 'phone'].iloc[0]}")
            conn = db.get_connection()
            orders = pd.read_sql_query("SELECT * FROM orders WHERE customer_id = ? ORDER BY id DESC", conn, params=(int(customer_id),))
            conn.close()
            if orders.empty:
                st.info("لا توجد طلبات لهذا الزبون.")
            else:
                st.dataframe(orders, use_container_width=True, hide_index=True)

    # ---------- البحث ----------
    elif menu == "🔍 البحث المتقدم":
        st.subheader("🔍 البحث المتقدم")
        search = st.text_input("ابحث بالاسم أو رقم الهاتف أو رقم الطلب")
        if search.strip():
            conn = db.get_connection()
            results = pd.read_sql_query(
                """SELECT * FROM orders WHERE name LIKE ? OR phone LIKE ? OR CAST(id AS TEXT) LIKE ? ORDER BY id DESC""",
                conn, params=(f"%{search}%", f"%{search}%", f"%{search}%")
            )
            conn.close()
            if results.empty:
                st.warning("لم يتم العثور على نتائج.")
            else:
                st.success(f"تم العثور على {len(results)} نتيجة.")
                st.dataframe(results, use_container_width=True, hide_index=True)

    # ---------- الإحصائيات ----------
    elif menu == "📊 الإحصائيات والتقارير":
        st.subheader("📊 الإحصائيات والتقارير")
        df = get_orders()
        if df.empty:
            st.info("لا توجد بيانات للإحصائيات.")
        else:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("عدد الطلبات", len(df))
            col2.metric("إجمالي المبيعات", f"{df['total_price'].fillna(0).sum():,.0f} د.ع")
            col3.metric("المقبوض", f"{df['advance_paid'].fillna(0).sum():,.0f} د.ع")
            col4.metric("الديون", f"{df['remaining_price'].fillna(0).sum():,.0f} د.ع")
            st.subheader("الطلبات حسب الحالة")
            status_counts = get_status_counts()
            if not status_counts.empty:
                st.bar_chart(status_counts)
            st.subheader("التقرير الشهري")
            monthly = get_monthly_report()
            if not monthly.empty:
                st.dataframe(monthly, use_container_width=True, hide_index=True)

    # ---------- النسخ الاحتياطي ----------
    elif menu == "💾 النسخ الاحتياطي":
        st.subheader("💾 النسخ الاحتياطي")
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

if __name__ == "__main__":
    main()
