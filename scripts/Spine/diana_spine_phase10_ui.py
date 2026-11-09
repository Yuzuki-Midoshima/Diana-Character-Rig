# -*- coding: utf-8 -*-
"""Small animator-facing UI for safe Spine mode matching."""
from __future__ import absolute_import, division, print_function
import os
import maya.cmds as cmds
from . import diana_spine_phase9_matcher as matcher
from . import diana_spine_phase9_correction as correction
from . import diana_spine_phase9_integrate as p9

WINDOW="DianaSpineMatcherWindow";LABELS={0:"FK",1:"IK",2:"IK + FK"}
RC_NAME="Character_spine37_SPINE_RC01.ma"


def _mode():return int(cmds.getAttr(matcher.MODE))
def status():
    mode=_mode();active="ACTIVE" if not correction.is_zero(mode) else "zero"
    return "Mode: {} ({}) | Correction: {}".format(mode,LABELS[mode],active)
def _refresh(*_):
    if cmds.control(WINDOW+"Status",exists=True):cmds.text(WINDOW+"Status",e=True,label=status())
def switch(mode,*_):
    report=matcher.match(int(mode),key=False)
    if not report["success"]:cmds.warning("Spine match failed; values restored")
    _refresh();return report
def reset_inactive(*_):
    current=_mode();reports={m:correction.safe_reset(m,force=False) for m in p9.MODES if m!=current};_refresh();return reports
def safe_reset_current(*_):
    report=correction.safe_reset(_mode(),force=False)
    if not report["reset"]:cmds.warning(report["reason"]+"; snap/bake before clearing")
    _refresh();return report
def show():
    if not cmds.objExists(p9.ROOT):
        scene=cmds.file(q=True,sn=True) or "<unsaved scene>"
        imported=cmds.ls("*"+p9.ROOT,long=True) or []
        if imported:
            raise RuntimeError(
                "The Spine RC appears to have been imported into the current scene, "
                "so its nodes were renamed or prefixed (example: {}). Use File > Open "
                "Scene to open '{}' directly; do not use Import.".format(imported[0],RC_NAME))
        raise RuntimeError(
            "Diana Spine Phase 9 is not installed in the current scene. "
            "Current scene: {}. Open the validated RC '{}' first; this UI does not "
            "modify or auto-integrate ordinary production scenes.".format(scene,RC_NAME))
    if cmds.window(WINDOW,exists=True):cmds.deleteUI(WINDOW)
    cmds.window(WINDOW,title="Diana Spine Matcher",widthHeight=(300,180),sizeable=False)
    cmds.columnLayout(adjustableColumn=True,rowSpacing=6,columnAttach=("both",8))
    cmds.text(WINDOW+"Status",label=status(),height=28)
    cmds.button(label="Snap to FK",command=lambda *_:switch(0))
    cmds.button(label="Snap to IK",command=lambda *_:switch(1))
    cmds.button(label="Snap to IK + FK",command=lambda *_:switch(2))
    cmds.separator(height=8,style="in")
    cmds.button(label="Reset inactive corrections",command=reset_inactive)
    cmds.button(label="Safe reset current correction",command=safe_reset_current)
    cmds.showWindow(WINDOW);return WINDOW
