from flask import Flask, render_template, request, jsonify
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio
from telegram import Bot
import config

app = Flask(__name__)

# تهيئة Google Sheets
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]
CREDENTIALS_FILE = 'credentials.json'

# إنشاء كائن البوت
bot = Bot(token=config.TELEGRAM_TOKEN)

def get_gspread_client():
    """إنشاء اتصال مع Google Sheets"""
    try:
        if not os.path.exists(CREDENTIALS_FILE):
            print(f"خطأ: ملف الاعتماد '{CREDENTIALS_FILE}' غير موجود")
            return None, "ملف الاعتماد (credentials.json) غير موجود. يرجى التأكد من وجود الملف في المجلد الصحيح"
        
        try:
            client = gspread.service_account(filename=CREDENTIALS_FILE)
            return client, None
        except ValueError as e:
            error_msg = str(e)
            if "No private key" in error_msg:
                return None, "ملف الاعتماد غير صالح: المفتاح الخاص مفقود"
            elif "No client email" in error_msg:
                return None, "ملف الاعتماد غير صالح: البريد الإلكتروني للحساب مفقود"
            else:
                return None, f"ملف الاعتماد غير صالح: {error_msg}"
                
    except Exception as e:
        error_msg = str(e)
        if "invalid_grant" in error_msg:
            return None, "فشل التوثيق: تأكد من تفعيل Google Sheets API وصلاحية ملف الاعتماد"
        elif "invalid_client" in error_msg:
            return None, "خطأ في حساب الخدمة: تأكد من إعداد المشروع بشكل صحيح في Google Cloud Console"
        else:
            return None, f"خطأ في الاتصال بـ Google Sheets: {error_msg}"

def verify_sheet_exists(sheet_name):
    """التحقق من وجود الجدول"""
    try:
        gc, error = get_gspread_client()
        if error:
            return None, error
        
        try:
            gc.open(sheet_name)
            return True, None
        except gspread.exceptions.SpreadsheetNotFound:
            return False, f"لم يتم العثور على جدول باسم '{sheet_name}'. تأكد من:\n1. كتابة اسم الجدول بشكل صحيح\n2. مشاركة الجدول مع حساب الخدمة: {gc.auth.service_account_email}"
        except gspread.exceptions.APIError as e:
            error_msg = str(e)
            if "PERMISSION_DENIED" in error_msg:
                return None, f"تم رفض الوصول للجدول. تأكد من مشاركة الجدول مع حساب الخدمة: {gc.auth.service_account_email}"
            elif "RESOURCE_EXHAUSTED" in error_msg:
                return None, "تم تجاوز حد الطلبات المسموح به. حاول مرة أخرى بعد قليل"
            else:
                return None, f"خطأ في API من Google Sheets: {error_msg}"
        
    except Exception as e:
        return None, f"خطأ غير متوقع: {str(e)}"

def get_worksheet_names(sheet_name):
    """الحصول على قائمة أسماء الصفحات في الجدول"""
    try:
        gc, error = get_gspread_client()
        if error:
            return None, error
        
        try:
            spreadsheet = gc.open(sheet_name)
            worksheets = spreadsheet.worksheets()
            if not worksheets:
                return None, "الجدول لا يحتوي على أي أوراق عمل"
            return [worksheet.title for worksheet in worksheets], None
        except gspread.exceptions.SpreadsheetNotFound:
            return None, f"لم يتم العثور على جدول باسم '{sheet_name}'"
        except gspread.exceptions.APIError as e:
            error_msg = str(e)
            if "PERMISSION_DENIED" in error_msg:
                return None, "تم رفض الوصول للجدول. تأكد من الصلاحيات"
            else:
                return None, f"خطأ في API من Google Sheets: {error_msg}"
            
    except Exception as e:
        return None, f"خطأ غير متوقع: {str(e)}"

