# -*- coding: utf-8 -*-
"""Numerical validation for the disposable Phase 5-A attachment proxies."""
from __future__ import absolute_import, division, print_function

import datetime
import json
import math
import os

import maya.api.OpenMaya as om
import maya.cmds as cmds

from . import diana_spine_phase5a_proxy as proxy

OUTPUT = os.path.join(os.path.dirname(__file__),
                      "Character_spine37_phase5a_validation.json")
TOLERANCE_MATRIX = 1.0e-4
TOLERANCE_POSITION = 1.0e-4
TOLERANCE_ROTATION_DEG = 1.0e-3
TOLERANCE_SCALE = 1.0e-4


def _matrix(plug):
    return proxy.matrix(plug)


def _matrix_error(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def _position(values):
    return values[12:15]


def _scale(values):
    return [math.sqrt(sum(values[row * 4 + column] ** 2 for column in range(3)))
            for row in range(3)]


def _vector_error(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def _rotation_error(a, b):
    qa = om.MTransformationMatrix(om.MMatrix(a)).rotation(asQuaternion=True)
    qb = om.MTransformationMatrix(om.MMatrix(b)).rotation(asQuaternion=True)
    delta = qa * qb.inverse()
    return math.degrees(2.0 * math.acos(min(1.0, abs(delta.w))))


def _cycles():
    try:
        return sorted(set(cmds.cycleCheck(all=True, list=True) or []))
    except Exception:
        return []


def _set_mode(mode):
    cmds.setAttr("Terminal.Spine_Mode", mode)
    cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)


def _zero_operation_controls():
    for part in ("HIP", "LOWER", "MIDDLE", "SHOULDER"):
        node = "DIANA_SPINE_P5_{}_OP_FK_CTRL".format(part)
        if cmds.objExists(node):
            cmds.setAttr(node + ".rotate", 0, 0, 0)


def _measure(side, manifest):
    actual = _matrix(manifest["proxies"][side]["proxy"] + ".worldMatrix[0]")
    expected = _matrix(manifest["proxies"][side]["final"] + ".matrixSum")
    item = {
        "actual_worldMatrix": actual,
        "expected_worldMatrix": expected,
        "matrix_error": _matrix_error(actual, expected),
        "position_error": _vector_error(_position(actual), _position(expected)),
        "rotation_error_degrees": _rotation_error(actual, expected),
        "scale_error": _vector_error(_scale(actual), _scale(expected)),
        "actual_scale": _scale(actual),
    }
    item["pass"] = (
        item["matrix_error"] <= TOLERANCE_MATRIX and
        item["position_error"] <= TOLERANCE_POSITION and
        item["rotation_error_degrees"] <= TOLERANCE_ROTATION_DEG and
        item["scale_error"] <= TOLERANCE_SCALE)
    return item


def _case(name, mode, manifest, rotations=None, driver=None):
    _zero_operation_controls()
    for part, value in (rotations or {}).items():
        cmds.setAttr("DIANA_SPINE_P5_{}_OP_FK_CTRL.rotate".format(part), *value)
    old = None
    if driver:
        plug, delta = driver
        old = cmds.getAttr(plug)
        cmds.setAttr(plug, old + delta)
    _set_mode(mode)
    sides = {side: _measure(side, manifest) for side in proxy.SIDES}
    if driver:
        cmds.setAttr(driver[0], old)
        cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
    return {"name": name, "mode": mode, "sides": sides,
            "pass": all(x["pass"] for x in sides.values())}


def run(path=OUTPUT, manifest_path=proxy.MANIFEST, baseline_cycles=None):
    manifest = proxy.build(manifest_path)
    baseline_cycles = baseline_cycles or []
    cases = [
        _case("mode0_rest", 0, manifest),
        _case("mode1_rest", 1, manifest),
        _case("mode2_rest", 2, manifest),
        _case("mode0_shoulder_fk", 0, manifest, {"SHOULDER": (10, 0, 0)}),
        _case("mode2_shoulder_fk", 2, manifest, {"SHOULDER": (10, 5, 0)}),
        _case("mode2_compound_fk", 2, manifest,
              {"LOWER": (8, 0, 0), "MIDDLE": (0, 12, 0), "SHOULDER": (0, 0, 9)}),
        _case("ik_hip_tx5_mode1", 1, manifest,
              driver=("DIANA_SPINE_IK_HIP_CTRL.translateX", 5.0)),
        _case("ik_upper_tx5_mode1", 1, manifest,
              driver=("DIANA_SPINE_IK_UPPER_CTRL.translateX", 5.0)),
        _case("ik_upper_rz10_mode1", 1, manifest,
              driver=("DIANA_SPINE_IK_UPPER_CTRL.rotateZ", 10.0)),
        _case("ik_upper_tx5_mode2", 2, manifest,
              {"SHOULDER": (0, 10, 0)},
              ("DIANA_SPINE_IK_UPPER_CTRL.translateX", 5.0)),
    ]
    twist_candidates = [x for x in ("Terminal.Twist", "Terminal.Spine_Twist")
                        if cmds.objExists(x) and not cmds.getAttr(x, lock=True)]
    if twist_candidates:
        cases.append(_case("twist_mode2", 2, manifest,
                           driver=(twist_candidates[0], 10.0)))
    current_cycles = _cycles()
    result = {
        "version": 1,
        "created_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "scene": cmds.file(q=True, sn=True),
        "tolerances": {"matrix": TOLERANCE_MATRIX,
                       "position": TOLERANCE_POSITION,
                       "rotation_degrees": TOLERANCE_ROTATION_DEG,
                       "scale": TOLERANCE_SCALE},
        "formula": "clavicleRestWorld x inverse(shoulderRestWorld) x finalShoulderWorld",
        "cases": cases,
        "cycles": {"baseline": baseline_cycles, "current": current_cycles,
                   "new": sorted(set(current_cycles) - set(baseline_cycles))},
    }
    measurements = [side for case in cases for side in case["sides"].values()]
    result["max_errors"] = {
        "matrix": max(x["matrix_error"] for x in measurements),
        "position": max(x["position_error"] for x in measurements),
        "rotation_degrees": max(x["rotation_error_degrees"] for x in measurements),
        "scale": max(x["scale_error"] for x in measurements),
    }
    result["all_pass"] = all(x["pass"] for x in cases) and not result["cycles"]["new"]
    _zero_operation_controls(); _set_mode(0)
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, sort_keys=True)
    return result


if __name__ == "__main__":
    print(run())
