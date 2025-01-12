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

# إعداد السجلات بمستوى تفصيلي
logging.basicConfig(
    level=logging.DEBUG,  # تغيير مستوى السجلات إلى DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_debug.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# تفعيل سجلات python-telegram-bot
logging.getLogger('telegram').setLevel(logging.DEBUG)
logging.getLogger('httpx').setLevel(logging.DEBUG)

# حالات المحادثة
CHOOSING_SHEET, CHOOSING_WORKSHEET, CHOOSING_ACTION, ENTERING_DATA = range(4)

async def load_sheets_config() -> dict:
    """تحميل إعدادات الجداول من الملف"""
    try:
        with open('sheets_config.json', 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            if not isinstance(config_data, dict):
                logger.error("تنسيق ملف الإعدادات غير صحيح")
                return {}
            return config_data
    except FileNotFoundError:
        logger.error("ملف الإعدادات غير موجود")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"خطأ في تنسيق ملف الإعدادات: {str(e)}")
        return {}
    except Exception as e:
        logger.error(f"خطأ غير متوقع في تحميل الإعدادات: {str(e)}")
        return {}

async def get_sheets_client():
    """إنشاء اتصال Google Sheets"""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        config.GOOGLE_SHEETS_CREDENTIALS_FILE, scope)
    return gspread.authorize(creds)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بداية المحادثة وعرض الجداول المتاحة"""
    try:
        user_id = str(update.effective_user.id)
        logger.debug(f"بدء محادثة جديدة من المستخدم: {user_id}")
        
        # إعادة تعيين حالة المحادثة
        if 'active_session' in context.user_data:
            logger.info(f"إنهاء الجلسة السابقة للمستخدم {update.effective_user.id}")
            context.user_data.clear()
        
        context.user_data['active_session'] = True
        
        # تحميل إعدادات الجداول
        sheets_config = await load_sheets_config()
        logger.debug(f"تم تحميل الإعدادات: {json.dumps(sheets_config, ensure_ascii=False)}")
        
        if not sheets_config:
            logger.error("لم يتم العثور على إعدادات الجداول")
            await update.message.reply_text("عذراً، حدث خطأ في تحميل إعدادات الجداول")
            return ConversationHandler.END
        
        # التحقق من صلاحيات المستخدم
        available_sheets = []
        for sheet_name, sheet_config in sheets_config.items():
            if not sheet_config.get('authorized_user_ids') or user_id in sheet_config.get('authorized_user_ids', []):
                available_sheets.append(sheet_name)
        
        logger.debug(f"الجداول المتاحة للمستخدم {user_id}: {available_sheets}")
        
        if not available_sheets:
            logger.warning(f"المستخدم {user_id} ليس لديه صلاحية للوصول إلى أي جدول")
            await update.message.reply_text("عذراً، ليس لديك صلاحية للوصول إلى أي جدول")
            context.user_data.clear()
            return ConversationHandler.END
        
        # إنشاء قائمة الجداول
        keyboard = []
        for sheet_name in available_sheets:
            keyboard.append([InlineKeyboardButton(sheet_name, callback_data=f"sheet:{sheet_name}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "مرحباً! الرجاء اختيار الجدول:",
            reply_markup=reply_markup
        )
        return CHOOSING_SHEET
        
    except Exception as e:
        logger.error(f"خطأ غير متوقع في دالة start: {str(e)}", exc_info=True)
        await update.message.reply_text("عذراً، حدث خطأ غير متوقع")
        context.user_data.clear()
        return ConversationHandler.END

async def handle_sheet_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار الجدول"""
    query = update.callback_query
    await query.answer()
    sheet_name = query.data.split(':')[1]
    context.user_data['sheet_name'] = sheet_name
    logger.info(f"تم اختيار الجدول: {sheet_name}")
    
    # تحميل إعدادات الجدول
    sheets_config = await load_sheets_config()
    sheet_config = sheets_config.get(sheet_name)
    context.user_data['sheet_config'] = sheet_config
    
    # التحقق من إعدادات الجدول
    if not sheet_config:
        logger.error(f"جدول غير موجود: {sheet_name}")
        await query.edit_message_text("جدول غير موجود، يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END
    
    # الاتصال بـ Google Sheets
    client = await get_sheets_client()
    if not client:
        logger.error("فشل الاتصال بـ Google Sheets")
        await query.edit_message_text("عذراً، حدث خطأ في الاتصال بالجدول.")
        return ConversationHandler.END
    
    # فتح الجدول
    try:
        spreadsheet = client.open(sheet_name)
        logger.debug(f"تم فتح الجدول: {sheet_name}")
        
        # الحصول على قائمة الأوراق
        worksheets = spreadsheet.worksheets()
        logger.debug(f"عدد الأوراق: {len(worksheets)}")
        
        # إنشاء أزرار للأوراق
        keyboard = [
            [InlineKeyboardButton(ws.title, callback_data=f"worksheet:{ws.title}")]
            for ws in worksheets
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"تم اختيار جدول '{sheet_name}'\nاختر الورقة:",
            reply_markup=reply_markup
        )
        
        return CHOOSING_WORKSHEET
    
    except Exception as e:
        logger.error(f"خطأ في فتح الجدول: {str(e)}")
        await query.edit_message_text(
            f"عذراً، حدث خطأ في فتح الجدول: {str(e)}"
        )
        return ConversationHandler.END

async def handle_worksheet_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار الورقة"""
    query = update.callback_query
    await query.answer()
    worksheet_title = query.data.split(':')[1]
    context.user_data['worksheet_name'] = worksheet_title
    
    # إنشاء أزرار الإجراءات
    keyboard = [
        [
            InlineKeyboardButton("إضافة صف", callback_data="action:add"),
            InlineKeyboardButton("عرض البيانات", callback_data="action:view")
        ],
        [InlineKeyboardButton("إلغاء", callback_data="action:cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"تم اختيار ورقة '{worksheet_title}'\nماذا تريد أن تفعل؟",
        reply_markup=reply_markup
    )
    
    return CHOOSING_ACTION

async def handle_action_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار الإجراء"""
    query = update.callback_query
    await query.answer()
    action = query.data.split(':')[1]
    sheet_name = context.user_data.get('sheet_name')
    worksheet_name = context.user_data.get('worksheet_name')
    
    if not sheet_name or not worksheet_name:
        await query.edit_message_text("حدث خطأ. الرجاء البدء من جديد باستخدام /start")
        return ConversationHandler.END
    
    # تحميل إعدادات الجدول
    sheets_config = await load_sheets_config()
    sheet_config = sheets_config.get(sheet_name)
    context.user_data['sheet_config'] = sheet_config
    
    if action == "add":
        # التحقق من وجود الأعمدة
        fields = sheet_config.get('column_order', [])
        if not fields:
            await query.edit_message_text("لم يتم تحديد الأعمدة في إعدادات الجدول")
            return ConversationHandler.END
        
        # تهيئة القيم
        context.user_data['values'] = {}
        context.user_data['current_field_index'] = 0
        
        # معالجة الحقل الأول
        current_field = fields[0]
        field_type = sheet_config['column_types'].get(current_field)
        is_required = current_field in sheet_config.get('required_columns', [])
        
        # معالجة التاريخ التلقائي
        if field_type == 'date':
            date_options = sheet_config.get('date_options', {}).get(current_field, {})
            if date_options.get('auto', False):
                context.user_data['values'][current_field] = datetime.now().strftime('%Y-%m-%d')
                if len(fields) > 1:
                    next_field = fields[1]
                    context.user_data['current_field_index'] = 1
                    message = f"الرجاء إدخال {next_field}"
                    if next_field not in sheet_config.get('required_columns', []):
                        message += " (اختياري - يمكنك كتابة 'سكب' أو 'skip' للتخطي)"
                    await query.edit_message_text(message)
                    return ENTERING_DATA
        
        # طلب الحقل الأول
        message = f"الرجاء إدخال {current_field}"
        if not is_required:
            message += " (اختياري - يمكنك كتابة 'سكب' أو 'skip' للتخطي)"
        await query.edit_message_text(message)
        return ENTERING_DATA
    
    elif action == "view":
        try:
            client = await get_sheets_client()
            if not client:
                raise Exception("فشل الاتصال بـ Google Sheets")
            
            sheet = client.open(sheet_name)
            worksheet = sheet.worksheet(worksheet_name)
            
            # الحصول على البيانات
            data = worksheet.get_all_values()
            if len(data) > 1:  # تجاهل الصف الأول (العناوين)
                last_rows = data[-5:]  # آخر 5 صفوف
                message = "آخر 5 إدخالات:\n\n"
                headers = sheet_config.get('column_order', [])
                
                # إضافة العناوين
                message += " | ".join(headers) + "\n"
                message += "-" * 50 + "\n"
                
                # إضافة البيانات
                for row in last_rows:
                    # التأكد من أن الصف يحتوي على نفس عدد الأعمدة
                    while len(row) < len(headers):
                        row.append("")
                    message += " | ".join(row[:len(headers)]) + "\n"
            else:
                message = "لا توجد بيانات بعد"
            
            await query.edit_message_text(message)
        
        except Exception as e:
            logger.error(f"خطأ في عرض البيانات: {str(e)}")
            await query.edit_message_text(f"حدث خطأ في عرض البيانات: {str(e)}")
        
        return ConversationHandler.END
    
    elif action == "cancel":
        await query.edit_message_text("تم إلغاء العملية. أرسل /start للبدء من جديد.")
        return ConversationHandler.END

async def handle_data_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إدخال البيانات"""
    sheet_config = context.user_data.get('sheet_config')
    if not sheet_config:
        await update.message.reply_text("حدث خطأ. الرجاء البدء من جديد باستخدام /start")
        return ConversationHandler.END
    
    fields = sheet_config.get('column_order', [])
    required_fields = sheet_config.get('required_columns', [])
    current_index = context.user_data.get('current_field_index', 0)
    values = context.user_data.get('values', {})
    
    if update.message and current_index < len(fields):
        current_field = fields[current_index]
        text = update.message.text.strip()
        
        if text.lower() in ['سكب', 'skip']:
            if current_field in required_fields:
                await update.message.reply_text(f"الحقل {current_field} إجباري ولا يمكن تخطيه. الرجاء إدخال قيمة:")
                return ENTERING_DATA
            else:
                values[current_field] = ''
        else:
            values[current_field] = text
        
        context.user_data['values'] = values
        logger.debug(f"تم تخزين القيمة '{text}' للحقل '{current_field}'")
        
        current_index += 1
        context.user_data['current_field_index'] = current_index
        
        if current_index >= len(fields):
            return await save_data(update, context)
        
        next_field = fields[current_index]
        await update.message.reply_text(f"الرجاء إدخال {next_field}:")
        return ENTERING_DATA

async def save_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """حفظ البيانات في Google Sheets"""
    try:
        client = await get_sheets_client()
        sheet_name = context.user_data.get('sheet_name')
        worksheet_name = context.user_data['sheet_config']['worksheet_name']
        sheet = client.open(sheet_name).worksheet(worksheet_name)
        
        row_data = [context.user_data['values'].get(field, '') for field in context.user_data['sheet_config']['column_order']]
        sheet.append_row(row_data)
        
        await update.message.reply_text("تم حفظ البيانات بنجاح!")
        context.user_data.clear()
        return ConversationHandler.END
    
    except Exception as e:
        logger.error(f"خطأ في حفظ البيانات: {str(e)}")
        await update.message.reply_text(f"حدث خطأ في حفظ البيانات: {str(e)}")
        return ConversationHandler.END

async def skip_data_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """تخطي حقل اختياري في إدخال البيانات"""
    user_id = str(update.effective_user.id)
    
    if 'current_sheet' not in context.user_data:
        await update.message.reply_text("الرجاء بدء عملية إدخال البيانات أولاً باستخدام /start")
        return ConversationHandler.END
    
    current_sheet = context.user_data['current_sheet']
    if not is_user_authorized(user_id, current_sheet):
        await update.message.reply_text("عذراً، ليس لديك صلاحية للوصول إلى هذا الجدول.")
        return ConversationHandler.END
    
    if 'current_field_index' not in context.user_data:
        await update.message.reply_text("الرجاء بدء عملية إدخال البيانات أولاً")
        return ConversationHandler.END
    
    sheet_config = load_sheets_config().get(current_sheet, {})
    required_fields = [field for field, type_ in sheet_config.get('column_types', {}).items() if type_ != 'optional']
    optional_fields = [field for field, type_ in sheet_config.get('column_types', {}).items() if type_ == 'optional']
    
    current_field_index = context.user_data['current_field_index']
    all_fields = required_fields + optional_fields
    
    # التحقق من أن الحقل الحالي اختياري
    if current_field_index < len(required_fields):
        await update.message.reply_text("لا يمكن تخطي الحقول الإلزامية!")
        field_name = required_fields[current_field_index]
        await update.message.reply_text(f"الرجاء إدخال {field_name}:")
        return ENTERING_DATA
    
    # تخطي الحقل الاختياري
    context.user_data['current_field_index'] = current_field_index + 1
    field_name = optional_fields[current_field_index - len(required_fields)]
    context.user_data[field_name] = ""
    
    # التحقق مما إذا كانت هناك المزيد من الحقول
    if current_field_index + 1 >= len(all_fields):
        # حفظ البيانات في جدول البيانات
        try:
            await save_data_to_sheet(context.user_data, current_sheet)
            await update.message.reply_text("تم حفظ البيانات بنجاح!")
        except Exception as e:
            logger.error(f"خطأ في حفظ البيانات: {e}")
            await update.message.reply_text("حدث خطأ أثناء حفظ البيانات. الرجاء المحاولة مرة أخرى.")
        context.user_data.clear()
        return ConversationHandler.END
    
    # طلب الحقل التالي
    next_field = all_fields[current_field_index + 1]
    await update.message.reply_text(f"الرجاء إدخال {next_field}:")
    return ENTERING_DATA

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إلغاء المحادثة الحالية وإعادة تعيين البيانات"""
    user_id = update.effective_user.id
    logger.info(f"إلغاء المحادثة للمستخدم {user_id}")
    
    # مسح بيانات المستخدم
    context.user_data.clear()
    
    await update.message.reply_text(
        "تم إلغاء العملية الحالية. يمكنك البدء من جديد باستخدام الأمر /start"
    )
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الأخطاء التي تحدث أثناء تشغيل البوت"""
    logger.error("حدث خطأ أثناء معالجة التحديث:", exc_info=context.error)
    
    try:
        # إرسال رسالة خطأ للمستخدم
        if update and hasattr(update, 'effective_message'):
            await update.effective_message.reply_text(
                "عذراً، حدث خطأ أثناء معالجة طلبك. الرجاء المحاولة مرة أخرى لاحقاً."
            )
    except Exception as e:
        logger.error(f"خطأ في إرسال رسالة الخطأ: {e}")

def main() -> None:
    """تشغيل البوت"""
    try:
        logger.info("بدء تشغيل البوت...")
        
        # التحقق من وجود TOKEN
        if not config.TELEGRAM_TOKEN:
            logger.error("لم يتم العثور على TELEGRAM_TOKEN")
            sys.exit(1)
            
        logger.debug(f"تم العثور على TELEGRAM_TOKEN: {config.TELEGRAM_TOKEN[:10]}...")
        
        # إنشاء التطبيق
        application = Application.builder().token(config.TELEGRAM_TOKEN).build()
        
        # إضافة معالجات المحادثة
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states={
                CHOOSING_SHEET: [
                    CallbackQueryHandler(handle_sheet_choice, pattern=r"^sheet:"),
                ],
                CHOOSING_WORKSHEET: [
                    CallbackQueryHandler(handle_worksheet_choice, pattern=r"^worksheet:"),
                ],
                ENTERING_DATA: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_data_entry),
                    CommandHandler("skip", skip_data_entry),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", cancel),
                CommandHandler("start", start),  # إضافة start كـ fallback
            ],
            allow_reentry=True,  # السماح بإعادة الدخول للمحادثة
            per_message=True,  # معالجة رسالة واحدة في كل مرة
            name="main_conversation",
        )
        
        application.add_handler(conv_handler)
        
        # إضافة معالج الأخطاء
        application.add_error_handler(error_handler)
        
        logger.info("بدء تشغيل البوت...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"خطأ في تشغيل البوت: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    # تعيين سياسة حلقة الأحداث للويندوز
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    main()
