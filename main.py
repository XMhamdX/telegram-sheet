import json
import logging
import os
import sys
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import config
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# حالات المحادثة
CHOOSING_SHEET, ENTERING_DATA = range(2)

async def load_sheets_config() -> dict:
    """تحميل إعدادات الجداول من الملف"""
    try:
        with open('sheets_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            if not isinstance(config, dict):
                logger.error("خطأ: ملف التكوين ليس بالتنسيق الصحيح")
                raise ValueError("ملف التكوين غير صالح: يجب أن يكون عبارة عن كائن JSON")
            return config
    except FileNotFoundError:
        logger.error("خطأ: ملف sheets_config.json غير موجود")
        raise FileNotFoundError("لم يتم العثور على ملف التكوين. الرجاء التأكد من وجود ملف sheets_config.json")
    except json.JSONDecodeError as e:
        logger.error(f"خطأ في تنسيق JSON: {str(e)}")
        raise ValueError("خطأ في تنسيق ملف التكوين. الرجاء التأكد من صحة تنسيق JSON")
    except Exception as e:
        logger.error(f"خطأ غير متوقع في تحميل الإعدادات: {str(e)}")
        raise Exception("حدث خطأ غير متوقع أثناء تحميل ملف التكوين")

async def get_sheets_client():
    """إنشاء اتصال Google Sheets"""
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        return gspread.authorize(creds)
    except FileNotFoundError:
        logger.error("خطأ: ملف credentials.json غير موجود")
        raise FileNotFoundError("لم يتم العثور على ملف التوثيق. الرجاء التأكد من وجود ملف credentials.json")
    except Exception as e:
        logger.error(f"خطأ في الاتصال بـ Google Sheets: {str(e)}")
        raise Exception("فشل الاتصال بخدمة Google Sheets. تأكد من صحة ملف التوثيق وصلاحيته")

def get_user_accessible_sheets(user_id: str, sheets_config: dict) -> dict:
    """الحصول على الجداول المتاحة للمستخدم"""
    accessible_sheets = {}
    for sheet_name, sheet_data in sheets_config.items():
        # التحقق من authorized_user_id الرئيسي
        if str(user_id) == str(sheet_data.get('authorized_user_id', '')):
            accessible_sheets[sheet_name] = sheet_data
            continue
            
        # التحقق من قائمة authorized_user_ids
        if str(user_id) in map(str, sheet_data.get('authorized_user_ids', [])):
            accessible_sheets[sheet_name] = sheet_data
    return accessible_sheets

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بداية المحادثة وعرض الجداول المتاحة"""
    try:
        # تسجيل معلومات المستخدم
        user_id = str(update.effective_user.id)
        logger.info(f"بدء محادثة جديدة من المستخدم: {user_id}")
        
        # تحميل الإعدادات
        logger.info("جاري تحميل ملف الإعدادات...")
        sheets_config = await load_sheets_config()
        logger.info(f"تم تحميل الإعدادات: {sheets_config}")
        
        # الحصول على الجداول المتاحة للمستخدم
        logger.info(f"التحقق من صلاحيات المستخدم {user_id}")
        accessible_sheets = get_user_accessible_sheets(user_id, sheets_config)
        logger.info(f"الجداول المتاحة: {accessible_sheets}")
        
        if not accessible_sheets:
            logger.warning(f"المستخدم {user_id} ليس لديه صلاحية الوصول لأي جدول")
            await update.message.reply_text(
                "⚠️ عذراً، ليس لديك صلاحية الوصول لأي جدول.\n"
                "الرجاء التواصل مع المسؤول للحصول على الصلاحيات اللازمة."
            )
            return ConversationHandler.END
        
        # حفظ معلومات الجداول في سياق المحادثة
        context.user_data['sheets_config'] = sheets_config
        context.user_data['accessible_sheets'] = accessible_sheets
        
        # إنشاء أزرار للجداول المتاحة
        keyboard = []
        for sheet_name in accessible_sheets:
            keyboard.append([InlineKeyboardButton(sheet_name, callback_data=f"sheet_{sheet_name}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "👋 مرحباً! الرجاء اختيار الجدول:",
            reply_markup=reply_markup
        )
        return CHOOSING_SHEET
        
    except Exception as e:
        logger.error(f"خطأ في start: {str(e)}", exc_info=True)
        await update.message.reply_text(
            "❌ عذراً، حدث خطأ غير متوقع.\n"
            "الرجاء المحاولة مرة أخرى لاحقاً."
        )
        return ConversationHandler.END

async def show_all_sheets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض كافة الجداول المتاحة"""
    try:
        query = update.callback_query
        await query.answer()
        
        accessible_sheets = context.user_data.get('accessible_sheets', {})
        if not accessible_sheets:
            await query.edit_message_text(
                "❌ عذراً، لم يتم العثور على معلومات الجداول.\n"
                "الرجاء استخدام /start مرة أخرى."
            )
            return ConversationHandler.END
        
        keyboard = [[InlineKeyboardButton(sheet_name, callback_data=f"sheet_{sheet_name}")] 
                    for sheet_name in accessible_sheets.keys()]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔍 الجداول المتاحة لك:\n"
            "اختر الجدول الذي تريد إدخال البيانات فيه:",
            reply_markup=reply_markup
        )
        
        return CHOOSING_SHEET
        
    except Exception as e:
        logger.error(f"خطأ في عرض كافة الجداول: {str(e)}", exc_info=True)
        await query.edit_message_text(
            "❌ عذراً، حدث خطأ أثناء عرض الجداول.\n"
            "الرجاء المحاولة مرة أخرى."
        )
        return ConversationHandler.END

