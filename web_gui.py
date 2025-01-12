from flask import Flask, render_template, request, jsonify
import json
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.errors import HttpError

app = Flask(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'credentials.json'

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

def get_sheets_service():
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=credentials)
        return service
    except Exception as e:
        print(f"Error getting sheets service: {e}")
        return None

def get_spreadsheet_metadata(spreadsheet_id):
    try:
        print(f"\n=== بداية جلب معلومات الجدول ===")
        print(f"معرف الجدول: {spreadsheet_id}")
        
        service = get_sheets_service()
        if not service:
            print("فشل في الحصول على خدمة Sheets")
            return None, None

        # جلب معلومات الجدول
        print("جلب معلومات الجدول...")
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        
        # جلب قائمة أوراق العمل
        sheets = spreadsheet.get('sheets', [])
        sheet_names = [sheet['properties']['title'] for sheet in sheets]
        
        print(f"تم العثور على الجدول: {spreadsheet['properties']['title']}")
        print(f"أوراق العمل: {sheet_names}")
        
        return spreadsheet['properties']['title'], sheet_names
        
    except HttpError as e:
        print(f"خطأ HTTP: {e.resp.status} - {str(e)}")
        if e.resp.status == 404:
            return None, None
        raise
    except Exception as e:
        print(f"خطأ غير متوقع: {str(e)}")
        return None, None
    finally:
        print("=== نهاية جلب معلومات الجدول ===\n")

def get_sheet_columns(spreadsheet_id, worksheet_name):
    try:
        print(f"\n=== بداية جلب الأعمدة ===")
        print(f"جلب أعمدة الورقة: {worksheet_name}")
        
        service = get_sheets_service()
        if not service:
            print("فشل في الحصول على خدمة Sheets")
            return None

        range_name = f"{worksheet_name}!1:1"
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name).execute()
        values = result.get('values', [])
        
        columns = values[0] if values else []
        print(f"تم العثور على الأعمدة: {columns}")
        return columns
        
    except Exception as e:
        print(f"خطأ في جلب الأعمدة: {str(e)}")
        return None
    finally:
        print("=== نهاية جلب الأعمدة ===\n")

@app.route('/')
def index():
    config = load_config()
    return render_template('index.html', config=config)

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
        config = load_config()
        sheet_name = data['sheet_name']
        
        if sheet_name in config:
            # تحديث الإعدادات الأساسية
            config[sheet_name].update({
                'sheet_name': sheet_name,
                'worksheet_name': data['worksheet_name'],
                'authorized_user_id': data['authorized_user_ids'][0] if data['authorized_user_ids'] else '',
                'authorized_user_ids': data['authorized_user_ids'][1:] if len(data['authorized_user_ids']) > 1 else [],
                'column_types': data['column_types'],
                'column_order': data['column_order']
            })
            
            # تحديث خيارات التاريخ
            if 'date_options' in data:
                config[sheet_name]['date_options'] = data['date_options']
            else:
                config[sheet_name]['date_options'] = {}
            
            # الحفاظ على الأعمدة المطلوبة والاختيارية إذا كانت موجودة
            if 'required_columns' in config[sheet_name]:
                config[sheet_name]['required_columns'] = data.get('required_columns', config[sheet_name]['required_columns'])
            if 'optional_columns' in config[sheet_name]:
                config[sheet_name]['optional_columns'] = data.get('optional_columns', config[sheet_name]['optional_columns'])
            
            if save_config(config):
                return jsonify({"status": "success", "message": "تم حفظ التغييرات بنجاح"})
            else:
                return jsonify({"status": "error", "message": "حدث خطأ أثناء حفظ التغييرات"}), 500
        else:
            return jsonify({"status": "error", "message": "الجدول غير موجود"}), 404
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/add_sheet', methods=['POST'])
def add_sheet():
    try:
        data = request.get_json()
        config = load_config()
        sheet_name = data['sheet_name']
        worksheet_name = data['worksheet_name']
        spreadsheet_id = data.get('spreadsheet_id')
        
        if sheet_name in config:
            return jsonify({"status": "error", "message": "الجدول موجود بالفعل"}), 400
        
        # جلب أسماء الأعمدة من Google Sheets
        if spreadsheet_id:
            columns = get_sheet_columns(spreadsheet_id, worksheet_name)
            if columns is None:
                return jsonify({"status": "error", "message": "حدث خطأ أثناء جلب أسماء الأعمدة"}), 500
                
            # إنشاء column_types تلقائياً (نوع نص افتراضي)
            column_types = {col: "text" for col in columns}
            column_order = columns
        else:
            column_types = {}
            column_order = []
            
        config[sheet_name] = {
            'sheet_name': sheet_name,
            'worksheet_name': worksheet_name,
            'spreadsheet_id': spreadsheet_id,
            'authorized_user_id': '',
            'authorized_user_ids': [],
            'column_types': column_types,
            'column_order': column_order,
            'date_options': {}
        }
        
        if save_config(config):
            return jsonify({
                "status": "success", 
                "message": "تم إضافة الجدول بنجاح",
                "columns": column_order
            })
        else:
            return jsonify({"status": "error", "message": "حدث خطأ أثناء إضافة الجدول"}), 500
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/delete_sheet/<sheet_name>', methods=['DELETE'])
def delete_sheet(sheet_name):
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
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/verify_sheet', methods=['POST'])
def verify_sheet():
    try:
        data = request.get_json()
        sheet_name = data['sheet_name']
        spreadsheet_id = data['spreadsheet_id']
        
        print(f"\n=== بداية التحقق من الجدول ===")
        print(f"اسم الجدول: {sheet_name}")
        print(f"معرف الجدول: {spreadsheet_id}")
        
        # التحقق من عدم وجود الجدول في الإعدادات
        config = load_config()
        if sheet_name in config:
            print("الجدول موجود بالفعل في الإعدادات")
            return jsonify({
                "status": "error",
                "message": "الجدول موجود بالفعل في الإعدادات"
            }), 400
        
        # التحقق من وجود الجدول في Google Sheets وجلب معلوماته
        service = get_sheets_service()
        if not service:
            return jsonify({
                "status": "error",
                "message": "فشل في الاتصال بخدمة Google Sheets"
            }), 500

        try:
            # محاولة الوصول للجدول
            spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets = spreadsheet.get('sheets', [])
            sheet_names = [sheet['properties']['title'] for sheet in sheets]
            
            if not sheet_names:
                return jsonify({
                    "status": "error",
                    "message": "الجدول فارغ - لا يحتوي على أي ورقة عمل"
                }), 400

            # جلب أسماء الأعمدة من الورقة الأولى
            first_sheet = sheet_names[0]
            range_name = f"{first_sheet}!1:1"
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=range_name).execute()
            columns = result.get('values', [[]])[0]

            return jsonify({
                "status": "success",
                "sheets": sheet_names,
                "columns": columns
            })

        except Exception as e:
            print(f"خطأ في الوصول للجدول: {str(e)}")
            return jsonify({
                "status": "error",
                "message": "لم يتم العثور على الجدول. تأكد من المعرف وصلاحيات الوصول"
            }), 404
            
    except Exception as e:
        print(f"خطأ غير متوقع: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        print("=== نهاية التحقق من الجدول ===\n")

if __name__ == '__main__':
    app.run(debug=True, port=5000)
