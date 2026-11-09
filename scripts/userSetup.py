# -*- coding: utf-8 -*-
"""Maya startup entry point supplied by the DianaCharacterRig module.

This file lives inside the repository.  Installation never replaces the
user's own Maya ``userSetup.py``.
"""
import traceback

import maya.utils


def _start_diana():
    try:
        import diana_pivot_autostart
        diana_pivot_autostart.start()
        print("[DIANA] Startup registered")
    except Exception:
        traceback.print_exc()


maya.utils.executeDeferred(_start_diana)
