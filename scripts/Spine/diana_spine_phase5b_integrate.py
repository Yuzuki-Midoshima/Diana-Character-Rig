# -*- coding: utf-8 -*-
"""Staged, manifest-backed Phase 5-B arm attachment integration."""
from __future__ import absolute_import, division, print_function

import datetime
import json
import os

import maya.api.OpenMaya as om
import maya.cmds as cmds

ROOT = "DIANA_SPINE_P5B_ATTACHMENT_GRP"
REGISTRY = "DIANA_SPINE_P5B_REGISTRY"
MANIFEST = os.path.join(os.path.dirname(__file__),
                        "Character_spine37_phase5b_manifest.json")
SIDE_DATA = {
    # clavice_anim is deliberately not OPM-driven here.  Its descendant
    # arm_GRP already has a production FINAL_FOLLOW network sourced from the
    # final shoulder choice; driving both levels applies the shoulder twice.
    "L": {"roots": ("L_clavice_jnt", "IK_L_elbow_anim"),
          "constraint": "L_ARM_IK_SPACE_PC", "hand_const": "IK_L_hand_anim_const",
          "setting": "L_arm_settings_anim.IK_Space", "reverse": "L_ARM_IK_SPACE_REV.outputX",
          "fk_root": "FK_L_shoulder_anim"},
    "R": {"roots": ("R_clavice_jnt", "IK_R_elbow_anim"),
          "constraint": "R_ARM_IK_SPACE_PC", "hand_const": "IK_R_hand_anim_const",
          "setting": "R_arm_settings_anim.IK_Space", "reverse": "R_ARM_IK_SPACE_REV.outputX",
          "fk_root": "FK_R_shoulder_anim"},
}


def matrix(plug):
    value = cmds.getAttr(plug)
    value = value[0] if len(value) == 1 and isinstance(value[0], (list, tuple)) else value
    return [float(x) for x in value]


def source(plug):
    return cmds.connectionInfo(plug, sourceFromDestination=True) or ""


def _connections(node):
    raw = cmds.listConnections(node, s=True, d=True, c=True, p=True,
                               skipConversionNodes=False) or []
    return [{"plug": raw[i], "other": raw[i + 1]}
            for i in range(0, len(raw) - 1, 2)]


def _constraint_record(node):
    targets = cmds.parentConstraint(node, q=True, targetList=True) or []
    aliases = cmds.parentConstraint(node, q=True, weightAliasList=True) or []
    return {"targets": [{"target": target, "alias": alias,
                          "source": source(node + "." + alias),
                          "value": cmds.getAttr(node + "." + alias)}
                         for target, alias in zip(targets, aliases)],
            "connections": _connections(node)}


def _cycles():
    try:
        return sorted(set(cmds.cycleCheck(all=True, list=True) or []))
    except Exception:
        return []