async def handle_sheet_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة اختيار الجدول وبدء إدخال البيانات"""
    try:
        query = update.callback_query
        await query.answer()
        
        logger.info(f"معالجة اختيار الجدول. البيانات المستلمة: {query.data}")
        
        sheet_name = query.data.replace("sheet_", "")
        logger.info(f"اسم الجدول المختار: {sheet_name}")
        
        if 'accessible_sheets' not in context.user_data:
            error_msg = "❌ لم يتم العثور على معلومات الجداول. الرجاء استخدام /start للبدء من جديد."
            logger.error(f"لم يتم العثور على accessible_sheets في user_data")
            await query.edit_message_text(error_msg)
            return ConversationHandler.END
            
        sheet_config = context.user_data['accessible_sheets'].get(sheet_name)
        logger.info(f"تكوين الجدول: {sheet_config}")
        
        if not sheet_config:
            error_msg = "❌ حدث خطأ في اختيار الجدول. الرجاء المحاولة مرة أخرى."
            logger.error(f"لم يتم العثور على تكوين الجدول: {sheet_name}")
            await query.edit_message_text(error_msg)
            return ConversationHandler.END
        
        # حفظ معلومات الجدول المختار
        context.user_data['current_sheet'] = sheet_config
        context.user_data['current_data'] = {}
        context.user_data['last_used_sheet'] = sheet_name  # حفظ آخر جدول تم استخدامه
        
        # إضافة التاريخ تلقائياً إذا كان مطلوباً
        if ('التاريخ' in sheet_config['column_types'] and 
            'date_options' in sheet_config and 
            'التاريخ' in sheet_config['date_options'] and 
            sheet_config['date_options']['التاريخ'].get('auto', False)):
            current_date = datetime.now().strftime('%Y-%m-%d')
            context.user_data['current_data']['التاريخ'] = current_date
            logger.info(f"تم إضافة التاريخ تلقائياً: {current_date}")
        
        # تحضير قائمة الأعمدة المتبقية مع تجاهل التاريخ التلقائي
        remaining_columns = []
        for col in sheet_config['column_order']:
            if col == 'التاريخ' and context.user_data['current_data'].get('التاريخ'):
                continue
            remaining_columns.append(col)
        
        context.user_data['remaining_columns'] = remaining_columns
        logger.info(f"الأعمدة المتبقية: {remaining_columns}")
        
        # بدء عملية إدخال البيانات
        return await request_next_column(query, context)
        
    except Exception as e:
        logger.error(f"خطأ في معالجة اختيار الجدول: {str(e)}", exc_info=True)
        try:
            error_msg = "❌ حدث خطأ غير متوقع. الرجاء المحاولة مرة أخرى."
            if query:
                await query.edit_message_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
        except Exception as e2:
            logger.error(f"خطأ في إرسال رسالة الخطأ: {e2}")
        return ConversationHandler.END

async def request_next_column(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    """طلب إدخال العمود التالي"""
    try:
        logger.info("بدء طلب العمود التالي...")
        logger.info(f"حالة المحادثة: {context.user_data}")
        
        if 'remaining_columns' not in context.user_data or not context.user_data['remaining_columns']:
            logger.error("لم يتم العثور على remaining_columns")
            error_msg = "❌ حدث خطأ في إدخال البيانات. الرجاء المحاولة مرة أخرى باستخدام /start"
            if hasattr(update_or_query, 'message'):
                await update_or_query.message.reply_text(error_msg)
            else:
                await update_or_query.edit_message_text(error_msg)
            return ConversationHandler.END

        current_column = context.user_data['remaining_columns'][0]
        logger.info(f"العمود الحالي: {current_column}")
        
        sheet_config = context.user_data.get('current_sheet')
        if not sheet_config:
            logger.error("لم يتم العثور على current_sheet")
            error_msg = "❌ حدث خطأ في إدخال البيانات. الرجاء المحاولة مرة أخرى باستخدام /start"
            if hasattr(update_or_query, 'message'):
                await update_or_query.message.reply_text(error_msg)
            else:
                await update_or_query.edit_message_text(error_msg)
            return ConversationHandler.END
        
        # التحقق مما إذا كان العمود اختياري
        optional_columns = sheet_config.get('optional_columns', [])
        is_optional = current_column in optional_columns
        
        # إنشاء زر التخطي إذا كان العمود اختياري
        keyboard = []
        if is_optional:
            keyboard = [[InlineKeyboardButton("⏭️ تخطي", callback_data="skip")]]
            
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        # إرسال رسالة طلب إدخال القيمة
        message = f"الرجاء إدخال قيمة {current_column}"
        if is_optional:
            message += "\nأرسل /skip للتخطي"
            
        if hasattr(update_or_query, 'message'):
            await update_or_query.message.reply_text(message, reply_markup=reply_markup)
        else:
            await update_or_query.edit_message_text(message, reply_markup=reply_markup)
            
        context.user_data['CURRENT_STATE'] = ENTERING_DATA
        logger.info(f"تم تعيين الحالة إلى ENTERING_DATA")
        return ENTERING_DATA
        
    except Exception as e:
        logger.error(f"خطأ في request_next_column: {str(e)}", exc_info=True)
        error_msg = "❌ حدث خطأ غير متوقع. الرجاء المحاولة مرة أخرى باستخدام /start"
        if hasattr(update_or_query, 'message'):
            await update_or_query.message.reply_text(error_msg)
        else:
            await update_or_query.edit_message_text(error_msg)
        return ConversationHandler.END

async def handle_data_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة البيانات المدخلة من المستخدم"""
    try:
        if not context.user_data.get('remaining_columns'):
            logger.error("لم يتم العثور على remaining_columns")
            await update.message.reply_text(
                "❌ حدث خطأ في إدخال البيانات. الرجاء المحاولة مرة أخرى باستخدام /start"
            )
            return ConversationHandler.END

        current_column = context.user_data['remaining_columns'][0]
        sheet_config = context.user_data.get('current_sheet')
        
        if not sheet_config:
            logger.error("لم يتم العثور على current_sheet")
            await update.message.reply_text(
                "❌ حدث خطأ في إدخال البيانات. الرجاء المحاولة مرة أخرى باستخدام /start"
            )
            return ConversationHandler.END

        # التعامل مع أمر التخطي
        if update.message.text == '/skip':
            if current_column not in sheet_config.get('optional_columns', []):
                await update.message.reply_text("❌ لا يمكن تخطي هذا الحقل لأنه إلزامي")
                return ENTERING_DATA
            context.user_data['remaining_columns'].pop(0)
            if not context.user_data['remaining_columns']:
                return await save_data_to_sheet(update, context)
            return await request_next_column(update, context)

        # حفظ القيمة المدخلة
        input_value = update.message.text.strip()
        column_type = sheet_config.get('column_types', {}).get(current_column)

        # التحقق من نوع البيانات
        if column_type == 'number':
            try:
                float(input_value)
            except ValueError:
                await update.message.reply_text("❌ الرجاء إدخال رقم صحيح")
                return ENTERING_DATA

        # حفظ القيمة وإزالة العمود من القائمة
        context.user_data.setdefault('current_data', {})
        context.user_data['current_data'][current_column] = input_value
        context.user_data['remaining_columns'].pop(0)

        # إذا لم تبق أعمدة، نحفظ البيانات
        if not context.user_data['remaining_columns']:
            return await save_data_to_sheet(update, context)

        # طلب العمود التالي
        return await request_next_column(update, context)

    except Exception as e:
        logger.error(f"خطأ في handle_data_input: {str(e)}", exc_info=True)
        await update.message.reply_text(
            "❌ حدث خطأ في إدخال البيانات. الرجاء المحاولة مرة أخرى باستخدام /start"
        )
        return ConversationHandler.END

