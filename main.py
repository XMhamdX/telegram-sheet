import json
import logging
import os
import sys
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import config
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# تكوين التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# حالات المحادثة
CHOOSING_SHEET, CHOOSING_ACTION, ENTERING_DATA = range(3)

# قراءة إعدادات الجداول
def load_sheets_config():
    try:
        with open('sheets_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"خطأ في قراءة ملف الإعدادات: {str(e)}")
        return {}

# إنشاء اتصال Google Sheets
def get_sheets_client():
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        config.GOOGLE_SHEETS_CREDENTIALS_FILE, scope)
    return gspread.authorize(creds)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بداية المحادثة وعرض الجداول المتاحة"""
    user_id = str(update.effective_user.id)
    sheets_config = load_sheets_config()
    
    # التحقق من صلاحيات المستخدم
    available_sheets = []
    for sheet_name, sheet_config in sheets_config.items():
        if sheet_config.get('authorized_user_id') == user_id:
            available_sheets.append(sheet_name)
    
    if not available_sheets:
        await update.message.reply_text(
            "عذراً، ليس لديك صلاحية الوصول إلى أي جدول."
        )
        return ConversationHandler.END
    
    keyboard = []
    for sheet_name in available_sheets:
        keyboard.append([InlineKeyboardButton(sheet_name, callback_data=f"sheet_{sheet_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "مرحباً! اختر الجدول الذي تريد العمل عليه:",
        reply_markup=reply_markup
    )
    return CHOOSING_SHEET

async def handle_sheet_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار الجدول"""
    query = update.callback_query
    await query.answer()
    
    sheet_name = query.data.replace("sheet_", "")
    context.user_data['current_sheet'] = sheet_name
    
    # قراءة إعدادات الجدول المحدد
    sheets_config = load_sheets_config()
    sheet_config = sheets_config.get(sheet_name, {})
    context.user_data['sheet_config'] = sheet_config
    
    # إنشاء لوحة مفاتيح للإجراءات
    keyboard = [
        [InlineKeyboardButton("إضافة بيانات", callback_data="action_add")],
        [InlineKeyboardButton("عرض البيانات", callback_data="action_view")],
        [InlineKeyboardButton("إلغاء", callback_data="action_cancel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"اخترت جدول {sheet_name}. ماذا تريد أن تفعل؟",
        reply_markup=reply_markup
    )
    return CHOOSING_ACTION

async def handle_action_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار الإجراء"""
    query = update.callback_query
    await query.answer()
    
    action = query.data.replace("action_", "")
    if action == "cancel":
        await query.edit_message_text("تم إلغاء العملية. أرسل /start للبدء من جديد.")
        return ConversationHandler.END
    
    context.user_data['current_action'] = action
    sheet_config = context.user_data.get('sheet_config', {})
    
    if action == "add":
        # تحضير حقول الإدخال
        fields = list(sheet_config.get('column_types', {}).keys())
        context.user_data['fields'] = fields
        context.user_data['current_field_index'] = 0
        
        await query.edit_message_text(
            f"أدخل {fields[0]}:"
        )
        return ENTERING_DATA
    elif action == "view":
        # عرض البيانات الحالية
        try:
            client = get_sheets_client()
            sheet = client.open(context.user_data['current_sheet'])
            worksheet = sheet.worksheet(sheet_config.get('worksheet_name', 'Sheet1'))
            data = worksheet.get_all_records()
            
            if not data:
                message = "لا توجد بيانات في الجدول."
            else:
                # عرض آخر 5 صفوف
                message = "آخر 5 إدخالات:\n\n"
                for row in data[-5:]:
                    message += " | ".join([f"{k}: {v}" for k, v in row.items()]) + "\n"
            
            await query.edit_message_text(message)
        except Exception as e:
            logging.error(f"خطأ في عرض البيانات: {str(e)}")
            await query.edit_message_text("حدث خطأ في عرض البيانات. حاول مرة أخرى.")
        
        return ConversationHandler.END

async def handle_data_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إدخال البيانات"""
    fields = context.user_data.get('fields', [])
    current_index = context.user_data.get('current_field_index', 0)
    
    # تخزين القيمة المدخلة
    if current_index > 0:  # تخزين القيمة السابقة
        context.user_data[fields[current_index - 1]] = update.message.text
    
    if current_index >= len(fields):
        # اكتملت جميع الحقول، حفظ البيانات
        try:
            client = get_sheets_client()
            sheet_name = context.user_data['current_sheet']
            sheet_config = context.user_data['sheet_config']
            
            sheet = client.open(sheet_name)
            worksheet = sheet.worksheet(sheet_config.get('worksheet_name', 'Sheet1'))
            
            # تجهيز البيانات للإدخال
            row_data = []
            for field in fields:
                value = context.user_data.get(field, '')
                field_type = sheet_config['column_types'].get(field)
                
                if field_type == 'date' and sheet_config['date_options'][field].get('auto'):
                    value = datetime.now().strftime('%Y-%m-%d')
                elif field_type == 'number':
                    try:
                        value = float(value)
                    except:
                        value = 0
                
                row_data.append(value)
            
            # إضافة الصف
            worksheet.append_row(row_data)
            await update.message.reply_text("تم حفظ البيانات بنجاح! أرسل /start للبدء من جديد.")
            
        except Exception as e:
            logging.error(f"خطأ في حفظ البيانات: {str(e)}")
            await update.message.reply_text("حدث خطأ في حفظ البيانات. حاول مرة أخرى.")
        
        return ConversationHandler.END
    
    # طلب الحقل التالي
    await update.message.reply_text(f"أدخل {fields[current_index]}:")
    context.user_data['current_field_index'] = current_index + 1
    return ENTERING_DATA

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إلغاء المحادثة"""
    await update.message.reply_text("تم إلغاء العملية. أرسل /start للبدء من جديد.")
    return ConversationHandler.END

async def get_my_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """إرسال معرف المستخدم"""
    await update.message.reply_text(f"معرف المستخدم الخاص بك هو: {update.effective_user.id}")

if __name__ == '__main__':
    # تعيين سياسة حلقة الأحداث للويندوز
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # إنشاء وتشغيل التطبيق
    app = Application.builder().token(config.TELEGRAM_TOKEN).build()
    
    # إضافة المعالجات
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_SHEET: [
                CallbackQueryHandler(handle_sheet_choice, pattern=r'^sheet_')
            ],
            CHOOSING_ACTION: [
                CallbackQueryHandler(handle_action_choice, pattern=r'^action_')
            ],
            ENTERING_DATA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_data_entry)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('myid', get_my_id))
    
    print("\n=== بدء تشغيل بوت Telegram للتعامل مع Google Sheets ===")
    print("جاري التحقق من الإعدادات والملفات المطلوبة...")
    
    try:
        # التحقق من وجود الملفات المطلوبة
        required_files = {
            'credentials.json': 'ملف اعتماد Google Sheets',
            'sheets_config.json': 'ملف إعدادات الجداول',
            '.env': 'ملف المتغيرات البيئية'
        }
        
        for file, description in required_files.items():
            if os.path.exists(file):
                print(f"[+] تم العثور على {description} ({file})")
            else:
                print(f"[-] لم يتم العثور على {description} ({file})")
                raise FileNotFoundError(f"الملف المطلوب غير موجود: {file}")

        # التحقق من التوكن
        if not config.TELEGRAM_TOKEN:
            raise ValueError("لم يتم العثور على توكن البوت في ملف .env")
        print(f"[+] تم التحقق من توكن البوت: {config.TELEGRAM_TOKEN[:20]}...")

        # قراءة إعدادات الجداول
        sheets_config = load_sheets_config()
        if sheets_config:
            print(f"[+] تم تحميل إعدادات الجداول: {len(sheets_config)} جدول")
            for sheet_name in sheets_config:
                print(f"    - {sheet_name}")
        else:
            print("[!] تحذير: لم يتم العثور على أي جداول في ملف الإعدادات")

        print("\n=== البوت جاهز للاستخدام! ===")
        print("- أرسل /start في Telegram لبدء استخدام البوت")
        print("- أرسل /myid للحصول على معرف المستخدم الخاص بك")
        print("- أرسل /cancel لإلغاء العملية الحالية")
        print("\nجاري تشغيل البوت... اضغط Ctrl+C للإيقاف")
        
        # تشغيل البوت
        app.run_polling()
        
    except KeyboardInterrupt:
        print("\nتم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        print(f"\n[!] حدث خطأ: {str(e)}")
        logging.error(f"خطأ في تشغيل البوت: {str(e)}", exc_info=True)
