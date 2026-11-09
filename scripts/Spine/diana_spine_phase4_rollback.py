# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function
import json, os
import maya.cmds as cmds
from Spine import diana_spine_phase4 as p4

def rollback(path=p4.MANIFEST_PATH):
    if not os.path.exists(path): raise RuntimeError("Manifest not found")
    with open(path,"r",encoding="utf-8") as f: m=json.load(f)
    for stage in reversed(m.get("stages",[])):
        part=stage["part"]; fk=p4.PARTS[part]
        dst="DIANA_SPINE_DEFORM_{}_MODE_CHOICE.input[2]".format(part)
        new=cmds.connectionInfo(dst,sourceFromDestination=True) or ""
        if new: cmds.disconnectAttr(new,dst)
        if stage["old_mode2_source"]: cmds.connectAttr(stage["old_mode2_source"],dst,force=True)
        if cmds.objExists(stage["follow"]): cmds.parent(fk,stage["original_parent"],relative=True)
    if cmds.objExists(p4.ROOT): cmds.delete(p4.ROOT)
    leftovers=cmds.ls("DIANA_SPINE_P4_*") or []
    if leftovers: cmds.delete(leftovers)
    print("[DIANA SPINE P4] Rolled back")
    return m
