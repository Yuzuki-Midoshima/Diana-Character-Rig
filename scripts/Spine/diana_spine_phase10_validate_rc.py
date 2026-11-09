# -*- coding: utf-8 -*-
"""Fresh-session validation of the retained Diana Spine RC scene."""
from __future__ import absolute_import, division, print_function
import hashlib, json, math, os, sys, tempfile, traceback
import maya.standalone
maya.standalone.initialize(name="python")
import maya.cmds as cmds

SCRIPTS=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));REPO=os.path.dirname(SCRIPTS)
if SCRIPTS not in sys.path:sys.path.insert(0,SCRIPTS)
from Spine import diana_spine_phase9_integrate as p9
from Spine import diana_spine_phase9_matcher as matcher
from Spine import diana_spine_phase9_correction as correction
from Spine import diana_spine_phase10_durability as durability
from Spine import diana_spine_phase10_ui as ui

HERE=os.path.dirname(__file__);RC=os.path.join(REPO,"dist","Character_spine37_SPINE_RC01.ma")
WORK=os.path.join(tempfile.gettempdir(),"Character_spine37_SPINE_RC01_P10_TEST.ma").replace("\\","/")
BUILD_MANIFEST=os.path.join(HERE,"Character_spine37_phase10_rc_manifest.json")
P5B_MANIFEST=os.path.join(HERE,"Character_spine37_phase5b_manifest.json")
OUTPUT=os.path.join(HERE,"Character_spine37_phase10_validation.json")
TRACE=os.path.join(HERE,"phase10_traceback.txt")
TRANSITIONS=((0,1),(1,0),(0,2),(2,0),(1,2),(2,1))
WATCH=("L_clavice_jnt","R_clavice_jnt","FK_L_shoulder_anim","FK_R_shoulder_anim","IK_L_elbow_anim","IK_R_elbow_anim",
       "IK_L_hand_anim_const","IK_R_hand_anim_const","neck_root_jnt","head_jnt","hair_short_back_jnt_1")


def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()
def matrix(n):return matcher.matrix(n)
def worlds(nodes):return {n:matrix(n) for n in nodes if cmds.objExists(n)}
def error(a,b):return max(abs(x-y) for x,y in zip(a,b))
def cycles():
    try:return sorted(set(cmds.cycleCheck(all=True,list=True) or []))
    except Exception:return []
def cycle_nodes(items):return {x.split(".",1)[0] for x in items}
def fingerprint():
    payload=[]
    for node in sorted((cmds.ls(type="skinCluster") or [])+(cmds.ls(type="parentConstraint") or [])+(cmds.ls(type="scaleConstraint") or [])):
        payload.append((node,sorted(cmds.listConnections(node,s=True,d=True,c=True,p=True) or [])))
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()


def reset(base):
    for mode in p9.MODES:correction.clear(mode)
    for plug,value in base.items():
        if cmds.objExists(plug) and not cmds.connectionInfo(plug,isDestination=True):cmds.setAttr(plug,value)
    cmds.setAttr(matcher.MODE,0);cmds.currentTime(1,e=True);cmds.dgdirty(allPlugs=True);cmds.refresh(force=True)


def snap_cases(base):
    result=[]
    for source,target in TRANSITIONS:
        reset(base)
        cmds.setAttr("DIANA_SPINE_P5_LOWER_OP_FK_CTRL.rotateX",24)
        cmds.setAttr("DIANA_SPINE_P5_MIDDLE_OP_FK_CTRL.rotateY",-17)
        cmds.setAttr("DIANA_SPINE_P5_SHOULDER_OP_FK_CTRL.rotateZ",13)
        cmds.setAttr("DIANA_SPINE_IK_HIP_CTRL.translateX",base["DIANA_SPINE_IK_HIP_CTRL.translateX"]+5)
        cmds.setAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX",base["DIANA_SPINE_IK_UPPER_CTRL.translateX"]-7)
        cmds.setAttr("DIANA_SPINE_IK_UPPER_CTRL.rotateZ",base["DIANA_SPINE_IK_UPPER_CTRL.rotateZ"]+20)
        cmds.setAttr(matcher.MODE,source);cmds.dgdirty(allPlugs=True);cmds.refresh(force=True)
        before=worlds(WATCH);report=matcher.match(target);after=worlds(WATCH)
        attachment=max(error(before[n],after[n]) for n in before)
        final_before=matcher.worlds()
        plug={0:"DIANA_SPINE_P5_MIDDLE_OP_FK_CTRL.rotateY",1:"DIANA_SPINE_IK_UPPER_CTRL.translateX",2:"DIANA_SPINE_P5_SHOULDER_OP_FK_CTRL.rotateZ"}[target]
        cmds.setAttr(plug,cmds.getAttr(plug)+2);cmds.dgdirty(allPlugs=True);cmds.refresh(force=True)
        motion=max(error(final_before[p],matrix(n)) for p,n in matcher.FINALS.items())
        result.append({"from":source,"to":target,"match":report,"attachment_error":attachment,"post_snap_motion":motion,
                       "pass":report["success"] and attachment<=1e-3 and motion>1e-6})
    return result


