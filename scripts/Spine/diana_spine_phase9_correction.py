# -*- coding: utf-8 -*-
"""Correction lifecycle management for Phase 9."""
from __future__ import absolute_import, division, print_function
import math
import maya.api.OpenMaya as om
import maya.cmds as cmds
from . import diana_spine_phase9_integrate as p9


def values(mode):
    result={p: {a: cmds.getAttr(p9.control(p,mode)+"."+a) for a in ("translateX","translateY","translateZ","rotateX","rotateY","rotateZ")}
            for p in p9.PARTS}
    result.update({"ARM_"+s:{a:cmds.getAttr(p9.arm_control(s,mode)+"."+a) for a in ("translateX","translateY","translateZ","rotateX","rotateY","rotateZ")} for s in p9.ARM_SIDES})
    return result


def _set(plug, value, key=False):
    if key:
        cmds.setKeyframe(plug, time=cmds.currentTime(q=True), value=float(value), inTangentType="stepnext", outTangentType="step")
    else: cmds.setAttr(plug, float(value))


def clear(mode, key=False):
    for part in p9.PARTS:
        ctrl = p9.control(part,mode)
        for attr in ("translateX","translateY","translateZ","rotateX","rotateY","rotateZ"): _set(ctrl+"."+attr, 0.0, key)
    for side in p9.ARM_SIDES:
        ctrl=p9.arm_control(side,mode)
        for attr in ("translateX","translateY","translateZ","rotateX","rotateY","rotateZ"): _set(ctrl+"."+attr,0.0,key)


def apply_world_delta(part, mode, base, target, key=False):
    delta = om.MMatrix(target) * om.MMatrix(base).inverse()
    tm = om.MTransformationMatrix(delta); t = tm.translation(om.MSpace.kTransform); e = tm.rotation()
    ctrl = p9.control(part,mode)
    for attr, value in zip(("translateX","translateY","translateZ"),(t.x,t.y,t.z)): _set(ctrl+"."+attr,value,key)
    for attr, value in zip(("rotateX","rotateY","rotateZ"),(math.degrees(e.x),math.degrees(e.y),math.degrees(e.z))): _set(ctrl+"."+attr,value,key)


def apply_arm_world(side, mode, target_world, key=False):
    arm=side+"_arm_GRP"; parent=(cmds.listRelatives(arm,p=True,fullPath=True) or [None])[0]
    def mat(plug):
        value=cmds.getAttr(plug);value=value[0] if len(value)==1 and isinstance(value[0],(list,tuple)) else value
        return om.MMatrix(value)
    local=mat(arm+".matrix"); parent_world=mat(parent+".worldMatrix[0]") if parent else om.MMatrix()
    desired_opm=local.inverse()*om.MMatrix(target_world)*parent_world.inverse()
    old=mat(p9.arm_control(side,mode)+"_MM.matrixIn[1]")
    delta=desired_opm*old.inverse(); tm=om.MTransformationMatrix(delta); t=tm.translation(om.MSpace.kTransform); e=tm.rotation()
    ctrl=p9.arm_control(side,mode)
    for attr,value in zip(("translateX","translateY","translateZ"),(t.x,t.y,t.z)):_set(ctrl+"."+attr,value,key)
    for attr,value in zip(("rotateX","rotateY","rotateZ"),(math.degrees(e.x),math.degrees(e.y),math.degrees(e.z))):_set(ctrl+"."+attr,value,key)


def is_zero(mode, tolerance=1e-8):
    return all(abs(value) <= tolerance for attrs in values(mode).values() for value in attrs.values())


def safe_reset(mode, force=False, key=False):
    active = int(cmds.getAttr("Terminal.Spine_Mode")) == int(mode)
    if active and not is_zero(mode) and not force:
        return {"reset": False, "reason": "active non-zero correction would change pose"}
    clear(mode,key); cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
    return {"reset": True, "reason": "forced" if force else "inactive or already zero"}

