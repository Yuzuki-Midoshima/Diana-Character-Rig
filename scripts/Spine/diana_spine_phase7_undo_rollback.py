# -*- coding: utf-8 -*-
"""Focused interactive Undo, idempotency, and failure-rollback checks."""
from __future__ import absolute_import, division, print_function

import maya.cmds as cmds
from . import diana_spine_phase7_matcher as matcher


def _error(a, b): return max(abs(x-y) for x, y in zip(a, b))


def validate():
    before = matcher._worlds()
    mode = int(cmds.getAttr(matcher.MODE_PLUG))
    same = matcher.match(mode)
    idempotent_error = max(_error(before[x], matcher._matrix(x)) for x in before)

    # A guaranteed zero-delta IK -> IK+FK transition validates one Maya undo
    # chunk without invoking an underdetermined solve.
    for plug in matcher._fk_plugs(): matcher._set(plug, 0.0)
    cmds.setAttr(matcher.MODE_PLUG, 1)
    undo_before = matcher._worlds()
    snap = matcher.match(2)
    snapped = matcher._worlds()
    cmds.undo(); cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
    undo_error = max(_error(undo_before[x], matcher._matrix(x)) for x in undo_before)
    cmds.redo(); cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
    redo_error = max(_error(snapped[x], matcher._matrix(x)) for x in snapped)
    return {"idempotent": {"report": same, "matrix_error": idempotent_error,
                            "pass": same["success"] and idempotent_error <= 1e-4},
            "undo_redo": {"report": snap, "undo_error": undo_error,
                           "redo_error": redo_error,
                           "pass": snap["success"] and undo_error <= 1e-4 and redo_error <= 1e-4}}

