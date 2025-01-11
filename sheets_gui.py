import tkinter as tk
from tkinter import ttk, messagebox
import json
from theme import Theme
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import config

class SheetsGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("إعداد جداول البيانات")
        
        # تهيئة Google Sheets
        try:
            self.gc = gspread.service_account(filename=config.GOOGLE_SHEETS_CREDENTIALS_FILE)
        except Exception as e:
            messagebox.showerror("خطأ", f"خطأ في الاتصال بـ Google Sheets: {str(e)}")
            self.gc = None
        
        # تهيئة السمة
        self.theme = Theme()
        self.theme.apply_theme(root)
        
        # تكوين النافذة
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # إنشاء الإطار الرئيسي
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # تحميل الإعدادات الحالية
        self.current_config = self.load_config()
        
        # إنشاء الأزرار
        buttons_frame = ttk.Frame(self.main_frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(buttons_frame, text="إضافة جدول جديد", 
                  command=self.show_add_sheet_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="عرض الجداول", 
                  command=self.show_sheets_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="حذف جدول", 
                  command=self.show_delete_dialog).pack(side=tk.LEFT, padx=5)
        
        # إنشاء منطقة عرض المعلومات
        self.info_frame = ttk.Frame(self.main_frame, padding="5")
        self.info_frame.pack(fill=tk.BOTH, expand=True)
        
        # عرض قائمة الجداول مباشرة
        self.show_sheets_list()

    def load_config(self):
        """تحميل إعدادات الجداول"""
        try:
            if os.path.exists('sheets_config.json'):
                with open('sheets_config.json', 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            messagebox.showerror("خطأ", f"خطأ في تحميل الإعدادات: {str(e)}")
        return {}

    def save_config(self):
        """حفظ إعدادات الجداول"""
        try:
            with open('sheets_config.json', 'w', encoding='utf-8') as f:
                json.dump(self.current_config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            messagebox.showerror("خطأ", f"خطأ في حفظ الإعدادات: {str(e)}")

    def verify_sheet_exists(self, sheet_name):
        """التحقق من وجود الجدول"""
        try:
            self.gc.open(sheet_name)
            return True
        except:
            return False

    def get_worksheet_names(self, sheet_name):
        """الحصول على قائمة أسماء الصفحات في الجدول"""
        try:
            spreadsheet = self.gc.open(sheet_name)
            return [worksheet.title for worksheet in spreadsheet.worksheets()]
        except:
            return []

    def get_sheet_columns(self, sheet_name, worksheet_name):
        """الحصول على أسماء الأعمدة في الصفحة"""
        try:
            spreadsheet = self.gc.open(sheet_name)
            worksheet = spreadsheet.worksheet(worksheet_name)
            return worksheet.row_values(1)
        except:
            return []

    def show_add_sheet_dialog(self):
        """عرض نافذة إضافة جدول جديد"""
        dialog = tk.Toplevel(self.root)
        dialog.title("إضافة جدول جديد")
        dialog.geometry("600x400")
        
        # إطار إدخال اسم الجدول
        sheet_frame = ttk.Frame(dialog, padding="5")
        sheet_frame.pack(fill=tk.X)
        
        ttk.Label(sheet_frame, text="اسم الجدول:").pack(side=tk.LEFT, padx=5)
        sheet_entry, sheet_name_var = self.create_entry(sheet_frame)
        sheet_entry.pack(side=tk.LEFT, padx=5)
        
        def verify_and_continue():
            sheet_name = sheet_name_var.get()
            if not sheet_name:
                messagebox.showerror("خطأ", "الرجاء إدخال اسم الجدول")
                return
                
            if not self.verify_sheet_exists(sheet_name):
                messagebox.showerror("خطأ", "الجدول غير موجود")
                return
                
            worksheets = self.get_worksheet_names(sheet_name)
            if not worksheets:
                messagebox.showerror("خطأ", "لا توجد صفحات في الجدول")
                return
                
            self.show_worksheet_selection(dialog, sheet_name, worksheets)
        
        ttk.Button(sheet_frame, text="متابعة", command=verify_and_continue).pack(side=tk.LEFT, padx=5)

    def show_worksheet_selection(self, parent, sheet_name, worksheets):
        """عرض نافذة اختيار الصفحة"""
        for widget in parent.winfo_children():
            widget.destroy()
            
        ws_frame = ttk.Frame(parent, padding="5")
        ws_frame.pack(fill=tk.X)
        
        ttk.Label(ws_frame, text="اختر الصفحة:").pack(side=tk.LEFT, padx=5)
        
        ws_var = tk.StringVar()
        ws_combo = ttk.Combobox(ws_frame, textvariable=ws_var, values=worksheets)
        ws_combo.pack(side=tk.LEFT, padx=5)
        ws_combo.set(worksheets[0])
        
        def select_worksheet():
            worksheet = ws_var.get()
            columns = self.get_sheet_columns(sheet_name, worksheet)
            if not columns:
                messagebox.showerror("خطأ", "لا توجد أعمدة في الصفحة")
                return
                
            self.show_columns_setup(parent, sheet_name, worksheet, columns)
        
        ttk.Button(ws_frame, text="متابعة", command=select_worksheet).pack(side=tk.LEFT, padx=5)

    def show_columns_setup(self, parent, sheet_name, worksheet, columns):
        """عرض نافذة إعداد الأعمدة"""
        for widget in parent.winfo_children():
            widget.destroy()
            
        columns_frame = ttk.Frame(parent, padding="5")
        columns_frame.pack(fill=tk.BOTH, expand=True)
        
        # عناوين الأعمدة
        ttk.Label(columns_frame, text="العمود").grid(row=0, column=0, padx=5)
        ttk.Label(columns_frame, text="نوع البيانات").grid(row=0, column=1, padx=5)
        ttk.Label(columns_frame, text="خيارات").grid(row=0, column=2, padx=5)
        ttk.Label(columns_frame, text="إجباري").grid(row=0, column=3, padx=5)
        
        column_types = {}
        date_options = {}
        required_fields = {}
        
        def create_column_setup(col, row):
            ttk.Label(columns_frame, text=col).grid(row=row, column=0, padx=5)
            
            type_var = tk.StringVar()
            type_combo = ttk.Combobox(columns_frame, textvariable=type_var, 
                                    values=["نص", "رقم", "تاريخ"])
            type_combo.grid(row=row, column=1, padx=5)
            type_combo.set("نص")
            
            options_frame = ttk.Frame(columns_frame)
            options_frame.grid(row=row, column=2, padx=5)
            
            time_var = tk.BooleanVar()
            auto_var = tk.BooleanVar()
            required_var = tk.BooleanVar(value=True)  # إجباري بشكل افتراضي
            
            def update_options(*args):
                for widget in options_frame.winfo_children():
                    widget.destroy()
                    
                if type_var.get() == "تاريخ":
                    ttk.Checkbutton(options_frame, text="تضمين الوقت", 
                                  variable=time_var).pack(side=tk.LEFT)
                    ttk.Checkbutton(options_frame, text="تلقائي", 
                                  variable=auto_var).pack(side=tk.LEFT)
            
            type_var.trace('w', update_options)
            
            # إضافة خانة الإجباري
            ttk.Checkbutton(columns_frame, variable=required_var).grid(row=row, column=3, padx=5)
            
            return type_var, time_var, auto_var, required_var
        
        column_vars = {}
        for i, col in enumerate(columns, 1):
            type_var, time_var, auto_var, required_var = create_column_setup(col, i)
            column_vars[col] = (type_var, time_var, auto_var, required_var)
        
        def save_setup():
            for col, (type_var, time_var, auto_var, required_var) in column_vars.items():
                col_type = type_var.get()
                if col_type == "نص":
                    column_types[col] = "text"
                elif col_type == "رقم":
                    column_types[col] = "number"
                elif col_type == "تاريخ":
                    column_types[col] = "date"
                    date_options[col] = {
                        'include_time': time_var.get(),
                        'auto': auto_var.get()
                    }
                required_fields[col] = required_var.get()
            
            # طلب معرف تيليجرام
            self.show_telegram_id_input(parent, sheet_name, worksheet, 
                                      column_types, date_options, required_fields)
        
        ttk.Button(columns_frame, text="حفظ", command=save_setup).grid(
            row=len(columns)+1, column=0, columnspan=4, pady=10)

    def show_telegram_id_input(self, parent, sheet_name, worksheet, column_types, date_options, required_fields):
        """عرض نافذة إدخال معرف تيليجرام"""
        for widget in parent.winfo_children():
            widget.destroy()
            
        frame = ttk.Frame(parent, padding="5")
        frame.pack(fill=tk.X)
        
        # إضافة خيار السماح لجميع المستخدمين
        allow_all_var = tk.BooleanVar(value=False)
        allow_all_check = ttk.Checkbutton(
            frame, 
            text="السماح لجميع المستخدمين بالوصول للجدول",
            variable=allow_all_var
        )
        allow_all_check.pack(side=tk.LEFT, padx=5)
        
        # إضافة حقل معرف تيليجرام
        id_label = ttk.Label(frame, text="معرفات تيليجرام للمستخدمين المصرح لهم (افصل بين المعرفات بفاصلة):")
        id_label.pack(side=tk.LEFT, padx=5)
        
        telegram_entry, telegram_id_var = self.create_entry(frame)
        telegram_entry.pack(side=tk.LEFT, padx=5)
        
        # إضافة تلميح للمستخدم
        hint_label = ttk.Label(
            frame, 
            text="مثال: 123456789, 987654321",
            font=("Arial", 8, "italic"),
            foreground="gray"
        )
        hint_label.pack(side=tk.LEFT, padx=5)
        
        def update_entry_state(*args):
            telegram_entry.configure(state='disabled' if allow_all_var.get() else 'normal')
            hint_label.configure(foreground="gray" if not allow_all_var.get() else "light gray")
        
        allow_all_var.trace('w', update_entry_state)
        
        def save_config():
            if allow_all_var.get():
                telegram_ids = "*"
            else:
                # تنظيف وتحقق من المعرفات
                ids = [id.strip() for id in telegram_id_var.get().split(',') if id.strip()]
                if not ids:
                    messagebox.showerror("خطأ", "الرجاء إدخال معرف تيليجرام واحد على الأقل أو اختيار السماح لجميع المستخدمين")
                    return
                
                # التحقق من صحة المعرفات
                for id in ids:
                    if not id.isdigit():
                        messagebox.showerror("خطأ", f"المعرف {id} غير صالح. يجب أن يحتوي على أرقام فقط")
                        return
                
                telegram_ids = ",".join(ids)
                
            # حفظ الإعدادات
            sheet_config = {
                'sheet_name': sheet_name,
                'worksheet_name': worksheet,
                'column_types': column_types,
                'date_options': date_options,
                'required_fields': required_fields,
                'authorized_user_ids': telegram_ids  # تغيير الاسم ليعكس تعدد المستخدمين
            }
            
            self.current_config[sheet_name] = sheet_config
            self.save_config()
            messagebox.showinfo("نجاح", "تم حفظ الإعدادات بنجاح")
            parent.destroy()
            self.show_sheets_list()
        
        save_button = ttk.Button(frame, text="حفظ", command=save_config)
        save_button.pack(side=tk.LEFT, padx=5)

    def show_sheets_list(self):
        """عرض قائمة الجداول المعدة"""
        for widget in self.info_frame.winfo_children():
            widget.destroy()
        
        if not self.current_config:
            ttk.Label(self.info_frame, text="لا توجد جداول معدة حتى الآن").pack()
            return
        
        # إنشاء إطار للجدول والأزرار
        table_frame = ttk.Frame(self.info_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # إنشاء جدول لعرض المعلومات
        tree = ttk.Treeview(table_frame, columns=('name', 'worksheet', 'users'),
                          show='headings', height=10)
        
        tree.heading('name', text='اسم الجدول')
        tree.heading('worksheet', text='اسم الصفحة')
        tree.heading('users', text='المستخدمين المصرح لهم')
        
        # تعيين عرض الأعمدة
        tree.column('name', width=150, minwidth=100)
        tree.column('worksheet', width=150, minwidth=100)
        tree.column('users', width=200, minwidth=150)
        
        # إضافة البيانات للجدول
        for sheet_name, config in self.current_config.items():
            users = config.get('authorized_user_ids', config.get('authorized_user_id', '*'))
            item = tree.insert('', tk.END, values=(
                sheet_name,
                config.get('worksheet_name', ''),
                users
            ))
            
        # إضافة شريط التمرير
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # إطار للأزرار
        buttons_frame = ttk.Frame(self.info_frame)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        def edit_selected():
            selection = tree.selection()
            if selection:
                item = selection[0]
                sheet_name = tree.item(item)['values'][0]
                self.show_edit_dialog(sheet_name)
        
        def delete_selected():
            selection = tree.selection()
            if selection:
                item = selection[0]
                sheet_name = tree.item(item)['values'][0]
                if messagebox.askyesno("تأكيد الحذف",
                                     f"هل أنت متأكد من حذف الجدول {sheet_name}؟"):
                    del self.current_config[sheet_name]
                    self.save_config()
                    self.show_sheets_list()
        
        # إضافة أزرار التحكم
        ttk.Button(buttons_frame, text="تعديل",
                  command=edit_selected).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(buttons_frame, text="حذف",
                  command=delete_selected).pack(side=tk.LEFT, padx=5)

    def show_edit_dialog(self, sheet_name):
        """عرض نافذة تعديل الجدول"""
        if sheet_name not in self.current_config:
            messagebox.showerror("خطأ", "لم يتم العثور على الجدول المحدد")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"تعديل جدول - {sheet_name}")
        dialog.geometry("600x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # إطار للمعلومات الأساسية
        basic_info_frame = ttk.LabelFrame(main_frame, text="معلومات أساسية", padding="5")
        basic_info_frame.pack(fill=tk.X, pady=5)
        
        # اسم الصفحة
        worksheet_frame = ttk.Frame(basic_info_frame)
        worksheet_frame.pack(fill=tk.X, pady=5)
        ttk.Label(worksheet_frame, text="اسم الصفحة:").pack(side=tk.LEFT)
        worksheet_var = tk.StringVar(value=self.current_config[sheet_name].get('worksheet_name', ''))
        worksheet_entry = ttk.Entry(worksheet_frame, textvariable=worksheet_var)
        worksheet_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # معرف المستخدم
        user_frame = ttk.Frame(basic_info_frame)
        user_frame.pack(fill=tk.X, pady=5)
        ttk.Label(user_frame, text="معرفات المستخدمين:").pack(side=tk.LEFT)
        user_var = tk.StringVar(value=self.current_config[sheet_name].get('authorized_user_ids', ''))
        user_entry = ttk.Entry(user_frame, textvariable=user_var)
        user_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # إطار لإعدادات الأعمدة
        columns_frame = ttk.LabelFrame(main_frame, text="إعدادات الأعمدة", padding="5")
        columns_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # إنشاء جدول لعرض الأعمدة
        tree = ttk.Treeview(columns_frame, columns=('column', 'type', 'auto_date', 'date_format'),
                          show='headings', height=10)
        
        tree.heading('column', text='اسم العمود')
        tree.heading('type', text='نوع البيانات')
        tree.heading('auto_date', text='تاريخ تلقائي')
        tree.heading('date_format', text='تنسيق التاريخ')
        
        tree.column('column', width=150)
        tree.column('type', width=100)
        tree.column('auto_date', width=100)
        tree.column('date_format', width=150)
        
        # إضافة البيانات للجدول
        column_types = self.current_config[sheet_name].get('column_types', {})
        date_options = self.current_config[sheet_name].get('date_options', {})
        
        for column, type_ in column_types.items():
            auto_date = 'نعم' if date_options.get(column, {}).get('auto', False) else 'لا'
            date_format = date_options.get(column, {}).get('format', '-')
            tree.insert('', tk.END, values=(column, type_, auto_date, date_format))
        
        # إضافة شريط التمرير
        scrollbar = ttk.Scrollbar(columns_frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # إطار للأزرار الخاصة بالأعمدة
        col_buttons_frame = ttk.Frame(columns_frame)
        col_buttons_frame.pack(fill=tk.X, pady=5)
        
        def edit_column():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("تنبيه", "الرجاء اختيار عمود للتعديل")
                return
                
            item = tree.selection()[0]
            column_name = tree.item(item)['values'][0]
            
            edit_dialog = tk.Toplevel(dialog)
            edit_dialog.title(f"تعديل عمود - {column_name}")
            edit_dialog.transient(dialog)
            edit_dialog.grab_set()
            
            # نوع البيانات
            type_frame = ttk.Frame(edit_dialog, padding="5")
            type_frame.pack(fill=tk.X, pady=5)
            ttk.Label(type_frame, text="نوع البيانات:").pack(side=tk.LEFT)
            type_var = tk.StringVar(value=column_types.get(column_name, 'text'))
            type_combo = ttk.Combobox(type_frame, textvariable=type_var, values=['text', 'number', 'date'])
            type_combo.pack(side=tk.LEFT, padx=5)
            
            # خيارات التاريخ
            date_frame = ttk.LabelFrame(edit_dialog, text="خيارات التاريخ", padding="5")
            
            def on_type_change(*args):
                if type_var.get() == 'date':
                    date_frame.pack(fill=tk.X, pady=5)
                else:
                    date_frame.pack_forget()
            
            type_var.trace('w', on_type_change)
            
            # تفعيل التاريخ التلقائي
            auto_var = tk.BooleanVar(value=date_options.get(column_name, {}).get('auto', False))
            auto_check = ttk.Checkbutton(date_frame, text="تعبئة التاريخ تلقائياً",
                                       variable=auto_var)
            auto_check.pack(fill=tk.X)
            
            # تنسيق التاريخ
            format_frame = ttk.Frame(date_frame)
            format_frame.pack(fill=tk.X, pady=5)
            ttk.Label(format_frame, text="تنسيق التاريخ:").pack(side=tk.LEFT)
            
            format_var = tk.StringVar(value=date_options.get(column_name, {}).get('format', 'date_time'))
            format_combo = ttk.Combobox(format_frame, textvariable=format_var, 
                                      values=['date_time', 'date_only', 'time_only'])
            format_combo['values'] = [
                'date_time - (YYYY-MM-DD HH:MM:SS)',
                'date_only - (YYYY-MM-DD)',
                'time_only - (HH:MM:SS)'
            ]
            format_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            
            # عرض إطار التاريخ إذا كان النوع تاريخ
            if type_var.get() == 'date':
                date_frame.pack(fill=tk.X, pady=5)
            
            def save_column():
                # حفظ التغييرات
                column_types[column_name] = type_var.get()
                if type_var.get() == 'date':
                    if column_name not in date_options:
                        date_options[column_name] = {}
                    date_options[column_name]['auto'] = auto_var.get()
                    date_options[column_name]['format'] = format_var.get().split(' - ')[0]
                elif column_name in date_options:
                    del date_options[column_name]
                
                # تحديث العرض
                tree.set(item, 'type', type_var.get())
                tree.set(item, 'auto_date', 'نعم' if auto_var.get() else 'لا')
                tree.set(item, 'date_format', format_var.get().split(' - ')[0])
                edit_dialog.destroy()
            
            # أزرار الحفظ والإلغاء
            buttons_frame = ttk.Frame(edit_dialog, padding="5")
            buttons_frame.pack(fill=tk.X, pady=5)
            ttk.Button(buttons_frame, text="حفظ", command=save_column).pack(side=tk.LEFT, padx=5)
            ttk.Button(buttons_frame, text="إلغاء", command=edit_dialog.destroy).pack(side=tk.LEFT)
        
        ttk.Button(col_buttons_frame, text="تعديل العمود المحدد", command=edit_column).pack(side=tk.LEFT, padx=5)
        
        # إطار للأزرار
        actions_frame = ttk.Frame(main_frame)
        actions_frame.pack(fill=tk.X, pady=10)
        
        def save_changes():
            # حفظ التغييرات في الإعدادات
            self.current_config[sheet_name].update({
                'worksheet_name': worksheet_var.get(),
                'authorized_user_ids': user_var.get(),
                'column_types': column_types,
                'date_options': date_options
            })
            self.save_config()
            messagebox.showinfo("نجاح", "تم حفظ التغييرات بنجاح")
            dialog.destroy()
            self.show_sheets_list()
        
        def delete_sheet():
            if messagebox.askyesno("تأكيد", "هل أنت متأكد من حذف هذا الجدول؟"):
                del self.current_config[sheet_name]
                self.save_config()
                dialog.destroy()
                self.show_sheets_list()
        
        ttk.Button(actions_frame, text="حفظ التغييرات", command=save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="حذف الجدول", command=delete_sheet).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="إلغاء", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def show_delete_dialog(self):
        """عرض نافذة حذف جدول"""
        if not self.current_config:
            messagebox.showinfo("تنبيه", "لا توجد جداول لحذفها")
            return
            
        dialog = tk.Toplevel(self.root)
        dialog.title("حذف جدول")
        dialog.geometry("400x200")
        
        ttk.Label(dialog, text="اختر الجدول المراد حذفه:").pack(padx=5, pady=5)
        
        sheet_var = tk.StringVar()
        sheet_combo = ttk.Combobox(dialog, textvariable=sheet_var, 
                                 values=list(self.current_config.keys()))
        sheet_combo.pack(padx=5, pady=5)
        
        def delete_sheet():
            sheet_name = sheet_var.get()
            if not sheet_name:
                messagebox.showerror("خطأ", "الرجاء اختيار جدول")
                return
                
            if messagebox.askyesno("تأكيد", f"هل أنت متأكد من حذف الجدول {sheet_name}؟"):
                del self.current_config[sheet_name]
                self.save_config()
                messagebox.showinfo("نجاح", "تم حذف الجدول بنجاح")
                dialog.destroy()
                self.show_sheets_list()
        
        ttk.Button(dialog, text="حذف", command=delete_sheet).pack(pady=10)

    def paste(self, event):
        """لصق النص"""
        try:
            event.widget.delete("sel.first", "sel.last")
        except:
            pass
        event.widget.insert("insert", self.root.clipboard_get())
        return "break"

    def copy(self, event):
        """نسخ النص"""
        try:
            selection = event.widget.selection_get()
            self.root.clipboard_clear()
            self.root.clipboard_append(selection)
        except:
            pass
        return "break"

    def cut(self, event):
        """قص النص"""
        try:
            selection = event.widget.selection_get()
            self.root.clipboard_clear()
            self.root.clipboard_append(selection)
            event.widget.delete("sel.first", "sel.last")
        except:
            pass
        return "break"

    def create_entry(self, parent):
        """إنشاء حقل إدخال مع قائمة سياق"""
        var = tk.StringVar()
        entry = ttk.Entry(parent, textvariable=var)
        
        # إنشاء قائمة السياق
        context_menu = tk.Menu(parent, tearoff=0)
        context_menu.add_command(label="نسخ", command=lambda: self.copy_text(entry))
        context_menu.add_command(label="لصق", command=lambda: self.paste_text(entry))
        context_menu.add_command(label="قص", command=lambda: self.cut_text(entry))
        
        # ربط القائمة بالحقل
        entry.bind('<Button-3>', lambda e: self.show_context_menu(e, context_menu))
        
        # دعم Ctrl+C, Ctrl+V, Ctrl+X
        entry.bind('<Control-c>', lambda e: self.copy_text(entry))
        entry.bind('<Control-v>', lambda e: self.paste_text(entry))
        entry.bind('<Control-x>', lambda e: self.cut_text(entry))
        
        return entry, var

    def show_context_menu(self, event, menu):
        """عرض قائمة السياق"""
        menu.tk_popup(event.x_root, event.y_root)

    def copy_text(self, widget):
        """نسخ النص المحدد"""
        widget.event_generate('<<Copy>>')

    def paste_text(self, widget):
        """لصق النص"""
        widget.event_generate('<<Paste>>')

    def cut_text(self, widget):
        """قص النص المحدد"""
        widget.event_generate('<<Cut>>')

    def set_font(self):
        """تعيين الخط للنافذة بأكملها"""
        default_font = ('Segoe UI', 10)
        self.root.option_add('*Font', default_font)
        
        style = ttk.Style()
        style.configure('.', font=default_font)

    def toggle_theme(self):
        """تبديل السمة بين الوضع الفاتح والمظلم"""
        self.theme.toggle_theme()
        self.theme.apply_theme(self.root)

def main():
    root = tk.Tk()
    root.tk.call("encoding", "system", "utf-8")  # لدعم الأحرف العربية
    app = SheetsGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
