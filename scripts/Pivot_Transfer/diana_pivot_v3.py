# -*- coding: utf-8 -*-
"""Diana pivot v3: suppress extra undo entries from pivot compensation.

Maya 2026 / Python 3. Run on a COPY of the working v2 scene.
This module does NOT rewire the rig or run prepare().
Undo behavior depends on Maya callback evaluation; test Undo/Redo before production.
"""
import maya.cmds as cmds
import maya.api.OpenMaya as om

CTRL = 'Body_Rot_Pivot_anim'
SYSTEM = 'Body_Rot_SYSTEM_GRP'
_callback = None
_busy = False


def _incoming(dst):
    return cmds.connectionInfo(dst, sourceFromDestination=True) or ''


def _require():
    for n in (CTRL, SYSTEM):
        if not cmds.objExists(n):
            raise RuntimeError('Missing node: ' + n)
    if cmds.listRelatives(SYSTEM, parent=True):
        raise RuntimeError('SYSTEM must be world-root.')
    for axis in 'XYZ':
        dst = SYSTEM + '.rotate' + axis
        if _incoming(dst) != CTRL + '.rotate' + axis:
            raise RuntimeError('Existing v2 rotation connection not found: ' + dst)
    if _incoming(SYSTEM + '.translate'):
        raise RuntimeError('SYSTEM translate is driven; expected prepared v2 rig.')


def _close(a, b, tol=1e-5):
    return all(abs(x-y) <= tol for x, y in zip(a, b))


def _sync():
    """Update pivot without adding extra Maya undo commands.

    This preserves SYSTEM world matrix for each pivot move. It is not an
    undoable command by itself; Undo/Redo needs interactive testing.
    """
    global _busy
    if _busy:
        return
    _busy = True
    try:
        before = cmds.xform(SYSTEM, q=True, ws=True, matrix=True)
        desired = cmds.xform(CTRL, q=True, ws=True, rp=True)
        current = cmds.xform(SYSTEM, q=True, ws=True, rp=True)
        if _close(desired, current):
            return
        was_enabled = bool(cmds.undoInfo(q=True, state=True))
        if was_enabled:
            # Unlike state=False, this keeps the existing Undo queue intact.
            cmds.undoInfo(stateWithoutFlush=False)
        try:
            cmds.xform(SYSTEM, ws=True, rp=desired, preserve=True)
        finally:
            if was_enabled:
                cmds.undoInfo(stateWithoutFlush=True)
        after = cmds.xform(SYSTEM, q=True, ws=True, matrix=True)
        if not _close(before, after, 1e-4):
            om.MGlobal.displayWarning('[DIANA V3] SYSTEM world matrix changed. Reopen backup if needed.')
    except Exception as exc:
        om.MGlobal.displayError('[DIANA V3] Pivot sync error: {}'.format(exc))
    finally:
        _busy = False


def _changed(msg, plug, other, data):
    if not (msg & om.MNodeMessage.kAttributeSet):
        return
    try:
        name = plug.partialName(useLongNames=True)
        if name in ('translate', 'translateX', 'translateY', 'translateZ'):
            _sync()
    except Exception as exc:
        om.MGlobal.displayError('[DIANA V3] Callback error: {}'.format(exc))


def install():
    """Install v3 callback only. Does not modify connections or rig hierarchy."""
    global _callback
    _require()
    uninstall()
    sel = om.MSelectionList()
    sel.add(CTRL)
    _callback = om.MNodeMessage.addAttributeChangedCallback(sel.getDependNode(0), _changed)
    _sync()
    print('[DIANA V3] Active: pivot sync without additional undo entries.')


def uninstall():
    global _callback
    if _callback is not None:
        om.MMessage.removeCallback(_callback)
        _callback = None
    print('[DIANA V3] Callback stopped. Scene connections unchanged.')


def status():
    _require()
    print('Callback active:', _callback is not None)
    print('CTRL pivot:', cmds.xform(CTRL, q=True, ws=True, rp=True))
    print('SYSTEM pivot:', cmds.xform(SYSTEM, q=True, ws=True, rp=True))
    print('Undo enabled:', cmds.undoInfo(q=True, state=True))