async def handle_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أمر التخطي"""
    try:
        if not context.user_data.get('remaining_columns'):
            await update.message.reply_text(
                "❌ حدث خطأ في إدخال البيانات. الرجاء المحاولة مرة أخرى باستخدام /start"
            )
            return ConversationHandler.END

        current_column = context.user_data['remaining_columns'][0]
        sheet_config = context.user_data.get('current_sheet')
        
        if not sheet_config:
            await update.message.reply_text(
                "❌ حدث خطأ في إدخال البيانات. الرجاء المحاولة مرة أخرى باستخدام /start"
            )
            return ConversationHandler.END

        if current_column not in sheet_config.get('optional_columns', []):
            await update.message.reply_text("❌ لا يمكن تخطي هذا الحقل لأنه إلزامي")
            return ENTERING_DATA

        # تخطي العمود الحالي
        context.user_data['remaining_columns'].pop(0)

        # إذا لم تبق أعمدة، نحفظ البيانات
        if not context.user_data['remaining_columns']:
            return await save_data_to_sheet(update, context)

        # طلب العمود التالي
        return await request_next_column(update, context)

    except Exception as e:
        logger.error(f"خطأ في handle_skip: {str(e)}", exc_info=True)
        await update.message.reply_text(
            "❌ حدث خطأ في إدخال البيانات. الرجاء المحاولة مرة أخرى باستخدام /start"
        )
        return ConversationHandler.END

async def handle_skip_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الضغط على زر التخطي"""
    try:
        query = update.callback_query
        await query.answer()

        if not context.user_data.get('remaining_columns'):
            await query.edit_message_text(
                "❌ حدث خطأ في إدخال البيانات. الرجاء المحاولة مرة أخرى باستخدام /start"
            )
            return ConversationHandler.END

        current_column = context.user_data['remaining_columns'][0]
        sheet_config = context.user_data.get('current_sheet')
        
        if not sheet_config:
            await query.edit_message_text(
                "❌ حدث خطأ في إدخال البيانات. الرجاء المحاولة مرة أخرى باستخدام /start"
            )
            return ConversationHandler.END

        if current_column not in sheet_config.get('optional_columns', []):
            await query.edit_message_text("❌ لا يمكن تخطي هذا الحقل لأنه إلزامي")
            return ENTERING_DATA

        # تخطي العمود الحالي
        context.user_data['remaining_columns'].pop(0)

        # إذا لم تبق أعمدة، نحفظ البيانات
        if not context.user_data['remaining_columns']:
            return await save_data_to_sheet(query, context)

        # طلب العمود التالي
        return await request_next_column(query, context)

    except Exception as e:
        logger.error(f"خطأ في handle_skip_button: {str(e)}", exc_info=True)
        if query:
            await query.edit_message_text(
                "❌ حدث خطأ في إدخال البيانات. الرجاء المحاولة مرة أخرى باستخدام /start"
            )
        return ConversationHandler.END

