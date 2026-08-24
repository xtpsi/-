from io import BytesIO
import sqlite3
import urllib.parse
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

# --- 1. إعداد قاعدة البيانات ---
DB_NAME = "sadeq_tailor.db"


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


# --- 2. دالة توليد صورة بطاقة الطلب ---
def create_order_image(
    order_id,
    name,
    phone,
    item_type,
    length,
    width,
    shoulder,
    sleeve,
    collar,
    cuff,
    total,
    paid,
    rem,
    deliv_date,
):
    img = Image.new("RGB", (600, 750), color="#1E293B")
    draw = ImageDraw.Draw(img)

    # رسم إطار بدائي ناعم
    draw.rectangle([20, 20, 580, 730], outline="#2563EB", width=4)

    # النصوص الأساسية
    draw.text((200, 50), "✂️ صادق الخياط", fill="#F8FAFC")
    draw.text((215, 90), "📞 07713146637", fill="#60A5FA")
    draw.line([(50, 130), (550, 130)], fill="#475569", width=2)

    draw.text((50, 150), f"رقم الطلب: #{order_id}", fill="#F8FAFC")
    draw.text((50, 190), f"الزبون: {name}", fill="#F8FAFC")
    draw.text((50, 230), f"الهاتف: {phone}", fill="#F8FAFC")
    draw.text((50, 270), f"نوع التفصال: {item_type}", fill="#F8FAFC")
    draw.text((50, 310), f"موعد التسليم: {deliv_date}", fill="#FBBF24")

    draw.line([(50, 350), (550, 350)], fill="#475569", width=2)
    draw.text((50, 370), "📐 القياسات (سم):", fill="#60A5FA")
    draw.text(
        (50, 410),
        f"الطول: {length}  |  العرض: {width}  |  الكتف: {shoulder}",
        fill="#F8FAFC",
    )
    draw.text(
        (50, 450),
        f"الردان: {sleeve}  |  الياخة: {collar}  |  البزمة: {cuff}",
        fill="#F8FAFC",
    )

    draw.line([(50, 500), (550, 500)], fill="#475569", width=2)
    draw.text((50, 520), "💰 الحساب والمالية:", fill="#60A5FA")
    draw.text((50, 560), f"المبلغ الكلي: {total:,.0f} د.ع", fill="#F8FAFC")
    draw.text((50, 600), f"الواصل (العربون): {paid:,.0f} د.ع", fill="#34D399")
    draw.text((50, 640), f"المتبقي: {rem:,.0f} د.ع", fill="#F87171")

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# --- 3. إعداد الصفحة والتنسيقات (CSS) ---
st.set_page_config(page_title="صادق الخياط", page_icon="✂️", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 50%, #d1d5db 100%); font-family: 'Segoe UI', sans-serif; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important; }
    section[data-testid="stSidebar"] * { color: #f8fafc !important; }
    .main-header { font-size: 26px; font-weight: bold; color: #1e293b; text-align: center; padding: 14px; background: rgba(255, 255, 255, 0.85); border-radius: 14px; box-shadow: 0px 8px 20px rgba(0,0,0,0.05); margin-bottom: 15px; }
    .shop-phone { font-size: 15px; color: #2563eb; font-weight: bold; text-align: center; margin-top: -8px; margin-bottom: 20px; }
    .measure-tag { display: inline-block; background-color: #ffffff; color: #1d4ed8; padding: 4px 10px; margin: 3px; border-radius: 8px; font-weight: bold; font-size: 13px; border: 1px solid #cbd5e1; }
    .date-badge-late { background-color: #fee2e2; color: #991b1b; padding: 4px 10px; border-radius: 8px; font-weight: bold; font-size: 12px; }
    .date-badge-today { background-color: #fef3c7; color: #92400e; padding: 4px 10px; border-radius: 8px; font-weight: bold; font-size: 12px; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: white; border: none; }
    </style>
""",
    unsafe_allow_html=True,
)

# --- 4. القائمة الجانبية ---
st.sidebar.markdown(
    "<h2 style='text-align: center; margin-bottom: 0;'>✂️ صادق الخياط</h2>",
    unsafe_allow_html=True,
)
st.sidebar.markdown(
    "<p style='text-align: center; color: #94a3b8 !important; font-weight: bold;'>📞 07713146637</p>",
    unsafe_allow_html=True,
)
st.sidebar.markdown("---")

menu = [
    "📝 إضافة طلب جديد",
    "📋 جدول العمل والدور",
    "✏️ تعديل طلب مسجل",
    "💵 تسديد الديون والحسابات",
    "🔍 البحث عن زبون",
    "📊 الإحصائيات والنسخ الاحتياطي",
]
choice = st.sidebar.radio("التنقل السريع:", menu)

# --- 5. إضافة طلب جديد ---
if choice == "📝 إضافة طلب جديد":
    st.markdown(
        "<div class='main-header'>📝 تسجيل طلب وقياسات جديدة</div>",
        unsafe_allow_html=True,
    )

    # أرشفة القياسات لاستدعاء زبون سابق
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT DISTINCT name, phone, length, width, shoulder, sleeve, collar, cuff FROM orders ORDER BY id DESC"
    )
    existing_clients = c.fetchall()
    conn.close()

    preset = None
    if existing_clients:
        client_names = ["-- زبون جديد --"] + [
            f"{cl[0]} ({cl[1]})" for cl in existing_clients
        ]
        selected_client = st.selectbox("📂 استدعاء قياسات زبون سابق:", client_names)
        if selected_client != "-- زبون جديد --":
            idx = client_names.index(selected_client) - 1
            preset = existing_clients[idx]

    with st.form("add_order_form", clear_on_submit=True):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            name = st.text_input(
                "👤 اسم الزبون *", value=preset[0] if preset else ""
            )
            phone = st.text_input(
                "📞 رقم هاتف الزبون", value=preset[1] if preset else ""
            )
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
            length = st.number_input(
                "📏 الطول الكلي",
                min_value=0.0,
                step=0.5,
                value=float(preset[2]) if preset else 0.0,
            )
            width = st.number_input(
                "↔️ العرض (الصدر)",
                min_value=0.0,
                step=0.5,
                value=float(preset[3]) if preset else 0.0,
            )
            shoulder = st.number_input(
                "📐 عرض الكتاف",
                min_value=0.0,
                step=0.5,
                value=float(preset[4]) if preset else 0.0,
            )
        with col_m2:
            sleeve = st.number_input(
                "🦾 طول الردان",
                min_value=0.0,
                step=0.5,
                value=float(preset[5]) if preset else 0.0,
            )
            collar = st.number_input(
                "👔 الياخة",
                min_value=0.0,
                step=0.5,
                value=float(preset[6]) if preset else 0.0,
            )
            cuff = st.number_input(
                "🔘 البزمة",
                min_value=0.0,
                step=0.5,
                value=float(preset[7]) if preset else 0.0,
            )

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
                    f"🎉 تم حفظ الطلب #{order_id} بنجاح! المتبقي: {remaining:,.0f}"
                )

                # توليد صورة الطلب فوراً للمشاركة
                img_bytes = create_order_image(
                    order_id,
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
                    advance_paid,
                    remaining,
                    delivery_date,
                )
                st.download_button(
                    label="📸 تنزيل بطاقة الطلب (صورة للزبون)",
                    data=img_bytes,
                    file_name=f"Order_{order_id}_{name}.png",
                    mime="image/png",
                )

# --- 6. جدول العمل والدور والتصفية الذكية ---
elif choice == "📋 جدول العمل والدور":
    st.markdown(
        "<div class='main-header'>📋 جدول العمل والدور ومواعيد التسليم</div>",
        unsafe_allow_html=True,
    )

    filter_status = st.selectbox(
        "🔍 تصفية القائمة حسب:",
        [
            "جميع الطلبات",
            "تسليم اليوم",
            "الطلبات المتأخرة",
            "قيد الانتظار",
            "جارِ التفصيل",
            "جاهز للتسليم",
        ],
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

            # تطبيق الفلتر
            if (
                filter_status == "تسليم اليوم"
                and (o_deliv != today_str or o_status == "تم التسليم")
            ):
                continue
            elif (
                filter_status == "الطلبات المتأخرة"
                and (o_deliv >= today_str or o_status == "تم التسليم")
            ):
                continue
            elif (
                filter_status not in ["جميع الطلبات", "تسليم اليوم", "الطلبات المتأخرة"]
                and o_status != filter_status
            ):
                continue

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
                st.markdown(
                    f"**حالة الموعد:** {date_status_html}",
                    unsafe_allow_html=True,
                )
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
                col_b1, col_b2, col_b3 = st.columns([2, 1, 1])
                with col_b1:
                    new_st = st.selectbox(
                        "تحديث حالة العمل:",
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
                    if st.button("🔄 حفظ الحالة", key=f"btn_st_{o_id}"):
                        conn = get_connection()
                        c = conn.cursor()
                        c.execute(
                            "UPDATE orders SET status = ? WHERE id = ?",
                            (new_st, o_id),
                        )
                        conn.commit()
                        conn.close()
                        st.rerun()

                with col_b2:
                    # زر إرسال واتساب مباشر
                    if o_phone:
                        msg = f"أهلاً بك زبوننا العزيز {o_name}، نود إعلامك أن تفصالك لدى (صادق الخياط) حالته الآن: [{o_status}]."
                        wa_url = f"https://wa.me/{o_phone}?text={urllib.parse.quote(msg)}"
                        st.markdown(
                            f"[📲 واتساب للزبون]({wa_url})", unsafe_allow_html=True
                        )

                with col_b3:
                    # زر تحميل البطاقة المصورة
                    img_b = create_order_image(
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
                        o_total,
                        o_paid,
                        o_rem,
                        o_deliv,
                    )
                    st.download_button(
                        label="📸 بطاقة صورة",
                        data=img_b,
                        file_name=f"Order_{o_id}.png",
                        mime="image/png",
                        key=f"dl_img_{o_id}",
                    )

# --- 7. تعديل طلب مسجل ---
elif choice == "✏️ تعديل طلب مسجل":
    st.markdown(
        "<div class='main-header'>✏️ تعديل بيانات وقياسات طلب مسجل</div>",
        unsafe_allow_html=True,
    )

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, item_type FROM orders ORDER BY id DESC")
    orders_list = c.fetchall()
    conn.close()

    if orders_list:
        order_options = [
            f"#{o[0]} - {o[1]} ({o[2]})" for o in orders_list
        ]
        selected_order = st.selectbox("اختر الطلب المراد تعديله:", order_options)
        selected_id = int(selected_order.split(" - ")[0].replace("#", ""))

        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM orders WHERE id = ?", (selected_id,))
        o = c.fetchone()
        conn.close()

        if o:
            with st.form("edit_order_form"):
                c1, c2 = st.columns(2)
                with c1:
                    e_name = st.text_input("اسم الزبون", value=o[1])
                    e_phone = st.text_input("الهاتف", value=o[2])
                    e_item = st.selectbox(
                        "نوع التفصال",
                        ["دشداشة", "قميص", "بنطلون", "بدلة كاملة"],
                        index=[
                            "دشداشة",
                            "قميص",
                            "بنطلون",
                            "بدلة كاملة",
                        ].index(o[3]),
                    )
                with c2:
                    e_deliv = st.text_input("تاريخ التسليم (YYYY-MM-DD)", value=o[16])
                    e_total = st.number_input(
                        "السعر الكلي", value=float(o[11]), step=1.0
                    )
                    e_paid = st.number_input(
                        "الواصل", value=float(o[12]), step=1.0
                    )

                st.markdown("---")
                st.markdown("📐 **القياسات المعدلة:**")
                m1, m2, m3 = st.columns(3)
                with m1:
                    e_len = st.number_input("الطول", value=float(o[4]))
                    e_wid = st.number_input("العرض", value=float(o[5]))
                with m2:
                    e_sh = st.number_input("الكتف", value=float(o[6]))
                    e_slv = st.number_input("الردان", value=float(o[7]))
                with m3:
                    e_col = st.number_input("الياخة", value=float(o[8]))
                    e_cuf = st.number_input("البزمة", value=float(o[9]))

                e_notes = st.text_area("الملاحظات", value=o[10])
                save_edit = st.form_submit_button("💾 حفظ التعديلات")

                if save_edit:
                    e_rem = max(0.0, e_total - e_paid)
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute(
                        """
                        UPDATE orders SET name=?, phone=?, item_type=?, length=?, width=?, shoulder=?,
                        sleeve=?, collar=?, cuff=?, notes=?, total_price=?, advance_paid=?, remaining_price=?, delivery_date=?
                        WHERE id=?
                    """,
                        (
                            e_name,
                            e_phone,
                            e_item,
                            e_len,
                            e_wid,
                            e_sh,
                            e_slv,
                            e_col,
                            e_cuf,
                            e_notes,
                            e_total,
                            e_paid,
                            e_rem,
                            e_deliv,
                            selected_id,
                        ),
                    )
                    conn.commit()
                    conn.close()
                    st.success("✅ تم تحديث بيانات الطلب بنجاح!")
                    st.rerun()
    else:
        st.info("لا توجد طلبات للتعديل.")

# --- 8. تسديد الديون والمالية ---
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
                    f"💰 **الكلي:** {d_total:,.0f} | **الواصل:** {d_paid:,.0f} | **المتبقي:** :red[{d_rem:,.0f}]"
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
                            st.success(f"✅ تم تسديد مبلغ {pay_amount:,.0f}!")
                            st.rerun()
    else:
        st.success("🎉 ممتاز! لا توجد ديون معلقة.")

# --- 9. البحث عن زبون ---
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
                st.write(f"📅 **التسليم:** {r[16]}")
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
                st.markdown("---")
        else:
            st.warning("⚠️ لم يتم العثور على زبون مطابق.")
        conn.close()

# --- 10. الإحصائيات والنسخ الاحتياطي ---
elif choice == "📊 الإحصائيات والنسخ الاحتياطي":
    st.markdown(
        "<div class='main-header'>📊 ملخص المالية والنسخ الاحتياطي</div>",
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

    st.markdown("---")
    st.markdown("### 💾 النسخ الاحتياطي لبياناتك")
    with open(DB_NAME, "rb") as f:
        db_data = f.read()

    st.download_button(
        label="📥 تنزيل نسخة احتياطية من البيانات (Backup)",
        data=db_data,
        file_name=f"sadeq_tailor_backup_{datetime.now().strftime('%Y_%m_%d')}.db",
        mime="application/x-sqlite3",
    )
