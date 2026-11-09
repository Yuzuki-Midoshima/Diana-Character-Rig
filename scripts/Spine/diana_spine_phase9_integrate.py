# -*- coding: utf-8 -*-
"""Manifest-backed production-copy integration of Phase 9 corrections."""
from __future__ import absolute_import, division, print_function
import datetime, json, os
import maya.cmds as cmds

ROOT = "DIANA_SPINE_P9_CORRECTION_GRP"
REGISTRY = "DIANA_SPINE_P9_REGISTRY"
MANIFEST = os.path.join(os.path.dirname(__file__), "Character_spine37_phase9_manifest.json")
PARTS = ("HIP", "LOWER", "MIDDLE", "SHOULDER")
MODES = (0, 1, 2)
ARM_SIDES = ("L", "R")


def source(plug): return cmds.connectionInfo(plug, sourceFromDestination=True) or ""


def connections(node):
    raw = cmds.listConnections(node, s=True, d=True, c=True, p=True, skipConversionNodes=False) or []
    return sorted((raw[i], raw[i+1]) for i in range(0, len(raw)-1, 2))


def capture(path=MANIFEST):
    scene = cmds.file(q=True, sn=True)
    name = os.path.basename(scene).upper()
    if not (("PHASE9" in name and "VALIDATION" in name) or "_SPINE_RC" in name):
        raise RuntimeError("Refusing scene that is neither validation nor Spine RC: " + scene)
    if cmds.objExists(ROOT) or cmds.objExists(REGISTRY): raise RuntimeError("Phase 9 already exists")
    data = {"version": 1, "created_utc": datetime.datetime.utcnow().isoformat()+"Z",
            "scene": scene, "choice_inputs": {}, "protected": {}, "created_nodes": []}
    for part in PARTS:
        choice = "DIANA_SPINE_DEFORM_{}_MODE_CHOICE".format(part)
        data["choice_inputs"][part] = {str(mode): source(choice+".input[{}]".format(mode)) for mode in MODES}
    for node in ("back_spine_curve", "RIG_spineStretch_MD", "DIANA_SPINE_INDEPENDENT_IK_CURVE",
                 "L_ARM_IK_SPACE_PC", "R_ARM_IK_SPACE_PC", "Terminal"):
        data["protected"][node] = connections(node)
    with open(path, "w", encoding="utf-8") as stream: json.dump(data, stream, indent=2, ensure_ascii=False, sort_keys=True)
    return data


def _register(node):
    index = len(cmds.getAttr(REGISTRY+".nodes", multiIndices=True) or [])
    cmds.connectAttr(node+".message", "{}.nodes[{}]".format(REGISTRY,index))


def _node(kind, name, parent=None):
    node = cmds.createNode(kind, name=name, parent=parent) if parent else cmds.createNode(kind, name=name)
    _register(node); return node


def control(part, mode): return "DIANA_SPINE_P9_{}_MODE{}_CORR".format(part, mode)
def arm_control(side, mode): return "DIANA_SPINE_P9_{}_ARM_MODE{}_CORR".format(side, mode)


def build(path=MANIFEST):
    manifest = capture(path)
    registry = cmds.createNode("network", name=REGISTRY); cmds.addAttr(registry, ln="nodes", at="message", multi=True)
    root = cmds.createNode("transform", name=ROOT); cmds.setAttr(root+".inheritsTransform", 0); cmds.setAttr(root+".visibility", 0); _register(root)
    for part in PARTS:
        choice = "DIANA_SPINE_DEFORM_{}_MODE_CHOICE".format(part)
        for mode in MODES:
            old = manifest["choice_inputs"][part][str(mode)]
            if not old: raise RuntimeError("Missing source: {}.input[{}]".format(choice, mode))
            ctrl = _node("transform", control(part, mode), root)
            cmds.addAttr(ctrl, ln="snapCorrection", at="bool", dv=1); cmds.setAttr(ctrl+".snapCorrection", keyable=False, channelBox=False)
            cm = _node("composeMatrix", ctrl+"_CM")
            mm = _node("multMatrix", ctrl+"_MM")
            cmds.connectAttr(ctrl+".translate", cm+".inputTranslate")
            cmds.connectAttr(ctrl+".rotate", cm+".inputRotate")
            cmds.connectAttr(cm+".outputMatrix", mm+".matrixIn[0]")
            cmds.connectAttr(old, mm+".matrixIn[1]")
            destination = choice+".input[{}]".format(mode)
            cmds.disconnectAttr(old, destination)
            cmds.connectAttr(mm+".matrixSum", destination)
    manifest["arm_choice_inputs"] = {}
    for side in ARM_SIDES:
        choice = "DIANA_SPINE_{}_arm_GRP_MODE_CHOICE".format(side)
        manifest["arm_choice_inputs"][side] = {}
        for mode in MODES:
            destination = choice+".input[{}]".format(mode); old = source(destination)
            if not old: raise RuntimeError("Missing source: " + destination)
            manifest["arm_choice_inputs"][side][str(mode)] = old
            ctrl = _node("transform", arm_control(side,mode), root)
            cm = _node("composeMatrix", ctrl+"_CM"); mm = _node("multMatrix", ctrl+"_MM")
            cmds.connectAttr(ctrl+".translate",cm+".inputTranslate"); cmds.connectAttr(ctrl+".rotate",cm+".inputRotate")
            cmds.connectAttr(cm+".outputMatrix",mm+".matrixIn[0]"); cmds.connectAttr(old,mm+".matrixIn[1]")
            cmds.disconnectAttr(old,destination); cmds.connectAttr(mm+".matrixSum",destination)
    manifest["created_nodes"] = sorted((cmds.listConnections(REGISTRY+".nodes", s=True, d=False) or [])+[REGISTRY])
    with open(path, "w", encoding="utf-8") as stream: json.dump(manifest, stream, indent=2, ensure_ascii=False, sort_keys=True)
    return manifest


if __name__ == "__main__": print(build())

