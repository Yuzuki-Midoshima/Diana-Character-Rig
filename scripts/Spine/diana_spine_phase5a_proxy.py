# -*- coding: utf-8 -*-
"""Build disposable left/right clavicle attachment proxies."""
from __future__ import absolute_import, division, print_function

import json
import os
import maya.api.OpenMaya as om
import maya.cmds as cmds

ROOT = "DIANA_SPINE_P5A_ATTACHMENT_PROXY_GRP"
REGISTRY = "DIANA_SPINE_P5A_REGISTRY"
MANIFEST = os.path.join(os.path.dirname(__file__),
                        "Character_spine37_phase5a_proxy_manifest.json")
SIDES = {"L": "L_clavice_jnt", "R": "R_clavice_jnt"}


def matrix(plug):
    value = cmds.getAttr(plug)
    value = value[0] if len(value) == 1 and isinstance(value[0], (list, tuple)) else value
    return [float(x) for x in value]


def _register(node):
    index = len(cmds.getAttr(REGISTRY + ".nodes", multiIndices=True) or [])
    cmds.connectAttr(node + ".message", "{}.nodes[{}]".format(REGISTRY, index))


def _node(node_type, name):
    node = cmds.createNode(node_type, name=name)
    _register(node)
    return node


def _constant(name, values):
    node = _node("fourByFourMatrix", name)
    for row in range(4):
        for column in range(4):
            cmds.setAttr("{}.in{}{}".format(node, row, column),
                         values[row * 4 + column])
    return node


def build(path=MANIFEST):
    scene = cmds.file(q=True, sn=True)
    if "PHASE5" not in os.path.basename(scene):
        raise RuntimeError("Refusing non-validation scene: " + scene)
    if cmds.objExists(ROOT) or cmds.objExists(REGISTRY):
        raise RuntimeError("Phase 5-A proxy already exists")
    shoulder = matrix("shoulder_fk_Spine_anim_jnt.worldMatrix[0]")
    root = cmds.createNode("transform", name=ROOT)
    cmds.setAttr(root + ".inheritsTransform", 0)
    registry = cmds.createNode("network", name=REGISTRY)
    cmds.addAttr(registry, ln="nodes", at="message", multi=True)
    _register(root)
    manifest = {"version": 1, "scene": scene, "shoulder_reference": shoulder,
                "production": {}, "proxies": {}, "created_nodes": []}
    shoulder_inverse = om.MMatrix(shoulder).inverse()
    for side, joint in SIDES.items():
        world = matrix(joint + ".worldMatrix[0]")
        offset = list(om.MMatrix(world) * shoulder_inverse)
        manifest["production"][side] = {"joint": joint, "worldMatrix": world,
                                         "parent": (cmds.listRelatives(joint, p=True, fullPath=True) or [None])[0]}
        offset_node = _constant("DIANA_SPINE_P5A_{}_CLAVICLE_OFFSET_FBF".format(side), offset)
        final = _node("multMatrix", "DIANA_SPINE_P5A_{}_CLAVICLE_FINAL_MM".format(side))
        cmds.connectAttr(offset_node + ".output", final + ".matrixIn[0]")
        cmds.connectAttr("DIANA_SPINE_DEFORM_SHOULDER_MODE_CHOICE.output",
                         final + ".matrixIn[1]")
        proxy = cmds.createNode("transform",
                                name="DIANA_SPINE_P5A_{}_CLAVICLE_PROXY".format(side),
                                parent=root)
        _register(proxy)
        cmds.connectAttr(final + ".matrixSum", proxy + ".offsetParentMatrix")
        manifest["proxies"][side] = {"proxy": proxy, "offset": offset,
                                      "final": final}
    manifest["created_nodes"] = sorted(set(
        (cmds.listConnections(REGISTRY + ".nodes", s=True, d=False) or []) + [REGISTRY]))
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=False, sort_keys=True)
    return manifest


if __name__ == "__main__":
    build()
