from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler, ContextTypes
import config
import honey_sheet
import new_sheet
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

# حالات المحادثة
CHOOSING_SHEET, CHOOSING_HONEY_PAGE = range(2)
CHOOSING_ACCOUNTS_SECTION = 3
ACCOUNTS_ITEM, ACCOUNTS_AMOUNT, ACCOUNTS_NOTES = range(4, 7)
PRODUCT, PRICE, NOTES = range(10, 13)
NEW_SHEET_SECTION, NEW_SHEET_ITEM, NEW_SHEET_AMOUNT, NEW_SHEET_NOTES = range(20, 24)

# متغيرات لتخزين البيانات المؤقتة
CURRENT_SECTION = "current_section"

def get_sheets_keyboard():
    """إنشاء لوحة مفاتيح لاختيار الجدول للمستخدم المسؤول"""
    keyboard = [
        [
            InlineKeyboardButton("جدول المشتريات", callback_data="purchases"),
            InlineKeyboardButton("جدول عسل عين", callback_data="honey")
        ],
        [
            InlineKeyboardButton("الجدول الجديد", callback_data="new_sheet")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بداية المحادثة واختيار الجدول"""
    context.user_data.clear()
    user_id = update.effective_user.id
    
    if str(user_id) == config.ADMIN_USER_ID:
        await update.message.reply_text(
            'مرحباً! اختر الجدول الذي تريد استخدامه:',
            reply_markup=get_sheets_keyboard()
        )
        return CHOOSING_SHEET
    
    await update.message.reply_text(
        'مرحباً! يمكنك إرسال:\n\n'
        '1️⃣ منتج واحد مع سعره مثل:\n'
        'كولا ٢٣\n\n'
        '2️⃣ أو قائمة منتجات، كل منتج في سطر مثل:\n'
        'كولا ٢٣\n'
        'شيبس ١٩.٥\n'
        'قهوة ٢٦.٥\n\n'
        '3️⃣ أو اسم منتج فقط وسأطلب منك السعر'
    )
    return PRODUCT

async def handle_sheet_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار الجدول"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "purchases":
        await query.message.reply_text(
            'مرحباً! يمكنك إرسال:\n\n'
            '1️⃣ منتج واحد مع سعره مثل:\n'
            'كولا ٢٣\n\n'
            '2️⃣ أو قائمة منتجات، كل منتج في سطر مثل:\n'
            'كولا ٢٣\n'
            'شيبس ١٩.٥\n'
            'قهوة ٢٦.٥\n\n'
            '3️⃣ أو اسم منتج فقط وسأطلب منك السعر'
        )
        return PRODUCT
    elif query.data == "honey":
        await query.message.reply_text(
            "اختر الصفحة التي تريد:",
            reply_markup=honey_sheet.get_sheets_keyboard()
        )
        return CHOOSING_HONEY_PAGE
    elif query.data == "new_sheet":
        await query.message.reply_text(
            "اختر القسم:",
            reply_markup=new_sheet.get_new_sheet_keyboard()
        )
        return NEW_SHEET_SECTION

async def handle_honey_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار الصفحة في جدول عسل عين"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "honey_accounts":
        await query.message.reply_text(
            "اختر القسم:",
            reply_markup=honey_sheet.get_accounts_keyboard()
        )
        return CHOOSING_ACCOUNTS_SECTION
    elif query.data == "honey_2024":
        await query.message.reply_text("تم اختيار صفحة 2024")
        return ConversationHandler.END

async def handle_accounts_section(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار قسم الديون أو السداد"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "accounts_debts":
        context.user_data[CURRENT_SECTION] = "ديون"
        await query.message.reply_text("أدخل المادة:")
        return ACCOUNTS_ITEM
    elif query.data == "accounts_payments":
        context.user_data[CURRENT_SECTION] = "سداد"
        await query.message.reply_text("أدخل المادة:")
        return ACCOUNTS_ITEM

async def handle_accounts_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إدخال المادة"""
    context.user_data['item'] = update.message.text
    await update.message.reply_text("أدخل المقدار (رقم فقط):")
    return ACCOUNTS_AMOUNT

async def handle_accounts_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إدخال المقدار"""
    try:
        amount = float(update.message.text.replace(',', '.'))
        context.user_data['amount'] = amount
        await update.message.reply_text("أدخل الملاحظات (أو أرسل /skip للتخطي):")
        return ACCOUNTS_NOTES
    except ValueError:
        await update.message.reply_text("الرجاء إدخال رقم صحيح!")
        return ACCOUNTS_AMOUNT

async def handle_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة الملاحظات"""
    user_data = context.user_data
    
    if update.message.text == '/skip':
        notes = ""
    else:
        notes = update.message.text
    
    try:
        success, message = honey_sheet.add_to_accounts(
            user_data[CURRENT_SECTION],
            user_data['item'],
            user_data['amount'],
            notes
        )
        
        if success:
            await update.message.reply_text("تم إضافة البيانات بنجاح!")
        else:
            await update.message.reply_text(f"حدث خطأ: {message}")
            
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ: {str(e)}")
    
    context.user_data.clear()
    return ConversationHandler.END

async def get_my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض معرف المستخدم"""
    user_id = update.effective_user.id
    await update.message.reply_text(f"معرف التليجرام الخاص بك هو: {user_id}\n"
                                  f"قم بنسخ هذا الرقم ووضعه في ملف config.py")

async def product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة المدخلات الأولية"""
    text = update.message.text
    
    if '\n' in text:
        lines = text.strip().split('\n')
        products_with_prices = []
        products_without_prices = []
        
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 2:
                try:
                    if parts[0].replace('.', '').replace(',', '').isdigit():
                        price = float(parts[0].replace(',', '.'))
                        product = ' '.join(parts[1:])
                        products_with_prices.append((product, price))
                        continue
                    
                    if parts[-1].replace('.', '').replace(',', '').isdigit():
                        price = float(parts[-1].replace(',', '.'))
                        product = ' '.join(parts[:-1])
                        products_with_prices.append((product, price))
                        continue
                    
                    products_without_prices.append(line.strip())
                except ValueError:
                    products_without_prices.append(line.strip())
            else:
                products_without_prices.append(line.strip())
        
        if products_without_prices:
            await update.message.reply_text(
                "لم أتمكن من فهم الأسعار في بعض المنتجات. "
                "الرجاء التأكد من كتابة السعر منفصلاً في بداية أو نهاية كل سطر.\n\n"
                "مثال:\n"
                "20 كرز وخوخ\n"
                "بندورة 25\n"
                "موز وتفاح 30"
            )
            return ConversationHandler.END
        
        context.user_data['products_with_prices'] = products_with_prices
        
        await update.message.reply_text("أدخل الملاحظات (أو أرسل /skip للتخطي):")
        return NOTES
    
    parts = text.split()
    if len(parts) >= 2:
        try:
            if parts[0].replace('.', '').replace(',', '').isdigit():
                price = float(parts[0].replace(',', '.'))
                product = ' '.join(parts[1:])
            elif parts[-1].replace('.', '').replace(',', '').isdigit():
                price = float(parts[-1].replace(',', '.'))
                product = ' '.join(parts[:-1])
            else:
                context.user_data['product'] = text
                await update.message.reply_text("أدخل السعر (رقم فقط):")
                return PRICE
                
            context.user_data['product'] = product
            context.user_data['price'] = price
            await update.message.reply_text("أدخل الملاحظات (أو أرسل /skip للتخطي):")
            return NOTES
        except ValueError:
            context.user_data['product'] = text
            await update.message.reply_text("أدخل السعر (رقم فقط):")
            return PRICE
    else:
        context.user_data['product'] = text
        await update.message.reply_text("أدخل السعر (رقم فقط):")
        return PRICE

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إدخال السعر"""
    try:
        price = float(update.message.text.replace(',', '.'))
        context.user_data['price'] = price
        await update.message.reply_text(
            'هل تريد إضافة ملاحظات؟ (أرسل الملاحظات أو /skip للتخطي)'
        )
        return NOTES
    except ValueError:
        await update.message.reply_text('الرجاء إدخال رقم صحيح!')
        return PRICE

async def notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إدخال الملاحظات"""
    if update.message.text == '/skip':
        notes = ""
    else:
        notes = update.message.text
    
    try:
        if 'products_with_prices' in context.user_data:
            products = context.user_data['products_with_prices']
            for product, price in products:
                add_to_sheets(product, price, notes)
            await update.message.reply_text(
                "تم إضافة جميع المنتجات بنجاح!\n\n"
                "لإضافة منتجات جديدة، اضغط على /start"
            )
        else:
            product = context.user_data['product']
            price = context.user_data['price']
            add_to_sheets(product, price, notes)
            await update.message.reply_text(
                "تم إضافة المنتج بنجاح!\n\n"
                "لإضافة منتجات جديدة، اضغط على /start"
            )
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ: {str(e)}")
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إلغاء المحادثة"""
    await update.message.reply_text('تم إلغاء العملية. استخدم /start للبدء من جديد.')
    return ConversationHandler.END

def check_user_access(user_id: str, sheet_name: str) -> bool:
    """التحقق من صلاحية المستخدم للوصول إلى الجدول"""
    try:
        with open('sheets_config.json', 'r', encoding='utf-8') as f:
            sheets_config = json.load(f)
        
        sheet_config = sheets_config.get(sheet_name)
        if not sheet_config:
            return False
        
        authorized_ids = sheet_config.get('authorized_user_ids', '*')
        # السماح لجميع المستخدمين
        if authorized_ids == "*":
            return True
        
        # التحقق من قائمة المستخدمين المصرح لهم
        authorized_list = [id.strip() for id in authorized_ids.split(',')]
        return str(user_id) in authorized_list
            
    except Exception:
        return False

async def handle_new_sheet_section(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار القسم في الجدول الجديد"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("new_section"):
        section = query.data.replace("new_section", "")
        user_id = update.effective_user.id
        
        # التحقق من صلاحية المستخدم
        if not check_user_access(user_id, config.NEW_SHEET_NAME):
            await query.message.reply_text("عذراً، ليس لديك صلاحية الوصول إلى هذا الجدول.")
            return ConversationHandler.END
            
        context.user_data['section'] = section
        context.user_data['current_field_index'] = 0  # تتبع الحقل الحالي
        
        # تحميل إعدادات الجدول
        gc = gspread.service_account(filename=config.GOOGLE_SHEETS_CREDENTIALS_FILE)
        with open('sheets_config.json', 'r', encoding='utf-8') as f:
            sheets_config = json.load(f)
        
        sheet_config = sheets_config.get(config.NEW_SHEET_NAME)
        if not sheet_config:
            await query.message.reply_text("لم يتم العثور على إعدادات الجدول!")
            return ConversationHandler.END
        
        context.user_data['sheet_config'] = sheet_config
        context.user_data['fields_data'] = {}  # لتخزين البيانات المدخلة
        
        # بدء طلب البيانات للحقل الأول
        return await request_next_field(update, context)
    
    return ConversationHandler.END

async def request_next_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """طلب البيانات للحقل التالي"""
    sheet_config = context.user_data['sheet_config']
    current_index = context.user_data['current_field_index']
    columns = list(sheet_config['column_types'].keys())
    
    # التحقق من اكتمال جميع الحقول
    if current_index >= len(columns):
        return await save_sheet_data(update, context)
    
    current_column = columns[current_index]
    column_type = sheet_config['column_types'][current_column]
    is_required = sheet_config['required_fields'].get(current_column, True)
    
    # التحقق من الحقول التلقائية للتاريخ
    if column_type == 'date' and sheet_config['date_options'].get(current_column, {}).get('auto', False):
        now = datetime.now()
        if sheet_config['date_options'][current_column].get('include_time', False):
            context.user_data['fields_data'][current_column] = now.strftime("%Y-%m-%d %H:%M:%S")
        else:
            context.user_data['fields_data'][current_column] = now.strftime("%Y-%m-%d")
        context.user_data['current_field_index'] += 1
        return await request_next_field(update, context)
    
    # إعداد الرسالة
    message = f"أدخل {current_column}"
    if not is_required:
        message += " (اختياري - أرسل /skip للتخطي)"
    
    if isinstance(update.callback_query, CallbackQuery):
        await update.callback_query.message.reply_text(message)
    else:
        await update.message.reply_text(message)
    
    return NEW_SHEET_ITEM

async def handle_new_sheet_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إدخال البيانات للحقل الحالي"""
    sheet_config = context.user_data['sheet_config']
    current_index = context.user_data['current_field_index']
    columns = list(sheet_config['column_types'].keys())
    current_column = columns[current_index]
    
    # معالجة التخطي للحقول الاختيارية
    if update.message.text == '/skip':
        is_required = sheet_config['required_fields'].get(current_column, True)
        if not is_required:
            context.user_data['fields_data'][current_column] = ""
            context.user_data['current_field_index'] += 1
            return await request_next_field(update, context)
        else:
            await update.message.reply_text("هذا الحقل إجباري! الرجاء إدخال قيمة.")
            return NEW_SHEET_ITEM
    
    # معالجة القيمة المدخلة
    value = update.message.text
    column_type = sheet_config['column_types'][current_column]
    
    if column_type == 'number':
        try:
            value = float(value.replace(',', '.'))
        except ValueError:
            await update.message.reply_text("الرجاء إدخال رقم صحيح!")
            return NEW_SHEET_ITEM
    
    context.user_data['fields_data'][current_column] = value
    context.user_data['current_field_index'] += 1
    return await request_next_field(update, context)

async def save_sheet_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """حفظ البيانات في الجدول"""
    try:
        sheet_config = context.user_data['sheet_config']
        fields_data = context.user_data['fields_data']
        section = context.user_data['section']
        
        # تحضير الصف للإضافة
        row = []
        for column in sheet_config['column_types'].keys():
            row.append(fields_data.get(column, ""))
        
        # إضافة البيانات إلى الجدول
        gc = gspread.service_account(filename=config.GOOGLE_SHEETS_CREDENTIALS_FILE)
        sheet = gc.open(config.NEW_SHEET_NAME).worksheet(section)
        sheet.append_row(row)
        
        await update.message.reply_text("تم حفظ البيانات بنجاح!")
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ: {str(e)}")
    
    context.user_data.clear()
    return ConversationHandler.END

def add_to_sheets(product: str, price: float, notes: str):
    """إضافة بيانات جديدة إلى Google Sheets"""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    
    gc = gspread.service_account(filename=config.GOOGLE_SHEETS_CREDENTIALS_FILE)
    sheet = gc.open(config.SPREADSHEET_NAME).sheet1
    
    today = datetime.now().strftime("%Y-%m-%d")
    row = [today, product, price, notes]
    sheet.append_row(row)

async def main() -> None:
    """النقطة الرئيسية لتشغيل البوت"""
    print("بدء تشغيل البوت...")
    
    try:
        # إنشاء التطبيق وإضافة المعالجات
        application = Application.builder().token(config.TELEGRAM_TOKEN).build()
        print(f"تم إنشاء التطبيق باستخدام التوكن: {config.TELEGRAM_TOKEN}")

        # معالج المحادثة للمستخدم المسؤول
        admin_conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                CHOOSING_SHEET: [CallbackQueryHandler(handle_sheet_choice)],
                CHOOSING_HONEY_PAGE: [CallbackQueryHandler(handle_honey_page)],
                CHOOSING_ACCOUNTS_SECTION: [CallbackQueryHandler(handle_accounts_section)],
                ACCOUNTS_ITEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_accounts_item)],
                ACCOUNTS_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_accounts_amount)],
                ACCOUNTS_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_notes)],
                NEW_SHEET_SECTION: [CallbackQueryHandler(handle_new_sheet_section)],
                NEW_SHEET_ITEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_sheet_item)],
                NEW_SHEET_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_sheet_item)],
                NEW_SHEET_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_sheet_item)]
            },
            fallbacks=[CommandHandler('cancel', cancel)],
            per_message=False
        )
        print("تم إعداد معالج المحادثة للمدير")

        # معالج المحادثة للمستخدمين العاديين
        user_conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                PRODUCT: [MessageHandler(filters.TEXT & ~filters.COMMAND, product)],
                PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, price)],
                NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, notes)]
            },
            fallbacks=[CommandHandler('cancel', cancel)],
            per_message=False
        )
        print("تم إعداد معالج المحادثة للمستخدمين")

        # إضافة المعالجات للتطبيق
        application.add_handler(admin_conv_handler)
        application.add_handler(user_conv_handler)
        application.add_handler(CommandHandler('myid', get_my_id))
        print("تم إضافة جميع المعالجات")

        print("جاري بدء تشغيل البوت...")
        await application.initialize()
        print("تم التهيئة")
        await application.start()
        print("تم البدء")
        print("البوت جاهز للاستخدام!")
        print(f"معرف المدير هو: {config.ADMIN_USER_ID}")
        print("يمكنك الآن استخدام البوت في تطبيق Telegram")
        
        await application.run_polling(drop_pending_updates=True)
    except Exception as e:
        print(f"حدث خطأ: {str(e)}")
        raise e

if __name__ == '__main__':
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        print(f"حدث خطأ: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        print("تم إيقاف البوت")
