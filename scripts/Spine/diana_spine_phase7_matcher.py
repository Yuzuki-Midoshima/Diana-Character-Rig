# -*- coding: utf-8 -*-
"""Command-based, undoable Diana Spine mode matcher for Maya 2026."""
from __future__ import absolute_import, division, print_function

import math
import maya.api.OpenMaya as om
import maya.cmds as cmds
import numpy as np

from . import diana_spine_phase6_animation as p6anim

MODE_PLUG = "Terminal.Spine_Mode"
PARTS = ("HIP", "LOWER", "MIDDLE", "SHOULDER")
FINAL_NODES = tuple("DIANA_SPINE_DEFORM_{}_FINAL_PROXY".format(x) for x in PARTS)
FK_CONTROLS = tuple("DIANA_SPINE_P5_{}_OP_FK_CTRL".format(x) for x in PARTS)
IK_CONTROLS = ("DIANA_SPINE_IK_HIP_CTRL", "DIANA_SPINE_IK_UPPER_CTRL")
POS_TOL = 5.0e-2
ROT_TOL = 1.0e-1


def _matrix(node):
    value = cmds.getAttr(node + ".worldMatrix[0]")
    value = value[0] if len(value) == 1 and isinstance(value[0], (list, tuple)) else value
    return [float(x) for x in value]


def _worlds(): return {node: _matrix(node) for node in FINAL_NODES}


def _rotation_delta(a, b):
    qa = om.MTransformationMatrix(om.MMatrix(a)).rotation(asQuaternion=True)
    qb = om.MTransformationMatrix(om.MMatrix(b)).rotation(asQuaternion=True)
    q = qa * qb.inverse()
    if q.w < 0: q = om.MQuaternion(-q.x, -q.y, -q.z, -q.w)
    axis, angle = q.asAxisAngle()
    return np.array((axis.x * angle, axis.y * angle, axis.z * angle), dtype=float)


def _residual(target):
    values = []
    for node in FINAL_NODES:
        actual, wanted = _matrix(node), target[node]
        values.extend((actual[12] - wanted[12], actual[13] - wanted[13], actual[14] - wanted[14]))
        # Radians are weighted to balance roughly one degree with one cm.
        values.extend(_rotation_delta(actual, wanted) * 20.0)
    return np.asarray(values, dtype=float)


def _errors(target):
    per_node = {}
    for node in FINAL_NODES:
        actual, wanted = _matrix(node), target[node]
        position = math.sqrt(sum((actual[i] - wanted[i]) ** 2 for i in (12, 13, 14)))
        rotation = math.degrees(float(np.linalg.norm(_rotation_delta(actual, wanted))))
        matrix_error = max(abs(x - y) for x, y in zip(actual, wanted))
        per_node[node] = {"position": position, "rotation_degrees": rotation,
                          "matrix": matrix_error}
    return {"nodes": per_node,
            "max_position": max(x["position"] for x in per_node.values()),
            "max_rotation_degrees": max(x["rotation_degrees"] for x in per_node.values()),
            "max_matrix": max(x["matrix"] for x in per_node.values())}


def _source(plug): return cmds.connectionInfo(plug, sourceFromDestination=True) or ""


def _writable(plug):
    if not cmds.objExists(plug) or cmds.getAttr(plug, lock=True): return False
    source = _source(plug)
    return not source or cmds.nodeType(source.split(".", 1)[0]).startswith("animCurve")


def _fk_plugs():
    return ["{}.rotate{}".format(node, axis) for node in FK_CONTROLS for axis in "XYZ"
            if _writable("{}.rotate{}".format(node, axis))]


def _ik_plugs():
    plugs = []
    for node in IK_CONTROLS:
        for channel in ("translateX", "translateY", "translateZ", "rotateX", "rotateY", "rotateZ"):
            plug = node + "." + channel
            if _writable(plug): plugs.append(plug)
    for plug in p6anim.twist_keys():
        if _writable(plug) and plug not in plugs: plugs.append(plug)
    return plugs


def _snapshot(plugs):
    time = cmds.currentTime(q=True)
    result = {"mode": cmds.getAttr(MODE_PLUG), "time": time, "attrs": {}, "keys": {}}
    for plug in plugs:
        result["attrs"][plug] = cmds.getAttr(plug)
        times = cmds.keyframe(plug, q=True, timeChange=True) or []
        values = cmds.keyframe(plug, q=True, valueChange=True) or []
        result["keys"][plug] = list(zip(times, values))
    return result


def _set(plug, value):
    source = _source(plug)
    if source and cmds.nodeType(source.split(".", 1)[0]).startswith("animCurve"):
        cmds.setKeyframe(plug, time=cmds.currentTime(q=True), value=float(value))
    else:
        cmds.setAttr(plug, float(value))


def _restore(snapshot):
    for plug, value in snapshot["attrs"].items():
        source = _source(plug)
        if source and cmds.nodeType(source.split(".", 1)[0]).startswith("animCurve"):
            cmds.cutKey(plug, clear=True)
            for time, key_value in snapshot["keys"][plug]:
                cmds.setKeyframe(plug, time=time, value=key_value)
        elif _writable(plug):
            cmds.setAttr(plug, value)
    cmds.setAttr(MODE_PLUG, snapshot["mode"])
    cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)


def _values(plugs): return np.asarray([cmds.getAttr(x) for x in plugs], dtype=float)


def _apply(plugs, values):
    for plug, value in zip(plugs, values): _set(plug, value)
    cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)


