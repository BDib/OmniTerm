import re

from PyQt6.QtWidgets import (
    QMainWindow, QTextEdit, QLineEdit, QApplication, QInputDialog,
    QScrollBar, QWidget, QVBoxLayout, QTabWidget,
    QMenuBar, QMenu, QFrame, QToolButton, QMenu as QMenuWidget,
)
from PyQt6.QtCore import Qt, pyqtSlot, QSettings, QPoint
from PyQt6.QtGui import (
    QColor,
    QTextCursor,
    QFont,
    QKeySequence,
    QShortcut,
    QTextCharFormat,
    QPalette,
    QMouseEvent,
)

from themes import get_theme, list_themes, Theme
from ansi_parser import parse_ansi, SpanKind, strip_ansi
from ansi_renderer import span_to_format
from mouse_handler import MouseHandler
from search_bar import SearchBar
from ssh_dialog import SSHDialog
from serial_dialog import SerialDialog
from profile_picker import ProfilePickerDialog
from wsl_manager import WSLManager
from config import Config


# ─── Cursor style mapping ─────────────────────────────────────────────────

_CURSOR_WIDTHS = {
    "bar": 2,
    "block": 0,  # block uses no extra width; we draw it via background
    "underline": 0,
}


# ─── Terminal Widget ───────────────────────────────────────────────────────

