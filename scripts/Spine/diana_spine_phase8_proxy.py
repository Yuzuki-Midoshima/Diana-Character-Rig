# -*- coding: utf-8 -*-
"""Independent, registry-backed Phase 8 correction proxies."""
from __future__ import absolute_import, division, print_function
import maya.cmds as cmds
from . import diana_spine_phase5_build as p5
from . import diana_spine_phase7_matcher as p7

ROOT = "DIANA_SPINE_P8_PROXY_GRP"
REGISTRY = "DIANA_SPINE_P8_REGISTRY"
PARTS = p7.PARTS


def _register(node):
    index = len(cmds.getAttr(REGISTRY + ".nodes", multiIndices=True) or [])
    cmds.connectAttr(node + ".message", "{}.nodes[{}]".format(REGISTRY, index))


def _node(kind, name, parent=None):
    node = cmds.createNode(kind, name=name, parent=parent) if parent else cmds.createNode(kind, name=name)
    _register(node); return node


def build():
    if cmds.objExists(ROOT) or cmds.objExists(REGISTRY):
        raise RuntimeError("Phase 8 proxy already exists")
    registry = cmds.createNode("network", name=REGISTRY)
    cmds.addAttr(registry, ln="nodes", at="message", multi=True)
    root = cmds.createNode("transform", name=ROOT); cmds.setAttr(root + ".inheritsTransform", 0); _register(root)
    data = {"fk_translation": {}, "ik_candidates": {x: {} for x in "ABDE"}}
    for part in PARTS:
        fk_ctrl = _node("transform", "DIANA_SPINE_P8_FK_{}_DELTA".format(part), root)
        fk_cm = _node("composeMatrix", "DIANA_SPINE_P8_FK_{}_DELTA_CM".format(part))
        fk_mm = _node("multMatrix", "DIANA_SPINE_P8_FK_{}_FINAL_MM".format(part))
        cmds.connectAttr(fk_ctrl + ".translate", fk_cm + ".inputTranslate")
        cmds.connectAttr(fk_ctrl + ".rotate", fk_cm + ".inputRotate")
        cmds.connectAttr(fk_cm + ".outputMatrix", fk_mm + ".matrixIn[0]")
        cmds.connectAttr(p5.PARTS[part] + ".worldMatrix[0]", fk_mm + ".matrixIn[1]")
        data["fk_translation"][part] = {"control": fk_ctrl, "output": fk_mm + ".matrixSum"}
        for candidate in "ABDE":
            enabled = (candidate in "DE" or (candidate == "A" and part == "MIDDLE") or
                       (candidate == "B" and part in ("LOWER", "MIDDLE")))
            ctrl = _node("transform", "DIANA_SPINE_P8_{}_{}_DELTA".format(candidate, part), root)
            cm = _node("composeMatrix", "DIANA_SPINE_P8_{}_{}_CM".format(candidate, part))
            mm = _node("multMatrix", "DIANA_SPINE_P8_{}_{}_MM".format(candidate, part))
            if enabled:
                cmds.connectAttr(ctrl + ".translate", cm + ".inputTranslate")
                if candidate in "DE": cmds.connectAttr(ctrl + ".rotate", cm + ".inputRotate")
            cmds.connectAttr(cm + ".outputMatrix", mm + ".matrixIn[0]")
            cmds.connectAttr("DIANA_SPINE_DEFORM_{}_MODE1_FINAL_MM.matrixSum".format(part), mm + ".matrixIn[1]")
            data["ik_candidates"][candidate][part] = {"control": ctrl, "output": mm + ".matrixSum",
                                                        "enabled": enabled}
    return data


def cleanup():
    nodes = cmds.listConnections(REGISTRY + ".nodes", s=True, d=False) or [] if cmds.objExists(REGISTRY) else []
    if nodes: cmds.delete([x for x in nodes if cmds.objExists(x)])
    if cmds.objExists(REGISTRY): cmds.delete(REGISTRY)
    return cmds.ls("DIANA_SPINE_P8_*") or []

