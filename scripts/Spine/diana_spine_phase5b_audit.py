# -*- coding: utf-8 -*-
"""Read-only pre-integration audit for Phase 5-B arm attachments."""
from __future__ import absolute_import, division, print_function

import datetime
import json
import os
import re
import maya.cmds as cmds

OUTPUT = os.path.join(os.path.dirname(__file__),
                      "Character_spine37_phase5b_audit.json")
NODES = (
    "shoulder_spine_anim", "shoulder_spine_anim_pad",
    "shoulder_fk_Spine_anim_jnt", "L_clavice_jnt", "R_clavice_jnt",
    "L_clavice_anim", "R_clavice_anim", "IK_L_elbow_anim",
    "IK_R_elbow_anim", "IK_L_hand_anim_const", "IK_R_hand_anim_const",
    "Ik_L_hand_anim", "Ik_R_hand_anim", "L_ARM_IK_SPACE_PC",
    "R_ARM_IK_SPACE_PC", "neck_root_jnt_parent_Constraint_1",
    "head_jnt_parent_Constraint_1", "Terminal",
)


def _source(plug):
    return cmds.connectionInfo(plug, sourceFromDestination=True) or ""


def _connections(node):
    raw = cmds.listConnections(node, s=True, d=True, c=True, p=True,
                               skipConversionNodes=False) or []
    return [{"plug": raw[i], "other": raw[i + 1]}
            for i in range(0, len(raw) - 1, 2)]


def _matrix(plug):
    value = cmds.getAttr(plug)
    value = value[0] if len(value) == 1 and isinstance(value[0], (list, tuple)) else value
    return [float(x) for x in value]


def _record(node):
    if not cmds.objExists(node):
        return {"exists": False}
    result = {"exists": True, "type": cmds.nodeType(node),
              "parent": (cmds.listRelatives(node, p=True, fullPath=True) or [None])[0],
              "connections": _connections(node), "attributes": {}}
    if cmds.objectType(node, isAType="transform"):
        result.update({
            "worldMatrix": _matrix(node + ".worldMatrix[0]"),
            "matrix": _matrix(node + ".matrix"),
            "offsetParentMatrix": _matrix(node + ".offsetParentMatrix"),
            "offsetParentMatrixSource": _source(node + ".offsetParentMatrix"),
            "rotate": cmds.getAttr(node + ".rotate"),
            "translate": cmds.getAttr(node + ".translate"),
            "rotateOrder": int(cmds.getAttr(node + ".rotateOrder")),
        })
        if cmds.nodeType(node) == "joint":
            result["jointOrient"] = cmds.getAttr(node + ".jointOrient")
    for attr in cmds.listAttr(node, userDefined=True) or []:
        if re.search(r"space|follow|world|local|ik", attr, re.I):
            plug = node + "." + attr
            try:
                result["attributes"][attr] = {
                    "value": cmds.getAttr(plug),
                    "type": cmds.getAttr(plug, type=True),
                    "enum": cmds.attributeQuery(attr, node=node, listEnum=True) or [],
                    "source": _source(plug),
                    "destinations": cmds.listConnections(plug, s=False, d=True, p=True) or [],
                }
            except Exception:
                pass
    if cmds.nodeType(node) == "parentConstraint":
        targets = cmds.parentConstraint(node, q=True, targetList=True) or []
        aliases = cmds.parentConstraint(node, q=True, weightAliasList=True) or []
        result["targets"] = []
        for target, alias in zip(targets, aliases):
            result["targets"].append({
                "target": target, "weightAlias": alias,
                "weight": cmds.getAttr(node + "." + alias),
                "weightSource": _source(node + "." + alias),
            })
    return result


def run(path=OUTPUT):
    scene = cmds.file(q=True, sn=True)
    data = {"version": 1,
            "created_utc": datetime.datetime.utcnow().isoformat() + "Z",
            "scene": scene, "read_only": True,
            "nodes": {node: _record(node) for node in NODES},
            "hair_constraints": {}}
    for node in cmds.ls(type="parentConstraint") or []:
        if "hair" in node.lower():
            data["hair_constraints"][node] = _record(node)
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False, sort_keys=True)
    return data


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))
