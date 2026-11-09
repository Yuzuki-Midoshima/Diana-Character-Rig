# -*- coding: utf-8 -*-
"""360-frame release-candidate animation durability test."""
from __future__ import absolute_import, division, print_function
import math
import maya.api.OpenMaya as om
import maya.cmds as cmds
from . import diana_spine_phase9_matcher as matcher


def _cycles():
    try:return sorted(set(cmds.cycleCheck(all=True,list=True) or []))
    except Exception:return []


def _matrix(node):return matcher.matrix(node)


def _twist_plugs():
    result=[]
    for node in ("DIANA_SPINE_DEFORM_HIP_TWIST_DELTA","DIANA_SPINE_DEFORM_CHEST_TWIST_DELTA"):
        for plug in cmds.listConnections(node+".input1D[0]",s=True,d=False,p=True,skipConversionNodes=True) or []:
            if cmds.objExists(plug) and cmds.getAttr(plug,settable=True):result.append(plug)
    return sorted(set(result))


def _tracked():
    fixed=list(matcher.FINALS.values())+["L_clavice_jnt","R_clavice_jnt","FK_L_shoulder_anim","FK_R_shoulder_anim",
          "IK_L_elbow_anim","IK_R_elbow_anim","IK_L_hand_anim_const","IK_R_hand_anim_const",
          "neck_root_jnt","head_jnt","hair_short_back_jnt_1"]
    discovered=[]
    for node in cmds.ls(type=("joint","transform")) or []:
        low=node.lower()
        if any(token in low for token in ("knee","ankle","foot","toe","weapon_socket")) and cmds.objExists(node+".worldMatrix[0]"):
            discovered.append(node)
    return list(dict.fromkeys([x for x in fixed+sorted(discovered)[:40] if cmds.objExists(x)]))


def run(start=1,end=360):
    baseline_cycles=_cycles();before_curves=set(cmds.ls(type="animCurve") or [])
    layer="DIANA_SPINE_P10_TEST_LAYER"
    if cmds.objExists(layer):cmds.delete(layer)
    cmds.animLayer(layer)
    layer_plug="DIANA_SPINE_P5_SHOULDER_OP_FK_CTRL.rotateZ"
    cmds.animLayer(layer,e=True,attribute=layer_plug,preferred=True)
    controls={
      "DIANA_SPINE_IK_HIP_CTRL.translateX":lambda f:7.0*math.sin(f*0.035),
      "DIANA_SPINE_IK_UPPER_CTRL.translateX":lambda f:9.0*math.sin(f*0.027),
      "DIANA_SPINE_IK_UPPER_CTRL.rotateZ":lambda f:28.0*math.sin(f*0.021),
      "DIANA_SPINE_P5_LOWER_OP_FK_CTRL.rotateX":lambda f:32.0*math.sin(f*0.023),
      "DIANA_SPINE_P5_MIDDLE_OP_FK_CTRL.rotateY":lambda f:25.0*math.sin(f*0.031),
      layer_plug:lambda f:22.0*math.sin(f*0.029),
      "FK_L_shoulder_anim.rotateX":lambda f:18.0*math.sin(f*0.019),
      "FK_R_shoulder_anim.rotateX":lambda f:-18.0*math.sin(f*0.019),
      "IK_L_elbow_anim.translateZ":lambda f:10.0*math.sin(f*0.025),
      "IK_R_elbow_anim.translateZ":lambda f:-10.0*math.sin(f*0.025),
    }
    for plug in _twist_plugs():controls[plug]=lambda f:35.0*math.sin(f*0.017)
    for frame in range(start,end+1,15):
        for plug,fn in controls.items():
            kwargs={"time":frame,"value":fn(frame),"inTangentType":"auto","outTangentType":"auto"}
            if plug==layer_plug:kwargs["animLayer"]=layer
            cmds.setKeyframe(plug,**kwargs)
    schedule=[];pattern=(0,1,2,1,0,2)
    for index,frame in enumerate(range(start,end+1,30)):
        cmds.currentTime(frame,e=True);mode=pattern[index%len(pattern)]
        if index==0:cmds.setAttr(matcher.MODE,mode);report={"success":True,"from":mode,"to":mode}
        else:report=matcher.match(mode,key=True)
        schedule.append({"frame":frame,"mode":mode,"report":report})
    cmds.playbackOptions(minTime=start,maxTime=end,animationStartTime=start,animationEndTime=end)
    tracked=_tracked();invalid=[];flips=[];cycle_frames=[];previous={}
    switch_frames={x["frame"] for x in schedule}
    for frame in range(start,end+1):
        cmds.currentTime(frame,e=True);cmds.dgdirty(allPlugs=True);cmds.refresh(force=True)
        current={n:_matrix(n) for n in tracked}
        bad=[n for n,m in current.items() if any(not math.isfinite(v) for v in m)]
        if bad:invalid.append({"frame":frame,"nodes":bad})
        if frame not in switch_frames:
            for node,m in current.items():
                if node not in previous:continue
                qa=om.MTransformationMatrix(om.MMatrix(previous[node])).rotation(asQuaternion=True)
                qb=om.MTransformationMatrix(om.MMatrix(m)).rotation(asQuaternion=True)
                angle=math.degrees(2*math.acos(min(1.0,abs((qa*qb.inverse()).w))))
                if angle>90.0:flips.append({"frame":frame,"node":node,"degrees":angle})
        current_cycles=sorted(set(_cycles())-set(baseline_cycles))
        if current_cycles:cycle_frames.append({"frame":frame,"nodes":current_cycles})
        previous=current
    curves=sorted(set(cmds.ls(type="animCurve") or [])-before_curves)
    result={"frames":end-start+1,"schedule":schedule,"tracked_nodes":tracked,"twist_plugs":_twist_plugs(),
            "animation_layer":layer,"new_curves":curves,"invalid_matrices":invalid,
            "unexpected_flips":flips,"cycle_frames":cycle_frames}
    result["pass"]=all(x["report"]["success"] for x in schedule) and not invalid and not flips and not cycle_frames and cmds.objExists(layer)
    return result
