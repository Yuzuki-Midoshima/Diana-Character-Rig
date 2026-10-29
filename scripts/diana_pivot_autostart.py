# -*- coding: utf-8 -*-
"""Diana pivot v3 bootstrap for Maya 2026.

Loaded from this repository's ``scripts`` package by ``startup/userSetup.py``.
"""
import os
import sys
import importlib
import maya.cmds as cmds
import maya.utils
import maya.api.OpenMaya as om

_SCENE_CALLBACKS = []
_STARTED = False

def _pivot_module():
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Pivot_Transfer')
    path = os.path.join(folder, 'diana_pivot_v3.py')
    if not os.path.isfile(path):
        raise RuntimeError('Missing: ' + path)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    existing = sys.modules.get('diana_pivot_v3')
    if existing is not None:
        loaded = os.path.normcase(os.path.abspath(getattr(existing, '__file__', '')))
        if loaded != os.path.normcase(os.path.abspath(path)):
            raise RuntimeError('Conflicting diana_pivot_v3: ' + loaded)
    return importlib.import_module('diana_pivot_v3')

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
