"""Maya shelf command for the Diana Pivot Transfer UI.

Paste the following into a Python shelf button::

    from Pivot_Transfer import Shelf
    Shelf.show()
"""
from importlib import import_module, reload


def show():
    """Reload and display the UI without modifying files or ``sys.path``."""
    pivot_ui = import_module("Pivot_Transfer.diana_pivot_transfer_ui")
    reload(pivot_ui)
    pivot_ui.show_ui()
    print("[DIANA] Pivot Transfer UI started")


if __name__ == "__main__":
    show()
