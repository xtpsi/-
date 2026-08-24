import io
import os
import sqlite3
from datetime import datetime, date, timedelta
import hashlib
import hmac
import time

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
import plotly.express as px
import plotly.graph_objects as go

# =========================
# إعدادات الأمان والثوابت
# =========================
DB_NAME = "tailor_master.db"
SHOP_NAME = "صادق الخياط"
SHOP_PHONE = "07713146637"
ADMIN_PASSWORD = "admin123"  # غيّر هذه القيمة

STATUSES = [
    "قيد الانتظار",
    "جارٍ القص",
    "جارٍ التفصيل",
    "جارٍ الكي",
    "جاهز للاستلام",
    "تم التسليم",
    "ملغي",
]

# إعدادات الصفحة
st.set_page_config(
    page_title=f"{SHOP_NAME} - إدارة الطلبات",
    page_icon="✂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================
# إدارة الجلسة
# =========================
def init_session_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = time.time()
    if "notification" not in st.session_state:
        st.session_state.notification = None

init_session_state()

# =========================
# نظام المصادقة المُحسّن
# =========================
def check_password():
    """التحقق من كلمة المرور مع تخزين آمن"""
    if st.session_state.authenticated:
        return True
    
    st.sidebar.markdown("### 🔐 تسجيل الدخول")
    password = st.sidebar.text_input("كلمة المرور", type="password", key="login_password")
    
    if password:
        # استخدم مقارنة آمنة
        if hmac.compare_digest(password, ADMIN_PASSWORD):
            st.session_state.authenticated = True
            st.sidebar.success("✅ تم تسجيل الدخول بنجاح")
            st.rerun()
        else:
            st.sidebar.error("❌ كلمة المرور غير صحيحة")
            return False
    
    return False

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
    """تحميل الخط مع التخزين المؤقت"""
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
# إدارة قاعدة البيانات (مُحسّنة)
# =========================
class DatabaseManager:
    """مدير قاعدة البيانات مع اتصال واحد وتحسين الأداء"""
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
        """تنفيذ استعلام مع إدارة الأخطاء"""
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

# =========================
# دوال قاعدة البيانات (مُحسّنة مع Caching)
# =========================
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
    
    # إنشاء الجداول
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
    
    # تحديث الجداول القديمة
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
    
    # إنشاء فهارس لتحسين الأداء
    conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at)")
    
    db.commit()

init_db()

# =========================
# دوال البيانات مع Caching
# =========================
@st.cache_data(ttl=60)
def get_customers():
    """جلب جميع الزبائن مع التخزين المؤقت"""
    conn = db.get_connection()
    df = pd.read_sql_query("SELECT * FROM customers ORDER BY id DESC", conn)
    return df

@st.cache_data(ttl=30)
def get_orders():
    """جلب جميع الطلبات مع التخزين المؤقت"""
    conn = db.get_connection()
    df = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
    return df

@st.cache_data(ttl=30)
def get_orders_by_status(status=None):
    """جلب الطلبات حسب الحالة"""
    conn = db.get_connection()
    if status:
        df = pd.read_sql_query(
            "SELECT * FROM orders WHERE status = ? ORDER BY id DESC",
            conn,
            params=(status,)
        )
    else:
        df = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
    return df

def get_order(order_id):
    """جلب طلب محدد"""
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    return row

def get_payments(order_id):
    """جلب دفعات طلب محدد"""
    conn = db.get_connection()
    rows = conn.execute(
        "SELECT * FROM payments WHERE order_id = ? ORDER BY id DESC",
        (order_id,)
    ).fetchall()
    return rows

def get_or_create_customer(name, phone):
    """الحصول على زبون أو إنشاؤه"""
    conn = db.get_connection()
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
            "UPDATE customers SET name = ?, phone = ?, last_order_date = ? WHERE id = ?",
            (name, phone, datetime.now().strftime("%Y-%m-%d %H:%M"), customer_id)
        )
    else:
        customer_id = conn.execute(
            "INSERT INTO customers (name, phone, created_at, last_order_date) VALUES (?, ?, ?, ?)",
            (name, phone, datetime.now().strftime("%Y-%m-%d %H:%M"), datetime.now().strftime("%Y-%m-%d %H:%M"))
        ).lastrowid
    
    db.commit()
    return customer_id