def _solve(plugs, target, max_iterations=24):
    x = _values(plugs)
    best_x, best_r = x.copy(), _residual(target)
    history = [float(np.linalg.norm(best_r))]
    for iteration in range(max_iterations):
        r = _residual(target)
        if np.linalg.norm(r) < np.linalg.norm(best_r): best_x, best_r = x.copy(), r.copy()
        if _errors(target)["max_position"] <= POS_TOL and _errors(target)["max_rotation_degrees"] <= ROT_TOL:
            break
        jacobian = np.zeros((len(r), len(plugs)), dtype=float)
        for column, plug in enumerate(plugs):
            step = 0.05 if ".translate" in plug else 0.1
            trial = x.copy(); trial[column] += step
            _apply(plugs, trial)
            jacobian[:, column] = (_residual(target) - r) / step
        _apply(plugs, x)
        lhs = np.vstack((jacobian, np.eye(len(plugs)) * 0.02))
        rhs = np.concatenate((-r, np.zeros(len(plugs))))
        delta = np.linalg.lstsq(lhs, rhs, rcond=None)[0]
        delta = np.clip(delta, -12.0, 12.0)
        accepted = False
        for scale in (1.0, 0.5, 0.25, 0.1):
            trial = x + delta * scale
            _apply(plugs, trial)
            trial_r = _residual(target)
            if np.linalg.norm(trial_r) < np.linalg.norm(r):
                x, accepted = trial, True
                history.append(float(np.linalg.norm(trial_r)))
                break
        if not accepted:
            _apply(plugs, x)
            break
    _apply(plugs, best_x if np.linalg.norm(best_r) < np.linalg.norm(_residual(target)) else x)
    return {"iterations": len(history) - 1, "objective_history": history}


def preflight(target_mode):
    if target_mode not in (0, 1, 2): raise ValueError("target_mode must be 0, 1, or 2")
    missing = [x for x in (MODE_PLUG,) + FINAL_NODES + FK_CONTROLS + IK_CONTROLS
               if not cmds.objExists(x)]
    if missing: raise RuntimeError("Missing Phase 7 nodes: " + ", ".join(missing))
    if not cmds.undoInfo(q=True, state=True): raise RuntimeError("Maya Undo must be enabled")


def match(target_mode, bake_nonzero_fk=True, raise_on_failure=False):
    """Match current final pose to target mode and return a numeric report."""
    preflight(target_mode)
    source_mode = int(cmds.getAttr(MODE_PLUG))
    target = _worlds()
    all_plugs = sorted(set(_fk_plugs() + _ik_plugs()))
    snapshot = _snapshot(all_plugs)
    report = {"source_mode": source_mode, "target_mode": target_mode,
              "policy": "bake_nonzero_fk" if bake_nonzero_fk else "preserve_fk_delta",
              "before": target, "changed_plugs": [], "solver": None}
    cmds.undoInfo(openChunk=True, chunkName="DianaSpineAutoMatch")
    try:
        if source_mode == target_mode:
            report["idempotent"] = True
        elif target_mode == 0:
            plugs = _fk_plugs()
            cmds.setAttr(MODE_PLUG, 0)
            report["solver"] = _solve(plugs, target)
        elif source_mode == 1 and target_mode == 2:
            # Defined zero-delta transition: do not destroy non-zero animation.
            if max(abs(cmds.getAttr(x)) for x in _fk_plugs()) <= 1.0e-8:
                cmds.setAttr(MODE_PLUG, 2)
            elif bake_nonzero_fk:
                plugs = _ik_plugs()
                cmds.setAttr(MODE_PLUG, 1)
                report["solver"] = _solve(plugs, target)
                for plug in _fk_plugs(): _set(plug, 0.0)
                cmds.setAttr(MODE_PLUG, 2)
            else:
                cmds.setAttr(MODE_PLUG, 2)
        elif source_mode == 2 and target_mode == 1:
            if max(abs(cmds.getAttr(x)) for x in _fk_plugs()) <= 1.0e-8:
                cmds.setAttr(MODE_PLUG, 1)
            elif bake_nonzero_fk:
                plugs = _ik_plugs()
                cmds.setAttr(MODE_PLUG, 1)
                report["solver"] = _solve(plugs, target)
                for plug in _fk_plugs(): _set(plug, 0.0)
            else:
                cmds.setAttr(MODE_PLUG, 1)
        else:
            # FK -> IK or FK -> IK+FK.  Solve the existing IK controls only.
            plugs = _ik_plugs()
            cmds.setAttr(MODE_PLUG, 1)
            report["solver"] = _solve(plugs, target)
            if target_mode == 2:
                for plug in _fk_plugs(): _set(plug, 0.0)
                cmds.setAttr(MODE_PLUG, 2)
        cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
        report["errors"] = _errors(target)
        report["success"] = (report["errors"]["max_position"] <= POS_TOL and
                             report["errors"]["max_rotation_degrees"] <= ROT_TOL)
        report["changed_plugs"] = [p for p in all_plugs
                                   if abs(cmds.getAttr(p) - snapshot["attrs"][p]) > 1.0e-10]
        if not report["success"]:
            report["failure_category"] = ("IK freedom limitation" if target_mode in (1, 2)
                                          else "FK rotation-only freedom limitation")
            _restore(snapshot)
            report["restored_after_failure"] = True
            if raise_on_failure: raise RuntimeError("Spine match exceeded tolerance: {}".format(report["errors"]))
        else:
            report["restored_after_failure"] = False
        return report
    except Exception:
        _restore(snapshot)
        raise
    finally:
        cmds.undoInfo(closeChunk=True)