async def save_data_to_sheet(update_or_query, context):
    """حفظ البيانات في Google Sheets"""
    try:
        sheet_config = context.user_data['current_sheet']
        data = context.user_data['current_data']
        
        logger.info(f"محاولة حفظ البيانات: {data}")
        logger.info(f"إعدادات الجدول: {sheet_config}")
        
        # التحقق من وجود جميع الأعمدة المطلوبة
        missing_columns = []
        for col in sheet_config.get('required_columns', []):
            if not data.get(col):
                missing_columns.append(col)
        
        if missing_columns:
            error_msg = "❌ لم يتم إدخال جميع الأعمدة المطلوبة:\n" + "\n".join(missing_columns)
            logger.error(error_msg)
            if hasattr(update_or_query, 'message'):
                await update_or_query.message.reply_text(error_msg)
            else:
                await update_or_query.edit_message_text(error_msg)
            return ConversationHandler.END
        
        # الاتصال بـ Google Sheets
        try:
            logger.info("جاري الاتصال بـ Google Sheets...")
            client = await get_sheets_client()
            logger.info("تم الاتصال بنجاح")
        except Exception as e:
            error_msg = (
                "❌ فشل الاتصال بخدمة Google Sheets\n"
                "تأكد من صحة ملف التوثيق وصلاحيته.\n"
                "الرجاء التواصل مع المسؤول."
            )
            logger.error(f"خطأ في الاتصال: {str(e)}", exc_info=True)
            if hasattr(update_or_query, 'message'):
                await update_or_query.message.reply_text(error_msg)
            else:
                await update_or_query.edit_message_text(error_msg)
            return ConversationHandler.END
        
        try:
            logger.info(f"محاولة فتح الجدول: {sheet_config['sheet_name']}")
            sheet = client.open(sheet_config['sheet_name']).worksheet(sheet_config['worksheet_name'])
            logger.info("تم فتح الجدول بنجاح")
        except gspread.exceptions.SpreadsheetNotFound:
            error_msg = (
                "❌ لم يتم العثور على الجدول المطلوب\n"
                "تأكد من وجود الجدول وصلاحيات الوصول إليه."
            )
            logger.error(error_msg)
            if hasattr(update_or_query, 'message'):
                await update_or_query.message.reply_text(error_msg)
            else:
                await update_or_query.edit_message_text(error_msg)
            return ConversationHandler.END
        except gspread.exceptions.WorksheetNotFound:
            error_msg = (
                "❌ لم يتم العثور على ورقة العمل المطلوبة\n"
                "تأكد من وجود ورقة العمل في الجدول."
            )
            logger.error(error_msg)
            if hasattr(update_or_query, 'message'):
                await update_or_query.message.reply_text(error_msg)
            else:
                await update_or_query.edit_message_text(error_msg)
            return ConversationHandler.END
        except gspread.exceptions.APIError as e:
            error_msg = (
                f"❌ خطأ في الاتصال بـ Google Sheets: {str(e)}\n"
                "قد تكون هناك مشكلة في الصلاحيات أو حد الاستخدام."
            )
            logger.error(f"خطأ في API: {str(e)}")
            if hasattr(update_or_query, 'message'):
                await update_or_query.message.reply_text(error_msg)
            else:
                await update_or_query.edit_message_text(error_msg)
            return ConversationHandler.END
        
        # تحضير البيانات للإضافة
        logger.info("تحضير البيانات للإضافة...")
        row_data = [data.get(col, '') for col in sheet_config['column_order']]
        logger.info(f"البيانات المراد إضافتها: {row_data}")
        
        # إضافة البيانات
        try:
            sheet.append_row(row_data)
            logger.info("تم إضافة البيانات بنجاح")
            success_msg = (
                "✅ تم حفظ البيانات بنجاح!\n"
                "استخدم /start للبدء من جديد."
            )
            if hasattr(update_or_query, 'message'):
                await update_or_query.message.reply_text(success_msg)
            else:
                await update_or_query.edit_message_text(success_msg)
        except Exception as e:
            error_msg = (
                "❌ حدث خطأ أثناء إضافة البيانات للجدول\n"
                "الرجاء المحاولة مرة أخرى."
            )
            logger.error(f"خطأ في إضافة البيانات: {str(e)}", exc_info=True)
            if hasattr(update_or_query, 'message'):
                await update_or_query.message.reply_text(error_msg)
            else:
                await update_or_query.edit_message_text(error_msg)
            return ConversationHandler.END
        
        return ConversationHandler.END
        
    except Exception as e:
        error_msg = (
            "❌ حدث خطأ غير متوقع\n"
            "الرجاء المحاولة مرة أخرى أو التواصل مع المسؤول."
        )
        logger.error(f"خطأ غير متوقع: {str(e)}", exc_info=True)
        if hasattr(update_or_query, 'message'):
            await update_or_query.message.reply_text(error_msg)
        else:
            await update_or_query.edit_message_text(error_msg)
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء العملية الحالية"""
    await update.message.reply_text("تم إلغاء العملية. استخدم /start للبدء من جديد.")
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الأخطاء العامة في البوت"""
    logger.error("حدث خطأ أثناء معالجة التحديث:", exc_info=context.error)
    
    try:
        # جمع معلومات الخطأ
        error_details = {
            'update_id': update.update_id if hasattr(update, 'update_id') else None,
            'user_id': update.effective_user.id if hasattr(update, 'effective_user') else None,
            'error': str(context.error)
        }
        logger.error(f"تفاصيل الخطأ: {error_details}")
        
        # إرسال رسالة للمستخدم
        if update and hasattr(update, 'effective_message'):
            await update.effective_message.reply_text(
                "⚠️ عذراً، حدث خطأ أثناء معالجة طلبك.\n"
                "تم تسجيل الخطأ وسيتم إصلاحه قريباً."
            )
    except Exception as e:
        logger.error(f"خطأ في معالج الأخطاء: {e}")