def get_sheet_columns(sheet_name, worksheet_name):
    """الحصول على أسماء الأعمدة في الصفحة"""
    try:
        gc, error = get_gspread_client()
        if error:
            return None, error
        
        try:
            spreadsheet = gc.open(sheet_name)
            worksheet = spreadsheet.worksheet(worksheet_name)
            columns = worksheet.row_values(1)
            if not columns:
                return None, "الصف الأول في ورقة العمل فارغ. يجب أن يحتوي على أسماء الأعمدة"
            return columns, None
        except gspread.exceptions.SpreadsheetNotFound:
            return None, f"لم يتم العثور على جدول باسم '{sheet_name}'"
        except gspread.exceptions.WorksheetNotFound:
            return None, f"لم يتم العثور على ورقة العمل '{worksheet_name}'"
        except gspread.exceptions.APIError as e:
            error_msg = str(e)
            if "PERMISSION_DENIED" in error_msg:
                return None, "تم رفض الوصول للجدول. تأكد من الصلاحيات"
            else:
                return None, f"خطأ في API من Google Sheets: {error_msg}"
            
    except Exception as e:
        return None, f"خطأ غير متوقع: {str(e)}"

def load_config():
    try:
        with open('sheets_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

def save_config(config):
    try:
        with open('sheets_config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

async def notify_users(old_config, new_config, sheet_name):
    """إشعار المستخدمين عند إضافتهم أو حذفهم من الجدول"""
    old_users = set(old_config.get(sheet_name, {}).get('authorized_user_ids', []))
    new_users = set(new_config.get(sheet_name, {}).get('authorized_user_ids', []))
    
    # المستخدمون الجدد
    added_users = new_users - old_users
    # المستخدمون المحذوفون
    removed_users = old_users - new_users
    
    # إرسال إشعارات للمستخدمين الجدد
    for user_id in added_users:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"تمت إضافتك إلى جدول '{sheet_name}'. أرسل /start لعرض الجداول المتاحة لك."
            )
        except Exception as e:
            print(f"خطأ في إرسال إشعار للمستخدم {user_id}: {str(e)}")
    
    # إرسال إشعارات للمستخدمين المحذوفين
    for user_id in removed_users:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"تم إلغاء وصولك إلى جدول '{sheet_name}'."
            )
        except Exception as e:
            print(f"خطأ في إرسال إشعار للمستخدم {user_id}: {str(e)}")

@app.route('/')
def index():
    config = load_config()
    return render_template('index.html', config=config)

@app.route('/verify_sheet', methods=['POST'])
def verify_sheet():
    try:
        data = request.get_json()
        sheet_name = data['sheet_name']
        
        # التحقق من عدم وجود الجدول في الإعدادات
        config = load_config()
        if sheet_name in config:
            return jsonify({
                "status": "error",
                "message": "الجدول موجود بالفعل في الإعدادات"
            }), 400
        
        # التحقق من وجود الجدول في Google Sheets
        exists, error = verify_sheet_exists(sheet_name)
        if error:
            return jsonify({
                "status": "error",
                "message": error,
                "details": {
                    "type": "auth_error" if "ملف الاعتماد" in error or "فشل التوثيق" in error else "access_error",
                    "credentials_file_exists": os.path.exists(CREDENTIALS_FILE)
                }
            }), 500 if exists is None else 404
            
        # جلب قائمة أوراق العمل
        sheets, error = get_worksheet_names(sheet_name)
        if error:
            return jsonify({
                "status": "error",
                "message": error
            }), 500
            
        # جلب أسماء الأعمدة من الورقة الأولى
        first_sheet = sheets[0] if sheets else None
        if first_sheet:
            columns, error = get_sheet_columns(sheet_name, first_sheet)
            if error:
                return jsonify({
                    "status": "error",
                    "message": error
                }), 500
        else:
            columns = []
            
        return jsonify({
            "status": "success",
            "sheets": sheets,
            "columns": columns
        })
        
    except KeyError:
        return jsonify({
            "status": "error",
            "message": "البيانات المرسلة غير مكتملة"
        }), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"خطأ غير متوقع: {str(e)}"
        }), 500

