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
        service = get_sheets_service()
        if not service:
            return None, None

        # جلب معلومات الجدول
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        
        # جلب قائمة أوراق العمل
        sheets = spreadsheet.get('sheets', [])
        sheet_names = [sheet['properties']['title'] for sheet in sheets]
        
        return spreadsheet['properties']['title'], sheet_names
        
    except HttpError as e:
        if e.resp.status == 404:
            return None, None
        raise
    except Exception as e:
        print(f"Error getting spreadsheet metadata: {e}")
        return None, None

def get_sheet_columns(spreadsheet_id, worksheet_name):
    try:
        service = get_sheets_service()
        if not service:
            return None

        range_name = f"{worksheet_name}!1:1"
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name).execute()
        values = result.get('values', [])
        
        return values[0] if values else []
        
    except Exception as e:
        print(f"Error getting sheet columns: {e}")
        return None

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
                'authorized_user_id': data['authorized_user_ids'][0],
                'authorized_user_ids': data['authorized_user_ids'][1:],
                'column_types': data['column_types'],
                'column_order': data['column_order'],
                'date_options': data['date_options']
            })
            
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
        
        # التحقق من عدم وجود الجدول في الإعدادات
        config = load_config()
        if sheet_name in config:
            return jsonify({
                "status": "error",
                "message": "الجدول موجود بالفعل في الإعدادات"
            }), 400
        
        # التحقق من وجود الجدول في Google Sheets وجلب معلوماته
        title, sheet_names = get_spreadsheet_metadata(spreadsheet_id)
        if title is None:
            return jsonify({
                "status": "error",
                "message": "لم يتم العثور على جدول البيانات. تأكد من المعرف وصلاحيات الوصول"
            }), 404
            
        # جلب أسماء الأعمدة من الورقة الأولى
        first_sheet = sheet_names[0] if sheet_names else None
        if first_sheet:
            columns = get_sheet_columns(spreadsheet_id, first_sheet)
            if columns is None:
                return jsonify({
                    "status": "error",
                    "message": "حدث خطأ أثناء جلب أسماء الأعمدة"
                }), 500
        else:
            columns = []
            
        return jsonify({
            "status": "success",
            "title": title,
            "sheets": sheet_names,
            "columns": columns
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
