from tkinter import ttk

class Theme:
    # الألوان الرئيسية
    PRIMARY = "#1E88E5"  # أزرق
    SECONDARY = "#FFC107"  # أصفر
    SUCCESS = "#4CAF50"  # أخضر
    ERROR = "#F44336"  # أحمر
    WARNING = "#FF9800"  # برتقالي
    INFO = "#2196F3"  # أزرق
    
    # ألوان الخلفية
    BG_PRIMARY = "#121212"  # أسود
    BG_SECONDARY = "#1E1E1E"  # رمادي داكن
    
    # ألوان النص
    TEXT_PRIMARY = "#FFFFFF"  # أبيض
    TEXT_SECONDARY = "#B3B3B3"  # رمادي فاتح
    TEXT_LIGHT = "#FFFFFF"  # أبيض
    
    # الخط
    FONT_FAMILY = "Arial"
    FONT_SIZE_SMALL = 10
    FONT_SIZE_NORMAL = 12
    FONT_SIZE_LARGE = 14
    FONT_SIZE_XLARGE = 16
    
    # الحواف
    BORDER_COLOR = "#383838"
    BORDER_WIDTH = 1
    
    # التباعد
    PADDING_SMALL = 5
    PADDING_NORMAL = 10
    PADDING_LARGE = 15
    
    # أنماط الأزرار
    BUTTON_BG = "#1E1E1E"
    BUTTON_FG = TEXT_LIGHT
    BUTTON_ACTIVE_BG = "#2C2C2C"  # رمادي داكن
    BUTTON_HOVER_BG = "#383838"  # رمادي متوسط
    
    # أنماط الإدخال
    ENTRY_BG = "#2C2C2C"
    ENTRY_FG = TEXT_PRIMARY
    ENTRY_BORDER = "#383838"
    
    # أنماط الجداول
    TABLE_BG = "#1E1E1E"
    TABLE_FG = TEXT_PRIMARY
    TABLE_SELECTED_BG = "#383838"
    TABLE_HEADER_BG = "#2C2C2C"
    TABLE_HEADER_FG = TEXT_PRIMARY
    
    # أنماط القوائم
    MENU_BG = "#1E1E1E"
    MENU_FG = TEXT_PRIMARY
    MENU_ACTIVE_BG = "#383838"
    MENU_ACTIVE_FG = TEXT_LIGHT

    @staticmethod
    def apply_theme(root):
        """تطبيق الثيم على النافذة الرئيسية"""
        style = ttk.Style()
        
        # تعيين الثيم الافتراضي
        style.theme_use('default')
        
        # تكوين النافذة الرئيسية
        root.configure(bg=Theme.BG_PRIMARY)
        
        # تكوين الأزرار
        style.configure('TButton',
            background=Theme.BUTTON_BG,
            foreground=Theme.BUTTON_FG,
            padding=(Theme.PADDING_NORMAL, Theme.PADDING_SMALL),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL)
        )
        
        # تكوين الإدخال
        style.configure('TEntry',
            background=Theme.ENTRY_BG,
            foreground=Theme.ENTRY_FG,
            fieldbackground=Theme.ENTRY_BG,
            borderwidth=Theme.BORDER_WIDTH
        )
        
        # تكوين التسميات
        style.configure('TLabel',
            background=Theme.BG_PRIMARY,
            foreground=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL)
        )
        
        # تكوين الإطارات
        style.configure('TFrame',
            background=Theme.BG_PRIMARY,
            borderwidth=Theme.BORDER_WIDTH,
            relief='flat'
        )
        
        # تكوين شريط التمرير
        style.configure('Vertical.TScrollbar',
            background=Theme.BG_SECONDARY,
            borderwidth=0,
            arrowsize=Theme.FONT_SIZE_SMALL
        )
        
        # تكوين الجداول
        style.configure('Treeview',
            background=Theme.TABLE_BG,
            foreground=Theme.TABLE_FG,
            fieldbackground=Theme.TABLE_BG,
            borderwidth=Theme.BORDER_WIDTH,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL)
        )
        
        style.configure('Treeview.Heading',
            background=Theme.TABLE_HEADER_BG,
            foreground=Theme.TABLE_HEADER_FG,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL, 'bold')
        )
        
        # تكوين القوائم
        style.configure('TMenubutton',
            background=Theme.MENU_BG,
            foreground=Theme.MENU_FG,
            padding=(Theme.PADDING_NORMAL, Theme.PADDING_SMALL),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL)
        )
