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
CHOOSING_SHEET, CHOOSING_WORKSHEET, CHOOSING_ACTION, ENTERING_DATA = range(4)

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
    available_sheets = []
    
    # تحميل إعدادات الجداول
    sheets_config = load_sheets_config()
    
    # التحقق من الجداول المتاحة للمستخدم
    for sheet_name, config in sheets_config.items():
        if config.get('authorized_user_id') == user_id:
            available_sheets.append(sheet_name)
    
    if not available_sheets:
        await update.message.reply_text(
            "عذراً، لا يوجد لديك أي جداول متاحة."
        )
        return ConversationHandler.END
    
    # إنشاء أزرار للجداول المتاحة
    keyboard = [
        [InlineKeyboardButton(sheet_name, callback_data=f"sheet:{sheet_name}")]
        for sheet_name in available_sheets
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "اختر الجدول:",
        reply_markup=reply_markup
    )
    
    return CHOOSING_SHEET

async def handle_sheet_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار الجدول"""
    query = update.callback_query
    await query.answer()
    
    sheet_name = query.data.split(':')[1]
    context.user_data['current_sheet'] = sheet_name
    
    # تحميل إعدادات الجدول
    sheets_config = load_sheets_config()
    sheet_config = sheets_config.get(sheet_name, {})
    context.user_data['sheet_config'] = sheet_config
    
    try:
        # الحصول على قائمة الأوراق في الجدول
        client = get_sheets_client()
        sheet = client.open(sheet_name)
        worksheets = sheet.worksheets()
        
        # إنشاء أزرار للأوراق
        keyboard = [
            [InlineKeyboardButton(ws.title, callback_data=f"worksheet:{ws.title}")]
            for ws in worksheets
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "اختر الورقة:",
            reply_markup=reply_markup
        )
        
        return CHOOSING_WORKSHEET
        
    except Exception as e:
        logging.error(f"خطأ في الوصول إلى الجدول: {str(e)}")
        await query.edit_message_text(
            "حدث خطأ في الوصول إلى الجدول. حاول مرة أخرى."
        )
        return ConversationHandler.END

async def handle_worksheet_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار الورقة"""
    query = update.callback_query
    await query.answer()
    
    worksheet_name = query.data.split(':')[1]
    
    # تحديث اسم الورقة في إعدادات الجدول
    sheet_name = context.user_data['current_sheet']
    sheet_config = context.user_data['sheet_config']
    sheet_config['worksheet_name'] = worksheet_name
    
    # إنشاء أزرار للإجراءات
    keyboard = [
        [
            InlineKeyboardButton("إضافة بيانات", callback_data="action:add"),
            InlineKeyboardButton("عرض البيانات", callback_data="action:view")
        ],
        [InlineKeyboardButton("إلغاء", callback_data="action:cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"تم اختيار ورقة {worksheet_name}. اختر الإجراء المطلوب:",
        reply_markup=reply_markup
    )
    
    return CHOOSING_ACTION

async def handle_action_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار الإجراء"""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    sheet_config = context.user_data['sheet_config']
    
    if action == "add":
        # تهيئة متغيرات الإدخال
        context.user_data['current_field_index'] = 0
        context.user_data['values'] = {}  # قاموس جديد لتخزين القيم
        
        # إذا كان هناك حقل تاريخ تلقائي، نتخطاه
        fields = sheet_config.get('column_order', [])
        if fields and sheet_config['column_types'].get(fields[0]) == 'date':
            if sheet_config.get('date_options', {}).get(fields[0], {}).get('auto', False):
                context.user_data['values'][fields[0]] = datetime.now().strftime('%Y-%m-%d')
                context.user_data['current_field_index'] = 1
                if len(fields) > 1:
                    await query.edit_message_text(f"الرجاء إدخال {fields[1]}:")
                    return ENTERING_DATA
        
        # طلب أول حقل
        await query.edit_message_text(f"الرجاء إدخال {fields[0]}:")
        return ENTERING_DATA
    
    elif action == "cancel":
        await query.edit_message_text("تم إلغاء العملية. أرسل /start للبدء من جديد.")
        return ConversationHandler.END
    
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
    sheet_config = context.user_data.get('sheet_config')
    if not sheet_config:
        await update.message.reply_text("حدث خطأ. الرجاء البدء من جديد باستخدام /start")
        return ConversationHandler.END

    fields = sheet_config.get('column_order', [])
    current_index = context.user_data.get('current_field_index', 0)
    values = context.user_data.get('values', {})
    
    # تخزين القيمة المدخلة
    if update.message and current_index < len(fields):
        current_field = fields[current_index]
        values[current_field] = update.message.text
        context.user_data['values'] = values
        logging.info(f"تم تخزين القيمة '{update.message.text}' للحقل '{current_field}'")
    
    # تحديث المؤشر للحقل التالي
    current_index += 1
    context.user_data['current_field_index'] = current_index
    
    if current_index >= len(fields):
        # اكتملت جميع الحقول، حفظ البيانات
        try:
            client = get_sheets_client()
            sheet_name = context.user_data['current_sheet']
            
            sheet = client.open(sheet_name)
            worksheet = sheet.worksheet(sheet_config.get('worksheet_name', 'Sheet1'))
            
            # تجهيز البيانات للإدخال بالترتيب الصحيح
            row_data = []
            for field in fields:
                value = values.get(field, '')
                field_type = sheet_config['column_types'].get(field)
                
                # معالجة حقول التاريخ
                if field_type == 'date':
                    date_options = sheet_config.get('date_options', {}).get(field, {})
                    if date_options.get('auto', False):
                        value = datetime.now().strftime('%Y-%m-%d')
                
                # معالجة الأرقام
                elif field_type == 'number':
                    try:
                        value = float(value) if value else 0
                    except:
                        value = 0
                
                row_data.append(value)
            
            # إضافة الصف
            worksheet.append_row(row_data)
            
            # مسح البيانات المؤقتة
            context.user_data.clear()
            
            await update.message.reply_text("تم حفظ البيانات بنجاح! أرسل /start للبدء من جديد.")
            return ConversationHandler.END
            
        except Exception as e:
            logging.error(f"خطأ في حفظ البيانات: {str(e)}")
            await update.message.reply_text("حدث خطأ في حفظ البيانات. حاول مرة أخرى.")
            return ConversationHandler.END

    # طلب الحقل التالي
    next_field = fields[current_index]
    field_type = sheet_config['column_types'].get(next_field)
    
    # تخطي الحقول التلقائية
    while field_type == 'date' and sheet_config.get('date_options', {}).get(next_field, {}).get('auto', False):
        values[next_field] = datetime.now().strftime('%Y-%m-%d')
        context.user_data['values'] = values
        current_index += 1
        if current_index >= len(fields):
            return await handle_data_entry(update, context)
        next_field = fields[current_index]
        field_type = sheet_config['column_types'].get(next_field)
        context.user_data['current_field_index'] = current_index
    
    await update.message.reply_text(f"الرجاء إدخال {next_field}:")
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
                CallbackQueryHandler(handle_sheet_choice, pattern=r'^sheet:')
            ],
            CHOOSING_WORKSHEET: [
                CallbackQueryHandler(handle_worksheet_choice, pattern=r'^worksheet:')
            ],
            CHOOSING_ACTION: [
                CallbackQueryHandler(handle_action_choice, pattern=r'^action:')
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
