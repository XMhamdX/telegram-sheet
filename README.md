# بوت تليجرام لتسجيل المشتريات في Google Sheets

هذا البوت يساعدك في تسجيل مشترياتك مباشرة في Google Sheets عبر تليجرام.

## المتطلبات
1. Python 3.7 أو أحدث
2. حساب Google Cloud مع تفعيل Google Sheets API
3. بوت تليجرام (يمكن إنشاؤه عبر @BotFather)

## خطوات الإعداد

1. قم بتثبيت المتطلبات:
```bash
pip install -r requirements.txt
```

2. إعداد Google Sheets:
   - قم بإنشاء مشروع في Google Cloud Console
   - قم بتفعيل Google Sheets API
   - قم بإنشاء Service Account وتحميل ملف credentials.json
   - ضع ملف credentials.json في نفس مجلد المشروع

3. إعداد ملف .env:
   - قم بتعديل ملف .env وأضف توكن البوت الخاص بك

4. إعداد جدول البيانات:
   - قم بإنشاء ملف Google Sheets جديد
   - شارك الملف مع عنوان البريد الإلكتروني الموجود في ملف credentials.json
   - قم بتعديل اسم الملف في config.py

## تشغيل البوت
```bash
python bot.py
```

## كيفية الاستخدام
1. ابدأ محادثة مع البوت عبر /start
2. أرسل اسم المنتج
3. أرسل السعر
4. أرسل الملاحظات (اختياري)

البوت سيقوم تلقائياً بإضافة التاريخ الحالي مع البيانات في جدول البيانات.
