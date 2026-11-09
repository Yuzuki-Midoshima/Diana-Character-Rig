# -*- coding: utf-8 -*-
"""Exact six-direction matcher using Phase 9 downstream corrections."""
from __future__ import absolute_import, division, print_function
import math
import maya.api.OpenMaya as om
import maya.cmds as cmds
from . import diana_spine_phase9_integrate as p9
from . import diana_spine_phase9_correction as correction

MODE="Terminal.Spine_Mode"; POS_TOL=1e-3; ROT_TOL=1e-3
FINALS={p:"DIANA_SPINE_DEFORM_{}_FINAL_PROXY".format(p) for p in p9.PARTS}
ARMS={s:s+"_arm_GRP" for s in p9.ARM_SIDES}


def matrix(node):
    v=cmds.getAttr(node+".worldMatrix[0]"); v=v[0] if len(v)==1 and isinstance(v[0],(list,tuple)) else v
    return [float(x) for x in v]


def worlds(): return {p:matrix(n) for p,n in FINALS.items()}


def errors(target):
    data={}
    for p,n in FINALS.items():
        a,b=matrix(n),target[p]
        pos=math.sqrt(sum((a[i]-b[i])**2 for i in (12,13,14)))
        qa=om.MTransformationMatrix(om.MMatrix(a)).rotation(asQuaternion=True)
        qb=om.MTransformationMatrix(om.MMatrix(b)).rotation(asQuaternion=True)
        q=qa*qb.inverse(); rot=math.degrees(2*math.acos(min(1.0,abs(q.w))))
        data[p]={"position":pos,"rotation_degrees":rot,"matrix":max(abs(x-y) for x,y in zip(a,b))}
    return {"parts":data,"max_position":max(x["position"] for x in data.values()),
            "max_rotation_degrees":max(x["rotation_degrees"] for x in data.values()),
            "max_matrix":max(x["matrix"] for x in data.values())}


def _plugs():
    result=[p9.control(part,mode)+"."+attr for mode in p9.MODES for part in p9.PARTS
            for attr in ("translateX","translateY","translateZ","rotateX","rotateY","rotateZ")]
    result += [p9.arm_control(side,mode)+"."+attr for mode in p9.MODES for side in p9.ARM_SIDES
               for attr in ("translateX","translateY","translateZ","rotateX","rotateY","rotateZ")]
    return result


def _snapshot():
    plugs=_plugs()+[MODE]; result={"values":{},"keys":{}}
    for plug in plugs:
        result["values"][plug]=cmds.getAttr(plug)
        result["keys"][plug]=list(zip(cmds.keyframe(plug,q=True,timeChange=True) or [],cmds.keyframe(plug,q=True,valueChange=True) or []))
    return result


def _restore(s):
    for plug,value in s["values"].items():
        source=cmds.connectionInfo(plug,sourceFromDestination=True) or ""
        if source and cmds.nodeType(source.split(".",1)[0]).startswith("animCurve"):
            cmds.cutKey(plug,clear=True)
            for t,v in s["keys"][plug]: cmds.setKeyframe(plug,time=t,value=v)
        elif not source: cmds.setAttr(plug,value)
    cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)


def _set_mode(mode,key):
    source=cmds.connectionInfo(MODE,sourceFromDestination=True) or ""
    if key or (source and cmds.nodeType(source.split(".",1)[0]).startswith("animCurve")):
        cmds.setKeyframe(MODE,time=cmds.currentTime(q=True),value=mode,inTangentType="stepnext",outTangentType="step")
    else: cmds.setAttr(MODE,mode)


def match(target_mode,key=False):
    if target_mode not in p9.MODES: raise ValueError(target_mode)
    if not cmds.objExists(p9.ROOT): raise RuntimeError("Phase 9 correction network is not installed")
    source_mode=int(cmds.getAttr(MODE)); target=worlds(); arm_target={s:matrix(n) for s,n in ARMS.items()}; snapshot=_snapshot()
    report={"from":source_mode,"to":target_mode,"keyed":bool(key),"before":target}
    cmds.undoInfo(openChunk=True,chunkName="DianaSpinePhase9Match")
    try:
        if source_mode==target_mode:
            report["idempotent"]=True
        else:
            # When correction channels are already animated, zero them at the
            # current switch frame.  setAttr cannot neutralize an animCurve.
            correction.clear(target_mode,key=key)
            _set_mode(target_mode,key)
            cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
            base=worlds()
            for part in p9.PARTS: correction.apply_world_delta(part,target_mode,base[part],target[part],key=key)
            cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
            for side in p9.ARM_SIDES: correction.apply_arm_world(side,target_mode,arm_target[side],key=key)
            cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
        report["errors"]=errors(target)
        report["success"]=(report["errors"]["max_position"]<=POS_TOL and report["errors"]["max_rotation_degrees"]<=ROT_TOL)
        if not report["success"]:
            _restore(snapshot); report["restored"]=True
        else: report["restored"]=False
        return report
    except Exception:
        _restore(snapshot); raise
    finally: cmds.undoInfo(closeChunk=True)

