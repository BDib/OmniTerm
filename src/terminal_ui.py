# -*- coding: utf-8 -*-
import os
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QTextEdit, QApplication, QInputDialog,
    QWidget, QVBoxLayout, QTabWidget,
    QToolButton, QMenu, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSlot, QSettings, QPoint, pyqtSignal
from PyQt6.QtGui import (
    QTextCursor,
    QKeySequence,
    QShortcut,
    QMouseEvent,
    QTextOption,
)

from config import VERSION
from themes import get_theme, list_themes
from ansi_parser import parse_ansi, SpanKind, strip_ansi
from ansi_renderer import span_to_format
from mouse_handler import MouseHandler
from search_bar import SearchDialog
from ssh_dialog import SSHDialog
from serial_dialog import SerialDialog
from profile_picker import ProfilePickerDialog
from wsl_manager import WSLManager
from i18n import t

# ─── Cursor style mapping ─────────────────────────────────────────────────

_CURSOR_WIDTHS = {
    "bar": 2,
    "block": 0,  # block uses no extra width; we draw it via background
    "underline": 0,
}

# ─── Custom QTextEdit that intercepts keyboard & mouse for PTY ─────────────

class TerminalScreen(QTextEdit):
    """Interactive output screen that forwards all keys and mouse events to the shell."""

    def __init__(self, parent=None, term_widget=None):
        super().__init__(parent)
        self.term_widget = term_widget
        self.setReadOnly(False)
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard |
            Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.setAcceptRichText(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setWordWrapMode(QTextOption.WrapMode.WordWrap)

    def keyPressEvent(self, event):
        if self.term_widget:
            self.term_widget.handle_key_event(event)
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if self.term_widget and self.term_widget._mouse.is_active:
            self.term_widget.handle_mouse_press(event)
        else:
            super().mousePressEvent(event)
            self.setFocus()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.term_widget and self.term_widget._mouse.is_active:
            self.term_widget.handle_mouse_release(event)
        else:
            super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.term_widget and self.term_widget._mouse.is_active:
            self.term_widget.handle_mouse_move(event)
        else:
            super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        if self.term_widget and self.term_widget._mouse.is_active:
            self.term_widget.handle_wheel(event)
        else:
            super().wheelEvent(event)

# ─── Terminal Widget (Unified QTextEdit) ──────────────────────────────────

class TerminalWidget(QWidget):
    """Terminal widget: a single unified interactive QTextEdit for input & output.

    Handles key events natively by capturing, translating to ANSI, and sending
    to the shell PTY, preventing default QTextEdit side-effects.
    """

    def __init__(self, parent=None, cfg=None, plain_mode=False):
        super().__init__(parent)
        self.parent_engine = None
        self._cfg = cfg
        self._plain_mode = plain_mode
        self._mouse = MouseHandler()
        self._mouse_last_pos = QPoint()
        self._opaque = True
        self._auto_arabic = True

        # ── Layout ──
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Single interactive QTextEdit terminal screen
        self._output = TerminalScreen(self, self)
        layout.addWidget(self._output, 1)

        # Search dialog (created on demand)
        self._search_dialog = None

        # ── Theme ──
        self._theme = get_theme(cfg.ui.theme if cfg else "campbell")
        self._apply_theme()

        # ── Shortcuts ──
        self._setup_shortcuts()

        # Focus the screen
        self._output.setFocus()

    def _shape_arabic(self, text: str) -> str:
        """Reshapes and applies bidi reordering on Arabic text dynamically."""
        if not text:
            return text
        # If there are any Arabic characters, reshape and reorder
        has_arabic = any(0x0600 <= ord(c) <= 0x06FF for c in text)
        if has_arabic:
            try:
                import arabic_reshaper
                from bidi.algorithm import get_display
                reshaped = arabic_reshaper.reshape(text)
                return get_display(reshaped)
            except Exception:
                pass
        return text

    # ── Key handling ──────────────────────────────────────────────────

    def handle_key_event(self, event):
        """Translate key press events into PTY sequences and write to shell."""
        if not self.parent_engine or not self.parent_engine.is_ready:
            return

        key = event.key()
        mods = event.modifiers()
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)

        # 1. Map Ctrl combos
        if ctrl:
            # Clipboard handling
            if key == Qt.Key.Key_C:
                cursor = self._output.textCursor()
                if cursor.hasSelection():
                    QApplication.clipboard().setText(cursor.selectedText())
                    return
                else:
                    self.parent_engine.write("\x03")  # SIGINT
                    return
            elif key == Qt.Key.Key_V:
                self._paste_clipboard()
                return

            ctrl_map = {
                Qt.Key.Key_A: "\x01",
                Qt.Key.Key_E: "\x05",
                Qt.Key.Key_K: "\x0b",
                Qt.Key.Key_U: "\x15",
                Qt.Key.Key_W: "\x17",
                Qt.Key.Key_L: "\x0c",
                Qt.Key.Key_Z: "\x1a",
                Qt.Key.Key_D: "\x04",
            }
            if key in ctrl_map:
                self.parent_engine.write(ctrl_map[key])
                return

        # 2. Map special keys to ANSI VT sequences
        key_map = {
            Qt.Key.Key_Return: "\r",
            Qt.Key.Key_Enter: "\r",
            Qt.Key.Key_Tab: "\t",
            Qt.Key.Key_Backspace: "\x7f",
            Qt.Key.Key_Escape: "\x1b",
            Qt.Key.Key_Delete: "\x1b[3~",
            Qt.Key.Key_Up: "\x1b[A",
            Qt.Key.Key_Down: "\x1b[B",
            Qt.Key.Key_Right: "\x1b[C",
            Qt.Key.Key_Left: "\x1b[D",
            Qt.Key.Key_Home: "\x1b[H",
            Qt.Key.Key_End: "\x1b[F",
            Qt.Key.Key_PageUp: "\x1b[5~",
            Qt.Key.Key_PageDown: "\x1b[6~",
        }
        if key in key_map:
            self.parent_engine.write(key_map[key])
            return

        # 3. Map regular printable characters
        text = event.text()
        if text:
            self.parent_engine.write(text)

    # ── Theme & Style ──────────────────────────────────────────────────

    def _apply_theme(self):
        ui = self._cfg.ui if self._cfg else None
        ff = ui.font_family if ui else "Cascadia Code"
        fs = ui.font_size if ui else 14

        bg = self._theme.background
        fg = self._theme.foreground
        sel_bg = self._theme.selection_bg
        sel_fg = self._theme.selection_fg

        # Output area
        self._output.setStyleSheet(
            f"QTextEdit {{ background-color: {bg}; color: {fg}; "
            f"font-family: '{ff}', 'Consolas', monospace; font-size: {fs}px; "
            f"padding: 10px; border: none; "
            f"selection-background-color: {sel_bg}; selection-color: {sel_fg}; }}"
        )

        # Cursor style for output
        style = ui.cursor_style if ui else "bar"
        self._output.setCursorWidth(_CURSOR_WIDTHS.get(style, 2))

        # Cursor blink
        blink = ui.cursor_blink if ui else True
        QApplication.setCursorFlashTime(1000 if blink else 0)

    def apply_theme_by_name(self, name: str):
        self._theme = get_theme(name)
        if self._cfg:
            self._cfg.ui.theme = name
        self._apply_theme()

    def cycle_theme(self):
        names = list_themes()
        try:
            idx = names.index(self._cfg.ui.theme if self._cfg else "campbell")
        except ValueError:
            idx = -1
        self.apply_theme_by_name(names[(idx + 1) % len(names)])

    def apply_font_size(self, size: int):
        size = max(6, min(72, size))
        if self._cfg:
            self._cfg.ui.font_size = size
        self._apply_theme()

    def increase_font_size(self):
        self.apply_font_size((self._cfg.ui.font_size if self._cfg else 14) + 2)

    def decrease_font_size(self):
        self.apply_font_size((self._cfg.ui.font_size if self._cfg else 14) - 2)

    def reset_font_size(self):
        self.apply_font_size(14)

    def set_cursor_style(self, style: str):
        if self._cfg:
            self._cfg.ui.cursor_style = style
        self._apply_theme()

    # ── Shortcuts ──────────────────────────────────────────────────────

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Shift+O"), self).activated.connect(
            self._toggle_opacity)
        # Search shortcuts
        QShortcut(QKeySequence("F3"), self).activated.connect(
            self._search_next)
        QShortcut(QKeySequence("Shift+F3"), self).activated.connect(
            self._search_prev)

    def _search_next(self):
        """F3: Open search dialog or find next."""
        if self._search_dialog and self._search_dialog.isVisible():
            self._search_dialog.find_next()
        else:
            # Open search for the current terminal's output
            window = self.window()
            if isinstance(window, MainWindow):
                widget = window._tabs.currentWidget()
                if isinstance(widget, TerminalWidget):
                    if widget._search_dialog and widget._search_dialog.isVisible():
                        widget._search_dialog.find_next()
                    else:
                        window._open_search()

    def _search_prev(self):
        """Shift+F3: Find previous."""
        if self._search_dialog and self._search_dialog.isVisible():
            self._search_dialog.find_prev()
        else:
            window = self.window()
            if isinstance(window, MainWindow):
                widget = window._tabs.currentWidget()
                if isinstance(widget, TerminalWidget):
                    if widget._search_dialog and widget._search_dialog.isVisible():
                        widget._search_dialog.find_prev()
                    else:
                        window._open_search()
                        if widget._search_dialog:
                            widget._search_dialog.find_prev()

    # ── Opacity ────────────────────────────────────────────────────────

    def _toggle_opacity(self):
        window = self.window()
        if self._opaque:
            opacity = self._cfg.ui.opacity if self._cfg else 0.98
            window.setWindowOpacity(opacity)
            self._opaque = False
        else:
            window.setWindowOpacity(1.0)
            self._opaque = True

    # ── Dialogs ────────────────────────────────────────────────────────

    def _pick_theme(self):
        names = list_themes()
        current = self._cfg.ui.theme if self._cfg else "campbell"
        try:
            idx = names.index(current)
        except ValueError:
            idx = 0
        name, ok = QInputDialog.getItem(
            self, "Select Theme", "Theme:", names, idx, False)
        if ok and name:
            self.apply_theme_by_name(name)

    # ── Shell output → screen ──────────────────────────────────────────

    @pyqtSlot(str)
    def append_shell_text(self, text: str):
        """Parse ANSI escapes and render styled text into the output area.

        Handles CURSOR_POS for PSReadLine rewrites: when the cursor moves
        backward (within the current line), we overwrite existing text.
        """
        if self._plain_mode:
            clean = strip_ansi(text)
            clean = "".join(c for c in clean if ord(c) >= 32 or c in "\n\r\t")
            if not clean:
                return
            out = self._output
            out.moveCursor(QTextCursor.MoveOperation.End)
            out.insertPlainText(clean)
            out.ensureCursorVisible()
            return

        spans = parse_ansi(text)
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        for span in spans:
            if span.kind == SpanKind.TEXT:
                # Apply dynamic Arabic shaping & bidi reordering if enabled
                processed_text = self._shape_arabic(span.text) if self._auto_arabic else span.text
                cursor.insertText(processed_text,
                    span_to_format(span.sgr, self._theme))

            elif span.kind == SpanKind.NEWLINE:
                cursor.insertText("\n")

            elif span.kind == SpanKind.CARRIAGE_RETURN:
                pass  # Ignored

            elif span.kind == SpanKind.CURSOR_POS:
                self._handle_cursor_pos(cursor, span.row, span.col)

            elif span.kind == SpanKind.CURSOR_BACK:
                for _ in range(max(1, span.col)):
                    if cursor.position() > 0:
                        cursor.movePosition(
                            QTextCursor.MoveOperation.Left,
                            QTextCursor.MoveMode.KeepAnchor)

            elif span.kind == SpanKind.CURSOR_FORWARD:
                for _ in range(max(1, span.col)):
                    cursor.movePosition(
                        QTextCursor.MoveOperation.Right,
                        QTextCursor.MoveMode.KeepAnchor)

            elif span.kind == SpanKind.TAB:
                cursor.insertText("    ")

            elif span.kind == SpanKind.BACKSPACE:
                cursor.deletePreviousChar()  # Corrected to delete character to the left

            elif span.kind == SpanKind.MOUSE_MODE:
                parts = span.text.split(",")
                if len(parts) == 2 and parts[0].isdigit():
                    self._mouse.set_mode(int(parts[0]), parts[1] == "h")

            elif span.kind == SpanKind.ERASE_DISPLAY:
                self._output.clear()
                cursor = self._output.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.Start)

            elif span.kind == SpanKind.ERASE_LINE:
                cursor.movePosition(
                    QTextCursor.MoveOperation.EndOfBlock,
                    QTextCursor.MoveMode.KeepAnchor)
                cursor.removeSelectedText()

        self._output.setTextCursor(cursor)
        self._output.ensureCursorVisible()

    def _handle_cursor_pos(self, cursor, row, col):
        """Move cursor to (row, col) and overwrite if moving backward."""
        doc = self._output.document()
        target_block = doc.findBlockByLineNumber(row - 1)
        if not target_block.isValid():
            cursor.movePosition(QTextCursor.MoveOperation.End)
            return

        block_text = target_block.text()
        col_offset = min(col - 1, len(block_text))
        target_pos = target_block.position() + col_offset

        current_pos = cursor.position()
        if target_pos < current_pos:
            # PSReadLine rewrite — delete old text from target to current
            cursor.setPosition(target_pos, QTextCursor.MoveMode.MoveAnchor)
            cursor.setPosition(current_pos, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
        else:
            cursor.setPosition(target_pos)

    @pyqtSlot(str)
    def show_exit_message(self, text: str):
        try:
            # Check if widget is still in the widget tree
            if not self.parent():
                return
            cursor = self._output.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(f"\n{text}\n")
            self._output.setTextCursor(cursor)
            self._output.ensureCursorVisible()
        except Exception as exc:
            import traceback
            import os
            import sys
            try:
                d = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.getcwd()
                with open(os.path.join(d, "errors.txt"), "a", encoding="utf-8") as f:
                    f.write("\n=== show_exit_message crash ===\n")
                    traceback.print_exception(type(exc), exc, exc.__traceback__, file=f)
                    f.write("\n")
            except Exception:
                pass

    # ── Save / Export ────────────────────────────────────────────────

    def save_output_html(self, filepath: str) -> None:
        """Export terminal output as HTML with theme colors preserved."""
        from datetime import datetime
        theme = self._theme
        html = self._output.toHtml()
        # Check RTL direction
        is_rtl = self._output.layoutDirection() == Qt.LayoutDirection.RightToLeft
        dir_attr = ' dir="rtl"' if is_rtl else ''
        styled_html = f"""<!DOCTYPE html>
<html{dir_attr}>
<head>
<meta charset="utf-8">
<title>OmniTerm Export — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</title>
<style>
body {{
    background-color: {theme.background};
    color: {theme.foreground};
    font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
    font-size: 14px;
    padding: 20px;
    margin: 0;
    white-space: pre-wrap;
    word-wrap: break-word;
    direction: {"rtl" if is_rtl else "ltr"};
    text-align: {"right" if is_rtl else "left"};
}}
</style>
</head>
<body>
{html}
</body>
</html>"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(styled_html)

    def save_output_text(self, filepath: str) -> None:
        """Export terminal output as plain text."""
        text = self._output.toPlainText()
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)

    # ── Focus proxy ────────────────────────────────────────────────────

    def setFocus(self, reason=Qt.FocusReason.OtherFocusReason):
        self._output.setFocus(reason)

    # ── Copy / Paste ───────────────────────────────────────────────────

    def _copy_selection(self):
        cursor = self._output.textCursor()
        if cursor.hasSelection():
            QApplication.clipboard().setText(cursor.selectedText())

    def _paste_clipboard(self):
        cb = QApplication.clipboard()
        text = cb.text()
        if text:
            # Replace CRLF/LF with \r for raw terminal typing behavior
            text = text.replace("\r\n", "\r").replace("\n", "\r")
            self.parent_engine.write(text)

    # ── QTextEdit compat proxies (used by MainWindow) ─────────────────

    def textCursor(self):
        return self._output.textCursor()

    def setTextCursor(self, cursor):
        self._output.setTextCursor(cursor)

    def moveCursor(self, op):
        self._output.moveCursor(op)

    def toPlainText(self):
        return self._output.toPlainText()

    def clear(self):
        self._output.clear()

    # ── Mouse events (terminal mouse protocol) ─────────────────────────

    def _pos_to_cell(self, pos: QPoint) -> tuple[int, int]:
        cursor = self._output.cursorForPosition(pos)
        return cursor.positionInBlock() + 1, cursor.blockNumber() + 1

    def handle_mouse_press(self, event: QMouseEvent):
        if not self._mouse.is_active or not self.parent_engine:
            return
        col, row = self._pos_to_cell(event.position().toPoint())
        button_map = {
            Qt.MouseButton.LeftButton: 0,
            Qt.MouseButton.MiddleButton: 1,
            Qt.MouseButton.RightButton: 2,
        }
        button = button_map.get(event.button())
        if button is None:
            return
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        alt = bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)
        seq = self._mouse.encode_press(col, row, button, shift, ctrl, alt)
        if seq and self.parent_engine.is_ready:
            self.parent_engine.write(seq)

    def handle_mouse_release(self, event: QMouseEvent):
        if not self._mouse.is_active or not self.parent_engine:
            return
        col, row = self._pos_to_cell(event.position().toPoint())
        button_map = {
            Qt.MouseButton.LeftButton: 0,
            Qt.MouseButton.MiddleButton: 1,
            Qt.MouseButton.RightButton: 2,
        }
        button = button_map.get(event.button(), 0)
        seq = self._mouse.encode_release(col, row, button)
        if seq and self.parent_engine.is_ready:
            self.parent_engine.write(seq)

    def handle_mouse_move(self, event: QMouseEvent):
        if not self._mouse.is_active or not self.parent_engine:
            return
        col, row = self._pos_to_cell(event.position().toPoint())
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        alt = bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)
        seq = self._mouse.encode_motion(col, row, 0, shift, ctrl, alt)
        if seq and self.parent_engine.is_ready:
            self.parent_engine.write(seq)

    def handle_wheel(self, event):
        if not self._mouse.is_active or not self.parent_engine:
            # Scroll the output widget instead
            delta = event.angleDelta().y()
            sb = self._output.verticalScrollBar()
            sb.setValue(sb.value() - delta)
            return
        col, row = self._pos_to_cell(event.position().toPoint())
        angle = event.angleDelta().y()
        button = 64 if angle > 0 else 65 if angle < 0 else None
        if button is None:
            return
        seq = self._mouse.encode_press(col, row, button)
        if seq and self.parent_engine.is_ready:
            self.parent_engine.write(seq)


# ─── Main Window ───────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """Top-level window with tabbed terminal support.

    Each tab contains its own TerminalWidget + TerminalEngine.
    """
    tab_process_exited_signal = pyqtSignal(object)

    def __init__(self, cfg=None, plain_mode=False, shell=None, cwd=None):
        super().__init__()
        self._cfg = cfg
        self._plain_mode = plain_mode
        self._settings = QSettings("OmniTerm", "OmniTerm")
        self._tab_engines: dict[TerminalWidget, "TerminalEngine"] = {}  # noqa: F821
        self._closing = False
        self.tab_process_exited_signal.connect(self._on_tab_process_exited)

        # Detect if running as admin
        self._is_admin = self._check_admin()
        self.setWindowTitle(f"OmniTerm v{VERSION}")
        self._apply_config()
        self._restore_geometry()

        # ── Tab widget ──
        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(True)
        self._tabs.setMovable(True)
        self._tabs.tabCloseRequested.connect(self._close_tab)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self._tabs)

        # ── "+" button with profile dropdown ──
        self._add_btn = QToolButton(self._tabs)
        self._add_btn.setText("+")
        self._add_btn.setFixedSize(28, 24)
        self._add_btn.setStyleSheet(
            "QToolButton { border: none; font-size: 16px; font-weight: bold; }"
            "QToolButton:hover { background: #555; border-radius: 4px; }")
        self._add_btn.clicked.connect(self._show_add_menu)
        self._tabs.setCornerWidget(self._add_btn)

        # ── Menu bar ──
        self._build_menu_bar()

        # ── Built-in shortcuts ──
        # Note: Most shortcuts are defined in _build_menu_bar() via setShortcut().
        # Only shortcuts NOT in the menu bar are defined here as standalone QShortcuts.
        QShortcut(QKeySequence("Ctrl+Tab"), self).activated.connect(self._next_tab)
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self).activated.connect(self._prev_tab)
        QShortcut(QKeySequence("Ctrl+Shift+U"), self).activated.connect(self._wsl_connect)
        QShortcut(QKeySequence("Ctrl+,"), self).activated.connect(self._theme_picker)

        # ── Custom keybindings from config ──
        if self._cfg:
            for kb in self._cfg.keybindings:
                action_fn = self._resolve_action(kb.action)
                if action_fn:
                    QShortcut(QKeySequence(kb.shortcut), self).activated.connect(action_fn)

        # ── Open first tab ──
        if shell:
            self.new_tab(shell=shell, cwd=cwd)
        else:
            self.new_tab(cwd=cwd)

        # Load initial UI Language and apply translation
        self._update_ui_language()

    @staticmethod
    def _check_admin() -> bool:
        """Check if the current process is running as Administrator."""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def _apply_config(self):
        ui = self._cfg.ui if self._cfg else None
        opacity = ui.opacity if ui else 0.98
        self.setWindowOpacity(opacity)
        self.resize(1000, 650)
        self.setMinimumSize(400, 200)

    # ── Menu bar ──────────────────────────────────────────────────────

    def _show_add_menu(self):
        """Show a dropdown menu with profiles for opening a new tab."""
        menu = QMenu(self)
        if self._cfg:
            for name, profile in sorted(self._cfg.profiles.items()):
                label = name.replace("_", " ").title()
                if profile.admin:
                    label += "  [Admin]"
                action = menu.addAction(label)
                action.triggered.connect(
                    lambda checked=False, n=name: self._open_profile_tab(n))
        menu.addSeparator()
        action = menu.addAction(t("menu_manage_profiles", self._cfg.ui.language if self._cfg else "en"))
        action.triggered.connect(self._manage_profiles)
        menu.exec(self._add_btn.mapToGlobal(self._add_btn.rect().bottomLeft()))

    def _open_profile_tab(self, profile_name: str):
        """Open a new tab using a named profile."""
        if not self._cfg:
            return
        profile = self._cfg.get_profile(profile_name)
        if not profile:
            return

        if profile.admin:
            # Relaunch OmniTerm as admin with --admin flag
            self._launch_as_admin(profile)
            return

        full_cmd = profile.command
        if profile.args:
            full_cmd = f"{profile.command} {' '.join(profile.args)}"
        self.new_tab(shell=full_cmd, admin=profile.admin)

    def _launch_as_admin(self, profile):
        """Relaunch OmniTerm as admin, auto-opening the given profile."""
        import ctypes
        import os

        # Find the profile name
        profile_name = ""
        for name, p in self._cfg.profiles.items():
            if p is profile:
                profile_name = name
                break

        if getattr(sys, 'frozen', False):
            exe = sys.executable
        else:
            exe = sys.executable
            main_py = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "Main.py")
            if not os.path.isfile(main_py):
                main_py = os.path.join(os.getcwd(), "src", "Main.py")

        if getattr(sys, 'frozen', False):
            shell_arg = f'--profile {profile_name}'
        else:
            shell_arg = f'"{main_py}" --profile {profile_name}'

        try:
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", exe, shell_arg, None, 1
            )
            if result <= 32:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Admin",
                    "Could not launch as admin.\n"
                    "The UAC prompt may have been cancelled.")
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Admin Error", str(e))

    def _manage_profiles(self):
        """Open the profile manager dialog."""
        try:
            from profile_manager import ProfileManagerDialog
            dlg = ProfileManagerDialog(self._cfg, self)
            dlg.exec()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to open Profile Manager:\n{e}")

    def _build_menu_bar(self):
        menu = self.menuBar()

        def _act(m, text, slot, shortcut=None):
            a = m.addAction(text)
            a.triggered.connect(lambda checked=False: slot())
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            return a

        # We construct all menus and actions, keeping references so they can be dynamically translated
        self._file_menu = menu.addMenu("")
        self._action_new_tab = _act(self._file_menu, "", self.new_tab, "Ctrl+T")
        self._action_close_tab = _act(self._file_menu, "", self._close_current_tab, "Ctrl+W")
        self._file_menu.addSeparator()
        self._action_profile_picker = _act(self._file_menu, "", self._profile_picker, "Ctrl+Shift+N")
        self._action_manage_profiles = _act(self._file_menu, "", self._manage_profiles)
        self._file_menu.addSeparator()
        self._action_save_html = _act(self._file_menu, "Save Output as HTML...", self._save_output_html, "Ctrl+Shift+H")
        self._action_save_text = _act(self._file_menu, "Save Output as Text...", self._save_output_text, "Ctrl+Shift+S")
        self._file_menu.addSeparator()
        self._action_exit = _act(self._file_menu, "", self.close, "Alt+F4")

        self._edit_menu = menu.addMenu("")
        self._action_copy = _act(self._edit_menu, "", self._menu_copy, QKeySequence.StandardKey.Copy)
        self._action_cut = _act(self._edit_menu, "", self._menu_cut, QKeySequence.StandardKey.Cut)
        self._action_paste = _act(self._edit_menu, "", self._menu_paste, QKeySequence.StandardKey.Paste)
        self._edit_menu.addSeparator()
        self._action_find = _act(self._edit_menu, "", self._open_search, "Ctrl+F")

        self._view_menu = menu.addMenu("")
        self._action_zoom_in = _act(self._view_menu, "", self._font_bigger, "Ctrl+=")
        self._action_zoom_out = _act(self._view_menu, "", self._font_smaller, "Ctrl+-")
        self._action_reset_zoom = _act(self._view_menu, "", self._font_reset, "Ctrl+0")
        self._view_menu.addSeparator()
        self._action_cycle_theme = _act(self._view_menu, "", self._theme_cycle, "Ctrl+Shift+T")
        self._action_toggle_opacity = _act(self._view_menu, "", self._toggle_opacity, "Ctrl+Shift+O")
        self._view_menu.addSeparator()
        self._action_toggle_rtl = _act(self._view_menu, "", self._toggle_rtl_window)

        # ── Language Selection Submenu under View ──
        self._lang_menu = self._view_menu.addMenu("")
        self._action_lang_en = self._lang_menu.addAction("")
        self._action_lang_en.triggered.connect(lambda: self._set_language("en"))
        self._action_lang_ar = self._lang_menu.addAction("")
        self._action_lang_ar.triggered.connect(lambda: self._set_language("ar"))

        self._text_menu = menu.addMenu("")
        self._action_toggle_line_rtl = _act(self._text_menu, "", self._toggle_rtl_line)

        self._tools_menu = menu.addMenu("")
        self._action_ssh_connect = _act(self._tools_menu, "", self._ssh_connect, "Ctrl+Shift+S")
        self._action_serial_connect = _act(self._tools_menu, "", self._serial_connect, "Ctrl+Shift+R")
        self._action_wsl_connect = _act(self._tools_menu, "", self._wsl_connect, "Ctrl+Shift+U")

        self._win_menu = menu.addMenu("")
        self._action_next_tab = _act(self._win_menu, "", self._next_tab, "Ctrl+Tab")
        self._action_prev_tab = _act(self._win_menu, "", self._prev_tab, "Ctrl+Shift+Tab")

        self._help_menu = menu.addMenu("")
        self._action_about = _act(self._help_menu, "", self._show_about)

    def _set_language(self, lang_code: str):
        """Set the active translation language and refresh the UI."""
        if self._cfg:
            self._cfg.ui.language = lang_code
            self._cfg.save()
        self._update_ui_language()

    def _update_ui_language(self):
        """Translate all UI texts dynamically and adjust layout direction based on current config."""
        lang = self._cfg.ui.language if self._cfg else "en"

        # Update menu titles
        self._file_menu.setTitle(t("menu_file", lang))
        self._action_new_tab.setText(t("menu_new_tab", lang))
        self._action_close_tab.setText(t("menu_close_tab", lang))
        self._action_profile_picker.setText(t("menu_profile_picker", lang))
        self._action_manage_profiles.setText(t("menu_manage_profiles", lang))
        self._action_save_html.setText(t("menu_save_html", lang))
        self._action_save_text.setText(t("menu_save_text", lang))
        self._action_exit.setText(t("menu_exit", lang))

        self._edit_menu.setTitle(t("menu_edit", lang))
        self._action_copy.setText(t("menu_copy", lang))
        self._action_cut.setText(t("menu_cut", lang))
        self._action_paste.setText(t("menu_paste", lang))
        self._action_find.setText(t("menu_find", lang))

        self._view_menu.setTitle(t("menu_view", lang))
        self._action_zoom_in.setText(t("menu_zoom_in", lang))
        self._action_zoom_out.setText(t("menu_zoom_out", lang))
        self._action_reset_zoom.setText(t("menu_reset_zoom", lang))
        self._action_cycle_theme.setText(t("menu_cycle_theme", lang))
        self._action_toggle_opacity.setText(t("menu_toggle_transparency", lang))
        self._action_toggle_rtl.setText(t("menu_toggle_window_rtl", lang))

        self._lang_menu.setTitle(t("menu_language", lang))
        self._action_lang_en.setText(t("menu_lang_en", lang))
        self._action_lang_ar.setText(t("menu_lang_ar", lang))

        self._text_menu.setTitle(t("menu_text_direction", lang))
        self._action_toggle_line_rtl.setText(t("menu_toggle_line_rtl", lang))

        self._tools_menu.setTitle(t("menu_tools", lang))
        self._action_ssh_connect.setText(t("menu_ssh_connect", lang))
        self._action_serial_connect.setText(t("menu_serial_connect", lang))
        self._action_wsl_connect.setText(t("menu_wsl_connect", lang))

        self._win_menu.setTitle(t("menu_window", lang))
        self._action_next_tab.setText(t("menu_next_tab", lang))
        self._action_prev_tab.setText(t("menu_prev_tab", lang))

        self._help_menu.setTitle(t("menu_help", lang))
        self._action_about.setText(t("menu_about", lang))

        # Dynamic layout direction
        if lang == "ar":
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            for i in range(self._tabs.count()):
                widget = self._tabs.widget(i)
                if isinstance(widget, TerminalWidget):
                    widget._output.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                    widget._output.setAlignment(Qt.AlignmentFlag.AlignRight)
                    widget._auto_arabic = True
        else:
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            for i in range(self._tabs.count()):
                widget = self._tabs.widget(i)
                if isinstance(widget, TerminalWidget):
                    widget._output.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
                    widget._output.setAlignment(Qt.AlignmentFlag.AlignLeft)

    def _menu_copy(self):
        """Copy selected text from the current terminal's output."""
        widget = self._tabs.currentWidget()
        if isinstance(widget, TerminalWidget):
            cursor = widget._output.textCursor()
            if cursor.hasSelection():
                QApplication.clipboard().setText(cursor.selectedText())

    def _menu_cut(self):
        """Cut is a no-op on a real terminal because terminal buffer is managed by the shell."""
        pass

    def _menu_paste(self):
        widget = self._tabs.currentWidget()
        if isinstance(widget, TerminalWidget):
            widget._paste_clipboard()

    def _show_about(self):
        """Show the About dialog."""
        from i18n import t
        lang = self._cfg.ui.language if self._cfg else "en"
        title = t("about_title", lang).format(version=VERSION)
        body = t("about_body", lang).format(version=VERSION)
        QMessageBox.about(self, title, body)

    def _toggle_rtl_line(self):
        """Manually toggle the current output line alignment (Right-to-Left / Left-to-Right)."""
        widget = self._tabs.currentWidget()
        if not isinstance(widget, TerminalWidget):
            return
        cursor = widget._output.textCursor()
        block_fmt = cursor.blockFormat()
        if block_fmt.layoutDirection() == Qt.LayoutDirection.RightToLeft:
            block_fmt.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            block_fmt.setAlignment(Qt.AlignmentFlag.AlignLeft)
        else:
            block_fmt.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            block_fmt.setAlignment(Qt.AlignmentFlag.AlignRight)
        cursor.setBlockFormat(block_fmt)
        widget._output.setTextCursor(cursor)

    def _toggle_rtl_window(self):
        """Manually toggle the entire OmniTerm layout direction."""
        if self.layoutDirection() == Qt.LayoutDirection.RightToLeft:
            new_dir = Qt.LayoutDirection.LeftToRight
        else:
            new_dir = Qt.LayoutDirection.RightToLeft

        self.setLayoutDirection(new_dir)
        for i in range(self._tabs.count()):
            widget = self._tabs.widget(i)
            if isinstance(widget, TerminalWidget):
                # Set widget layout direction — this moves the text visually
                widget._output.setLayoutDirection(new_dir)
                # Set document-level text direction for proper rendering
                widget._output.document().setDefaultTextDirection(new_dir)
                # Set alignment on all blocks
                cursor = widget._output.textCursor()
                cursor.select(QTextCursor.SelectionType.Document)
                block_fmt = cursor.blockFormat()
                block_fmt.setLayoutDirection(new_dir)
                if new_dir == Qt.LayoutDirection.RightToLeft:
                    block_fmt.setAlignment(Qt.AlignmentFlag.AlignRight)
                else:
                    block_fmt.setAlignment(Qt.AlignmentFlag.AlignLeft)
                cursor.setBlockFormat(block_fmt)
                widget._output.setTextCursor(cursor)

    # ── Tab management ─────────────────────────────────────────────────

    def _close_tab(self, index: int) -> None:
        """Close the tab at *index*."""
        if self._closing:
            return
        if self._tabs.count() <= 1:
            self._closing = True
            self.close()
            return

        try:
            widget = self._tabs.widget(index)
            engine = self._tab_engines.pop(widget, None) if widget else None

            if engine:
                try:
                    engine.signals.exited.disconnect()
                    engine.signals.text_ready.disconnect()
                except (RuntimeError, TypeError):
                    pass
                engine.kill()

            # Delete widget before removing tab to prevent signal delivery issues
            if widget:
                widget.deleteLater()
            self._tabs.removeTab(index)
        except Exception as exc:
            import traceback
            import os
            import sys
            try:
                d = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.getcwd()
                with open(os.path.join(d, "errors.txt"), "a", encoding="utf-8") as f:
                    f.write(f"\n=== _close_tab crash (index={index}) ===\n")
                    traceback.print_exception(type(exc), exc, exc.__traceback__, file=f)
                    f.write("\n")
            except Exception:
                pass

    def _close_current_tab(self) -> None:
        idx = self._tabs.currentIndex()
        if idx >= 0:
            self._close_tab(idx)

    # ── Save / Export ────────────────────────────────────────────────

    def _save_output_html(self) -> None:
        """Save current terminal output as HTML with theme colors."""
        from PyQt6.QtWidgets import QFileDialog
        from datetime import datetime
        ts = datetime.now().strftime('%Y%m%d-%H%M%S')
        default_name = f"omniterm-export-{ts}.html"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Output as HTML", default_name,
            "HTML Files (*.html);;All Files (*)")
        if filepath:
            widget = self._tabs.currentWidget()
            if isinstance(widget, TerminalWidget):
                widget.save_output_html(filepath)

    def _save_output_text(self) -> None:
        """Save current terminal output as plain text."""
        from PyQt6.QtWidgets import QFileDialog
        from datetime import datetime
        ts = datetime.now().strftime('%Y%m%d-%H%M%S')
        default_name = f"omniterm-export-{ts}.txt"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Output as Text", default_name,
            "Text Files (*.txt);;All Files (*)")
        if filepath:
            widget = self._tabs.currentWidget()
            if isinstance(widget, TerminalWidget):
                widget.save_output_text(filepath)

    def _next_tab(self) -> None:
        count = self._tabs.count()
        if count > 1:
            self._tabs.setCurrentIndex((self._tabs.currentIndex() + 1) % count)

    def _prev_tab(self) -> None:
        count = self._tabs.count()
        if count > 1:
            self._tabs.setCurrentIndex((self._tabs.currentIndex() - 1) % count)

    def _on_tab_changed(self, index: int) -> None:
        """Focus the terminal widget in the newly active tab."""
        widget = self._tabs.widget(index)
        if widget and hasattr(widget, "setFocus"):
            widget.setFocus()

    def _on_tab_process_exited(self, terminal: TerminalWidget) -> None:
        """Close the tab when the shell process exits."""
        try:
            idx = self._tabs.indexOf(terminal)
            if idx >= 0:
                self._close_tab(idx)
        except Exception as exc:
            import traceback
            import os
            import sys
            try:
                d = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.getcwd()
                with open(os.path.join(d, "errors.txt"), "a", encoding="utf-8") as f:
                    f.write("\n=== _on_tab_process_exited crash ===\n")
                    traceback.print_exception(type(exc), exc, exc.__traceback__, file=f)
                    f.write("\n")
            except Exception:
                pass

    @staticmethod
    def _shell_title(shell: str) -> str:
        """Derive a short tab title from the shell command."""
        name = shell.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        name = name.replace(".exe", "")
        return name

    # ── Actions ────────────────────────────────────────────────────────

    def _open_search(self) -> None:
        """Open the search dialog for the current terminal's output."""
        widget = self._tabs.currentWidget()
        if isinstance(widget, TerminalWidget):
            if widget._search_dialog is None:
                widget._search_dialog = SearchDialog(widget._output, self)
            widget._search_dialog.open_dialog()

    def _profile_picker(self) -> None:
        """Open the profile picker dialog and launch the selected shell."""
        if not self._cfg:
            return
        dlg = ProfilePickerDialog(self._cfg, self)
        if dlg.exec():
            profile_name = dlg.get_selected()
            if profile_name:
                self._open_profile_tab(profile_name)

    def _ssh_connect(self) -> None:
        """Open the SSH connection dialog and start a new SSH tab."""
        dlg = SSHDialog(self)
        if dlg.exec():
            params = dlg.get_connection_params()
            self.new_tab_ssh(**params)

    def new_tab_ssh(self, host: str, port: int = 22, username: str = "",
                    password: str | None = None,
                    key_filename: str | None = None,
                    **kwargs) -> int:
        """Open a new tab with an SSH connection. Returns the tab index."""
        from terminal_core import TerminalEngine

        terminal = TerminalWidget(cfg=self._cfg, plain_mode=self._plain_mode)
        engine = TerminalEngine()

        terminal.parent_engine = engine
        engine.signals.text_ready.connect(terminal.append_shell_text)
        engine.signals.exited.connect(terminal.show_exit_message)
        engine.signals.exited.connect(lambda _: self.tab_process_exited_signal.emit(terminal))

        title = f"ssh:{username}@{host}"
        idx = self._tabs.addTab(terminal, title)
        self._tab_engines[terminal] = engine
        self._tabs.setCurrentIndex(idx)

        success = engine.start_ssh(
            host=host, port=port, username=username,
            password=password, key_filename=key_filename,
        )
        if not success:
            terminal.append_shell_text("[SSH connection failed]\n")

        # Set default alignments based on current config language
        lang = self._cfg.ui.language if self._cfg else "en"
        if lang == "ar":
            terminal._output.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            terminal._output.setAlignment(Qt.AlignmentFlag.AlignRight)
            terminal._auto_arabic = True

        terminal.setFocus()
        return idx

    # ── Serial ─────────────────────────────────────────────────────────

    def _serial_connect(self) -> None:
        """Open the serial connection dialog and start a new serial tab."""
        dlg = SerialDialog(self)
        if dlg.exec():
            params = dlg.get_connection_params()
            self.new_tab_serial(**params)

    def new_tab_serial(self, port: str, baudrate: int = 115200,
                       bytesize: int = 8, parity: str = "N",
                       stopbits: float = 1, **kwargs) -> int:
        """Open a new tab with a serial connection. Returns the tab index."""
        from terminal_core import TerminalEngine

        terminal = TerminalWidget(cfg=self._cfg, plain_mode=self._plain_mode)
        engine = TerminalEngine()

        terminal.parent_engine = engine
        engine.signals.text_ready.connect(terminal.append_shell_text)
        engine.signals.exited.connect(terminal.show_exit_message)
        engine.signals.exited.connect(lambda _: self.tab_process_exited_signal.emit(terminal))

        title = f"serial:{port}"
        idx = self._tabs.addTab(terminal, title)
        self._tab_engines[terminal] = engine
        self._tabs.setCurrentIndex(idx)

        success = engine.start_serial(
            port=port, baudrate=baudrate, bytesize=bytesize,
            parity=parity, stopbits=stopbits,
        )
        if not success:
            terminal.append_shell_text("[Serial connection failed]\n")

        # Set default alignments based on current config language
        lang = self._cfg.ui.language if self._cfg else "en"
        if lang == "ar":
            terminal._output.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            terminal._output.setAlignment(Qt.AlignmentFlag.AlignRight)
            terminal._auto_arabic = True

        terminal.setFocus()
        return idx

    # ── WSL ────────────────────────────────────────────────────────────

    def _wsl_connect(self) -> None:
        """Open WSL — pick a distribution or use the default."""
        if not WSLManager.is_available():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "WSL", "WSL is not installed or not available.")
            return

        distros = WSLManager.list_distributions()
        if not distros:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "WSL", "No WSL distributions found.")
            return

        names = [d["name"] for d in distros]
        name, ok = QInputDialog.getItem(
            self, "Select WSL Distribution", "Distribution:", names, 0, False,
        )
        if ok and name:
            self.new_tab(wsl=True, distribution=name)

    def new_tab(self, shell: str = "cmd.exe", wsl: bool = False,
                distribution: str | None = None, admin: bool = False,
                cwd: str | None = None) -> int:
        """Open a new tab running *shell* or WSL. Returns the tab index."""
        from terminal_core import TerminalEngine

        terminal = TerminalWidget(cfg=self._cfg, plain_mode=self._plain_mode)
        engine = TerminalEngine()

        terminal.parent_engine = engine
        engine.signals.text_ready.connect(terminal.append_shell_text)
        engine.signals.exited.connect(terminal.show_exit_message)
        engine.signals.exited.connect(lambda _: self.tab_process_exited_signal.emit(terminal))

        if wsl:
            cmd = WSLManager.get_shell_command(distribution)
            title = f"wsl:{distribution or 'default'}"
        else:
            cmd = shell
            title = self._shell_title(shell)

        # Show [Admin] if this process is elevated OR if admin was requested
        if admin or self._is_admin:
            title += " [Admin]"

        idx = self._tabs.addTab(terminal, title)
        self._tab_engines[terminal] = engine
        self._tabs.setCurrentIndex(idx)

        # Start the engine passing custom working directory (CWD)
        engine.start(cmd, admin=admin, cwd=cwd)

        # Set default alignments based on current config language
        lang = self._cfg.ui.language if self._cfg else "en"
        if lang == "ar":
            terminal._output.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            terminal._output.setAlignment(Qt.AlignmentFlag.AlignRight)
            terminal._auto_arabic = True

        terminal.setFocus()
        return idx

    def _font_bigger(self) -> None:
        widget = self._tabs.currentWidget()
        if isinstance(widget, TerminalWidget):
            widget.increase_font_size()

    def _font_smaller(self) -> None:
        widget = self._tabs.currentWidget()
        if isinstance(widget, TerminalWidget):
            widget.decrease_font_size()

    def _font_reset(self) -> None:
        widget = self._tabs.currentWidget()
        if isinstance(widget, TerminalWidget):
            widget.reset_font_size()

    def _theme_cycle(self) -> None:
        widget = self._tabs.currentWidget()
        if isinstance(widget, TerminalWidget):
            widget.cycle_theme()

    def _theme_picker(self) -> None:
        widget = self._tabs.currentWidget()
        if isinstance(widget, TerminalWidget):
            widget._pick_theme()

    def _toggle_opacity(self) -> None:
        widget = self._tabs.currentWidget()
        if isinstance(widget, TerminalWidget):
            widget._toggle_opacity()

    def _resolve_action(self, action: str):
        """Map an action name to a callable."""
        actions = {
            "new_tab": self.new_tab,
            "close_tab": self._close_current_tab,
            "next_tab": self._next_tab,
            "prev_tab": self._prev_tab,
            "font_bigger": self._font_bigger,
            "font_smaller": self._font_smaller,
            "font_reset": self._font_reset,
            "theme_cycle": self._theme_cycle,
            "theme_picker": self._theme_picker,
            "toggle_opacity": self._toggle_opacity,
            "find": self._open_search,
            "profile_picker": self._profile_picker,
            "ssh_connect": self._ssh_connect,
            "serial_connect": self._serial_connect,
            "wsl_connect": self._wsl_connect,
        }
        return actions.get(action)

    # ── Geometry persistence ───────────────────────────────────────────

    def _restore_geometry(self):
        geom = self._settings.value("window/geometry")
        if geom is not None:
            self.restoreGeometry(geom)
        state = self._settings.value("window/state")
        if state is not None:
            self.restoreState(state)

    def closeEvent(self, event):
        import traceback
        try:
            self._closing = True
            self.kill_all_engines()
            self._settings.setValue("window/geometry", self.saveGeometry())
            self._settings.setValue("window/state", self.saveState())
        except Exception as exc:
            # Log crash to errors.txt
            try:
                d = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.getcwd()
                with open(os.path.join(d, "errors.txt"), "a", encoding="utf-8") as f:
                    f.write("\n=== closeEvent crash ===\n")
                    traceback.print_exception(type(exc), exc, exc.__traceback__, file=f)
                    f.write("\n")
            except Exception:
                pass
        super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        widget = self._tabs.currentWidget()
        if widget and hasattr(widget, "setFocus"):
            widget.setFocus()

    def kill_all_engines(self) -> None:
        """Kill all tab engines. Called on window close."""
        try:
            for engine in list(self._tab_engines.values()):
                try:
                    engine.kill()
                except Exception:
                    pass
            self._tab_engines.clear()
        except Exception as exc:
            import traceback
            import os
            import sys
            try:
                d = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.getcwd()
                with open(os.path.join(d, "errors.txt"), "a", encoding="utf-8") as f:
                    f.write("\n=== kill_all_engines crash ===\n")
                    traceback.print_exception(type(exc), exc, exc.__traceback__, file=f)
                    f.write("\n")
            except Exception:
                pass
