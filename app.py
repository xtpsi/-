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
# إعدادات المحل
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

# =========================
# تنسيق الصفحة
# =========================
st.set_page_config(
    page_title=f"{SHOP_NAME} - إدارة الطلبات",
    page_icon="✂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================
# CSS المخصص
# =========================
def apply_custom_css():
    st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        .css-1d391kg {
            background: linear-gradient(180deg, #1e3c72 0%, #2a5298 100%);
        }
        .stRadio > div {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .stRadio label {
            background-color: rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 12px 18px;
            color: white !important;
            font-size: 18px;
            font-weight: bold;
            transition: 0.3s;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .stRadio label:hover {
            background-color: rgba(255,255,255,0.25);
            transform: scale(1.02);
            border-color: #f1c40f;
        }
        .stRadio label > div:first-child {
            display: none;
        }
        .stButton button {
            background: linear-gradient(135deg, #f1c40f, #f39c12);
            color: #1e3c72;
            border: none;
            border-radius: 30px;
            padding: 10px 25px;
            font-weight: bold;
            font-size: 16px;
            transition: 0.3s;
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        }
        .stButton button:hover {
            transform: scale(1.05);
            box-shadow: 0 6px 15px rgba(0,0,0,0.3);
        }
        .streamlit-expanderHeader {
            background: linear-gradient(135deg, #2a5298, #1e3c72) !important;
            color: white !important;
            border-radius: 15px !important;
            font-weight: bold;
            font-size: 18px;
            border: 1px solid #f1c40f;
        }
        .streamlit-expanderContent {
            background: rgba(255,255,255,0.95);
            border-radius: 0 0 15px 15px;
            padding: 20px;
            border: 1px solid #1e3c72;
            border-top: none;
        }
        .css-1xarl3l {
            background: rgba(255,255,255,0.85);
            border-radius: 15px;
            padding: 15px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }
        h1, h2, h3 {
            color: #1e3c72;
            font-weight: 700;
        }
        footer {
            visibility: hidden;
        }
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }
        ::-webkit-scrollbar-thumb {
            background: #2a5298;
            border-radius: 10px;
        }
        /* تنسيق بطاقات المؤشرات */
        .metric-card {
            background: white;
            border-radius: 15px;
            padding: 15px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        .metric-card .label {
            font-size: 16px;
            color: #555;
        }
        .metric-card .value {
            font-size: 28px;
            font-weight: bold;
            margin-top: 5px;
        }
        .metric-card .value.overdue { color: #e74c3c; }
        .metric-card .value.soon { color: #f39c12; }
        .metric-card .value.normal { color: #27ae60; }
        /* تنسيق حالة الموعد في الجدول */
        .badge-overdue {
            background-color: #e74c3c;
            color: white;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
        }
        .badge-soon {
            background-color: #f39c12;
            color: white;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
        }
        .badge-normal {
            background-color: #27ae60;
            color: white;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)

# =========================
# دوال اللغة العربية
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
            except:
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
    return pd.read_sql_query("SELECT * FROM customers ORDER BY name", conn)

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

def get_last_order_by_customer(customer_id):
    conn = db.get_connection()
    return conn.execute(
        "SELECT * FROM orders WHERE customer_id = ? ORDER BY id DESC LIMIT 1",
        (customer_id,)
    ).fetchone()

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

# =========================
# دوال التقارير والإحصائيات
# =========================
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

# =========================
# دالة توليد الإيصال
# =========================
def generate_receipt(order):
    width, height = 1100, 1600
    image = Image.new("RGB", (width, height), "#f8f9fa")
    draw = ImageDraw.Draw(image)
    
    title_font = get_font(56)
    big_font = get_font(40)
    body_font = get_font(32)
    small_font = get_font(26)
    bold_font = get_font(36)
    
    draw.rectangle((30, 30, width-30, height-30), outline="#1e3c72", width=8, fill=(255,255,255,240))
    draw.rectangle((45, 45, width-45, height-45), outline="#f1c40f", width=3)
    
    draw.rectangle((45, 45, width-45, 230), fill="#1e3c72")
    draw.text((width//2, 80), rtl(SHOP_NAME), font=title_font, fill="white", anchor="mt")
    draw.text((width//2, 150), f"📞 {SHOP_PHONE}", font=big_font, fill="#f1c40f", anchor="mt")
    
    draw.text((width//2, 280), rtl("وصل استلام طلب"), font=title_font, fill="#1e3c72", anchor="mt")
    draw.line((300, 320, width-300, 320), fill="#f1c40f", width=4)
    
    y = 380
    fields = [
        ("رقم الطلب", f"#{order['id']}"),
        ("تاريخ التسجيل", order['created_at'] or ""),
        ("تاريخ التسليم", order['delivery_date'] or "غير محدد"),
        ("اسم الزبون", order['name']),
        ("الهاتف", order['phone'] or "غير محدد"),
        ("نوع التفصيل", order['item_type'] or ""),
    ]
    for label, value in fields:
        draw.text((80, y), rtl(f"{label}:"), font=body_font, fill="#1e3c72")
        draw.text((80, y+40), rtl(str(value)), font=bold_font, fill="#2a5298")
        y += 100
    
    draw.line((80, y-20, width-80, y-20), fill="#e0e0e0", width=2)
    
    y += 20
    draw.text((80, y), rtl("القياسات (سم)"), font=big_font, fill="#1e3c72")
    y += 60
    measurements = [
        (f"الطول: {order['length']}", f"العرض: {order['width']}"),
        (f"الكتاف: {order['shoulder']}", f"الردان: {order['sleeve']}"),
        (f"الياخة: {order['collar']}", f"البزمة: {order['cuff']}"),
    ]
    for pair in measurements:
        draw.text((100, y), rtl(pair[0]), font=body_font, fill="#333")
        draw.text((400, y), rtl(pair[1]), font=body_font, fill="#333")
        y += 60
    
    draw.line((80, y-20, width-80, y-20), fill="#e0e0e0", width=2)
    y += 20
    
    draw.text((80, y), rtl("الحساب"), font=big_font, fill="#1e3c72")
    y += 60
    finance = [
        (f"السعر الكلي", f"{float(order['total_price'] or 0):,.0f} د.ع"),
        (f"المدفوع", f"{float(order['advance_paid'] or 0):,.0f} د.ع"),
        (f"المتبقي", f"{float(order['remaining_price'] or 0):,.0f} د.ع"),
    ]
    for label, value in finance:
        draw.text((100, y), rtl(f"{label}:"), font=body_font, fill="#333")
        draw.text((350, y), rtl(value), font=bold_font, fill="#e67e22")
        y += 70
    
    status_color = "#27ae60" if order['status'] == "جاهز للاستلام" else "#2980b9"
    draw.text((80, y), rtl(f"الحالة: {order['status']}"), font=bold_font, fill=status_color)
    y += 80
    
    draw.line((80, y-20, width-80, y-20), fill="#e0e0e0", width=2)
    y += 20
    draw.text((80, y), rtl("ملاحظات:"), font=big_font, fill="#1e3c72")
    y += 60
    notes = order["notes"] or "لا توجد ملاحظات"
    words = str(notes).split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if len(test) > 50:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    for line in lines[:5]:
        draw.text((100, y), rtl(line), font=small_font, fill="#555")
        y += 45
    
    footer_y = height - 150
    draw.line((80, footer_y-30, width-80, footer_y-30), fill="#f1c40f", width=3)
    draw.text((width//2, footer_y), rtl("شكراً لتعاملكم معنا"), font=big_font, fill="#1e3c72", anchor="mt")
    draw.text((width//2, footer_y+60), rtl(SHOP_NAME), font=small_font, fill="#7f8c8d", anchor="mt")
    draw.ellipse((width-250, footer_y-20, width-150, footer_y+80), outline="#f1c40f", width=4)
    draw.text((width-200, footer_y+30), rtl("معتمد"), font=small_font, fill="#1e3c72", anchor="mm")
    
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()

# =========================
# الواجهة الرئيسية
# =========================
def main():
    apply_custom_css()
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1e3c72, #2a5298); padding: 25px; border-radius: 20px; text-align: center; margin-bottom: 30px; box-shadow: 0 8px 20px rgba(0,0,0,0.3);">
        <h1 style="color: white; font-size: 3.5em; margin: 0;">✂️ صادق الخياط</h1>
        <p style="color: #f1c40f; font-size: 1.3em; margin-top: 5px;">نظام إدارة الطلبات والقياسات – مع تنبيهات المواعيد</p>
    </div>
    """, unsafe_allow_html=True)
    
    overdue = get_overdue_orders()
    if not overdue.empty:
        st.warning(f"⚠️ هناك {len(overdue)} طلباً متأخراً عن موعد التسليم!")
    
    menu_icons = {
        "🏠 لوحة التحكم": "📊",
        "➕ إضافة طلب": "📝",
        "📋 إدارة الطلبات": "📂",
        "💵 الدفعات والديون": "💰",
        "👥 الزبائن": "👤",
        "🔍 البحث المتقدم": "🔎",
        "📊 الإحصائيات والتقارير": "📈",
        "💾 النسخ الاحتياطي": "💾"
    }
    menu = st.sidebar.radio(
        "القائمة الرئيسية",
        list(menu_icons.keys()),
        format_func=lambda x: f"{menu_icons[x]} {x}"
    )
    
    # ----- 1. لوحة التحكم -----
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
                st.area_chart(monthly.set_index('الشهر')['إجمالي المبيعات'])
        
        st.subheader("📋 آخر الطلبات")
        show = df.head(10)[["id", "name", "phone", "item_type", "status", "delivery_date", "remaining_price"]].copy()
        show.columns = ["رقم", "الزبون", "الهاتف", "الطلب", "الحالة", "التسليم", "المتبقي"]
        st.dataframe(show, use_container_width=True, hide_index=True)
    
    # ----- 2. إضافة طلب (مع اقتراح القياسات) -----
    elif menu == "➕ إضافة طلب":
        st.subheader("➕ تسجيل طلب جديد")
        customers_df = get_customers()
        customer_options = ["【زبون جديد】"]
        customer_ids = {0: None}
        if not customers_df.empty:
            for idx, row in customers_df.iterrows():
                display_name = f"{row['name']} - {row['phone'] or 'بدون هاتف'}"
                customer_options.append(display_name)
                customer_ids[len(customer_options)-1] = row['id']
        selected_option = st.selectbox(
            "👤 اختر زبوناً موجوداً (أو اختر 'زبون جديد')",
            customer_options,
            key="customer_selector"
        )
        selected_index = customer_options.index(selected_option)
        customer_id = customer_ids.get(selected_index, None)
        suggested_length = suggested_width = suggested_shoulder = suggested_sleeve = suggested_collar = suggested_cuff = 0.0
        suggested_phone = ""
        suggested_name = ""
        if customer_id is not None:
            last_order = get_last_order_by_customer(customer_id)
            if last_order:
                suggested_name = last_order['name']
                suggested_phone = last_order['phone'] or ""
                suggested_length = float(last_order['length'] or 0)
                suggested_width = float(last_order['width'] or 0)
                suggested_shoulder = float(last_order['shoulder'] or 0)
                suggested_sleeve = float(last_order['sleeve'] or 0)
                suggested_collar = float(last_order['collar'] or 0)
                suggested_cuff = float(last_order['cuff'] or 0)
                st.success(f"✅ تم جلب قياسات {suggested_name} من آخر طلب له.")
                st.info(f"📏 الطول: {suggested_length} | العرض: {suggested_width} | الكتاف: {suggested_shoulder} | يمكنك تعديلها قبل الحفظ.")
            else:
                st.warning("⚠️ هذا الزبون مسجل لكن ليس لديه طلبات سابقة، أدخل القياسات يدوياً.")
        with st.form("new_order", clear_on_submit=True):
            st.markdown("### 👤 معلومات الزبون")
            col1, col2 = st.columns(2)
            name = col1.text_input("اسم الزبون *", value=suggested_name, placeholder="أدخل اسم الزبون")
            phone = col2.text_input("رقم الهاتف", value=suggested_phone, placeholder="أدخل رقم الهاتف")
            st.markdown("### 📋 تفاصيل الطلب")
            col1, col2 = st.columns(2)
            item_type = col1.selectbox("نوع التفصيل", ["دشداشة", "قميص", "بنطلون", "بدلة كاملة", "عباءة", "جاكيت", "تفصيل آخر"])
            delivery_date = col2.date_input("تاريخ التسليم المتوقع", value=date.today() + timedelta(days=7))
            st.markdown("### 📏 القياسات بالسنتيمتر")
            col1, col2, col3 = st.columns(3)
            length = col1.number_input("الطول", min_value=0.0, step=0.5, format="%.1f", value=suggested_length)
            width = col1.number_input("العرض", min_value=0.0, step=0.5, format="%.1f", value=suggested_width)
            shoulder = col2.number_input("عرض الكتاف", min_value=0.0, step=0.5, format="%.1f", value=suggested_shoulder)
            sleeve = col2.number_input("طول الردان", min_value=0.0, step=0.5, format="%.1f", value=suggested_sleeve)
            collar = col3.number_input("الياخة", min_value=0.0, step=0.5, format="%.1f", value=suggested_collar)
            cuff = col3.number_input("البزمة", min_value=0.0, step=0.5, format="%.1f", value=suggested_cuff)
            notes = st.text_area("📝 ملاحظات", placeholder="القماش، اللون، الموديل...")
            st.markdown("### 💰 الحساب")
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
    
    # ----- 3. إدارة الطلبات (المُحسَّنة) -----
    elif menu == "📋 إدارة الطلبات":
        st.subheader("📋 إدارة الطلبات")
        
        # جلب جميع الطلبات
        df = get_orders()
        if df.empty:
            st.info("لا توجد طلبات.")
            return
        
        # تحويل تاريخ التسليم إلى datetime
        df['delivery_date_dt'] = pd.to_datetime(df['delivery_date'])
        today = pd.Timestamp(date.today())
        
        # حساب الأيام المتبقية
        df['days_left'] = (df['delivery_date_dt'] - today).dt.days
        
        # تحديد حالة الموعد
        def get_deadline_status(days):
            if days < 0:
                return "متأخر"
            elif days <= 3:
                return "قريب"
            else:
                return "عادي"
        
        df['deadline_status'] = df['days_left'].apply(get_deadline_status)
        
        # ترتيب الطلبات: المتأخر أولاً، ثم القريب، ثم العادي
        status_order = {"متأخر": 0, "قريب": 1, "عادي": 2}
        df['sort_order'] = df['deadline_status'].map(status_order)
        df = df.sort_values(by=['sort_order', 'days_left']).drop(columns=['sort_order'])
        
        # مؤشرات سريعة
        overdue_count = len(df[df['deadline_status'] == 'متأخر'])
        soon_count = len(df[df['deadline_status'] == 'قريب'])
        normal_count = len(df[df['deadline_status'] == 'عادي'])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">🔴 متأخر</div>
                <div class="value overdue">{overdue_count}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">🟡 قريب (≤ 3 أيام)</div>
                <div class="value soon">{soon_count}</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">🟢 عادي</div>
                <div class="value normal">{normal_count}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # فلاتر البحث
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_status = st.selectbox("فلترة حسب الحالة", ["الكل"] + STATUSES)
        with col2:
            search_text = st.text_input("بحث في الأسماء", placeholder="ابحث باسم الزبون")
        with col3:
            filter_deadline = st.selectbox("فلترة حسب الموعد", ["الكل", "متأخر", "قريب", "عادي"])
        
        # تطبيق الفلاتر
        filtered_df = df.copy()
        if selected_status != "الكل":
            filtered_df = filtered_df[filtered_df["status"] == selected_status]
        if search_text:
            filtered_df = filtered_df[filtered_df["name"].str.contains(search_text, case=False, na=False)]
        if filter_deadline != "الكل":
            filtered_df = filtered_df[filtered_df["deadline_status"] == filter_deadline]
        
        st.caption(f"📊 عدد الطلبات: {len(filtered_df)}")
        
        # عرض الجدول مع تلوين الصفوف
        if not filtered_df.empty:
            # اختيار الأعمدة للعرض
            display_df = filtered_df[["id", "name", "phone", "item_type", "status", "delivery_date", "days_left", "deadline_status", "remaining_price"]].copy()
            display_df.columns = ["رقم", "الزبون", "الهاتف", "الطلب", "الحالة", "التسليم", "المتبقي (يوم)", "حالة الموعد", "المتبقي (د.ع)"]
            
            # تنسيق الأعمدة
            display_df["المتبقي (يوم)"] = display_df["المتبقي (يوم)"].astype(int)
            display_df["المتبقي (د.ع)"] = display_df["المتبقي (د.ع)"].apply(lambda x: f"{x:,.0f} د.ع")
            
            # تلوين الصفوف باستخدام Styler
            def color_rows(row):
                status = row["حالة الموعد"]
                if status == "متأخر":
                    return ['background-color: #f8d7da; color: #721c24;'] * len(row)
                elif status == "قريب":
                    return ['background-color: #fff3cd; color: #856404;'] * len(row)
                else:
                    return ['background-color: #d4edda; color: #155724;'] * len(row)
            
            styled_df = display_df.style.apply(color_rows, axis=1)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        # عرض تفاصيل كل طلب في expander
        for _, row in filtered_df.iterrows():
            order_id = int(row["id"])
            status_icon = {"قيد الانتظار":"🟡","جارٍ القص":"🔵","جارٍ التفصيل":"🟣","جارٍ الكي":"🟠","جاهز للاستلام":"🟢","تم التسليم":"✅","ملغي":"❌"}.get(row["status"], "📌")
            
            # إضافة حالة الموعد في عنوان التوسيع
            deadline_icon = "🔴" if row["deadline_status"] == "متأخر" else "🟡" if row["deadline_status"] == "قريب" else "🟢"
            with st.expander(f"{status_icon} #{order_id} | {row['name']} | {row['item_type']} | {row['status']} | {deadline_icon} {row['deadline_status']}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**👤 الزبون:** {row['name']}")
                    st.write(f"**📞 الهاتف:** {row['phone'] or 'غير محدد'}")
                    st.write(f"**📅 التسجيل:** {row['created_at']}")
                    st.write(f"**📆 التسليم:** {row['delivery_date']}")
                    st.write(f"**⏳ المتبقي:** {row['days_left']} يوم")
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
    
    # ----- 4. الدفعات والديون -----
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
    
    # ----- 5. الزبائن -----
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
    
    # ----- 6. البحث المتقدم -----
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
    
    # ----- 7. الإحصائيات والتقارير -----
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
    
    # ----- 8. النسخ الاحتياطي -----
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
