# -*- coding: utf-8 -*-
"""Diana pivot v3 bootstrap for Maya 2026.

Loaded from this repository's Maya module by ``scripts/userSetup.py``.
"""
import importlib
import maya.cmds as cmds
import maya.utils
import maya.api.OpenMaya as om

_SCENE_CALLBACKS = []
_STARTED = False

def _pivot_module():
    return importlib.import_module('Pivot_Transfer.diana_pivot_v3')

def _activate():
    try:
        module = _pivot_module()
        if all(cmds.objExists(n) for n in ('Body_Rot_Pivot_anim', 'Body_Rot_SYSTEM_GRP')):
            module.install()
            print('[DIANA AUTO] Pivot sync installed')
        else:
            module.uninstall()
            print('[DIANA AUTO] No Diana rig; sync inactive')
    except Exception as exc:
        cmds.warning('[DIANA AUTO] Activation failed: {}'.format(exc))

def _after_scene(*_):
    maya.utils.executeDeferred(_activate)

def start():
    global _STARTED
    if _STARTED:
        return
    _SCENE_CALLBACKS.append(om.MSceneMessage.addCallback(om.MSceneMessage.kAfterOpen, _after_scene))
    _SCENE_CALLBACKS.append(om.MSceneMessage.addCallback(om.MSceneMessage.kAfterNew, _after_scene))
    _STARTED = True
    _after_scene()
    print('[DIANA AUTO] Scene listeners registered')

def stop():
    global _STARTED
    for callback in _SCENE_CALLBACKS:
        om.MMessage.removeCallback(callback)
    _SCENE_CALLBACKS.clear()
    try:
        _pivot_module().uninstall()
    except Exception as exc:
        cmds.warning('[DIANA AUTO] Stop cleanup: {}'.format(exc))
    _STARTED = False
