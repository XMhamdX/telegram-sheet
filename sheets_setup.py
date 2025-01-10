import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import config

class SheetsSetup:
    def __init__(self):
        self.gc = gspread.service_account(filename=config.GOOGLE_SHEETS_CREDENTIALS_FILE)
        self.config_file = 'sheets_config.json'
        self.current_config = {}
        self.load_config()

    def load_config(self):
        """تحميل إعدادات الجداول من الملف"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.current_config = json.load(f)
        else:
            self.current_config = {}

    def save_config(self):
        """حفظ إعدادات الجداول إلى الملف"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.current_config, f, ensure_ascii=False, indent=4)

    def verify_sheet_exists(self, sheet_name: str) -> bool:
        """التحقق من وجود الجدول"""
        try:
            self.gc.open(sheet_name)
            return True
        except:
            return False

    def get_worksheet_names(self, sheet_name: str) -> list:
        """الحصول على قائمة أسماء الصفحات في الجدول"""
        try:
            spreadsheet = self.gc.open(sheet_name)
            return [worksheet.title for worksheet in spreadsheet.worksheets()]
        except:
            return []

    def get_sheet_columns(self, sheet_name: str, worksheet_name: str) -> list:
        """الحصول على أسماء الأعمدة في الصفحة"""
        try:
            spreadsheet = self.gc.open(sheet_name)
            worksheet = spreadsheet.worksheet(worksheet_name)
            return worksheet.row_values(1)  # نفترض أن الصف الأول يحتوي على أسماء الأعمدة
        except:
            return []

    def setup_new_sheet(self):
        """إعداد جدول جديد"""
        print("\n=== إعداد جدول جديد ===")
        
        # طلب اسم الجدول
        sheet_name = safe_input("أدخل اسم الجدول في Google Sheets: ")
        if not self.verify_sheet_exists(sheet_name):
            print("خطأ: الجدول غير موجود!")
            return
        
        # عرض الصفحات المتاحة
        worksheets = self.get_worksheet_names(sheet_name)
        if not worksheets:
            print("خطأ: لا توجد صفحات في الجدول!")
            return
        
        print("\nالصفحات المتاحة:")
        for i, ws in enumerate(worksheets, 1):
            print(f"{i}. {ws}")
        
        # اختيار الصفحة
        try:
            ws_index = int(safe_input("\nاختر رقم الصفحة: ")) - 1
            worksheet_name = worksheets[ws_index]
        except (ValueError, IndexError):
            print("خطأ: اختيار غير صالح!")
            return
        
        # الحصول على الأعمدة
        columns = self.get_sheet_columns(sheet_name, worksheet_name)
        if not columns:
            print("خطأ: لا توجد أعمدة في الصفحة!")
            return
        
        # إعداد أنواع الأعمدة
        column_types = {}
        date_options = {}
        
        print("\nأنواع البيانات المتاحة:")
        print("1. نص")
        print("2. رقم")
        print("3. تاريخ")
        
        for col in columns:
            while True:
                try:
                    print(f"\nالعمود: {col}")
                    type_choice = int(safe_input("اختر نوع البيانات (1-3): "))
                    if type_choice == 1:
                        column_types[col] = "text"
                        break
                    elif type_choice == 2:
                        column_types[col] = "number"
                        break
                    elif type_choice == 3:
                        column_types[col] = "date"
                        # خيارات إضافية للتاريخ
                        include_time = safe_input("هل تريد تضمين الوقت؟ (نعم/لا): ").lower() == 'نعم'
                        auto_date = safe_input("هل تريد تعيين التاريخ تلقائياً؟ (نعم/لا): ").lower() == 'نعم'
                        date_options[col] = {
                            'include_time': include_time,
                            'auto': auto_date
                        }
                        break
                    else:
                        print("خطأ: اختيار غير صالح!")
                except ValueError:
                    print("خطأ: الرجاء إدخال رقم!")
        
        # طلب معرف تيليجرام
        telegram_id = safe_input("\nأدخل معرف تيليجرام للمستخدم المصرح له: ")
        
        # حفظ الإعدادات
        sheet_config = {
            'sheet_name': sheet_name,
            'worksheet_name': worksheet_name,
            'column_types': column_types,
            'date_options': date_options,
            'authorized_user_id': telegram_id
        }
        
        self.current_config[sheet_name] = sheet_config
        self.save_config()
        print("\nتم حفظ الإعدادات بنجاح!")

    def list_sheets(self):
        """عرض قائمة الجداول المعدة"""
        print("\n=== الجداول المعدة ===")
        if not self.current_config:
            print("لا توجد جداول معدة حتى الآن!")
            return
        
        for sheet_name, config in self.current_config.items():
            print(f"\nالجدول: {sheet_name}")
            print(f"الصفحة: {config['worksheet_name']}")
            print("الأعمدة:")
            for col, col_type in config['column_types'].items():
                print(f"- {col}: {col_type}")
                if col_type == 'date' and col in config['date_options']:
                    opts = config['date_options'][col]
                    print(f"  * تضمين الوقت: {'نعم' if opts['include_time'] else 'لا'}")
                    print(f"  * تلقائي: {'نعم' if opts['auto'] else 'لا'}")
            print(f"المستخدم المصرح له: {config['authorized_user_id']}")

    def remove_sheet(self):
        """إزالة جدول من الإعدادات"""
        print("\n=== إزالة جدول ===")
        if not self.current_config:
            print("لا توجد جداول معدة حتى الآن!")
            return
        
        print("\nالجداول المتاحة:")
        sheets = list(self.current_config.keys())
        for i, sheet in enumerate(sheets, 1):
            print(f"{i}. {sheet}")
        
        try:
            choice = int(safe_input("\nاختر رقم الجدول لإزالته: ")) - 1
            sheet_to_remove = sheets[choice]
            del self.current_config[sheet_to_remove]
            self.save_config()
            print(f"\nتم إزالة الجدول {sheet_to_remove} بنجاح!")
        except (ValueError, IndexError):
            print("خطأ: اختيار غير صالح!")

def safe_input(prompt):
    """قراءة المدخلات بشكل آمن"""
    print(prompt, end='', flush=True)
    try:
        return input()
    except EOFError:
        return ''

def main():
    # تعيين ترميز وحدة الإدخال والإخراج
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    
    setup = SheetsSetup()
    while True:
        print("\n=== قائمة الخيارات ===")
        print("1. إعداد جدول جديد")
        print("2. عرض الجداول المعدة")
        print("3. إزالة جدول")
        print("4. خروج")
        
        try:
            choice = int(safe_input("\nاختر رقم العملية: "))
            if choice == 1:
                setup.setup_new_sheet()
            elif choice == 2:
                setup.list_sheets()
            elif choice == 3:
                setup.remove_sheet()
            elif choice == 4:
                print("\nشكراً لك!")
                break
            else:
                print("خطأ: اختيار غير صالح!")
        except ValueError:
            print("خطأ: الرجاء إدخال رقم!")

if __name__ == '__main__':
    main()
