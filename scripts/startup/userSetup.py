# -*- coding: utf-8 -*-
"""Diana-only Maya startup. Install as userSetup.py in Maya scripts path."""
import os
import sys
import traceback
import maya.utils

# Override by setting DIANA_RIG_REPO environment variable if the repo moves.
REPO = os.environ.get('DIANA_RIG_REPO', os.path.join(
    os.path.expanduser('~'), 'OneDrive', 'ドキュメント', 'GitHub', 'Diana-Character-Rig'))


def _start():
    if not os.path.isfile(os.path.join(REPO, 'scripts', 'diana_pivot_autostart.py')):
        print('[DIANA] Repository not found:', REPO)
        return
    try:
        if REPO not in sys.path:
            sys.path.insert(0, REPO)
        from scripts import diana_pivot_autostart
        diana_pivot_autostart.start()
        print('[DIANA] Startup registered')
    except Exception:
        traceback.print_exc()


maya.utils.executeDeferred(_start)
