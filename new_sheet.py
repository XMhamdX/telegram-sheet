from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_new_sheet_keyboard():
    """إنشاء لوحة مفاتيح لاختيار القسم في الجدول الجديد"""
    keyboard = [
        [
            InlineKeyboardButton("المبيعات", callback_data="sales"),
            InlineKeyboardButton("المشتريات", callback_data="purchases")
        ],
        [
            InlineKeyboardButton("المصروفات", callback_data="expenses"),
            InlineKeyboardButton("الإيرادات", callback_data="income")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_section_keyboard(section):
    """إنشاء لوحة مفاتيح للقسم المحدد"""
    if section == "sales":
        keyboard = [
            [InlineKeyboardButton("إضافة مبيع", callback_data="add_sale")],
            [InlineKeyboardButton("عرض المبيعات", callback_data="view_sales")]
        ]
    elif section == "purchases":
        keyboard = [
            [InlineKeyboardButton("إضافة مشتريات", callback_data="add_purchase")],
            [InlineKeyboardButton("عرض المشتريات", callback_data="view_purchases")]
        ]
    elif section == "expenses":
        keyboard = [
            [InlineKeyboardButton("إضافة مصروف", callback_data="add_expense")],
            [InlineKeyboardButton("عرض المصروفات", callback_data="view_expenses")]
        ]
    elif section == "income":
        keyboard = [
            [InlineKeyboardButton("إضافة إيراد", callback_data="add_income")],
            [InlineKeyboardButton("عرض الإيرادات", callback_data="view_income")]
        ]
    else:
        keyboard = [[InlineKeyboardButton("رجوع", callback_data="back")]]
    
    return InlineKeyboardMarkup(keyboard)