def reset_and_undo(base):
    reset(base);cmds.setAttr(matcher.MODE,1);first=matcher.match(0)
    active=correction.safe_reset(0,force=False);cmds.setAttr(matcher.MODE,1);inactive=correction.safe_reset(0,force=False)
    reset(base);cmds.undoInfo(state=True);before=worlds(matcher.FINALS.values());before_mode=cmds.getAttr(matcher.MODE)
    matched=matcher.match(1);after=worlds(matcher.FINALS.values());after_mode=cmds.getAttr(matcher.MODE)
    cmds.undo();undo_world=worlds(matcher.FINALS.values());undo_mode=cmds.getAttr(matcher.MODE)
    cmds.redo();redo_world=worlds(matcher.FINALS.values());redo_mode=cmds.getAttr(matcher.MODE)
    undo_error=max(error(before[n],undo_world[n]) for n in before);redo_error=max(error(after[n],redo_world[n]) for n in after)
    return {"match":first,"active_reset":active,"inactive_reset":inactive,"undo_error":undo_error,"redo_error":redo_error,
            "undo_mode":undo_mode,"redo_mode":redo_mode,"pass":first["success"] and not active["reset"] and inactive["reset"] and
            matched["success"] and undo_error<=1e-3 and redo_error<=1e-3 and undo_mode==before_mode and redo_mode==after_mode}


def hand_space(base):
    result={}
    for side in ("L","R"):
        setting=side+"_arm_settings_anim.IK_Space";hand="IK_"+side+"_hand_anim_const"
        reset(base);cmds.setAttr(matcher.MODE,1);old=cmds.getAttr(setting)
        cmds.setAttr(setting,1);before=matrix(hand);x=cmds.getAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX");cmds.setAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX",x+5);cmds.dgdirty(allPlugs=True);cmds.refresh(force=True);world_error=error(before,matrix(hand))
        cmds.setAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX",x);cmds.setAttr(setting,0);before=matrix(hand);cmds.setAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX",x+5);cmds.dgdirty(allPlugs=True);cmds.refresh(force=True);body_motion=error(before,matrix(hand))
        cmds.setAttr(setting,old);result[side]={"world_error":world_error,"body_motion":body_motion,"pass":world_error<=1e-3 and body_motion>1e-6}
    return result


def control_exercise(tokens):
    candidates=[]
    for node in cmds.ls(type="transform") or []:
        low=node.lower()
        if any(t in low for t in tokens) and ("anim" in low or "ctrl" in low):candidates.append(node)
    for node in sorted(candidates):
        for attr in ("rotateX","translateX"):
            plug=node+"."+attr
            if cmds.objExists(plug) and cmds.getAttr(plug,settable=True):
                old=cmds.getAttr(plug);before=matrix(node);cmds.setAttr(plug,old+1);cmds.dgdirty(allPlugs=True);cmds.refresh(force=True);motion=error(before,matrix(node));cmds.setAttr(plug,old)
                return {"node":node,"plug":plug,"motion":motion,"pass":motion>1e-8}
    return {"node":None,"pass":False,"reason":"no settable controller found"}


def arm_switch_audit():
    result={}
    for side in ("L","R"):
        node=side+"_arm_settings_anim";attrs=cmds.listAttr(node,userDefined=True) or []
        switches=[a for a in attrs if "ik" in a.lower() and "space" not in a.lower()]
        tests=[]
        for attr in switches:
            plug=node+"."+attr
            if not cmds.getAttr(plug,settable=True):continue
            old=cmds.getAttr(plug);cmds.setAttr(plug,1 if old==0 else 0);cmds.dgdirty(allPlugs=True);cmds.refresh(force=True);cmds.setAttr(plug,old);tests.append(plug)
        result[side]={"candidate_attributes":switches,"exercised":tests,"pass":bool(tests)}
    return result