def capture_manifest(path=MANIFEST):
    scene = cmds.file(q=True, sn=True)
    name = os.path.basename(scene).upper()
    if "PHASE5B" not in name and "_SPINE_RC" not in name:
        raise RuntimeError("Refusing scene that is neither Phase5B nor Spine RC: " + scene)
    if cmds.objExists(ROOT) or cmds.objExists(REGISTRY):
        raise RuntimeError("Phase 5-B already exists")
    shoulder = matrix("shoulder_fk_Spine_anim_jnt.worldMatrix[0]")
    data = {"version": 1,
            "created_utc": datetime.datetime.utcnow().isoformat() + "Z",
            "scene": scene, "shoulder_rest": shoulder, "sides": {},
            "baseline_cycles": _cycles(), "stages": [], "created_nodes": [],
            "protected_connections": {}}
    for node in ("neck_root_jnt_parent_Constraint_1", "head_jnt_parent_Constraint_1",
                 "Terminal", "back_spine_curve", "RIG_spineStretch_MD"):
        data["protected_connections"][node] = _connections(node)
    for side, spec in SIDE_DATA.items():
        side_record = {"roots": {}, "constraint": _constraint_record(spec["constraint"]),
                       "setting_value": cmds.getAttr(spec["setting"]),
                       "hand_world": matrix(spec["hand_const"] + ".worldMatrix[0]"),
                       "fk_world": matrix(spec["fk_root"] + ".worldMatrix[0]")}
        for node in spec["roots"]:
            side_record["roots"][node] = {
                "parent": (cmds.listRelatives(node, p=True, fullPath=True) or [None])[0],
                "matrix": matrix(node + ".matrix"),
                "world": matrix(node + ".worldMatrix[0]"),
                "opm": matrix(node + ".offsetParentMatrix"),
                "opm_source": source(node + ".offsetParentMatrix"),
                "rotate": cmds.getAttr(node + ".rotate"),
                "translate": cmds.getAttr(node + ".translate"),
            }
        data["sides"][side] = side_record
    # Record the Phase-5 arm-FK response before adding any attachment nodes.
    # This is the authoritative compatibility reference because the existing
    # rig already has arm_GRP compensation driven from the final shoulder.
    old_mode = cmds.getAttr("Terminal.Spine_Mode")
    upper_plug = "DIANA_SPINE_IK_UPPER_CTRL.translateX"
    old_upper = cmds.getAttr(upper_plug)
    cmds.setAttr("Terminal.Spine_Mode", 1)
    cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
    for side, spec in SIDE_DATA.items():
        data["sides"][side]["fk_follow_reference"] = {
            "base": matrix(spec["fk_root"] + ".worldMatrix[0]")}
    cmds.setAttr(upper_plug, old_upper + 5.0)
    cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
    for side, spec in SIDE_DATA.items():
        data["sides"][side]["fk_follow_reference"]["upper_x_plus_5"] = \
            matrix(spec["fk_root"] + ".worldMatrix[0]")
    cmds.setAttr(upper_plug, old_upper)
    cmds.setAttr("Terminal.Spine_Mode", old_mode)
    cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
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


def _constant(name, values):
    node = _node("fourByFourMatrix", name)
    for row in range(4):
        for column in range(4):
            cmds.setAttr("{}.in{}{}".format(node, row, column), values[row * 4 + column])
    return node


def _setup_root():
    if not cmds.objExists(REGISTRY):
        registry = cmds.createNode("network", name=REGISTRY)
        cmds.addAttr(registry, ln="nodes", at="message", multi=True)
        root = cmds.createNode("transform", name=ROOT)
        cmds.setAttr(root + ".inheritsTransform", 0)
        _register(root)


def _world_driver(side, label, target, rest, shoulder_rest):
    prefix = "DIANA_SPINE_P5B_{}_{}".format(side, label)
    rest_world = om.MMatrix(rest["world"])
    rest_shoulder_inverse = om.MMatrix(shoulder_rest).inverse()
    offset = list(rest_world * rest_shoulder_inverse)
    local_inverse = list(om.MMatrix(rest["matrix"]).inverse())
    offset_node = _constant(prefix + "_SHOULDER_OFFSET_FBF", offset)
    desired = _node("multMatrix", prefix + "_DESIRED_WORLD_MM")
    cmds.connectAttr(offset_node + ".output", desired + ".matrixIn[0]")
    cmds.connectAttr("DIANA_SPINE_DEFORM_SHOULDER_MODE_CHOICE.output",
                     desired + ".matrixIn[1]")
    local_inv = _constant(prefix + "_REST_LOCAL_INV_FBF", local_inverse)
    opm = _node("multMatrix", prefix + "_OPM_MM")
    cmds.connectAttr(local_inv + ".output", opm + ".matrixIn[0]")
    cmds.connectAttr(desired + ".matrixSum", opm + ".matrixIn[1]")
    # Do not read parentInverseMatrix from the driven transform itself.  Maya
    # treats that plug as part of the transform's evaluation cluster, so using
    # it to compute the same transform's offsetParentMatrix creates a real DG
    # cycle.  The parent's worldInverseMatrix is numerically equivalent here
    # and keeps the driver upstream of the attachment transform.
    parent = (cmds.listRelatives(target, p=True, fullPath=True) or [None])[0]
    if parent:
        cmds.connectAttr(parent + ".worldInverseMatrix[0]", opm + ".matrixIn[2]")
    cmds.connectAttr(opm + ".matrixSum", target + ".offsetParentMatrix")
    return {"target": target, "desired": desired, "opm": opm, "offset": offset}


