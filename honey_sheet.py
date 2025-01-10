from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import config

def get_honey_sheets():
    """الاتصال بجدول عسل عين والحصول على الصفحات"""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        config.GOOGLE_SHEETS_CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    
    # فتح جدول عسل عين
    spreadsheet = client.open("عسل عين")
    return spreadsheet

def get_sheets_keyboard():
    """إنشاء لوحة مفاتيح للصفحات المتاحة"""
    keyboard = [
        [
            InlineKeyboardButton("صفحة 2024", callback_data="honey_2024"),
            InlineKeyboardButton("صفحة الحسابات", callback_data="honey_accounts")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_accounts_keyboard():
    """إنشاء لوحة مفاتيح لاختيار قسم الديون أو السداد"""
    keyboard = [
        [
            InlineKeyboardButton("ديون", callback_data="accounts_debts"),
            InlineKeyboardButton("سداد", callback_data="accounts_payments")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_honey_sheet():
    """الحصول على جدول عسل عين"""
    try:
        gc = gspread.service_account(filename=config.GOOGLE_SHEETS_CREDENTIALS_FILE)
        # فتح الجدول باستخدام معرفه الجديد
        return gc.open_by_key("1_FvS5M8xaRBd4sr3ErI3rKGtDUqoM5CbsL9DQpZo9CY")
    except Exception as e:
        print(f"خطأ في الاتصال بالجدول: {str(e)}")
        raise e

def add_to_accounts(section: str, item: str, amount: float, notes: str = ""):
    """إضافة بيانات إلى صفحة الحسابات
    
    Args:
        section: إما 'ديون' أو 'سداد'
        item: المادة
        amount: المقدار
        notes: ملاحظات (اختياري)
    """
    try:
        sheet = get_honey_sheet()
        worksheet = sheet.worksheet("حسابات")
        today = datetime.now().strftime("%Y-%m-%d")
        
        # تحديد نطاق الإضافة حسب القسم
        if section == "سداد":
            # إضافة في قسم السداد (F-I)
            range_name = "F:I"
            amount_column = "G"  # عمود المقدار في قسم السداد
        else:  # ديون
            # إضافة في قسم الديون (A-D)
            range_name = "A:D"
            amount_column = "B"  # عمود المقدار في قسم الديون
        
        # تجهيز البيانات بالترتيب الصحيح (من اليمين لليسار)
        row = ["" for _ in range(4)]  # صف من 4 أعمدة
        if section == "سداد":
            row[0] = today   # عمود التاريخ (F)
            row[1] = amount  # عمود المقدار (G)
            row[2] = item    # عمود المادة (H)
            row[3] = notes if notes else ""  # عمود الملاحظات (I)
        else:  # ديون
            row[0] = today   # عمود التاريخ (A - أقصى اليمين)
            row[1] = amount  # عمود المقدار (B)
            row[2] = item    # عمود المادة (C)
            row[3] = notes if notes else ""  # عمود الملاحظات (D - أقصى اليسار)
        
        # إضافة الصف في النطاق المحدد
        worksheet.append_row(row, table_range=range_name)
        
        # تحديد نطاق عمود المقدار بالكامل
        last_row = len(worksheet.get_all_values())
        amount_range = f"{amount_column}2:{amount_column}{last_row}"  # نبدأ من الصف 2 لتجنب العنوان
        
        # تنسيق عمود المقدار بالكامل
        worksheet.format(amount_range, {
            "numberFormat": {
                "type": "NUMBER",
                "pattern": "0.00"  # تنسيق رقمي مع فاصلتين عشريتين
            },
            "horizontalAlignment": "LEFT"  # محاذاة لليسار مثل الصورة
        })
        
        return True, "تمت إضافة البيانات بنجاح"
    except Exception as e:
        return False, f"حدث خطأ: {str(e)}"

async def handle_honey_sheet_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, sheet_name: str):
    """معالجة اختيار الصفحة من جدول عسل عين"""
    # التحقق من أن المستخدم هو أنت
    if str(update.effective_user.id) != config.ADMIN_USER_ID:
        await update.callback_query.answer("عذراً، هذا الجدول خاص")
        return
    
    try:
        spreadsheet = get_honey_sheets()
        if sheet_name == "2024":
            worksheet = spreadsheet.worksheet("2024")
            # هنا يمكنك إضافة الوظائف الخاصة بصفحة 2024
            await update.callback_query.message.reply_text(
                "تم اختيار صفحة 2024. ما الذي تريد القيام به؟"
            )
        elif sheet_name == "accounts":
            worksheet = spreadsheet.worksheet("حسابات")
            # هنا يمكنك إضافة الوظائف الخاصة بصفحة الحسابات
            await update.callback_query.message.reply_text(
                "تم اختيار صفحة الحسابات. ما الذي تريد القيام به؟",
                reply_markup=get_accounts_keyboard()
            )
    except Exception as e:
        await update.callback_query.message.reply_text(
            f"حدث خطأ: {str(e)}"
        )

async def handle_accounts_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, section: str):
    """معالجة اختيار قسم الديون أو السداد"""
    try:
        if section == "debts":
            await update.callback_query.message.reply_text(
                "تم اختيار قسم الديون. ما الذي تريد القيام به؟"
            )
        elif section == "payments":
            await update.callback_query.message.reply_text(
                "تم اختيار قسم السداد. ما الذي تريد القيام به؟"
            )
    except Exception as e:
        await update.callback_query.message.reply_text(
            f"حدث خطأ: {str(e)}"
        )

def test_connection():
    """اختبار الاتصال بجدول عسل عين"""
    try:
        # محاولة الاتصال بالجدول
        sheet = get_honey_sheet()
        
        # محاولة الوصول إلى صفحة الحسابات
        worksheet = sheet.worksheet("حسابات")
        
        # محاولة قراءة بيانات
        values = worksheet.get_all_values()
        
        print(f"تم الاتصال بنجاح! عدد الصفوف: {len(values)}")
        return True, "تم الاتصال بالجدول بنجاح"
    except Exception as e:
        return False, f"فشل الاتصال بالجدول: {str(e)}"

if __name__ == "__main__":
    # اختبار الاتصال
    success, message = test_connection()
    print(message)
