import json
import os
from tkinter import ttk

class Theme:
    def __init__(self):
        self.theme_file = 'theme_settings.json'
        self.current_theme = self.load_theme()
        
        # تعريف الألوان للسمات المختلفة
        self.themes = {
            'light': {
                'bg': '#f8f9fa',
                'fg': '#212529',
                'button_bg': '#0d6efd',
                'button_fg': '#ffffff',
                'entry_bg': '#ffffff',
                'entry_fg': '#212529',
                'tree_bg': '#ffffff',
                'tree_fg': '#212529',
                'selected_bg': '#0d6efd',
                'selected_fg': '#ffffff',
                'header_bg': '#e9ecef',
                'header_fg': '#212529',
                'accent1': '#198754',  # نجاح
                'accent2': '#dc3545',  # خطأ
                'accent3': '#ffc107',  # تحذير
                'hover_bg': '#e9ecef'
            },
            'dark': {
                'bg': '#1e1e1e',
                'fg': '#ffffff',
                'button_bg': '#0d6efd',
                'button_fg': '#ffffff',
                'entry_bg': '#2d2d2d',
                'entry_fg': '#ffffff',
                'tree_bg': '#1e1e1e',
                'tree_fg': '#ffffff',
                'selected_bg': '#0d6efd',
                'selected_fg': '#ffffff',
                'header_bg': '#2d2d2d',
                'header_fg': '#ffffff',
                'accent1': '#198754',
                'accent2': '#dc3545',
                'accent3': '#ffc107',
                'hover_bg': '#2d2d2d'
            },
            'colorful': {
                'bg': '#ffffff',
                'fg': '#1a1a1a',
                'button_bg': '#ff6b6b',
                'button_fg': '#ffffff',
                'entry_bg': '#f8f9fa',
                'entry_fg': '#1a1a1a',
                'tree_bg': '#ffffff',
                'tree_fg': '#1a1a1a',
                'selected_bg': '#4ecdc4',
                'selected_fg': '#ffffff',
                'header_bg': '#ffe66d',
                'header_fg': '#1a1a1a',
                'accent1': '#95e1d3',
                'accent2': '#f38181',
                'accent3': '#fce38a',
                'hover_bg': '#eaffd0'
            }
        }

    def load_theme(self):
        """تحميل إعدادات السمة"""
        try:
            if os.path.exists(self.theme_file):
                with open(self.theme_file, 'r') as f:
                    settings = json.load(f)
                    return settings.get('theme', 'light')
        except:
            pass
        return 'light'

    def save_theme(self):
        """حفظ إعدادات السمة"""
        try:
            with open(self.theme_file, 'w') as f:
                json.dump({'theme': self.current_theme}, f)
        except:
            pass

    def toggle_theme(self):
        """تبديل بين السمات"""
        themes = list(self.themes.keys())
        current_index = themes.index(self.current_theme)
        next_index = (current_index + 1) % len(themes)
        self.current_theme = themes[next_index]
        self.save_theme()

    def apply_theme(self, root):
        """تطبيق السمة على النافذة"""
        style = ttk.Style()
        colors = self.themes[self.current_theme]
        
        # تطبيق الألوان على النافذة الرئيسية والإطار الرئيسي
        root.configure(bg=colors['bg'])
        for child in root.winfo_children():
            try:
                child.configure(bg=colors['bg'])
            except:
                pass
        
        # تكوين نمط الأزرار
        style.configure('TButton',
                      background=colors['button_bg'],
                      foreground=colors['button_fg'],
                      padding=6)
        
        style.map('TButton',
                background=[('active', colors['hover_bg'])],
                foreground=[('active', colors['button_fg'])])
        
        # تكوين نمط الإطارات
        style.configure('TFrame',
                      background=colors['bg'])
        
        # تكوين نمط حقول الإدخال
        style.configure('TEntry',
                      fieldbackground=colors['entry_bg'],
                      foreground=colors['entry_fg'],
                      padding=5)
        
        # تكوين نمط التسميات
        style.configure('TLabel',
                      background=colors['bg'],
                      foreground=colors['fg'],
                      padding=3)
        
        # تكوين نمط عرض البيانات
        style.configure('Treeview',
                      background=colors['tree_bg'],
                      foreground=colors['tree_fg'],
                      fieldbackground=colors['tree_bg'],
                      rowheight=25)
        
        style.configure('Treeview.Heading',
                      background=colors['header_bg'],
                      foreground=colors['header_fg'],
                      padding=5)
        
        # تكوين نمط التحديد
        style.map('Treeview',
                background=[('selected', colors['selected_bg'])],
                foreground=[('selected', colors['selected_fg'])])
        
        # تكوين نمط زر السمة
        style.configure('Theme.TButton',
                      padding=5,
                      relief='flat',
                      background=colors['button_bg'],
                      foreground=colors['button_fg'])
        
        # تكوين نمط الأزرار الخاصة
        style.configure('Success.TButton',
                      background=colors['accent1'],
                      foreground='white')
        
        style.configure('Danger.TButton',
                      background=colors['accent2'],
                      foreground='white')
        
        style.configure('Warning.TButton',
                      background=colors['accent3'],
                      foreground='black')
        
        # تكوين نمط LabelFrame
        style.configure('TLabelframe',
                      background=colors['bg'],
                      foreground=colors['fg'])
        
        style.configure('TLabelframe.Label',
                      background=colors['bg'],
                      foreground=colors['fg'])
                      
        # تكوين نمط Checkbutton
        style.configure('TCheckbutton',
                      background=colors['bg'],
                      foreground=colors['fg'])
                      
        # تكوين نمط Scrollbar
        style.configure('TScrollbar',
                      background=colors['bg'],
                      troughcolor=colors['bg'],
                      arrowcolor=colors['fg'])
