# -*- coding: utf-8 -*-
"""Automated staged numerical validation for Diana Spine Phase 5."""
from __future__ import absolute_import, division, print_function

import datetime
import json
import math
import os

import maya.api.OpenMaya as om
import maya.cmds as cmds

from . import diana_spine_phase5_build as build
from . import diana_spine_phase5_integrate as integrate

OUTPUT = os.path.join(os.path.dirname(__file__),
                      "Character_spine37_phase5_validation.json")
TOLERANCE = 1.0e-4


def _matrix(plug):
    return build.matrix(plug)


def _error(a, b):
    return max(abs(float(x) - float(y)) for x, y in zip(a, b))


def _multiply(a, b):
    return list(om.MMatrix(a) * om.MMatrix(b))


def _cycles():
    try:
        return sorted(set(cmds.cycleCheck(all=True, list=True) or []))
    except Exception:
        return []


def _set_mode(value):
    cmds.setAttr("Terminal.Spine_Mode", value)
    cmds.dgdirty(allPlugs=True)
    cmds.refresh(force=True)


def _zero_controls():
    for part in build.PARTS:
        cmds.setAttr("DIANA_SPINE_P5_{}_OP_FK_CTRL.rotate".format(part), 0, 0, 0)


def _case(name, mode, rotations=None):
    _zero_controls()
    rotations = rotations or {}
    for part, value in rotations.items():
        cmds.setAttr("DIANA_SPINE_P5_{}_OP_FK_CTRL.rotate".format(part), *value)
    _set_mode(mode)
    parts = {}
    for part in build.PARTS:
        choice = "DIANA_SPINE_DEFORM_{}_MODE_CHOICE.output".format(part)
        actual = _matrix(choice)
        if mode == 0:
            expected = _matrix("DIANA_SPINE_P5_{}_MODE0_FINAL_MM.matrixSum".format(part))
        elif mode == 1:
            expected = _matrix("DIANA_SPINE_DEFORM_{}_MODE1_FINAL_MM.matrixSum".format(part))
        else:
            expected = _matrix("DIANA_SPINE_P5_{}_MODE2_FINAL_MM.matrixSum".format(part))
        follow_actual = _matrix("DIANA_SPINE_P5_{}_FOLLOW.worldMatrix[0]".format(part))
        if mode == 0:
            follow_expected = _matrix("DIANA_SPINE_P5_{}_REST_WORLD_FBF.output".format(part))
        else:
            follow_expected = _matrix("DIANA_SPINE_DEFORM_{}_MODE1_FINAL_MM.matrixSum".format(part))
        parts[part] = {
            "matrix_error": _error(actual, expected),
            "follow_error": _error(follow_actual, follow_expected),
        }
    return {"name": name, "mode": mode, "parts": parts,
            "pass": all(max(x["matrix_error"], x["follow_error"]) <= TOLERANCE
                        for x in parts.values())}


def _ik_case(name, control, attribute, delta, mode):
    old = cmds.getAttr(control + "." + attribute)
    cmds.setAttr(control + "." + attribute, old + delta)
    try:
        return _case(name, mode)
    finally:
        cmds.setAttr(control + "." + attribute, old)


def _skins(manifest):
    result = {}
    for skin, expected in manifest["skinClusters"].items():
        result[skin] = {
            "exists": cmds.objExists(skin),
            "influences_equal": (cmds.skinCluster(skin, q=True, influence=True) or []) == expected["influences"],
            "geometry_equal": (cmds.skinCluster(skin, q=True, geometry=True) or []) == expected["geometry"],
        }
    return result


def _scale_components(values):
    return [math.sqrt(sum(values[row * 4 + column] ** 2 for column in range(3)))
            for row in range(3)]


def _follow_motion_test(manifest):
    control = "DIANA_SPINE_IK_UPPER_CTRL"
    attribute = "translateX"
    _zero_controls(); _set_mode(1)
    before = {node: _matrix(node + ".worldMatrix[0]")
              for node in manifest["follow_targets"] if cmds.objExists(node)}
    old = cmds.getAttr(control + "." + attribute)
    cmds.setAttr(control + "." + attribute, old + 5.0)
    cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
    after = {node: _matrix(node + ".worldMatrix[0]") for node in before}
    cmds.setAttr(control + "." + attribute, old)
    cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
    restored = {node: _matrix(node + ".worldMatrix[0]") for node in before}
    required_motion = {"neck_root_jnt", "head_jnt", "L_clavice_jnt",
                       "R_clavice_jnt", "IK_back_spine_jnt_1",
                       "DIANA_SPINE_DEFORM_SHOULDER_FINAL_PROXY"}
    targets = {}
    for node in before:
        targets[node] = {
            "motion": _error(before[node], after[node]),
            "restore_error": _error(before[node], restored[node]),
            "motion_required": node in required_motion,
            "connections_equal": (build._connections(node) ==
                                  manifest["follow_targets"][node]["connections"]),
        }
    return {"driver": control + "." + attribute, "delta": 5.0,
            "targets": targets,
            "pass": (all((not v["motion_required"] or v["motion"] > 1.0e-6) and
                         v["restore_error"] <= TOLERANCE and v["connections_equal"]
                         for v in targets.values())
                     if targets else False)}


