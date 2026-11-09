# -*- coding: utf-8 -*-
"""Automated staged validation for Phase 5-B arm attachments."""
from __future__ import absolute_import, division, print_function

import datetime
import json
import math
import os

import maya.api.OpenMaya as om
import maya.cmds as cmds

from . import diana_spine_phase5b_integrate as integration

OUTPUT = os.path.join(os.path.dirname(__file__),
                      "Character_spine37_phase5b_validation.json")
TOL_MATRIX = 1.0e-4
TOL_POSITION = 1.0e-4
TOL_ROTATION = 1.0e-3
TOL_SCALE = 1.0e-4


def _matrix(plug): return integration.matrix(plug)
def _error(a, b): return max(abs(x - y) for x, y in zip(a, b))
def _position(m): return m[12:15]
def _scale(m): return [math.sqrt(sum(m[r * 4 + c] ** 2 for c in range(3))) for r in range(3)]


def _rotation_error(a, b):
    qa = om.MTransformationMatrix(om.MMatrix(a)).rotation(asQuaternion=True)
    qb = om.MTransformationMatrix(om.MMatrix(b)).rotation(asQuaternion=True)
    delta = qa * qb.inverse()
    return math.degrees(2 * math.acos(min(1.0, abs(delta.w))))


def _cycles():
    try: return sorted(set(cmds.cycleCheck(all=True, list=True) or []))
    except Exception: return []


def _set_mode(mode):
    cmds.setAttr("Terminal.Spine_Mode", mode)
    cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)


def _zero_spine():
    for part in ("HIP", "LOWER", "MIDDLE", "SHOULDER"):
        node = "DIANA_SPINE_P5_{}_OP_FK_CTRL".format(part)
        if cmds.objExists(node): cmds.setAttr(node + ".rotate", 0, 0, 0)


def _root_measure(side, manifest):
    items = {}
    for driver in manifest["stages"][("L", "R").index(side)]["drivers"]:
        actual = _matrix(driver["target"] + ".worldMatrix[0]")
        local = _matrix(driver["target"] + ".matrix")
        rest_local_inverse = om.MMatrix(manifest["sides"][side]["roots"][driver["target"]]["matrix"]).inverse()
        desired = _matrix(driver["desired"] + ".matrixSum")
        expected = list(om.MMatrix(local) * rest_local_inverse * om.MMatrix(desired))
        items[driver["target"]] = {
            "matrix_error": _error(actual, expected),
            "position_error": _error(_position(actual), _position(expected)),
            "rotation_error_degrees": _rotation_error(actual, expected),
            "scale_error": _error(_scale(actual), _scale(expected)),
        }
        items[driver["target"]]["pass"] = (
            items[driver["target"]]["matrix_error"] <= TOL_MATRIX and
            items[driver["target"]]["position_error"] <= TOL_POSITION and
            items[driver["target"]]["rotation_error_degrees"] <= TOL_ROTATION and
            items[driver["target"]]["scale_error"] <= TOL_SCALE)
    return items


def _case(name, mode, manifest, rotations=None, driver=None):
    _zero_spine()
    for part, value in (rotations or {}).items():
        cmds.setAttr("DIANA_SPINE_P5_{}_OP_FK_CTRL.rotate".format(part), *value)
    old = None
    if driver:
        old = cmds.getAttr(driver[0]); cmds.setAttr(driver[0], old + driver[1])
    _set_mode(mode)
    sides = {side: _root_measure(side, manifest) for side in ("L", "R")}
    if driver:
        cmds.setAttr(driver[0], old); cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
    passed = all(item["pass"] for roots in sides.values() for item in roots.values())
    return {"name": name, "mode": mode, "sides": sides, "pass": passed}


