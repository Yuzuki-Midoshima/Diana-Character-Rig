# -*- coding: utf-8 -*-
"""Create and remove the non-production Phase 6 animation test."""
from __future__ import absolute_import, division, print_function

import maya.cmds as cmds

TAG = "DIANA_SPINE_P6_ANIMATION_REGISTRY"

KEYS = {
    "Terminal.Spine_Mode": [(1, 0), (18, 0), (19, 1), (34, 1),
                             (35, 2), (54, 2), (55, 1), (64, 1), (65, 0), (72, 0)],
    "DIANA_SPINE_IK_HIP_CTRL.translateX": [(1, 0), (20, 5), (40, -2), (72, 0)],
    "DIANA_SPINE_IK_UPPER_CTRL.translateX": [(1, 0), (26, 5), (46, -3), (72, 0)],
    "DIANA_SPINE_IK_UPPER_CTRL.rotateZ": [(1, 0), (30, 16), (50, -10), (72, 0)],
    "DIANA_SPINE_P5_LOWER_OP_FK_CTRL.rotateX": [(1, 0), (12, 10), (18, 0),
                                                  (36, 0), (45, 14), (54, 0), (72, 0)],
    "DIANA_SPINE_P5_MIDDLE_OP_FK_CTRL.rotateY": [(1, 0), (14, -8), (18, 0),
                                                   (36, 0), (48, 11), (54, 0), (72, 0)],
    "DIANA_SPINE_P5_SHOULDER_OP_FK_CTRL.rotateZ": [(1, 0), (16, 7), (18, 0),
                                                     (36, 0), (50, -9), (54, 0), (72, 0)],
    "FK_L_shoulder_anim.rotateX": [(1, 0), (28, 12), (52, -6), (72, 0)],
    "FK_R_shoulder_anim.rotateX": [(1, 0), (28, -12), (52, 6), (72, 0)],
    "IK_L_elbow_anim.translateZ": [(1, 0), (22, 8), (42, -4), (72, 0)],
    "IK_R_elbow_anim.translateZ": [(1, 0), (22, -8), (42, 4), (72, 0)],
    "L_arm_settings_anim.IK_Space": [(1, 1), (31, 1), (32, 0), (56, 0), (57, 1), (72, 1)],
    "R_arm_settings_anim.IK_Space": [(1, 1), (31, 1), (32, 0), (56, 0), (57, 1), (72, 1)],
}


def twist_keys():
    result = {}
    for delta in ("DIANA_SPINE_DEFORM_HIP_TWIST_DELTA",
                  "DIANA_SPINE_DEFORM_CHEST_TWIST_DELTA"):
        sources = cmds.listConnections(delta + ".input1D[0]", s=True, d=False,
                                       p=True, skipConversionNodes=True) or []
        for plug in sources:
            if cmds.objExists(plug) and cmds.getAttr(plug, settable=True):
                result[plug] = [(1, 0), (24, 12), (44, -8), (60, 0), (72, 0)]
    return result


def build():
    if cmds.objExists(TAG):
        raise RuntimeError("Phase 6 animation already exists")
    registry = cmds.createNode("network", name=TAG)
    cmds.addAttr(registry, ln="curves", at="message", multi=True)
    original = {}
    keys = dict(KEYS)
    keys.update(twist_keys())
    for plug, samples in keys.items():
        if not cmds.objExists(plug):
            continue
        original[plug] = cmds.getAttr(plug)
        incoming = cmds.listConnections(plug, s=True, d=False, p=True) or []
        if incoming and not all(cmds.nodeType(x.split(".")[0]).startswith("animCurve") for x in incoming):
            continue
        tangent = "stepnext" if plug.endswith("Spine_Mode") or plug.endswith("IK_Space") else "auto"
        for frame, value in samples:
            cmds.setKeyframe(plug, time=frame, value=value,
                             inTangentType=tangent, outTangentType=tangent)
    curves = cmds.listConnections(list(keys), s=True, d=False, type="animCurve") or []
    for index, curve in enumerate(sorted(set(curves))):
        cmds.connectAttr(curve + ".message", "{}.curves[{}]".format(registry, index))
    cmds.playbackOptions(minTime=1, maxTime=72, animationStartTime=1, animationEndTime=72)
    return {"registry": registry, "curves": sorted(set(curves)), "original": original,
            "twist_plugs": sorted(twist_keys())}


def cleanup(original=None):
    curves = []
    if cmds.objExists(TAG):
        curves = cmds.listConnections(TAG + ".curves", s=True, d=False) or []
    if curves:
        cmds.delete(list(set(curves)))
    if cmds.objExists(TAG):
        cmds.delete(TAG)
    for plug, value in (original or {}).items():
        if cmds.objExists(plug) and not cmds.connectionInfo(plug, isDestination=True):
            cmds.setAttr(plug, value)
    cmds.currentTime(1, edit=True)
    return {"remaining_curves": [x for x in curves if cmds.objExists(x)],
            "registry_exists": cmds.objExists(TAG)}

