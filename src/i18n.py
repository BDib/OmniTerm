# -*- coding: utf-8 -*-
"""
OmniTerm simple translation helper for English (en) and Arabic (ar).
"""

_TRANSLATIONS = {
    "en": {
        "menu_file": "&File",
        "menu_new_tab": "New &Tab",
        "menu_close_tab": "&Close Tab",
        "menu_profile_picker": "&Profile Picker...",
        "menu_manage_profiles": "&Manage Profiles...",
        "menu_exit": "E&xit",
        "menu_save_html": "Save Output as &HTML...",
        "menu_save_text": "Save Output as &Text...",
        "menu_edit": "&Edit",
        "menu_copy": "&Copy",
        "menu_cut": "Cu&t",
        "menu_paste": "&Paste",
        "menu_find": "&Find...",
        "menu_view": "&View",
        "menu_zoom_in": "Zoom &In",
        "menu_zoom_out": "Zoom &Out",
        "menu_reset_zoom": "&Reset Zoom",
        "menu_cycle_theme": "Cycle &Theme",
        "menu_toggle_transparency": "Toggle &Transparency",
        "menu_toggle_window_rtl": "Toggle Window &RTL",
        "menu_text_direction": "Te&xt Direction",
        "menu_toggle_line_rtl": "Toggle &Line RTL",
        "menu_tools": "&Tools",
        "menu_ssh_connect": "&SSH Connect...",
        "menu_serial_connect": "&Serial Connect...",
        "menu_wsl_connect": "&WSL Connect...",
        "menu_window": "&Window",
        "menu_next_tab": "N&ext Tab",
        "menu_prev_tab": "&Previous Tab",
        "menu_language": "&Language",
        "menu_lang_en": "English",
        "menu_lang_ar": "العربية (Arabic)",

        "input_placeholder": "Type a command...",
        "select_theme": "Select Theme",
        "theme_label": "Theme:",
        "restart_shell": "Restart Shell",
        "menu_help": "&Help",
        "menu_about": "&About OmniTerm",
        "about_title": "About OmniTerm v{version}",
        "about_body": "<h3>OmniTerm v{version}</h3>"
                      "<p>A modern, cross-platform terminal emulator built with Python and PyQt6.</p>"
                      "<p>Features: ConPTY backend, ANSI color rendering, Arabic/bidi support, "
                      "13 themes, multi-tab, SSH/Serial/WSL integration.</p>"
                      "<p>License: MIT</p>"
                      "<p>GitHub: <a href='https://github.com/BDib/OmniTerm'>github.com/BDib/OmniTerm</a></p>"
                      "<p>Author: BDib (Buddy)</p>",
    },
    "ar": {
        "menu_file": "ملف",
        "menu_new_tab": "علامة تبويب جديدة",
        "menu_close_tab": "إغلاق علامة التبويب",
        "menu_profile_picker": "منتقي الملفات الشخصية...",
        "menu_manage_profiles": "إدارة الملفات الشخصية...",
        "menu_exit": "خروج",
        "menu_save_html": "حفظ المخرجات كـ HTML...",
        "menu_save_text": "حفظ المخرجات كنص...",
        "menu_edit": "تحرير",
        "menu_copy": "نسخ",
        "menu_cut": "قص",
        "menu_paste": "لصق",
        "menu_find": "بحث...",
        "menu_view": "عرض",
        "menu_zoom_in": "تكبير",
        "menu_zoom_out": "تصغير",
        "menu_reset_zoom": "إعادة تعيين التكبير",
        "menu_cycle_theme": "تبديل السمة",
        "menu_toggle_transparency": "تبديل الشفافية",
        "menu_toggle_window_rtl": "تبديل اتجاه النافذة (يمين ليسار)",
        "menu_text_direction": "اتجاه النص",
        "menu_toggle_line_rtl": "تبديل اتجاه السطر (يمين ليسار)",
        "menu_tools": "أدوات",
        "menu_ssh_connect": "اتصال SSH...",
        "menu_serial_connect": "اتصال تسلسلي...",
        "menu_wsl_connect": "اتصال WSL...",
        "menu_window": "نافذة",
        "menu_next_tab": "علامة التبويب التالية",
        "menu_prev_tab": "علامة التبويب السابقة",
        "menu_language": "اللغة",
        "menu_lang_en": "English (الإنجليزية)",
        "menu_lang_ar": "العربية",

        "input_placeholder": "اكتب أمراً...",
        "select_theme": "اختر سمة",
        "theme_label": "السمة:",
        "restart_shell": "إعادة تشغيل الطرفية",
        "menu_help": "مساعدة",
        "menu_about": "حول OmniTerm",
        "about_title": "حول OmniTerm v{version}",
        "about_body": "<h3>OmniTerm v{version}</h3>"
                      "<p>محاكي طرفيات عصري ومتعدد المنصات مبني بـ Python و PyQt6.</p>"
                      "<p>الميزات: خلفية ConPTY، عرض ألوان ANSI، دعم العربية والنص ثنائي الاتجاه، "
                      "13 سمة، علامات تبويب متعددة، تكامل SSH/_serial/WSL.</p>"
                      "<p>الرخصة: MIT</p>"
                      "<p>GitHub: <a href='https://github.com/BDib/OmniTerm'>github.com/BDib/OmniTerm</a></p>"
                      "<p>المؤلف: BDib (Buddy)</p>",
    }
}

def t(key: str, lang: str = "en") -> str:
    """Translate key for the given language (falls back to English, then key)."""
    lang_map = _TRANSLATIONS.get(lang, _TRANSLATIONS["en"])
    return lang_map.get(key, _TRANSLATIONS["en"].get(key, key))
