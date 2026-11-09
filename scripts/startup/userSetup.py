# -*- coding: utf-8 -*-
"""Legacy compatibility entry point.

New installations use the repository's ``scripts/userSetup.py`` through a
Maya module. Do not copy this file over an existing userSetup.py.
"""
import traceback
import maya.utils


def _start():
    try:
        import diana_pivot_autostart
        diana_pivot_autostart.start()
        print('[DIANA] Startup registered')
    except Exception:
        traceback.print_exc()


maya.utils.executeDeferred(_start)