@app.route('/add_sheet', methods=['POST'])
def add_sheet():
    try:
        data = request.get_json()
        sheet_name = data.get('sheet_name')
        worksheet_name = data.get('worksheet_name')
        column_types = data.get('column_types', {})
        required_columns = data.get('required_columns', [])
        
        if not sheet_name or not worksheet_name:
            return jsonify({
                "status": "error",
                "message": "البيانات المرسلة غير مكتملة"
            }), 400
            
        # التحقق من عدم وجود الجدول في الإعدادات
        config = load_config()
        if sheet_name in config:
            return jsonify({
                "status": "error",
                "message": "الجدول موجود بالفعل في الإعدادات"
            }), 400
            
        # جلب أسماء الأعمدة
        columns, error = get_sheet_columns(sheet_name, worksheet_name)
        if error:
            return jsonify({
                "status": "error",
                "message": error
            }), 500
            
        if not columns:
            columns = []
            
        # إنشاء إعدادات الجدول
        sheet_config = {
            "sheet_name": sheet_name,
            "worksheet_name": worksheet_name,
            "authorized_user_id": "",
            "authorized_user_ids": [],
            "column_types": column_types or {},
            "column_order": columns,
            "date_options": {},
            "required_columns": required_columns or [],  # قائمة الحقول الإجبارية
            "optional_columns": [col for col in columns if col not in required_columns]  # قائمة الحقول الاختيارية
        }
        
        # تعيين النوع الافتراضي لكل عمود كنص إذا لم يتم تحديده
        for column in columns:
            if column not in sheet_config["column_types"]:
                sheet_config["column_types"][column] = "text"
            
        # حفظ الإعدادات
        config[sheet_name] = sheet_config
        if save_config(config):
            return jsonify({
                "status": "success",
                "message": "تم إضافة الجدول بنجاح",
                "config": sheet_config
            })
        else:
            return jsonify({
                "status": "error",
                "message": "حدث خطأ أثناء حفظ الإعدادات"
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"خطأ غير متوقع: {str(e)}"
        }), 500

@app.route('/get_sheet_config/<sheet_name>')
def get_sheet_config(sheet_name):
    config = load_config()
    if sheet_name in config:
        return jsonify(config[sheet_name])
    return jsonify({"error": "Sheet not found"}), 404

@app.route('/save', methods=['POST'])
def save():
    try:
        data = request.get_json()
        sheet_name = data.get('sheet_name')
        
        if not sheet_name:
            return jsonify({'success': False, 'error': 'لم يتم تحديد اسم الجدول'})
        
        # قراءة الإعدادات الحالية
        with open('sheets_config.json', 'r', encoding='utf-8') as f:
            old_config = json.load(f)
        
        # نسخة من الإعدادات القديمة
        new_config = old_config.copy()
        
        # تحديث إعدادات الجدول
        if sheet_name in new_config:
            new_config[sheet_name].update({
                'worksheet_name': data.get('worksheet_name', 'Sheet1'),
                'authorized_user_ids': data.get('authorized_user_ids', []),
                'column_types': data.get('column_types', {}),
                'column_order': data.get('column_order', []),
                'date_options': data.get('date_options', {}),
                'required_columns': data.get('required_columns', []),
                'optional_columns': data.get('optional_columns', [])
            })
            
            # حفظ الإعدادات
            with open('sheets_config.json', 'w', encoding='utf-8') as f:
                json.dump(new_config, f, ensure_ascii=False, indent=4)
            
            # إشعار المستخدمين بالتغييرات
            asyncio.run(notify_users(old_config, new_config, sheet_name))
            
            return jsonify({'success': True, 'config': new_config})
        else:
            return jsonify({'success': False, 'error': 'الجدول غير موجود'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete_sheet', methods=['POST'])
def delete_sheet():
    try:
        data = request.get_json()
        sheet_name = data.get('sheet_name')
        
        if not sheet_name:
            return jsonify({'success': False, 'error': 'لم يتم تحديد اسم الجدول'})
        
        # قراءة الإعدادات الحالية
        with open('sheets_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # حذف الجدول من الإعدادات
        if sheet_name in config:
            del config[sheet_name]
            
            # حفظ الإعدادات
            with open('sheets_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            
            return jsonify({'success': True, 'config': config})
        else:
            return jsonify({'success': False, 'error': 'الجدول غير موجود'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete_sheet/<sheet_name>', methods=['DELETE'])
def delete_sheet_by_name(sheet_name):
    try:
        config = load_config()
        if sheet_name in config:
            del config[sheet_name]
            if save_config(config):
                return jsonify({"status": "success", "message": "تم حذف الجدول بنجاح"})
            else:
                return jsonify({"status": "error", "message": "حدث خطأ أثناء حذف الجدول"}), 500
        else:
            return jsonify({"status": "error", "message": "الجدول غير موجود"}), 404
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