def create_order(data):
    """إنشاء طلب جديد مع التحقق من الأخطاء"""
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
            conn.execute(
                "INSERT INTO payments (order_id, amount, payment_date, notes) VALUES (?, ?, ?, ?)",
                (order_id, data["advance_paid"], now, "عربون عند تسجيل الطلب")
            )
        
        db.commit()
        
        # مسح التخزين المؤقت
        st.cache_data.clear()
        
        return order_id, remaining, None
    except Exception as e:
        return None, None, str(e)

def update_status(order_id, status):
    """تحديث حالة الطلب"""
    try:
        conn = db.get_connection()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn.execute(
            "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, order_id)
        )
        db.commit()
        st.cache_data.clear()
        return True, None
    except Exception as e:
        return False, str(e)

def delete_order(order_id):
    """حذف طلب مع جميع دفعاته"""
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
    """إضافة دفعة جديدة"""
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
        conn.execute(
            "UPDATE orders SET advance_paid = ?, remaining_price = ?, updated_at = ? WHERE id = ?",
            (new_paid, new_remaining, now, order_id)
        )
        conn.execute(
            "INSERT INTO payments (order_id, amount, payment_date, notes) VALUES (?, ?, ?, ?)",
            (order_id, amount, now, notes or "دفعة جديدة")
        )
        db.commit()
        st.cache_data.clear()
        return True, "تم تسجيل الدفعة بنجاح."
    except Exception as e:
        return False, str(e)

# =========================
# تحليلات وتقارير متقدمة
# =========================
def get_monthly_report():
    """تقرير شهري للمبيعات"""
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
    """جلب الطلبات المتأخرة"""
    df = get_orders()
    if df.empty:
        return df
    
    df['delivery_date'] = pd.to_datetime(df['delivery_date']).dt.date
    today = date.today()
    overdue = df[
        (df['delivery_date'] < today) & 
        (df['status'] != 'تم التسليم') & 
        (df['status'] != 'ملغي')
    ]
    return overdue

def get_status_counts():
    """إحصائيات حسب الحالة"""
    df = get_orders()
    if df.empty:
        return pd.Series()
    return df['status'].value_counts()

# =========================
# توليد الوصل (مُحسّن)
# =========================
def generate_receipt(order):
    """إنشاء وصل مع تحسين التنسيق"""
    width, height = 1100, 1550
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    
    title_font = get_font(52)
    big_font = get_font(38)
    body_font = get_font(29)
    small_font = get_font(24)
    
    # إطار وزخرفة
    draw.rectangle((20, 20, width - 20, height - 20), outline=(35, 55, 75), width=5)
    draw.rectangle((25, 25, width - 25, 220), fill=(35, 55, 75))
    
    def right(text, y, font, fill=(20, 20, 20), margin=70):
        shaped = rtl(text)
        box = draw.textbbox((0, 0), shaped, font=font)
        x = width - margin - (box[2] - box[0])
        draw.text((x, y), shaped, font=font, fill=fill)
    
    # العنوان والرأس
    right(SHOP_NAME, 55, title_font, "white")
    right(f"الهاتف: {SHOP_PHONE}", 135, big_font, (230, 235, 240))
    
    y = 270
    right("وصل استلام طلب", y, title_font)
    y += 95
    
    # معلومات الطلب
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
    
    # خط فاصل
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
    
    # تذييل
    footer_y = height - 130
    draw.line((70, footer_y - 25, width - 70, footer_y - 25), fill=(160, 160, 160), width=2)
    right("شكراً لتعاملكم معنا", footer_y, big_font)
    right(SHOP_NAME, footer_y + 55, small_font)
    
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()