def main():
    with open(BUILD_MANIFEST,"r",encoding="utf-8") as stream:build=json.load(stream)
    source_hash_before=sha256(build["source"]);rc_hash_before=sha256(RC)
    cmds.file(RC,o=True,f=True,prompt=False)
    with open(P5B_MANIFEST,"r",encoding="utf-8") as stream:known_baseline=json.load(stream).get("baseline_cycles",[])
    baseline_cycle_nodes=cycle_nodes(cycles())|cycle_nodes(known_baseline)
    required=[p9.ROOT,p9.REGISTRY,"Terminal"]+list(matcher.FINALS.values())
    missing=[x for x in required if not cmds.objExists(x)]
    cmds.file(rename=WORK);cmds.file(save=True,type="mayaAscii",force=True)
    base_plugs=["DIANA_SPINE_IK_HIP_CTRL.translateX","DIANA_SPINE_IK_UPPER_CTRL.translateX","DIANA_SPINE_IK_UPPER_CTRL.rotateZ"]
    base_plugs += ["DIANA_SPINE_P5_{}_OP_FK_CTRL.rotate{}".format(part,axis) for part in p9.PARTS for axis in "XYZ"]
    base={p:cmds.getAttr(p) for p in base_plugs};cases=snap_cases(base);lifecycle=reset_and_undo(base);spaces=hand_space(base)
    arms=arm_switch_audit();legs=control_exercise(("leg","knee"));feet=control_exercise(("foot","toe"));facial=control_exercise(("face","jaw","brow","mouth","eye"))
    reset(base);durable=durability.run(1,360);structure=fingerprint();reloads=[]
    for index in range(3):
        cmds.file(save=True,type="mayaAscii",force=True);cmds.file(WORK,o=True,f=True,prompt=False)
        reloads.append({"index":index+1,"root":cmds.objExists(p9.ROOT),"structure_equal":fingerprint()==structure,
                        "new_cycle_nodes":sorted(cycle_nodes(cycles())-baseline_cycle_nodes)})
    # UI is constructed and removed in this fresh Maya session.
    window=ui.show();ui_status=ui.status();cmds.deleteUI(window)
    duplicate_stopped=False
    try:p9.build()
    except RuntimeError:duplicate_stopped=True
    result={"version":1,"rc_scene":RC,"work_scene":WORK,"rc_size_bytes":os.path.getsize(RC),"missing_required_nodes":missing,
            "snap_cases":cases,"correction_undo_redo":lifecycle,"hand_space":spaces,"arm_fk_ik_switch":arms,
            "legs":legs,"reverse_foot":feet,"facial":facial,"durability":durable,"save_reload":reloads,
            "ui":{"window_created":bool(window),"status":ui_status},"duplicate_execution_stopped":duplicate_stopped,
            "new_cycle_nodes":sorted(cycle_nodes(cycles())-baseline_cycle_nodes),"source_hash_before":source_hash_before,
            "source_hash_after":sha256(build["source"]),"rc_hash_before":rc_hash_before,"rc_hash_after":sha256(RC),
            "build_manifest_complete":build["phase10_build_complete"],"phase10_complete":False}
    result["phase10_complete"]=not missing and all(x["pass"] for x in cases) and lifecycle["pass"] and all(x["pass"] for x in spaces.values()) and all(x["pass"] for x in arms.values()) and legs["pass"] and feet["pass"] and facial["pass"] and durable["pass"] and all(x["root"] and x["structure_equal"] and not x["new_cycle_nodes"] for x in reloads) and duplicate_stopped and not result["new_cycle_nodes"] and result["source_hash_before"]==result["source_hash_after"]==build["source_sha256_before"] and result["rc_hash_before"]==result["rc_hash_after"] and build["phase10_build_complete"]
    with open(OUTPUT,"w",encoding="utf-8") as stream:json.dump(result,stream,indent=2,ensure_ascii=False,sort_keys=True)
    print("[DIANA SPINE P10 VALIDATE] complete:",result["phase10_complete"]);return result


if __name__=="__main__":
    try:main()
    except Exception:
        with open(TRACE,"w",encoding="utf-8") as stream:stream.write(traceback.format_exc())
        raise
    finally:maya.standalone.uninitialize()