def run(manifest_path=build.MANIFEST, output_path=OUTPUT):
    manifest = build.build(manifest_path)
    result = {
        "version": 1,
        "created_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "scene": cmds.file(q=True, sn=True),
        "tolerance": TOLERANCE,
        "mode0_design": {
            "selected": "B",
            "formula": "operation local delta x existing production FK worldMatrix",
            "reason": "Preserves production FK animation and hierarchy while operation controls remain independent.",
        },
        "stages": [], "cases": [],
    }
    _zero_controls()
    for part in integrate.ORDER:
        original = _matrix(manifest["parts"][part]["choice_inputs"]["0"])
        integrate.integrate_part(part, manifest_path)
        _set_mode(0)
        actual = _matrix("DIANA_SPINE_DEFORM_{}_MODE_CHOICE.output".format(part))
        result["stages"].append({"part": part,
                                 "mode0_baseline_error": _error(actual, original),
                                 "pass": _error(actual, original) <= TOLERANCE})

    result["cases"].extend([
        _case("mode0_zero", 0),
        _case("mode0_hip", 0, {"HIP": (10, 0, 0)}),
        _case("mode0_lower", 0, {"LOWER": (0, 12, 0)}),
        _case("mode0_middle", 0, {"MIDDLE": (0, 0, 14)}),
        _case("mode0_shoulder", 0, {"SHOULDER": (8, 5, 0)}),
        _case("mode0_compound", 0, {"LOWER": (10, 0, 0), "MIDDLE": (0, 15, 0)}),
        _case("mode1_zero", 1),
        _case("mode1_ignores_fk_delta", 1, {"LOWER": (20, 0, 0)}),
        _case("mode2_lower", 2, {"LOWER": (20, 0, 0)}),
        _case("mode2_middle", 2, {"MIDDLE": (0, 18, 0)}),
        _case("mode2_shoulder", 2, {"SHOULDER": (0, 0, 12)}),
        _case("mode2_compound", 2, {"LOWER": (10, 0, 0), "MIDDLE": (0, 15, 0), "SHOULDER": (0, 0, 8)}),
    ])
    for label, control in (("ik_hip", "DIANA_SPINE_IK_HIP_CTRL"),
                           ("ik_upper", "DIANA_SPINE_IK_UPPER_CTRL")):
        if cmds.objExists(control + ".translateX") and not cmds.getAttr(control + ".translateX", lock=True):
            result["cases"].append(_ik_case(label + "_tx5_mode1", control, "translateX", 5.0, 1))
            result["cases"].append(_ik_case(label + "_tx5_mode2", control, "translateX", 5.0, 2))
        if cmds.objExists(control + ".rotateZ") and not cmds.getAttr(control + ".rotateZ", lock=True):
            result["cases"].append(_ik_case(label + "_rz10_mode1", control, "rotateZ", 10.0, 1))
    if cmds.objExists("Terminal.Twist") and not cmds.getAttr("Terminal.Twist", lock=True):
        result["cases"].append(_ik_case("twist_mode2", "Terminal", "Twist", 10.0, 2))

    result["shoulder_pivot"] = {
        "expected": [0.0, 145.989, 0.0],
        "actual": cmds.xform("DIANA_SPINE_P5_SHOULDER_OP_FK_CTRL", q=True, os=True, rp=True),
    }
    result["shoulder_pivot"]["error"] = _error(
        result["shoulder_pivot"]["actual"], result["shoulder_pivot"]["expected"])
    result["skins"] = _skins(manifest)
    result["downstream_follow"] = _follow_motion_test(manifest)
    result["world_scale_components"] = {
        part: _scale_components(_matrix(fk + ".worldMatrix[0]"))
        for part, fk in build.PARTS.items()
    }
    result["protected_hierarchy_equal"] = all(
        (cmds.listRelatives(node, p=True, fullPath=True) or [None])[0] == parent
        for node, parent in manifest["protected_hierarchy"].items())
    current_cycles = _cycles()
    result["cycles"] = {
        "baseline": manifest["baseline_cycles"],
        "current": current_cycles,
        "new": sorted(set(current_cycles) - set(manifest["baseline_cycles"])),
    }
    result["max_matrix_error"] = max(
        [max(v["matrix_error"], v["follow_error"])
         for case in result["cases"] for v in case["parts"].values()] +
        [stage["mode0_baseline_error"] for stage in result["stages"]])
    result["all_pass"] = (
        all(x["pass"] for x in result["stages"]) and
        all(x["pass"] for x in result["cases"]) and
        result["shoulder_pivot"]["error"] <= TOLERANCE and
        not result["cycles"]["new"] and
        result["protected_hierarchy_equal"] and
        result["downstream_follow"]["pass"] and
        all(x["exists"] and x["influences_equal"] and x["geometry_equal"]
            for x in result["skins"].values()))
    _zero_controls(); _set_mode(0)
    with open(output_path, "w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, sort_keys=True)
    return result


def post_reload(output_path=OUTPUT):
    with open(output_path, "r", encoding="utf-8") as stream:
        result = json.load(stream)
    result["save_reload"] = {
        "scene": cmds.file(q=True, sn=True),
        "root_exists": cmds.objExists(build.ROOT),
        "registry_exists": cmds.objExists(build.REGISTRY),
        "connections": {
            part: {
                "0": build.source("DIANA_SPINE_DEFORM_{}_MODE_CHOICE.input[0]".format(part)),
                "2": build.source("DIANA_SPINE_DEFORM_{}_MODE_CHOICE.input[2]".format(part)),
            } for part in build.PARTS
        },
    }
    result["save_reload"]["pass"] = (
        result["save_reload"]["root_exists"] and
        result["save_reload"]["registry_exists"] and
        all("DIANA_SPINE_P5_" in values[index]
            for values in result["save_reload"]["connections"].values()
            for index in ("0", "2")))
    result["all_pass"] = bool(result["all_pass"] and result["save_reload"]["pass"])
    with open(output_path, "w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, sort_keys=True)
    return result


if __name__ == "__main__":
    print(run())