def _space_test(side, manifest):
    spec = integration.SIDE_DATA[side]
    setting = spec["setting"]
    original = cmds.getAttr(setting)
    _zero_spine(); _set_mode(1)
    # World=1 must remain fixed.
    cmds.setAttr(setting, 1); cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
    world_before = _matrix(spec["hand_const"] + ".worldMatrix[0]")
    upper_old = cmds.getAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX")
    cmds.setAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX", upper_old + 5)
    cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
    world_after = _matrix(spec["hand_const"] + ".worldMatrix[0]")
    world_error = _error(world_before, world_after)
    cmds.setAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX", upper_old)

    # Body=0 must preserve its relative offset to the new target.
    cmds.setAttr(setting, 0); cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
    body_target = manifest["stages"][("L", "R").index(side)]["body_target"]
    hand_before = _matrix(spec["hand_const"] + ".worldMatrix[0]")
    target_before = _matrix(body_target + ".worldMatrix[0]")
    offset = om.MMatrix(hand_before) * om.MMatrix(target_before).inverse()
    cmds.setAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX", upper_old + 5)
    cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
    target_after = _matrix(body_target + ".worldMatrix[0]")
    hand_after = _matrix(spec["hand_const"] + ".worldMatrix[0]")
    expected = list(offset * om.MMatrix(target_after))
    body_error = _error(hand_after, expected)
    body_motion = _error(hand_before, hand_after)
    cmds.setAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX", upper_old)
    cmds.setAttr(setting, original); cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
    return {"world_error": world_error, "body_error": body_error,
            "body_motion": body_motion,
            "pass": world_error <= TOL_MATRIX and body_error <= TOL_MATRIX and body_motion > 1e-6}


def _descendant_test(side, manifest):
    spec = integration.SIDE_DATA[side]
    _zero_spine(); _set_mode(1)
    child = spec["fk_root"]
    child_before = _matrix(child + ".worldMatrix[0]")
    local_before = _matrix(child + ".matrix")
    old = cmds.getAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX")
    cmds.setAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX", old + 5)
    cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
    child_after = _matrix(child + ".worldMatrix[0]")
    reference = manifest["sides"][side]["fk_follow_reference"]
    base_error = _error(child_before, reference["base"])
    error = _error(child_after, reference["upper_x_plus_5"])
    motion = _error(child_before, child_after)
    local_error = _error(local_before, _matrix(child + ".matrix"))
    cmds.setAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX", old)
    return {"baseline_matrix_error": base_error, "matrix_error": error,
            "local_channel_matrix_error": local_error,
            "motion": motion,
            "pass": base_error <= TOL_MATRIX and error <= TOL_MATRIX and
                    local_error <= TOL_MATRIX and motion > 1e-6}


def run(manifest_path=integration.MANIFEST, output=OUTPUT):
    with open(manifest_path, "r", encoding="utf-8") as stream: manifest = json.load(stream)
    cases = [
        _case("mode0", 0, manifest), _case("mode1", 1, manifest),
        _case("mode2", 2, manifest),
        _case("mode0_shoulder_fk", 0, manifest, {"SHOULDER": (10, 0, 0)}),
        _case("mode2_fk", 2, manifest, {"SHOULDER": (10, 5, 0)}),
        _case("ik_hip", 1, manifest, driver=("DIANA_SPINE_IK_HIP_CTRL.translateX", 5)),
        _case("ik_upper", 1, manifest, driver=("DIANA_SPINE_IK_UPPER_CTRL.translateX", 5)),
        _case("ik_rotate", 1, manifest, driver=("DIANA_SPINE_IK_UPPER_CTRL.rotateZ", 10)),
    ]
    cycles = _cycles()
    measurements = [item for case in cases for side in case["sides"].values() for item in side.values()]
    result = {"version": 1, "created_utc": datetime.datetime.utcnow().isoformat() + "Z",
              "scene": cmds.file(q=True, sn=True),
              "tolerances": {"matrix": TOL_MATRIX, "position": TOL_POSITION,
                             "rotation_degrees": TOL_ROTATION, "scale": TOL_SCALE},
              "cases": cases,
              "arm_fk": {side: _descendant_test(side, manifest) for side in ("L", "R")},
              "hand_space": {side: _space_test(side, manifest) for side in ("L", "R")},
              "cycles": {"baseline": manifest["baseline_cycles"], "current": cycles,
                         "new": sorted(set(cycles) - set(manifest["baseline_cycles"]))},
              "max_errors": {"matrix": max(x["matrix_error"] for x in measurements),
                             "position": max(x["position_error"] for x in measurements),
                             "rotation_degrees": max(x["rotation_error_degrees"] for x in measurements),
                             "scale": max(x["scale_error"] for x in measurements)}}
    result["all_pass"] = (all(x["pass"] for x in cases) and
                          all(x["pass"] for x in result["arm_fk"].values()) and
                          all(x["pass"] for x in result["hand_space"].values()) and
                          not result["cycles"]["new"])
    _zero_spine(); _set_mode(0)
    with open(output, "w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, sort_keys=True)
    return result