async def main():
    """تشغيل البوت"""
    try:
        # إعداد السجلات
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        logger.info("بدء تشغيل البوت...")
        
        # تحميل إعدادات الجداول
        await load_sheets_config()
        
        # إنشاء التطبيق
        application = Application.builder().token(config.TELEGRAM_TOKEN).build()
        
        # إضافة معالج المحادثة
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                CHOOSING_SHEET: [
                    CallbackQueryHandler(handle_sheet_choice, pattern='^sheet_.*$'),
                    CallbackQueryHandler(show_all_sheets, pattern='^show_all_sheets$')
                ],
                ENTERING_DATA: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_data_input),
                    CommandHandler('skip', handle_skip),
                    CallbackQueryHandler(handle_skip_button, pattern='^skip$'),
                    CommandHandler('cancel', cancel)
                ]
            },
            fallbacks=[
                CommandHandler('cancel', cancel),
                MessageHandler(filters.COMMAND, cancel)
            ],
            per_message=False
        )
        
        application.add_handler(conv_handler)
        application.add_error_handler(error_handler)
        
        # بدء البوت
        logger.info("جاري بدء البوت...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        # الانتظار إلى ما لا نهاية
        stop_signal = asyncio.Event()
        await stop_signal.wait()
        
    except Exception as e:
        logger.error(f"خطأ في تشغيل البوت: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        # إيقاف البوت
        await application.updater.stop()
        await application.stop()

if __name__ == '__main__':
    # تشغيل البوت
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"خطأ غير متوقع: {str(e)}", exc_info=True)
    finally:
        loop.close()