def integrate_side(side, path=MANIFEST):
    side = side.upper()
    if side not in SIDE_DATA:
        raise ValueError(side)
    if not os.path.exists(path):
        capture_manifest(path)
    with open(path, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    expected = ("L", "R")[len(manifest["stages"])]
    if side != expected:
        raise RuntimeError("Expected {}, got {}".format(expected, side))
    _setup_root()
    spec, saved = SIDE_DATA[side], manifest["sides"][side]
    drivers = []
    for node in spec["roots"]:
        label = node.replace(side + "_", "").replace("_anim", "").replace("_jnt", "").upper()
        drivers.append(_world_driver(side, label, node, saved["roots"][node],
                                     manifest["shoulder_rest"]))

    # Independent body-space target matching shoulder_spine_anim at rest.
    body_target = cmds.createNode("transform",
                                  name="DIANA_SPINE_P5B_{}_ARM_BODY_TARGET".format(side),
                                  parent=ROOT)
    _register(body_target)
    body_rest = {"world": matrix("shoulder_spine_anim.worldMatrix[0]"),
                 "matrix": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]}
    body_offset = list(om.MMatrix(body_rest["world"]) *
                       om.MMatrix(manifest["shoulder_rest"]).inverse())
    body_offset_node = _constant("DIANA_SPINE_P5B_{}_ARM_BODY_OFFSET_FBF".format(side),
                                 body_offset)
    body_final = _node("multMatrix", "DIANA_SPINE_P5B_{}_ARM_BODY_FINAL_MM".format(side))
    cmds.connectAttr(body_offset_node + ".output", body_final + ".matrixIn[0]")
    cmds.connectAttr("DIANA_SPINE_DEFORM_SHOULDER_MODE_CHOICE.output",
                     body_final + ".matrixIn[1]")
    cmds.connectAttr(body_final + ".matrixSum", body_target + ".offsetParentMatrix")

    constraint = spec["constraint"]
    before_targets = cmds.parentConstraint(constraint, q=True, targetList=True) or []
    cmds.parentConstraint(body_target, spec["hand_const"], e=True, mo=True, weight=0.0)
    after_targets = cmds.parentConstraint(constraint, q=True, targetList=True) or []
    if body_target not in after_targets:
        raise RuntimeError("Failed to add body target to " + constraint)
    aliases = cmds.parentConstraint(constraint, q=True, weightAliasList=True) or []
    new_alias = aliases[after_targets.index(body_target)]
    old_alias = saved["constraint"]["targets"][0]["alias"]
    old_plug, new_plug = constraint + "." + old_alias, constraint + "." + new_alias
    old_source = source(old_plug)
    if old_source:
        cmds.disconnectAttr(old_source, old_plug)
    cmds.setAttr(old_plug, 0.0)
    cmds.connectAttr(spec["reverse"], new_plug, force=True)

    stage = {"side": side, "drivers": drivers, "body_target": body_target,
             "constraint": constraint, "old_alias": old_alias,
             "old_source": old_source, "new_alias": new_alias,
             "targets_before": before_targets, "targets_after": after_targets}
    manifest["stages"].append(stage)
    manifest["created_nodes"] = sorted(set(
        (cmds.listConnections(REGISTRY + ".nodes", s=True, d=False) or []) + [REGISTRY]))
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=False, sort_keys=True)
    return stage


if __name__ == "__main__":
    capture_manifest()
    integrate_side("L")
    integrate_side("R")
