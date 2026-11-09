# -*- coding: utf-8 -*-
"""Build independent animator FK controls for Diana Spine Phase 5."""
from __future__ import absolute_import, division, print_function

import datetime
import json
import math
import os

import maya.cmds as cmds

ROOT = "DIANA_SPINE_P5_OPERATION_FK_GRP"
REGISTRY = "DIANA_SPINE_P5_REGISTRY"
MANIFEST = os.path.join(os.path.dirname(__file__),
                        "Character_spine37_phase5_manifest.json")
PARTS = {
    "HIP": "hip_fk_Spine_anim_jnt",
    "LOWER": "lower_fk_Spine_anim",
    "MIDDLE": "middle_fk_Spine_anim",
    "SHOULDER": "shoulder_fk_Spine_anim_jnt",
}
FOLLOW_TARGETS = (
    "neck_root_jnt", "head_jnt", "L_clavice_jnt", "R_clavice_jnt",
    "hair_short_back_jnt_1", "IK_back_spine_jnt_1",
    "DIANA_SPINE_DEFORM_SHOULDER_FINAL_PROXY",
)


def matrix(plug):
    value = cmds.getAttr(plug)
    value = value[0] if len(value) == 1 and isinstance(value[0], (list, tuple)) else value
    return [float(x) for x in value]


def source(plug):
    return cmds.connectionInfo(plug, sourceFromDestination=True) or ""


def _connections(node):
    raw = cmds.listConnections(node, s=True, d=True, c=True, p=True) or []
    return [{"plug": raw[i], "other": raw[i + 1]}
            for i in range(0, len(raw) - 1, 2)]


def _cycle_list():
    try:
        return sorted(set(cmds.cycleCheck(all=True, list=True) or []))
    except Exception:
        return []


def preflight():
    scene = cmds.file(q=True, sn=True)
    name = os.path.basename(scene).upper()
    if not (("PHASE5" in name and "VALIDATION" in name) or "_SPINE_RC" in name):
        raise RuntimeError("Refusing scene that is neither validation nor Spine RC: " + scene)
    if cmds.objExists(ROOT) or cmds.objExists(REGISTRY):
        raise RuntimeError("Phase 5 network already exists")
    required = ["Terminal", "shoulder_spine_anim", "back_spine_curve",
                "RIG_spineStretch_MD"]
    for part, fk in PARTS.items():
        required += [fk,
                     "DIANA_SPINE_DEFORM_{}_MODE1_FINAL_MM".format(part),
                     "DIANA_SPINE_DEFORM_{}_MODE_CHOICE".format(part)]
    missing = [x for x in required if not cmds.objExists(x)]
    if missing:
        raise RuntimeError("Missing: " + ", ".join(missing))
    return scene


def capture_manifest(path=MANIFEST):
    scene = preflight()
    data = {
        "version": 1,
        "created_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "scene": scene,
        "parts": {},
        "skinClusters": {},
        "baseline_cycles": _cycle_list(),
        "protected_hierarchy": {},
        "legacy_connections": {
            "back_spine_curve": _connections("back_spine_curve"),
            "RIG_spineStretch_MD": _connections("RIG_spineStretch_MD"),
        },
        "stages": [],
        "created_nodes": [],
        "follow_targets": {},
    }
    for part, fk in PARTS.items():
        choice = "DIANA_SPINE_DEFORM_{}_MODE_CHOICE".format(part)
        data["parts"][part] = {
            "fk": fk,
            "fk_parent": (cmds.listRelatives(fk, p=True, fullPath=True) or [None])[0],
            "fk_worldMatrix": matrix(fk + ".worldMatrix[0]"),
            "fk_rotateOrder": int(cmds.getAttr(fk + ".rotateOrder")),
            "choice_inputs": {str(i): source(choice + ".input[{}]".format(i))
                              for i in range(3)},
            "choice_output": matrix(choice + ".output"),
        }
    for node in list(PARTS.values()) + ["shoulder_spine_anim", "Terminal"]:
        data["protected_hierarchy"][node] = (
            cmds.listRelatives(node, p=True, fullPath=True) or [None])[0]
    data["shoulder_pivot_local"] = cmds.xform(
        "shoulder_spine_anim", q=True, os=True, rp=True)
    for node in FOLLOW_TARGETS:
        if cmds.objExists(node):
            data["follow_targets"][node] = {
                "worldMatrix": matrix(node + ".worldMatrix[0]"),
                "connections": _connections(node),
            }
    for skin in cmds.ls(type="skinCluster") or []:
        influences = cmds.skinCluster(skin, q=True, influence=True) or []
        if any("spine" in x.lower() or "back" in x.lower() for x in influences):
            data["skinClusters"][skin] = {
                "influences": influences,
                "geometry": cmds.skinCluster(skin, q=True, geometry=True) or [],
            }
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False, sort_keys=True)
    return data


