"""
اختبار وظائف بوت التليجرام للتعامل مع جداول جوجل.
يقوم هذا الملف بمحاكاة تفاعلات المستخدم مع البوت واختبار جميع الوظائف الأساسية.

الوظائف المختبرة:
1. إدارة المستخدمين (إضافة/إزالة/التحقق من الصلاحيات)
2. التعامل مع الأوامر الأساسية (/start, /skip)
3. إدخال البيانات (التاريخ، التسمية، المربح، الملاحظات)
4. التحقق من صحة المدخلات
5. إدارة حالة المحادثة

المتطلبات:
- Python 3.7+
- وجود ملف إعدادات (sheets_config.json)
- صلاحيات القراءة والكتابة في مجلد العمل
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import sys
import os

# إعداد الترميز للأحرف العربية
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# إنشاء ملف الإعدادات إذا لم يكن موجوداً
DEFAULT_CONFIG = {
    "مرابح غفران للسياحة": {
        "sheet_name": "مرابح غفران للسياحة",
        "worksheet_name": "الورقة1",
        "authorized_user_ids": ["123456"],
        "column_types": {
            "التاريخ": "date",
            "تسمية": "text",
            "المربح": "number",
            "ملاحظات": "text"
        },
        "column_order": [
            "التاريخ",
            "تسمية",
            "المربح",
            "ملاحظات"
        ]
    }
}

class MockUpdate:
    """محاكاة كائن Update من التليجرام"""
    def __init__(self, user_id: int, message_text: str):
        self.effective_user = type('User', (), {'id': user_id})
        self.message = type('Message', (), {
            'text': message_text,
            'reply_text': lambda text, reply_markup=None: logger.info(f"Bot Response: {text}")
        })

class MockContext:
    """محاكاة كائن Context من التليجرام"""
    def __init__(self):
        self.user_data: Dict[str, Any] = {}

class TestBot:
    """اختبار وظائف البوت"""
    def __init__(self):
        self.context = MockContext()
        self.current_state = None
        self.config_file = 'test_sheets_config.json'
        self._create_test_config()
        self.sheets_config = self._load_config()
        self.required_fields = ['التاريخ', 'تسمية', 'المربح']
        self.optional_fields = ['ملاحظات']
        self.current_field_index = 0

    def _create_test_config(self):
        """إنشاء ملف إعدادات للاختبار"""
        if not os.path.exists(self.config_file):
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=4)
            logger.info(f"تم إنشاء ملف إعدادات الاختبار: {self.config_file}")

    def _load_config(self) -> dict:
        """تحميل إعدادات الجداول"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"خطأ في تحميل الإعدادات: {e}")
            return {}

    def _save_config(self, config: dict) -> bool:
        """حفظ إعدادات الجداول"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            logger.error(f"خطأ في حفظ الإعدادات: {e}")
            return False

    def cleanup(self):
        """تنظيف ملفات الاختبار"""
        try:
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
                logger.info(f"تم حذف ملف الإعدادات: {self.config_file}")
        except Exception as e:
            logger.error(f"خطأ في حذف ملف الإعدادات: {e}")

    async def add_user_to_sheet(self, sheet_name: str, user_id: str) -> str:
        """إضافة مستخدم إلى جدول"""
        config = self._load_config()
        if not config:
            return "خطأ: لا يمكن تحميل ملف الإعدادات. يرجى التحقق من وجود الملف وصلاحياته."

        if sheet_name not in config:
            available_sheets = ", ".join(config.keys())
            return f"خطأ: الجدول {sheet_name} غير موجود. الجداول المتاحة: {available_sheets}"

        if 'authorized_user_ids' not in config[sheet_name]:
            config[sheet_name]['authorized_user_ids'] = []

        if user_id in config[sheet_name]['authorized_user_ids']:
            return f"تنبيه: المستخدم {user_id} مضاف مسبقاً إلى الجدول {sheet_name}"

        config[sheet_name]['authorized_user_ids'].append(user_id)
        if self._save_config(config):
            self.sheets_config = config
            return f"تم بنجاح: إضافة المستخدم {user_id} إلى الجدول {sheet_name}"
        return "خطأ: فشل في حفظ الإعدادات. يرجى التحقق من صلاحيات الكتابة."

    async def remove_user_from_sheet(self, sheet_name: str, user_id: str) -> str:
        """إزالة مستخدم من جدول"""
        config = self._load_config()
        if not config:
            return "خطأ: لا يمكن تحميل ملف الإعدادات. يرجى التحقق من وجود الملف وصلاحياته."

        if sheet_name not in config:
            available_sheets = ", ".join(config.keys())
            return f"خطأ: الجدول {sheet_name} غير موجود. الجداول المتاحة: {available_sheets}"

        if 'authorized_user_ids' not in config[sheet_name]:
            return f"تنبيه: لا يوجد مستخدمين مصرح لهم في الجدول {sheet_name}"

        if user_id not in config[sheet_name]['authorized_user_ids']:
            return f"تنبيه: المستخدم {user_id} غير موجود في الجدول {sheet_name}"

        config[sheet_name]['authorized_user_ids'].remove(user_id)
        if self._save_config(config):
            self.sheets_config = config
            return f"تم بنجاح: إزالة المستخدم {user_id} من الجدول {sheet_name}"
        return "خطأ: فشل في حفظ الإعدادات. يرجى التحقق من صلاحيات الكتابة."

    async def simulate_command(self, user_id: int, command: str) -> Optional[str]:
        """محاكاة إرسال أمر للبوت"""
        logger.info(f"\nUser {user_id} sent: {command}")
        start_time = datetime.now()
        
        # إنشاء كائن التحديث المزيف
        update = MockUpdate(user_id, command)
        
        # معالجة الأمر
        response = await self._process_command(update, str(user_id))
        
        # حساب وتسجيل زمن الاستجابة
        response_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Response time: {response_time:.3f} seconds")
        
        return response

    async def _process_command(self, update: MockUpdate, user_id: str) -> str:
        """معالجة الأمر وإرجاع الاستجابة"""
        command = update.message.text
        logger.info(f"Processing {'/start' if command.startswith('/') else 'message'}: {command}")

        # التحقق من صلاحية المستخدم
        if not self._is_user_authorized(user_id) and command != "/start":
            return "عذراً، ليس لديك صلاحية للوصول إلى هذا البوت. يرجى التواصل مع المسؤول."

        # معالجة الأوامر
        if command == "/start":
            response = self._handle_start()
        elif command == "/skip":
            response = self._handle_skip()
        elif command.isdigit():
            response = self._handle_number(command)
        else:
            response = self._handle_text(command)

        logger.info(response)
        return response

    def _is_user_authorized(self, user_id: str) -> bool:
        """التحقق من صلاحية المستخدم"""
        for sheet_config in self.sheets_config.values():
            if user_id in sheet_config.get('authorized_user_ids', []):
                return True
        return False

    def _handle_start(self) -> str:
        """معالجة أمر البداية"""
        logger.info("Processing /start command")
        self.context.user_data.clear()
        self.current_field_index = 0
        
        # عرض الجداول المتاحة
        available_sheets = list(self.sheets_config.keys())
        if not available_sheets:
            msg = "لا توجد جداول متاحة"
            logger.warning(msg)
            return msg
        
        sheets_list = "\n".join(f"{i+1}. {sheet}" for i, sheet in enumerate(available_sheets))
        msg = f"الجداول المتاحة:\n{sheets_list}\nالرجاء اختيار رقم الجدول:"
        logger.info(msg)
        self.current_state = "choosing_sheet"
        return msg

    def _handle_skip(self) -> str:
        """معالجة أمر التخطي"""
        logger.info("Processing /skip command")
        if self.current_state == "entering_data" and self.current_field_index >= len(self.required_fields):
            field = self.optional_fields[self.current_field_index - len(self.required_fields)]
            self.context.user_data[field] = ""
            self.current_field_index += 1
            
            msg = f"تم تخطي الحقل: {field}"
            if self.current_field_index >= len(self.required_fields) + len(self.optional_fields):
                msg += "\nتم إدخال جميع البيانات بنجاح!"
                self.current_state = None
            else:
                next_field = self.get_next_field()
                msg += f"\nالرجاء إدخال {next_field}:"
            
            logger.info(msg)
            return msg
        else:
            msg = "لا يمكن تخطي هذا الحقل لأنه إجباري"
            logger.warning(msg)
            return msg

    def get_next_field(self) -> str:
        """الحصول على الحقل التالي المطلوب"""
        if self.current_field_index < len(self.required_fields):
            return self.required_fields[self.current_field_index]
        elif self.current_field_index < len(self.required_fields) + len(self.optional_fields):
            return self.optional_fields[self.current_field_index - len(self.required_fields)]
        return ""

    def _handle_number(self, command: str) -> str:
        """معالجة الأمر الرقمي"""
        logger.info(f"Processing number: {command}")
        if self.current_state == "choosing_sheet":
            try:
                sheet_index = int(command) - 1
                available_sheets = list(self.sheets_config.keys())
                if 0 <= sheet_index < len(available_sheets):
                    selected_sheet = available_sheets[sheet_index]
                    self.context.user_data['selected_sheet'] = selected_sheet
                    self.current_state = "entering_data"
                    next_field = self.get_next_field()
                    msg = f"تم اختيار الجدول: {selected_sheet}\nالرجاء إدخال {next_field}:"
                    logger.info(msg)
                    return msg
                else:
                    msg = "رقم الجدول غير صحيح"
                    logger.warning(msg)
                    return msg
            except ValueError:
                msg = "الرجاء إدخال رقم صحيح"
                logger.error(msg)
                return msg
        else:
            msg = "الأمر غير صالح في هذه الحالة"
            logger.warning(msg)
            return msg

    def _handle_text(self, command: str) -> str:
        """معالجة الأمر النصي"""
        logger.info(f"Processing text: {command}")
        if self.current_state == "entering_data":
            current_field = self.get_next_field()
            if not current_field:
                msg = "تم إدخال جميع البيانات"
                logger.info(msg)
                return msg

            self.context.user_data[current_field] = command
            self.current_field_index += 1
            
            if self.current_field_index >= len(self.required_fields) + len(self.optional_fields):
                msg = "تم إدخال جميع البيانات بنجاح!"
                logger.info(f"All data entered: {self.context.user_data}")
                self.current_state = None
            else:
                next_field = self.get_next_field()
                msg = f"تم حفظ {current_field}\nالرجاء إدخال {next_field}:"
                if self.current_field_index >= len(self.required_fields):
                    msg += " (اختياري - يمكنك استخدام /skip للتخطي)"
            
            logger.info(msg)
            return msg
        else:
            msg = "الأمر غير صالح في هذه الحالة"
            logger.warning(msg)
            return msg

async def run_test():
    """تشغيل الاختبار"""
    bot = TestBot()
    test_user_id = "123456"
    new_user_id = "6758582992"
    sheet_name = list(bot.sheets_config.keys())[0]  # أول جدول متاح

    # اختبار تسلسل العمليات
    logger.info("\n=== بدء اختبار إدارة المستخدمين ===")

    # اختبار 1: إضافة مستخدم جديد
    logger.info("\n--- اختبار إضافة مستخدم جديد ---")
    result = await bot.add_user_to_sheet(sheet_name, new_user_id)
    logger.info(f"نتيجة إضافة المستخدم: {result}")

    # اختبار 2: التحقق من وصول المستخدم الجديد
    logger.info("\n--- اختبار وصول المستخدم الجديد ---")
    response = await bot.simulate_command(int(new_user_id), "/start")
    logger.info(f"استجابة البوت للمستخدم الجديد: {response}")

    # اختبار 3: إزالة المستخدم
    logger.info("\n--- اختبار إزالة المستخدم ---")
    result = await bot.remove_user_from_sheet(sheet_name, new_user_id)
    logger.info(f"نتيجة إزالة المستخدم: {result}")

    # اختبار 4: التحقق من عدم وصول المستخدم بعد إزالته
    logger.info("\n--- اختبار عدم وصول المستخدم بعد إزالته ---")
    response = await bot.simulate_command(int(new_user_id), "/start")
    logger.info(f"استجابة البوت بعد إزالة المستخدم: {response}")

    # اختبار 5: إعادة إضافة المستخدم
    logger.info("\n--- اختبار إعادة إضافة المستخدم ---")
    result = await bot.add_user_to_sheet(sheet_name, new_user_id)
    logger.info(f"نتيجة إعادة إضافة المستخدم: {result}")
    response = await bot.simulate_command(int(new_user_id), "/start")
    logger.info(f"استجابة البوت بعد إعادة إضافة المستخدم: {response}")

    # اختبار تسلسل العمليات العادية
    test_sequence = [
        ("/start", "بدء محادثة جديدة"),
        ("1", "اختيار الجدول الأول"),
        ("2024-01-12", "إدخال التاريخ"),
        ("اختبار", "إدخال التسمية"),
        ("100", "إدخال المربح"),
        ("/skip", "تخطي الملاحظات"),
    ]

    logger.info("\n=== اختبار العمليات العادية ===")
    total_time = 0
    
    for command, description in test_sequence:
        logger.info(f"\n--- اختبار: {description} ---")
        start_time = datetime.now()
        response = await bot.simulate_command(int(test_user_id), command)
        command_time = (datetime.now() - start_time).total_seconds()
        total_time += command_time
        
        logger.info(f"الأمر: {command}")
        logger.info(f"الاستجابة: {response}")
        logger.info(f"زمن الاستجابة: {command_time:.3f} ثانية")
        
        await asyncio.sleep(0.1)

    logger.info(f"\n=== نتائج الاختبار ===")
    logger.info(f"عدد الأوامر: {len(test_sequence)}")
    logger.info(f"إجمالي الوقت: {total_time:.2f} ثانية")
    logger.info(f"متوسط زمن الاستجابة: {total_time/len(test_sequence):.3f} ثانية لكل أمر")

    bot.cleanup()

if __name__ == '__main__':
    asyncio.run(run_test())
