import re

from PyQt6.QtWidgets import (
    QMainWindow, QTextEdit, QApplication, QInputDialog,
    QScrollBar, QWidget, QVBoxLayout, QTabWidget, QSplitter,
    QMenuBar, QMenu,
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

class TerminalWidget(QTextEdit):
    """QTextEdit subclass that forwards keyboard input to a PTY and renders
    plain-text output from the PTY read thread."""

    def __init__(self, parent=None, cfg=None, plain_mode=False):
        super().__init__(parent)
        self.parent_engine = None
        self._cfg = cfg
        self._plain_mode = plain_mode
        self._saved_cursor_pos = 0
        self._mouse = MouseHandler()
        self._mouse_last_pos = QPoint()

        self.setAcceptRichText(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursorWidth(_CURSOR_WIDTHS.get(cfg.ui.cursor_style if cfg else "bar", 2))
        self.setReadOnly(False)
        self.setMouseTracking(True)  # Enable mouse move events

        # Load theme and apply
        self._theme = get_theme(cfg.ui.theme if cfg else "campbell")
        self._apply_theme()

        # ── Shortcuts ──
        self._setup_shortcuts()

    # ── Theme & Style ──────────────────────────────────────────────────

    def _apply_theme(self):
        ui = self._cfg.ui if self._cfg else None
        ff = ui.font_family if ui else "Cascadia Code"
        fs = ui.font_size if ui else 14

        self.setStyleSheet(self._theme.stylesheet(ff, fs))

        # Cursor style
        style = (ui.cursor_style if ui else "bar")
        width = _CURSOR_WIDTHS.get(style, 2)
        self.setCursorWidth(width)

        if style == "block":
            pal = self.palette()
            pal.setColor(QPalette.ColorRole.Text, QColor(self._theme.background))
            self.setPalette(pal)
        else:
            pal = self.palette()
            pal.setColor(QPalette.ColorRole.Text, QColor(self._theme.foreground))
            self.setPalette(pal)

        # Cursor blink
        blink = ui.cursor_blink if ui else True
        QApplication.setCursorFlashTime(1000 if blink else 0)

    def apply_theme_by_name(self, name: str):
        """Switch to a named theme at runtime."""
        self._theme = get_theme(name)
        if self._cfg:
            self._cfg.ui.theme = name
        self._apply_theme()

    def cycle_theme(self):
        """Advance to the next built-in theme."""
        names = list_themes()
        try:
            idx = names.index(self._cfg.ui.theme if self._cfg else "campbell")
        except ValueError:
            idx = -1
        next_idx = (idx + 1) % len(names)
        self.apply_theme_by_name(names[next_idx])

    def apply_font_size(self, size: int):
        """Change the font size at runtime."""
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
        """Switch cursor style at runtime."""
        if self._cfg:
            self._cfg.ui.cursor_style = style
        self._apply_theme()

    # ── Shortcuts ──────────────────────────────────────────────────────

    def _setup_shortcuts(self):
        # Font size
        QShortcut(QKeySequence("Ctrl+="), self).activated.connect(self.increase_font_size)
        QShortcut(QKeySequence("Ctrl+-"), self).activated.connect(self.decrease_font_size)
        QShortcut(QKeySequence("Ctrl+0"), self).activated.connect(self.reset_font_size)

        # Theme cycle
        QShortcut(QKeySequence("Ctrl+Shift+T"), self).activated.connect(self.cycle_theme)

        # Theme picker dialog
        QShortcut(QKeySequence("Ctrl+,"), self).activated.connect(self._pick_theme)

        # Opacity toggle
        self._opaque = True
        QShortcut(QKeySequence("Ctrl+Shift+O"), self).activated.connect(self._toggle_opacity)

        # Copy / Paste
        QShortcut(QKeySequence.StandardKey.Copy, self).activated.connect(
            self._copy_selection
        )
        QShortcut(QKeySequence.StandardKey.Paste, self).activated.connect(
            self._paste_clipboard
        )

    # ── Dialogs ────────────────────────────────────────────────────────

    def _pick_theme(self):
        """Show a theme-picker dialog."""
        names = list_themes()
        current = self._cfg.ui.theme if self._cfg else "campbell"
        try:
            idx = names.index(current)
        except ValueError:
            idx = 0
        name, ok = QInputDialog.getItem(
            self, "Select Theme", "Theme:", names, idx, False
        )
        if ok and name:
            self.apply_theme_by_name(name)

    # ── Opacity toggle ─────────────────────────────────────────────────

    def _toggle_opacity(self):
        window = self.window()
        if self._opaque:
            opacity = self._cfg.ui.opacity if self._cfg else 0.98
            window.setWindowOpacity(opacity)
            self._opaque = False
        else:
            window.setWindowOpacity(1.0)
            self._opaque = True

    # ── PTY output → screen ────────────────────────────────────────────

    @pyqtSlot(str)
    def append_shell_text(self, text: str):
        """Parse ANSI escapes and render styled text into the widget.

        Append-only renderer with line-level overwrite support for \\r.
        """
        if self._plain_mode:
            clean = strip_ansi(text)
            clean = "".join(c for c in clean if ord(c) >= 32 or c in "\n\r\t")
            if not clean:
                return
            self.moveCursor(QTextCursor.MoveOperation.End)
            self.insertPlainText(clean)
            self.ensureCursorVisible()
            return

        spans = parse_ansi(text)
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        for span in spans:
            if span.kind == SpanKind.TEXT:
                fmt = span_to_format(span.sgr, self._theme)
                cursor.insertText(span.text, fmt)

            elif span.kind == SpanKind.NEWLINE:
                cursor.insertText("\n")

            elif span.kind == SpanKind.CARRIAGE_RETURN:
                pass  # Ignored — QTextEdit is append-only

            elif span.kind == SpanKind.TAB:
                cursor.insertText("    ")

            elif span.kind == SpanKind.BACKSPACE:
                cursor.deleteChar()

            elif span.kind == SpanKind.MOUSE_MODE:
                parts = span.text.split(",")
                if len(parts) == 2 and parts[0].isdigit():
                    self._mouse.set_mode(int(parts[0]), parts[1] == "h")

            # Ignored: ERASE_DISPLAY, ERASE_LINE, CURSOR_*,
            # SAVE/RESTORE, SCROLL — QTextEdit is not a grid terminal.

        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    @pyqtSlot(str)
    def show_exit_message(self, text: str):
        """Called by the engine when the PTY process exits."""
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.insertPlainText(f"\n{text}\n")
        self.ensureCursorVisible()

    # ── Keyboard → PTY ─────────────────────────────────────────────────

    def keyPressEvent(self, event):
        if not self.parent_engine or not self.parent_engine.is_ready:
            return

        key = event.key()
        text = event.text()
        mods = event.modifiers()

        # ── Enter / Return ──
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.parent_engine.write("\r")
            return

        # ── Backspace ──
        if key == Qt.Key.Key_Backspace:
            self.parent_engine.write("\b")
            return

        # ── Tab ──
        if key == Qt.Key.Key_Tab:
            self.parent_engine.write("\t")
            return

        # ── Delete ──
        if key == Qt.Key.Key_Delete:
            self.parent_engine.write("\x1b[3~")
            return

        # ── Arrow keys ──
        arrow_map = {
            Qt.Key.Key_Up: "A",
            Qt.Key.Key_Down: "B",
            Qt.Key.Key_Right: "C",
            Qt.Key.Key_Left: "D",
        }
        if key in arrow_map:
            if mods & Qt.KeyboardModifier.ControlModifier:
                self.parent_engine.write(f"\x1b[1;5{arrow_map[key]}")
            else:
                self.parent_engine.write(f"\x1b[{arrow_map[key]}")
            return

        # ── Home / End ──
        if key == Qt.Key.Key_Home:
            self.parent_engine.write("\x1b[H")
            return
        if key == Qt.Key.Key_End:
            self.parent_engine.write("\x1b[F")
            return

        # ── Page Up / Page Down ──
        if key == Qt.Key.Key_PageUp:
            self.parent_engine.write("\x1b[5~")
            return
        if key == Qt.Key.Key_PageDown:
            self.parent_engine.write("\x1b[6~")
            return

        # ── Escape ──
        if key == Qt.Key.Key_Escape:
            self.parent_engine.write("\x1b")
            return

        # ── Ctrl combinations ──
        if mods & Qt.KeyboardModifier.ControlModifier:
            code = text.lower() if text else ""
            ctrl_map = {
                "c": "\x03",
                "d": "\x04",
                "z": "\x1a",
                "l": "\x0c",
                "a": "\x01",
                "e": "\x05",
                "k": "\x0b",
                "u": "\x15",
                "w": "\x17",
            }
            if code in ctrl_map:
                self.parent_engine.write(ctrl_map[code])
                return

        # ── Fallback: printable characters ──
        if text:
            self.parent_engine.write(text)

    # ── Copy / Paste ───────────────────────────────────────────────────

    def _copy_selection(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            QApplication.clipboard().setText(cursor.selectedText())

    def _paste_clipboard(self):
        cb = QApplication.clipboard()
        text = cb.text()
        if text and self.parent_engine and self.parent_engine.is_ready:
            self.parent_engine.write(text)

    # ── Mouse events ───────────────────────────────────────────────────

    def _pos_to_cell(self, pos: QPoint) -> tuple[int, int]:
        """Convert a pixel position to (col, row) in character cells."""
        cursor = self.cursorForPosition(pos)
        block = cursor.blockNumber()
        col = cursor.positionInBlock() + 1
        row = block + 1
        return col, row

    def mousePressEvent(self, event: QMouseEvent):
        if not self._mouse.is_active or not self.parent_engine:
            super().mousePressEvent(event)
            return

        col, row = self._pos_to_cell(event.position().toPoint())
        button = 0
        if event.button() == Qt.MouseButton.LeftButton:
            button = 0
        elif event.button() == Qt.MouseButton.MiddleButton:
            button = 1
        elif event.button() == Qt.MouseButton.RightButton:
            button = 2
        else:
            super().mousePressEvent(event)
            return

        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        alt = bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)

        seq = self._mouse.encode_press(col, row, button, shift, ctrl, alt)
        if seq and self.parent_engine.is_ready:
            self.parent_engine.write(seq)

        self._mouse_last_pos = event.position().toPoint()
        # Still allow normal selection when not in mouse tracking
        # (handled by super() for text selection)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if not self._mouse.is_active or not self.parent_engine:
            super().mouseReleaseEvent(event)
            return

        col, row = self._pos_to_cell(event.position().toPoint())
        button = 0
        if event.button() == Qt.MouseButton.LeftButton:
            button = 0
        elif event.button() == Qt.MouseButton.MiddleButton:
            button = 1
        elif event.button() == Qt.MouseButton.RightButton:
            button = 2

        seq = self._mouse.encode_release(col, row, button)
        if seq and self.parent_engine.is_ready:
            self.parent_engine.write(seq)

    def mouseMoveEvent(self, event: QMouseEvent):
        if not self._mouse.is_active or not self.parent_engine:
            super().mouseMoveEvent(event)
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
            super().wheelEvent(event)
            return

        col, row = self._pos_to_cell(event.position().toPoint())
        angle = event.angleDelta().y()
        if angle > 0:
            button = 64  # scroll up
        elif angle < 0:
            button = 65  # scroll down
        else:
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

        # ── Menu bar ──
        self._build_menu_bar()

        # ── Search bar ──
        self._search_bar = SearchBar(self)
        self._search_bar.hide()

        # ── Built-in shortcuts ──
        QShortcut(QKeySequence("Ctrl+T"), self).activated.connect(self.new_tab)
        QShortcut(QKeySequence("Ctrl+W"), self).activated.connect(self._close_current_tab)
        QShortcut(QKeySequence("Ctrl+Tab"), self).activated.connect(self._next_tab)
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self).activated.connect(self._prev_tab)
        QShortcut(QKeySequence("Ctrl+Shift+D"), self).activated.connect(
            lambda: self._split(Qt.Orientation.Horizontal)
        )
        QShortcut(QKeySequence("Ctrl+Shift+Backslash"), self).activated.connect(
            lambda: self._split(Qt.Orientation.Vertical)
        )
        QShortcut(QKeySequence("Ctrl+Shift+N"), self).activated.connect(self._profile_picker)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self).activated.connect(self._ssh_connect)
        QShortcut(QKeySequence("Ctrl+Shift+R"), self).activated.connect(self._serial_connect)
        QShortcut(QKeySequence("Ctrl+Shift+U"), self).activated.connect(self._wsl_connect)
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self._open_search)
        QShortcut(QKeySequence("Ctrl+="), self).activated.connect(self._font_bigger)
        QShortcut(QKeySequence("Ctrl+-"), self).activated.connect(self._font_smaller)
        QShortcut(QKeySequence("Ctrl+0"), self).activated.connect(self._font_reset)
        QShortcut(QKeySequence("Ctrl+Shift+T"), self).activated.connect(self._theme_cycle)
        QShortcut(QKeySequence("Ctrl+,"), self).activated.connect(self._theme_picker)
        QShortcut(QKeySequence("Ctrl+Shift+O"), self).activated.connect(self._toggle_opacity)

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
        _act(win_menu, "Split &Horizontal",
             lambda: self._split(Qt.Orientation.Horizontal), "Ctrl+Shift+D")
        _act(win_menu, "Split &Vertical",
             lambda: self._split(Qt.Orientation.Vertical), "Ctrl+Shift+Backslash")
        win_menu.addSeparator()
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
        from PyQt6.QtCore import Qt as QtDir
        if fmt.layoutDirection() == QtDir.LayoutDirection.RightToLeft:
            fmt.setLayoutDirection(QtDir.LayoutDirection.LeftToRight)
        else:
            fmt.setLayoutDirection(QtDir.LayoutDirection.RightToLeft)
        cursor.setBlockCharFormat(fmt)

    def _toggle_rtl_window(self):
        if self.layoutDirection() == Qt.LayoutDirection.RightToLeft:
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        else:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

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
        """Update tab title when the shell process exits."""
        idx = self._tabs.indexOf(terminal)
        if idx >= 0:
            self._tabs.setTabText(idx, "[exited]")

    @staticmethod
    def _shell_title(shell: str) -> str:
        """Derive a short tab title from the shell command."""
        name = shell.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        name = name.replace(".exe", "")
        return name

    # ── Split panes ────────────────────────────────────────────────────

    def _split(self, orientation: Qt.Orientation) -> None:
        """Split the current tab's terminal horizontally or vertically."""
        current = self._tabs.currentWidget()
        if not current or not isinstance(current, TerminalWidget):
            return

        # Create a new terminal for the split
        new_terminal = TerminalWidget(cfg=self._cfg, plain_mode=self._plain_mode)
        from terminal_core import TerminalEngine
        engine = TerminalEngine()
        new_terminal.parent_engine = engine
        engine.signals.text_ready.connect(new_terminal.append_shell_text)
        engine.signals.exited.connect(new_terminal.show_exit_message)
        engine.start("cmd.exe")

        # Replace the single widget with a splitter
        splitter = QSplitter(orientation)
        splitter.addWidget(current)
        splitter.addWidget(new_terminal)

        idx = self._tabs.indexOf(current)
        self._tabs.removeTab(idx)
        self._tabs.insertTab(idx, splitter, self._tabs.tabText(idx))
        self._tabs.setCurrentIndex(idx)

        new_terminal.setFocus()

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
                distribution: str | None = None) -> int:
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

        idx = self._tabs.addTab(terminal, title)
        self._tab_engines[idx] = engine
        self._tabs.setCurrentIndex(idx)

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
            "split_horizontal": lambda: self._split(Qt.Orientation.Horizontal),
            "split_vertical": lambda: self._split(Qt.Orientation.Vertical),
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