def _register(node):
    index = len(cmds.getAttr(REGISTRY + ".nodes", multiIndices=True) or [])
    cmds.connectAttr(node + ".message", "{}.nodes[{}]".format(REGISTRY, index))


def _node(node_type, name):
    node = cmds.createNode(node_type, name=name)
    _register(node)
    return node


def _constant_matrix(name, values):
    node = _node("fourByFourMatrix", name)
    for row in range(4):
        for column in range(4):
            cmds.setAttr("{}.in{}{}".format(node, row, column),
                         values[row * 4 + column])
    return node


def _shape(control, part):
    radius = {"HIP": 18.0, "LOWER": 16.0, "MIDDLE": 14.0,
              "SHOULDER": 20.0}[part]
    center_y = 145.989 if part == "SHOULDER" else 0.0
    points = []
    for i in range(17):
        angle = (math.pi * 2.0 * i) / 16.0
        points.append((math.cos(angle) * radius, center_y,
                       math.sin(angle) * radius))
    temp = cmds.curve(d=1, p=points, name="DIANA_SPINE_P5_{}_TMP".format(part))
    shape = cmds.listRelatives(temp, shapes=True, fullPath=True)[0]
    shape = cmds.parent(shape, control, shape=True, relative=True)[0]
    cmds.delete(temp)
    shape = cmds.rename(shape, control + "Shape")
    cmds.setAttr(shape + ".overrideEnabled", 1)
    cmds.setAttr(shape + ".overrideColor", {"HIP": 18, "LOWER": 17,
                                             "MIDDLE": 14, "SHOULDER": 13}[part])
    return shape


def build(path=MANIFEST):
    manifest = capture_manifest(path)
    root = cmds.createNode("transform", name=ROOT)
    cmds.setAttr(root + ".inheritsTransform", 0)
    registry = cmds.createNode("network", name=REGISTRY)
    cmds.addAttr(registry, ln="nodes", at="message", multi=True)
    _register(root)

    for part, fk in PARTS.items():
        prefix = "DIANA_SPINE_P5_" + part
        follow = cmds.createNode("transform", name=prefix + "_FOLLOW", parent=root)
        _register(follow)
        control = cmds.createNode("transform", name=prefix + "_OP_FK_CTRL", parent=follow)
        _register(control)
        cmds.setAttr(control + ".rotateOrder", manifest["parts"][part]["fk_rotateOrder"])
        if part == "SHOULDER":
            cmds.setAttr(control + ".rotatePivot", 0, 145.989, 0)
            cmds.setAttr(control + ".scalePivot", 0, 145.989, 0)
        shape = _shape(control, part)

        rest = _constant_matrix(prefix + "_REST_WORLD_FBF",
                                manifest["parts"][part]["fk_worldMatrix"])
        follow_choice = _node("choice", prefix + "_FOLLOW_MODE_CHOICE")
        cmds.connectAttr("Terminal.Spine_Mode", follow_choice + ".selector")
        cmds.connectAttr(rest + ".output", follow_choice + ".input[0]")
        mode1 = "DIANA_SPINE_DEFORM_{}_MODE1_FINAL_MM.matrixSum".format(part)
        cmds.connectAttr(mode1, follow_choice + ".input[1]")
        cmds.connectAttr(mode1, follow_choice + ".input[2]")
        cmds.connectAttr(follow_choice + ".output", follow + ".offsetParentMatrix")

        delta = _node("composeMatrix", prefix + "_LOCAL_DELTA_CM")
        cmds.connectAttr(control + ".rotate", delta + ".inputRotate")
        if cmds.objExists(delta + ".inputRotateOrder"):
            cmds.connectAttr(control + ".rotateOrder", delta + ".inputRotateOrder")

        mode0 = _node("multMatrix", prefix + "_MODE0_FINAL_MM")
        cmds.connectAttr(delta + ".outputMatrix", mode0 + ".matrixIn[0]")
        cmds.connectAttr(fk + ".worldMatrix[0]", mode0 + ".matrixIn[1]")
        mode2 = _node("multMatrix", prefix + "_MODE2_FINAL_MM")
        cmds.connectAttr(delta + ".outputMatrix", mode2 + ".matrixIn[0]")
        cmds.connectAttr(mode1, mode2 + ".matrixIn[1]")

        visible = _node("condition", prefix + "_VALID_MODE_VIS_COND")
        cmds.setAttr(visible + ".operation", 5)  # less or equal
        cmds.connectAttr("Terminal.Spine_Mode", visible + ".firstTerm")
        cmds.setAttr(visible + ".secondTerm", 2)
        cmds.setAttr(visible + ".colorIfTrueR", 1)
        cmds.setAttr(visible + ".colorIfFalseR", 0)
        cmds.connectAttr(visible + ".outColorR", shape + ".visibility")

    manifest["created_nodes"] = sorted(set(
        (cmds.listConnections(REGISTRY + ".nodes", s=True, d=False) or []) +
        [REGISTRY]))
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=False, sort_keys=True)
    return manifest


if __name__ == "__main__":
    build()
