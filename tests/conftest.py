"""Pytest configuration for OmniTerm tests.

Ensures QApplication is created once and cleaned up properly
to avoid the PyQt6 shutdown crash (STATUS_STACK_BUFFER_OVERRUN).
"""
import sys
import pytest


@pytest.fixture(scope="session", autouse=True)
def qapp_session():
    """Create a single QApplication for the entire test session."""
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app
    # Process any pending events before shutdown
    app.processEvents()


@pytest.fixture(autouse=True)
def cleanup_qt():
    """Process pending Qt events after each test."""
    yield
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app:
        app.processEvents()
