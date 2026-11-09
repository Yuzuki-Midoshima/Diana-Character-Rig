# -*- coding: utf-8 -*-
"""Transactional numerical validation for the Diana Spine P23 proxy."""

from __future__ import absolute_import, division, print_function

import datetime
import json
import math

import maya.cmds as cmds
import maya.api.OpenMaya as om

from Spine import diana_spine_proxy


MATRIX_TOLERANCE = 1.0e-4
POSITION_TOLERANCE = 1.0e-4
SCALE_TOLERANCE = 1.0e-5
ROTATION_TOLERANCE_DEGREES = 1.0e-5
PARTS = dict(diana_spine_proxy.PARTS)
IK_HIP = "DIANA_SPINE_IK_HIP_CTRL"
IK_UPPER = "DIANA_SPINE_IK_UPPER_CTRL"


def _matrix(plug):
    value = cmds.getAttr(plug)
    if len(value) == 1 and isinstance(value[0], (tuple, list)):
        value = value[0]
    return [float(item) for item in value]


def _mm(a, b):
    return list(om.MMatrix(a) * om.MMatrix(b))


def _identity():
    return list(om.MMatrix())


def _max_error(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def _position(matrix):
    return matrix[12:15]


def _distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _scale(matrix):
    return [math.sqrt(sum(matrix[row * 4 + col] ** 2 for col in range(3))) for row in range(3)]


def _rotation_error_degrees(a, b):
    """Angular difference of scale-normalized rotation bases."""
    sa, sb = _scale(a), _scale(b)
    ra = [[a[row * 4 + col] / sa[row] for col in range(3)] for row in range(3)]
    rb = [[b[row * 4 + col] / sb[row] for col in range(3)] for row in range(3)]
    # trace(Ra * Rb^T) is invariant to row/column vector convention.
    trace = sum(sum(ra[row][k] * rb[row][k] for k in range(3)) for row in range(3))
    cosine = max(-1.0, min(1.0, (trace - 1.0) * 0.5))
    return math.degrees(math.acos(cosine))


def _snapshot():
    nodes = ["Terminal", IK_HIP, IK_UPPER] + list(PARTS.values())
    values = {}
    for node in nodes:
        # Snapshot only channels the test actually writes. FK translation and
        # control scale are locked/connected in this production rig.
        if node == "Terminal":
            attrs = ["Spine_Mode"]
        elif node in (IK_HIP, IK_UPPER):
            attrs = ["translate", "rotate"]
        else:
            attrs = ["rotate"]
        for attr in attrs:
            plug = node + "." + attr
            if cmds.objExists(plug):
                value = cmds.getAttr(plug)
                values[plug] = list(value[0]) if isinstance(value, list) and value and isinstance(value[0], tuple) else value
    return {
        "values": values,
        "selection": cmds.ls(selection=True, long=True) or [],
        "time": cmds.currentTime(q=True),
        "modified": bool(cmds.file(q=True, modified=True)),
        "production_world": {node: _matrix(node + ".worldMatrix[0]") for node in PARTS.values()},
    }


def _restore(snapshot):
    for plug, value in snapshot["values"].items():
        if isinstance(value, list):
            cmds.setAttr(plug, *value)
        else:
            cmds.setAttr(plug, value)
    cmds.currentTime(snapshot["time"], edit=True)
    if snapshot["selection"]:
        cmds.select(snapshot["selection"], replace=True)
    else:
        cmds.select(clear=True)
    cmds.dgdirty(allPlugs=True)
    cmds.refresh(force=True)


def _set_vector(node, attr, value):
    cmds.setAttr(node + "." + attr, *value)


def _case_metrics(label, mode):
    cmds.setAttr("Terminal.Spine_Mode", mode)
    cmds.dgdirty(allPlugs=True)
    result = {"label": label, "mode": mode, "parts": {}}
    for part, fk in PARTS.items():
        prefix = "DIANA_SPINE_P23_" + part
        actual = _matrix(prefix + "_PROXY.worldMatrix[0]")
        if mode == 0:
            expected = _matrix(fk + ".worldMatrix[0]")
        else:
            base = _matrix("DIANA_SPINE_DEFORM_{}_MODE1_FINAL_MM.matrixSum".format(part))
            delta = _matrix(prefix + "_FK_DELTA_CM.outputMatrix") if mode == 2 else _identity()
            expected = _mm(delta, base)
        matrix_error = _max_error(actual, expected)
        position_error = _distance(_position(actual), _position(expected))
        rotation_error = _rotation_error_degrees(actual, expected)
        scale = _scale(actual)
        result["parts"][part] = {
            "matrix_max_abs_error": matrix_error,
            "position_error": position_error,
            "rotation_error_degrees": rotation_error,
            "world_scale": scale,
            "scale_uniform_2_error": max(abs(value - 2.0) for value in scale),
            "pass": (
                matrix_error <= MATRIX_TOLERANCE
                and position_error <= POSITION_TOLERANCE
                and rotation_error <= ROTATION_TOLERANCE_DEGREES
            ),
        }
        if mode == 2:
            alternate = _mm(base, delta)
            result["parts"][part]["alternate_order_difference"] = _max_error(
                expected, alternate
            )
    pivot = cmds.xform("DIANA_SPINE_P23_SHOULDER_CTRL_PROXY", q=True, ws=True, rp=True)
    result["shoulder_pivot_world"] = list(pivot)
    result["pass"] = all(item["pass"] for item in result["parts"].values())
    return result


def _proxy_world_snapshot():
    return {
        part: _matrix("DIANA_SPINE_P23_{}_PROXY.worldMatrix[0]".format(part))
        for part in PARTS
    }


def _proxy_cycles():
    root = diana_spine_proxy.ROOT
    registered = set(cmds.listConnections(
        root + ".dianaProxyNodes", source=True, destination=False
    ) or [])
    # ROOT is only the registry destination for every node.message; excluding
    # it prevents those bookkeeping links from looking like DG feedback.
    edges = {node: set() for node in registered}
    for node in registered:
        downstream = cmds.listConnections(node, source=False, destination=True) or []
        edges[node].update(other for other in downstream if other in registered and other != node)
    visiting, visited, cycles = set(), set(), []

    def visit(node, path):
        if node in visiting:
            start = path.index(node) if node in path else 0
            cycles.append(path[start:] + [node])
            return
        if node in visited:
            return
        visiting.add(node)
        for other in edges[node]:
            visit(other, path + [node])
        visiting.remove(node)
        visited.add(node)

    for node in registered:
        visit(node, [])
    return cycles


def _reset_channels(snapshot):
    for plug, value in snapshot["values"].items():
        if plug == "Terminal.Spine_Mode":
            continue
        if isinstance(value, list):
            cmds.setAttr(plug, *value)
        else:
            cmds.setAttr(plug, value)


def run(output_path=None):
    """Run destructive-in-memory test poses, always restoring production values."""
    if not cmds.objExists(diana_spine_proxy.ROOT):
        raise RuntimeError("Build the proxy first")
    snapshot = _snapshot()
    report = {
        "generated_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "scene": cmds.file(q=True, sceneName=True),
        "tolerances": {
            "matrix_max_abs": MATRIX_TOLERANCE,
            "position_world_units": POSITION_TOLERANCE,
            "scale": SCALE_TOLERANCE,
            "rotation_degrees": ROTATION_TOLERANCE_DEGREES,
        },
        "cases": [],
    }
    tests = [
        ("initial_ik", 1, None),
        ("ik_hip_translate_x_plus_5", 1, (IK_HIP, "translate", (5, 0, 0))),
        ("ik_upper_translate_x_plus_5", 1, (IK_UPPER, "translate", (5, 0, 0))),
        ("ik_hip_rotate", 1, (IK_HIP, "rotate", (10, 15, 5))),
        ("ik_upper_rotate", 1, (IK_UPPER, "rotate", (-8, 12, 7))),
        ("spine_bend", 1, (IK_UPPER, "rotate", (20, 0, 0))),
        ("spine_twist", 1, (IK_UPPER, "rotate", (0, 25, 0))),
        ("ik_mode_ignores_fk_lower", 1, (PARTS["LOWER"], "rotate", (12, 8, -5))),
        ("fk_lower", 2, (PARTS["LOWER"], "rotate", (12, 8, -5))),
        ("fk_middle", 2, (PARTS["MIDDLE"], "rotate", (-9, 6, 11))),
        ("fk_shoulder", 2, (PARTS["SHOULDER"], "rotate", (7, -10, 13))),
    ]
    try:
        for label, mode, change in tests:
            _reset_channels(snapshot)
            if change:
                original = snapshot["values"][change[0] + "." + change[1]]
                value = tuple(original[index] + change[2][index] for index in range(3))
                _set_vector(change[0], change[1], value)
            report["cases"].append(_case_metrics(label, mode))

        _reset_channels(snapshot)
        lower = snapshot["values"][PARTS["LOWER"] + ".rotate"]
        middle = snapshot["values"][PARTS["MIDDLE"] + ".rotate"]
        _set_vector(PARTS["LOWER"], "rotate", tuple(lower[i] + (10, 5, 0)[i] for i in range(3)))
        _set_vector(PARTS["MIDDLE"], "rotate", tuple(middle[i] + (-5, 0, 12)[i] for i in range(3)))
        report["cases"].append(_case_metrics("fk_lower_middle_combined", 2))

        _set_vector(IK_UPPER, "translate", tuple(snapshot["values"][IK_UPPER + ".translate"][i] + (5, 0, 0)[i] for i in range(3)))
        report["cases"].append(_case_metrics("ik_with_fk_additive", 2))

        _reset_channels(snapshot)
        report["mode_switches"] = []
        previous_mode = 0
        cmds.setAttr("Terminal.Spine_Mode", previous_mode)
        previous_world = _proxy_world_snapshot()
        for label, mode in (("switch_fk_to_ik", 1), ("switch_ik_to_fk", 0),
                            ("switch_fk_to_ik_again", 1),
                            ("switch_ik_to_ikfk", 2), ("switch_ikfk_to_ik", 1)):
            case = _case_metrics(label, mode)
            report["cases"].append(case)
            current_world = _proxy_world_snapshot()
            report["mode_switches"].append({
                "label": label,
                "from": previous_mode,
                "to": mode,
                "world_matrix_max_differences": {
                    part: _max_error(previous_world[part], current_world[part])
                    for part in PARTS
                },
            })
            previous_mode, previous_world = mode, current_world
    finally:
        _restore(snapshot)

    restored = {node: _matrix(node + ".worldMatrix[0]") for node in PARTS.values()}
    report["restore"] = {
        "channel_values_restored": all(
            cmds.getAttr(plug) == value or
            (isinstance(value, list) and list(cmds.getAttr(plug)[0]) == value)
            for plug, value in snapshot["values"].items()
        ),
        "production_world_max_errors": {
            node: _max_error(restored[node], before)
            for node, before in snapshot["production_world"].items()
        },
        "selection_restored": (cmds.ls(selection=True, long=True) or []) == snapshot["selection"],
        "time_restored": cmds.currentTime(q=True) == snapshot["time"],
    }
    report["all_numeric_cases_pass"] = all(case["pass"] for case in report["cases"])
    report["proxy_cycles"] = _proxy_cycles()
    report["proxy_graph_acyclic"] = not report["proxy_cycles"]
    report["production_restored"] = (
        report["restore"]["channel_values_restored"] and
        max(report["restore"]["production_world_max_errors"].values()) <= MATRIX_TOLERANCE
    )
    if output_path:
        with open(output_path, "w", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, sort_keys=True, ensure_ascii=False)
        print("[DIANA SPINE P23] Validation wrote: " + output_path)
    print("[DIANA SPINE P23] Numeric pass:", report["all_numeric_cases_pass"])
    print("[DIANA SPINE P23] Production restored:", report["production_restored"])
    return report
