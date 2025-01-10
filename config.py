from dotenv import load_dotenv
import os

load_dotenv()

# معلومات Google Sheets
GOOGLE_SHEETS_CREDENTIALS_FILE = 'credentials.json'

# معلومات Telegram
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# معرفات جداول Google
SPREADSHEET_NAME = "المشتريات"  # اسم جدول المشتريات
HONEY_SHEET_NAME = "عسل عين"  # اسم جدول عسل عين
NEW_SHEET_NAME = "الجدول الجديد"  # اسم الجدول الجديد

# Admin User ID
ADMIN_USER_ID = "773012141"  # معرف المستخدم المسؤول
