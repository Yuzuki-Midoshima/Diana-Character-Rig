# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
import json
import maya.cmds as cmds
from . import diana_spine_phase9_integrate as p9


def rollback(path=p9.MANIFEST):
    with open(path,"r",encoding="utf-8") as stream: manifest=json.load(stream)
    for part in p9.PARTS:
        choice="DIANA_SPINE_DEFORM_{}_MODE_CHOICE".format(part)
        for mode in p9.MODES:
            dst=choice+".input[{}]".format(mode); current=p9.source(dst)
            if current: cmds.disconnectAttr(current,dst)
            old=manifest["choice_inputs"][part][str(mode)]
            if old: cmds.connectAttr(old,dst,force=True)
    for side,modes in manifest.get("arm_choice_inputs",{}).items():
        choice="DIANA_SPINE_{}_arm_GRP_MODE_CHOICE".format(side)
        for mode in p9.MODES:
            dst=choice+".input[{}]".format(mode);current=p9.source(dst)
            if current:cmds.disconnectAttr(current,dst)
            old=modes[str(mode)]
            if old:cmds.connectAttr(old,dst,force=True)
    nodes=cmds.listConnections(p9.REGISTRY+".nodes",s=True,d=False) or [] if cmds.objExists(p9.REGISTRY) else []
    if nodes: cmds.delete([x for x in nodes if cmds.objExists(x)])
    if cmds.objExists(p9.REGISTRY): cmds.delete(p9.REGISTRY)
    return {"remaining":cmds.ls("DIANA_SPINE_P9_*") or [],"root_exists":cmds.objExists(p9.ROOT)}

