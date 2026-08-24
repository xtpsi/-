st.markdown("""
    <!-- استدعاء Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    
    <style>
    /* اتجاه الصفحة والخلفية */
    .stApp {
        background-color: #f8fafc;
        direction: rtl;
        text-align: right;
    }

    /* تحسين البطاقات مع التجاوب للجوّال */
    div[data-testid="stVerticalBlock"] > div {
        background-color: #ffffff;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
        padding: 0.85rem;
        width: 100% !important;
    }

    /* إصلاح القائمة الجانبية للشاشات الصغيرة */
    @media (max-width: 768px) {
        section[data-testid="stSidebar"] {
            width: 100% !important;
        }
        .main .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 100% !important;
        }
    }

    /* تحسين الخانات والأزرار */
    .stTextInput input, .stSelectbox select, .stTextArea textarea {
        border-radius: 8px !important;
        border: 1px solid #cbd5e1 !important;
    }

    .stButton > button {
        background-color: #2563eb !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)
