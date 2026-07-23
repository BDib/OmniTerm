## Description

Toggling RTL (Right-to-Left) mode should visually move all text to the right side of the terminal and change text alignment. Currently, toggling RTL only causes bidi reordering (swapping character order within lines) but the text remains anchored to the left side of the screen.

## Expected Behavior

When RTL is toggled:
- All text should visually move to the right side of the terminal
- New text should be right-aligned
- The layout direction should change the entire terminal appearance

## Actual Behavior

- Text characters get reordered (bidi algorithm runs) — e.g., "Hello World" becomes "dlroW olleH"
- But the text block stays left-aligned
- `document().setDefaultTextDirection()` is called but QTextEdit's internal LTR layout overrides it
- `setLayoutDirection()` on the widget changes the scrollbar but not the text alignment
- `blockFormat().setAlignment()` doesn't persist because QTextEdit resets it on the next layout pass

## Root Cause

QTextEdit's layout engine has an inherent LTR bias. Even when `setLayoutDirection(Qt.RightToLeft)` is called on the widget, the text blocks remain left-aligned because QTextEdit doesn't fully support RTL layout for programmatically inserted text. The `setAlignment()` on block format is overridden by the widget's internal layout logic.

## Files Involved

- `src/terminal_ui.py` — `_toggle_rtl_window()` method (line ~915), `_toggle_rtl_line()` method (line ~911)
- The `TerminalScreen` class (QTextEdit subclass) — may need overrides for RTL support

## Suggested Investigation

1. Check if `QTextOption.setAlignment()` on the document level works better than block-level alignment
2. Try setting `self._output.document().setDefaultTextOption(option)` where option has RTL alignment
3. Consider using `QWidget.setLayoutDirection()` at the QPalette level instead of widget level
4. Look into whether `QTextEdit` needs a custom `QTextLayout` or `QAbstractTextDocumentLayout` for proper RTL support
5. Test if the issue is specific to text inserted via `cursor.insertText()` vs text set via `setPlainText()`
6. Check Qt6 documentation for QTextEdit RTL limitations — there may be a known issue

## Environment

- Windows 11, Python 3.13
- Built with PyInstaller (also affects Nuitka and Python interpreter runs)
- v2.4.4
