# -*- coding: utf-8 -*-
"""Matrix correction and residual helpers for Phase 8 candidates."""
from __future__ import absolute_import, division, print_function
import math
import maya.api.OpenMaya as om
import maya.cmds as cmds


def matrix(plug):
    value = cmds.getAttr(plug)
    value = value[0] if len(value) == 1 and isinstance(value[0], (list, tuple)) else value
    return [float(x) for x in value]


def set_delta(control, base, target, rotation=True):
    delta = om.MMatrix(target) * om.MMatrix(base).inverse()
    tm = om.MTransformationMatrix(delta)
    t = tm.translation(om.MSpace.kTransform)
    cmds.setAttr(control + ".translate", t.x, t.y, t.z)
    if rotation:
        e = tm.rotation()
        cmds.setAttr(control + ".rotate", math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


def errors(outputs, targets):
    result = {}
    for part, plug in outputs.items():
        actual, target = matrix(plug), targets[part]
        pos = math.sqrt(sum((actual[i] - target[i]) ** 2 for i in (12, 13, 14)))
        qa = om.MTransformationMatrix(om.MMatrix(actual)).rotation(asQuaternion=True)
        qb = om.MTransformationMatrix(om.MMatrix(target)).rotation(asQuaternion=True)
        q = qa * qb.inverse()
        rot = math.degrees(2 * math.acos(min(1.0, abs(q.w))))
        result[part] = {"position": pos, "rotation_degrees": rot,
                        "matrix": max(abs(x-y) for x, y in zip(actual, target))}
    return {"parts": result,
            "max_position": max(x["position"] for x in result.values()),
            "max_rotation_degrees": max(x["rotation_degrees"] for x in result.values()),
            "max_matrix": max(x["matrix"] for x in result.values())}

