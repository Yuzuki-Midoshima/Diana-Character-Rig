# -*- coding: utf-8 -*-
"""Finite-difference DOF/Jacobian analysis for Diana Spine modes."""
from __future__ import absolute_import, division, print_function
import math
import maya.api.OpenMaya as om
import maya.cmds as cmds
import numpy as np
from . import diana_spine_phase7_matcher as p7


def vector():
    values = []
    for node in p7.FINAL_NODES:
        m = p7._matrix(node)
        values.extend(m[12:15])
        q = om.MTransformationMatrix(om.MMatrix(m)).rotation(asQuaternion=True)
        values.extend((q.x, q.y, q.z))
    return np.asarray(values, dtype=float)


def parameters(mode):
    if mode == 0: return p7._fk_plugs()
    if mode == 1: return p7._ik_plugs()
    return p7._ik_plugs() + p7._fk_plugs()


def analyze(mode, relative_threshold=1e-5):
    cmds.setAttr(p7.MODE_PLUG, mode); cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
    plugs = parameters(mode); base_values = [cmds.getAttr(x) for x in plugs]
    base = vector(); jacobian = np.zeros((len(base), len(plugs)))
    for column, (plug, value) in enumerate(zip(plugs, base_values)):
        step = 0.05 if ".translate" in plug else 0.1
        cmds.setAttr(plug, value + step); cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
        jacobian[:, column] = (vector() - base) / step
        cmds.setAttr(plug, value)
    cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
    singular = np.linalg.svd(jacobian, compute_uv=False)
    threshold = (singular[0] * relative_threshold) if len(singular) else 0.0
    rank = int(np.sum(singular > threshold))
    row_position = jacobian.reshape(4, 6, len(plugs))[:, :3, :].reshape(12, len(plugs))
    row_rotation = jacobian.reshape(4, 6, len(plugs))[:, 3:, :].reshape(12, len(plugs))
    return {"mode": mode, "parameters": plugs, "parameter_count": len(plugs),
            "output_components": len(base), "rank": rank,
            "redundant_parameters": max(0, len(plugs)-rank),
            "unreachable_components": max(0, len(base)-rank),
            "position_rank": int(np.linalg.matrix_rank(row_position, tol=max(threshold, 1e-10))),
            "rotation_rank": int(np.linalg.matrix_rank(row_rotation, tol=max(threshold, 1e-10))),
            "singular_values": [float(x) for x in singular],
            "column_norms": {plug: float(np.linalg.norm(jacobian[:, i]))
                             for i, plug in enumerate(plugs)}}

