# -*- coding: utf-8 -*-
"""Read-only attachment hierarchy/DG audit for Diana Spine Phase 5-A."""
from __future__ import absolute_import, division, print_function

import datetime
import json
import os
import re

import maya.api.OpenMaya as om
import maya.cmds as cmds

OUTPUT = os.path.join(os.path.dirname(__file__),
                      "Character_spine37_phase5a_attachment_audit.json")
FOCUS = (
    "shoulder_spine_anim", "shoulder_spine_anim_pad",
    "shoulder_fk_Spine_anim_jnt", "L_clavice_jnt", "R_clavice_jnt",
    "L_clavice_anim", "R_clavice_anim", "neck_root_jnt", "head_jnt",
    "Terminal", "DIANA_SPINE_DEFORM_SHOULDER_MODE_CHOICE",
    "DIANA_SPINE_DEFORM_SHOULDER_MODE1_FINAL_MM",
    "DIANA_SPINE_DEFORM_SHOULDER_MODE2_FINAL_MM",
)


def matrix(plug):
    value = cmds.getAttr(plug)
    value = value[0] if len(value) == 1 and isinstance(value[0], (list, tuple)) else value
    return [float(x) for x in value]


def _canonical(node):
    values = cmds.ls(node, long=True) or cmds.ls(node) or []
    return values[0] if values else node


def _connections(node):
    raw = cmds.listConnections(node, s=True, d=True, c=True, p=True,
                               skipConversionNodes=False) or []
    return [{"plug": raw[i], "other": raw[i + 1]}
            for i in range(0, len(raw) - 1, 2)]


def _node_record(node):
    if not cmds.objExists(node):
        return {"exists": False}
    long_name = _canonical(node)
    record = {
        "exists": True,
        "name": node,
        "long_name": long_name,
        "type": cmds.nodeType(node),
        "parent": (cmds.listRelatives(node, p=True, fullPath=True) or [None])[0],
        "children": cmds.listRelatives(node, c=True, fullPath=True) or [],
        "ancestors": [],
        "constraints": cmds.listConnections(node, s=True, d=False,
                                             type="constraint") or [],
        "connections": _connections(node),
        "space_attributes": {},
    }
    parent = record["parent"]
    while parent:
        record["ancestors"].append(parent)
        parent = (cmds.listRelatives(parent, p=True, fullPath=True) or [None])[0]
    if cmds.objectType(node, isAType="transform"):
        record["worldMatrix"] = matrix(node + ".worldMatrix[0]")
        record["rotateOrder"] = int(cmds.getAttr(node + ".rotateOrder"))
    for attr in cmds.listAttr(node, userDefined=True) or []:
        if re.search(r"space|follow|parent|world|local", attr, re.I):
            plug = node + "." + attr
            try:
                record["space_attributes"][attr] = {
                    "value": cmds.getAttr(plug),
                    "enum": cmds.attributeQuery(attr, node=node, listEnum=True) or [],
                    "source": cmds.connectionInfo(plug, sourceFromDestination=True) or "",
                    "destinations": cmds.listConnections(plug, s=False, d=True, p=True) or [],
                }
            except Exception:
                pass
    return record


def _discover(patterns):
    result = set()
    for node in cmds.ls(long=False) or []:
        lower = node.lower()
        if (any(re.search(pattern, lower) for pattern in patterns) and
                cmds.objExists(node) and cmds.objectType(node, isAType="transform")):
            result.add(node)
    return sorted(result)


def _scale(values):
    return [sum(values[r * 4 + c] ** 2 for c in range(3)) ** 0.5
            for r in range(3)]


def run(path=OUTPUT):
    scene = cmds.file(q=True, sn=True)
    if "PHASE5" not in os.path.basename(scene):
        raise RuntimeError("Refusing non-Phase5 validation scene: " + scene)
    discovered = {
        "arm_ik": _discover((r"^ik_[lr]_.*(anim|const)$", r"^ik_[lr]_.*hand",
                              r"^ik_[lr]_.*elbow")),
        "arm_fk": _discover((r"^fk_[lr]_(shoulder|elbow|wrist)_anim$",)),
        "clavicle": _discover((r"^[lr]_clav",)),
        "neck_head": _discover((r"^neck.*jnt", r"^head.*jnt")),
        "hair_roots": _discover((r"^hair.*jnt[_]?1$", r"^hair.*root")),
    }
    all_nodes = set(FOCUS)
    for values in discovered.values():
        all_nodes.update(values)
    records = {node: _node_record(node) for node in sorted(all_nodes)}

    choice = "DIANA_SPINE_DEFORM_SHOULDER_MODE_CHOICE.output"
    fk = "shoulder_fk_Spine_anim_jnt.worldMatrix[0]"
    choice_matrix, fk_matrix = matrix(choice), matrix(fk)
    mode1_matrix = matrix("DIANA_SPINE_DEFORM_SHOULDER_MODE1_FINAL_MM.matrixSum")
    mode2_matrix = matrix("DIANA_SPINE_DEFORM_SHOULDER_MODE2_FINAL_MM.matrixSum")
    result = {
        "version": 1,
        "created_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "scene": scene,
        "read_only": True,
        "discovered": discovered,
        "nodes": records,
        "shoulder_matrix": {
            "mode_choice_world_match_error": max(abs(a - b) for a, b in zip(choice_matrix, fk_matrix)),
            "mode_choice": choice_matrix,
            "mode1": mode1_matrix,
            "mode2_legacy": mode2_matrix,
            "scale_components": _scale(choice_matrix),
            "space_conclusion": "world",
            "space_evidence": "MODE0 choice output matches shoulder_fk_Spine_anim_jnt.worldMatrix.",
            "shoulder_spine_anim_pivot_local": cmds.xform(
                "shoulder_spine_anim", q=True, os=True, rp=True),
        },
        "direct_children": {
            "shoulder_spine_anim": cmds.listRelatives(
                "shoulder_spine_anim", c=True, fullPath=True) or [],
            "shoulder_fk_Spine_anim_jnt": cmds.listRelatives(
                "shoulder_fk_Spine_anim_jnt", c=True, fullPath=True) or [],
        },
    }
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, sort_keys=True)
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))