class TerminalWidget(QWidget):
    """Terminal widget: read-only QTextEdit for output + QLineEdit for input.

    This avoids all QTextEdit key-handling issues by letting the shell handle
    everything.  The QLineEdit provides a native, visible cursor and editing.
    """

    def __init__(self, parent=None, cfg=None, plain_mode=False):
        super().__init__(parent)
        self.parent_engine = None
        self._cfg = cfg
        self._plain_mode = plain_mode
        self._mouse = MouseHandler()
        self._mouse_last_pos = QPoint()
        self._opaque = True

        # ── Command history ──
        self._history: list[str] = []
        self._hist_idx = -1          # -1 = not browsing
        self._hist_saved = ""        # saved input while browsing

        # ── Layout ──
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Output (read-only QTextEdit)
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setAcceptRichText(False)
        self._output.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self._output.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        layout.addWidget(self._output, 1)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #444; max-height: 1px;")
        layout.addWidget(sep)

        # Input (QLineEdit — provides native cursor + editing)
        self._input = QLineEdit()
        self._input.setPlaceholderText("")
        self._input.returnPressed.connect(self._on_enter)
        # Intercept Up/Down arrows for history
        self._input.installEventFilter(self)
        layout.addWidget(self._input)

        # ── Theme ──
        self._theme = get_theme(cfg.ui.theme if cfg else "campbell")
        self._apply_theme()

        # ── Shortcuts ──
        self._setup_shortcuts()

        # Focus the input
        self._input.setFocus()

    # ── Send command ──────────────────────────────────────────────────

    def eventFilter(self, obj, event):
        """Intercept Up/Down arrows in the input field for history."""
        from PyQt6.QtCore import QEvent
        if obj is self._input and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Up:
                self._history_up()
                return True
            if key == Qt.Key.Key_Down:
                self._history_down()
                return True
        return super().eventFilter(obj, event)

    def _history_up(self):
        """Load the previous command from history."""
        if not self._history:
            return
        if self._hist_idx == -1:
            self._hist_saved = self._input.text()
            self._hist_idx = len(self._history) - 1
        elif self._hist_idx > 0:
            self._hist_idx -= 1
        self._input.setText(self._history[self._hist_idx])
        self._input.setCursorPosition(len(self._input.text()))

    def _history_down(self):
        """Load the next command from history."""
        if self._hist_idx < 0:
            return
        if self._hist_idx < len(self._history) - 1:
            self._hist_idx += 1
            self._input.setText(self._history[self._hist_idx])
        else:
            self._hist_idx = -1
            self._input.setText(self._hist_saved)
        self._input.setCursorPosition(len(self._input.text()))

    def _on_enter(self):
        """Send the current input line to the shell."""
        cmd = self._input.text()
        self._input.clear()
        self._hist_idx = -1
        self._hist_saved = ""
        if cmd.strip():
            self._history.append(cmd)
        if not self.parent_engine or not self.parent_engine.is_ready:
            return
        # Send to shell
        self.parent_engine.write(cmd + "\r")

    # ── Theme & Style ──────────────────────────────────────────────────

    def _apply_theme(self):
        ui = self._cfg.ui if self._cfg else None
        ff = ui.font_family if ui else "Cascadia Code"
        fs = ui.font_size if ui else 14

        bg = self._theme.background
        fg = self._theme.foreground
        sel_bg = self._theme.selection_bg
        sel_fg = self._theme.selection_fg

        self._output.setStyleSheet(
            f"QTextEdit {{ background-color: {bg}; color: {fg}; "
            f"font-family: '{ff}', 'Consolas', monospace; font-size: {fs}px; "
            f"padding: 10px; border: none; "
            f"selection-background-color: {sel_bg}; selection-color: {sel_fg}; }}"
        )
        self._input.setStyleSheet(
            f"QLineEdit {{ background-color: {bg}; color: {fg}; "
            f"font-family: '{ff}', 'Consolas', monospace; font-size: {fs}px; "
            f"padding: 8px 10px; border: none; "
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
                cursor.insertText(span.text,
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
                cursor.deleteChar()

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
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(f"\n{text}\n")
        self._output.setTextCursor(cursor)
        self._output.ensureCursorVisible()

    # ── Focus proxy ────────────────────────────────────────────────────

    def setFocus(self, reason=Qt.FocusReason.OtherFocusReason):
        self._input.setFocus(reason)

    # ── Copy / Paste ───────────────────────────────────────────────────

    def _copy_selection(self):
        cursor = self._output.textCursor()
        if cursor.hasSelection():
            QApplication.clipboard().setText(cursor.selectedText())

    def _paste_clipboard(self):
        cb = QApplication.clipboard()
        text = cb.text()
        if text:
            self._input.insert(text)

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

    def mousePressEvent(self, event: QMouseEvent):
        if not self._mouse.is_active or not self.parent_engine:
            super().mousePressEvent(event)
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

    def mouseReleaseEvent(self, event: QMouseEvent):
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

    def mouseMoveEvent(self, event: QMouseEvent):
        if not self._mouse.is_active or not self.parent_engine:
            return
        col, row = self._pos_to_cell(event.position().toPoint())
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        alt = bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)
        seq = self._mouse.encode_motion(col, row, 0, shift, ctrl, alt)
        if seq and self.parent_engine.is_ready:
            self.parent_engine.write(seq)

    def wheelEvent(self, event: QMouseEvent):
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

    def __init__(self, cfg=None, plain_mode=False):
        super().__init__()
        self._cfg = cfg
        self._plain_mode = plain_mode
        self._settings = QSettings("OmniTerm", "OmniTerm")
        self._tab_engines: dict[int, "TerminalEngine"] = {}

        self.setWindowTitle("OmniTerm")
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

        # ── Search bar ──
        self._search_bar = SearchBar(self)
        self._search_bar.hide()

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
        self.new_tab()

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
        action = menu.addAction("Manage Profiles...")
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
        import sys
        import os

        # Get the path to the running executable or script
        if getattr(sys, 'frozen', False):
            exe = sys.executable
        else:
            exe = sys.executable  # python.exe

        # Build args to pass to the elevated instance
        args = [f"--shell", f"{profile.command} {' '.join(profile.args)}".strip()]

        params = " ".join(f'"{a}"' for a in args)

        # Use ShellExecuteW with "runas" — triggers UAC
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", exe, params, None, 1
        )
        if result <= 32:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Admin",
                "Failed to launch as admin. User may have cancelled UAC.")

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

        # ── File ──
        file_menu = menu.addMenu("&File")
        _act(file_menu, "New &Tab", self.new_tab, "Ctrl+T")
        _act(file_menu, "&Close Tab", self._close_current_tab, "Ctrl+W")
        file_menu.addSeparator()
        _act(file_menu, "&Profile Picker...", self._profile_picker, "Ctrl+Shift+N")
        _act(file_menu, "&Manage Profiles...", self._manage_profiles)
        file_menu.addSeparator()
        _act(file_menu, "E&xit", self.close, "Alt+F4")

        # ── Edit ──
        edit_menu = menu.addMenu("&Edit")
        _act(edit_menu, "&Copy", self._menu_copy, QKeySequence.StandardKey.Copy)
        _act(edit_menu, "Cu&t", self._menu_cut, QKeySequence.StandardKey.Cut)
        _act(edit_menu, "&Paste", self._menu_paste, QKeySequence.StandardKey.Paste)
        edit_menu.addSeparator()
        _act(edit_menu, "&Find...", self._open_search, "Ctrl+F")

        # ── View ──
        view_menu = menu.addMenu("&View")
        _act(view_menu, "Zoom &In", self._font_bigger, "Ctrl+=")
        _act(view_menu, "Zoom &Out", self._font_smaller, "Ctrl+-")
        _act(view_menu, "&Reset Zoom", self._font_reset, "Ctrl+0")
        view_menu.addSeparator()
        _act(view_menu, "Cycle &Theme", self._theme_cycle, "Ctrl+Shift+T")
        _act(view_menu, "Toggle &Transparency", self._toggle_opacity, "Ctrl+Shift+O")
        view_menu.addSeparator()
        _act(view_menu, "Toggle Window &RTL", self._toggle_rtl_window)

        # ── Text Direction ──
        text_menu = menu.addMenu("Te&xt Direction")
        _act(text_menu, "Toggle &Line RTL", self._toggle_rtl_line)

        # ── Tools ──
        tools_menu = menu.addMenu("&Tools")
        _act(tools_menu, "&SSH Connect...", self._ssh_connect, "Ctrl+Shift+S")
        _act(tools_menu, "&Serial Connect...", self._serial_connect, "Ctrl+Shift+R")
        _act(tools_menu, "&WSL Connect...", self._wsl_connect, "Ctrl+Shift+U")

        # ── Window ──
        win_menu = menu.addMenu("&Window")
        _act(win_menu, "N&ext Tab", self._next_tab, "Ctrl+Tab")
        _act(win_menu, "&Previous Tab", self._prev_tab, "Ctrl+Shift+Tab")

    def _menu_copy(self):
        widget = self._tabs.currentWidget()
        if isinstance(widget, TerminalWidget):
            widget._copy_selection()

    def _menu_cut(self):
        widget = self._tabs.currentWidget()
        if isinstance(widget, TerminalWidget):
            widget._copy_selection()
            cursor = widget.textCursor()
            if cursor.hasSelection():
                cursor.removeSelectedText()

    def _menu_paste(self):
        widget = self._tabs.currentWidget()
        if isinstance(widget, TerminalWidget):
            widget._paste_clipboard()

    def _toggle_rtl_line(self):
        widget = self._tabs.currentWidget()
        if not isinstance(widget, TerminalWidget):
            return
        cursor = widget.textCursor()
        block = cursor.block()
        fmt = block.charFormat()
        if fmt.layoutDirection() == Qt.LayoutDirection.RightToLeft:
            fmt.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        else:
            fmt.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        cursor.setBlockCharFormat(fmt)

    def _toggle_rtl_window(self):
        if self.layoutDirection() == Qt.LayoutDirection.RightToLeft:
            new_dir = Qt.LayoutDirection.LeftToRight
        else:
            new_dir = Qt.LayoutDirection.RightToLeft
        self.setLayoutDirection(new_dir)
        # Propagate to output and input widgets
        for w in (self._output, self._input):
            w.setLayoutDirection(new_dir)

    # ── Tab management ─────────────────────────────────────────────────

    def _close_tab(self, index: int) -> None:
        """Close the tab at *index*."""
        if self._tabs.count() <= 1:
            self.close()
            return

        engine = self._tab_engines.pop(index, None)
        widget = self._tabs.widget(index)

        if engine:
            # Disconnect signals before killing to avoid referencing deleted widget
            try:
                engine.signals.exited.disconnect()
                engine.signals.text_ready.disconnect()
            except (RuntimeError, TypeError):
                pass
            engine.kill()

        self._tabs.removeTab(index)
        if widget:
            widget.deleteLater()

    def _close_current_tab(self) -> None:
        idx = self._tabs.currentIndex()
        if idx >= 0:
            self._close_tab(idx)

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
        idx = self._tabs.indexOf(terminal)
        if idx >= 0:
            self._close_tab(idx)

    @staticmethod
    def _shell_title(shell: str) -> str:
        """Derive a short tab title from the shell command."""
        name = shell.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        name = name.replace(".exe", "")
        return name

    # ── Actions ────────────────────────────────────────────────────────

    def _open_search(self) -> None:
        """Open the search bar and attach it to the current terminal."""
        widget = self._tabs.currentWidget()
        if isinstance(widget, TerminalWidget):
            self._search_bar.attach(widget)
            self._search_bar.open_bar()

    def _profile_picker(self) -> None:
        """Open the profile picker dialog and launch the selected shell."""
        if not self._cfg:
            return
        dlg = ProfilePickerDialog(self._cfg, self)
        if dlg.exec():
            cmd, args = dlg.get_command()
            full_cmd = cmd
            if args:
                full_cmd = f"{cmd} {' '.join(args)}"
            self.new_tab(shell=full_cmd)

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
        engine.signals.exited.connect(lambda _: self._on_tab_process_exited(terminal))

        title = f"ssh:{username}@{host}"
        idx = self._tabs.addTab(terminal, title)
        self._tab_engines[idx] = engine
        self._tabs.setCurrentIndex(idx)

        success = engine.start_ssh(
            host=host, port=port, username=username,
            password=password, key_filename=key_filename,
        )
        if not success:
            terminal.append_shell_text("[SSH connection failed]\n")

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
        engine.signals.exited.connect(lambda _: self._on_tab_process_exited(terminal))

        title = f"serial:{port}"
        idx = self._tabs.addTab(terminal, title)
        self._tab_engines[idx] = engine
        self._tabs.setCurrentIndex(idx)

        success = engine.start_serial(
            port=port, baudrate=baudrate, bytesize=bytesize,
            parity=parity, stopbits=stopbits,
        )
        if not success:
            terminal.append_shell_text("[Serial connection failed]\n")

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
                distribution: str | None = None, admin: bool = False) -> int:
        """Open a new tab running *shell* or WSL. Returns the tab index."""
        from terminal_core import TerminalEngine

        terminal = TerminalWidget(cfg=self._cfg, plain_mode=self._plain_mode)
        engine = TerminalEngine()

        terminal.parent_engine = engine
        engine.signals.text_ready.connect(terminal.append_shell_text)
        engine.signals.exited.connect(terminal.show_exit_message)
        engine.signals.exited.connect(lambda _: self._on_tab_process_exited(terminal))

        if wsl:
            cmd = WSLManager.get_shell_command(distribution)
            title = f"wsl:{distribution or 'default'}"
        else:
            cmd = shell
            title = self._shell_title(shell)

        if admin:
            title += " [Admin]"

        idx = self._tabs.addTab(terminal, title)
        self._tab_engines[idx] = engine
        self._tabs.setCurrentIndex(idx)

        engine.start(cmd, admin=admin)

        engine.start(cmd)
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
        self.kill_all_engines()
        self._settings.setValue("window/geometry", self.saveGeometry())
        self._settings.setValue("window/state", self.saveState())
        super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        widget = self._tabs.currentWidget()
        if widget and hasattr(widget, "setFocus"):
            widget.setFocus()

    def kill_all_engines(self) -> None:
        """Kill all tab engines. Called on window close."""
        for engine in self._tab_engines.values():
            engine.kill()
        self._tab_engines.clear()
