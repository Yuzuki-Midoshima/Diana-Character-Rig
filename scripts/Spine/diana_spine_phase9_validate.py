# -*- coding: utf-8 -*-
"""End-to-end Maya validation for Phase 9 correction integration."""
from __future__ import absolute_import, division, print_function
import json, math, os, sys, tempfile, traceback
import maya.standalone
maya.standalone.initialize(name="python")
import maya.api.OpenMaya as om
import maya.cmds as cmds

SCRIPTS=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPTS not in sys.path: sys.path.insert(0,SCRIPTS)
from Spine import diana_spine_phase5_build as p5
from Spine import diana_spine_phase5_integrate as p5i
from Spine import diana_spine_phase5_rollback as p5r
from Spine import diana_spine_phase5b_integrate as p5b
from Spine import diana_spine_phase5b_rollback as p5br
from Spine import diana_spine_phase9_integrate as p9
from Spine import diana_spine_phase9_matcher as matcher
from Spine import diana_spine_phase9_correction as correction
from Spine import diana_spine_phase9_rollback as p9r

HERE=os.path.dirname(__file__)
SOURCE=r"C:/Users/draco/OneDrive/ドキュメント/maya/projects/JAM_rig/scenes/Character_spine37.ma"
SCENE=os.path.join(tempfile.gettempdir(),"Character_spine37_PHASE5B_PHASE9_VALIDATION.ma").replace("\\","/")
OUTPUT=os.path.join(HERE,"Character_spine37_phase9_validation.json")
TRACEBACK=os.path.join(HERE,"phase9_traceback.txt")
TRANSITIONS=((0,1),(1,0),(0,2),(2,0),(1,2),(2,1))
WATCH=("L_clavice_jnt","R_clavice_jnt","FK_L_shoulder_anim","FK_R_shoulder_anim",
       "IK_L_elbow_anim","IK_R_elbow_anim","IK_L_hand_anim_const","IK_R_hand_anim_const",
       "neck_root_jnt","head_jnt","hair_short_back_jnt_1")


def cycles():
    try:return sorted(set(cmds.cycleCheck(all=True,list=True) or []))
    except Exception:return []
def cnodes(x):return {v.split(".",1)[0] for v in x}
def matrix(n):return matcher.matrix(n)
def err(a,b):return max(abs(x-y) for x,y in zip(a,b))
def worlds(nodes):return {n:matrix(n) for n in nodes}
def conns(n):
    r=cmds.listConnections(n,s=True,d=True,c=True,p=True,skipConversionNodes=False) or []
    return sorted((r[i],r[i+1]) for i in range(0,len(r)-1,2))


def key_state(nodes):
    result={}
    for node in nodes:
        result[node]={"times":cmds.keyframe(node,q=True,timeChange=True) or [],
                      "values":cmds.keyframe(node,q=True,valueChange=True) or []}
    return result


def skin_state():
    result={}
    for s in cmds.ls(type="skinCluster") or []:
        inf=cmds.skinCluster(s,q=True,influence=True) or []
        if any("spine" in x.lower() or "back" in x.lower() for x in inf):
            result[s]={"influences":inf,"geometry":cmds.skinCluster(s,q=True,geometry=True) or []}
    return result


def equipment_state():
    def yes(n):
        x=n.lower();return any(t in x for t in ("weapon","sword","gun","socket","equipment")) or x.startswith("bow") or "_bow" in x
    nodes=sorted(n for n in (cmds.ls(type="transform") or []) if yes(n))
    return {n:{"parent":(cmds.listRelatives(n,p=True,fullPath=True) or [None])[0],"connections":conns(n)} for n in nodes}


def reset(base):
    for plug,value in base.items():
        if not cmds.connectionInfo(plug,isDestination=True):cmds.setAttr(plug,value)
    for mode in p9.MODES: correction.clear(mode)
    cmds.setAttr(matcher.MODE,0);cmds.currentTime(1,e=True);cmds.dgdirty(allPlugs=True);cmds.refresh(force=True)


def rerun_test():
    nodes=set(cmds.ls() or []);before=worlds(tuple(matcher.FINALS.values())+WATCH)
    stopped=False;message=""
    try:p9.build()
    except RuntimeError as exc:stopped=True;message=str(exc)
    after=worlds(tuple(matcher.FINALS.values())+WATCH)
    return {"stopped_safely":stopped,"message":message,
            "new_nodes":sorted(set(cmds.ls() or [])-nodes),
            "matrix_error":max(err(before[n],after[n]) for n in before),
            "pass":stopped and not (set(cmds.ls() or [])-nodes) and max(err(before[n],after[n]) for n in before)<=1e-10}


def pose(base,mode,index):
    reset(base)
    fk={0:(8,-6,5),1:(-7,9,-8)}[index]
    ik={0:(3,5,10),1:(-2,-4,-8)}[index]
    for part,value in zip(("LOWER","MIDDLE","SHOULDER"),fk):cmds.setAttr("DIANA_SPINE_P5_{}_OP_FK_CTRL.rotateX".format(part),value)
    cmds.setAttr("DIANA_SPINE_IK_HIP_CTRL.translateX",base["DIANA_SPINE_IK_HIP_CTRL.translateX"]+ik[0])
    cmds.setAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX",base["DIANA_SPINE_IK_UPPER_CTRL.translateX"]+ik[1])
    cmds.setAttr("DIANA_SPINE_IK_UPPER_CTRL.rotateZ",base["DIANA_SPINE_IK_UPPER_CTRL.rotateZ"]+ik[2])
    cmds.setAttr(matcher.MODE,mode);cmds.dgdirty(allPlugs=True);cmds.refresh(force=True)


def cases(base):
    result=[]
    for index in (0,1):
        for source,target in TRANSITIONS:
            pose(base,source,index);before=worlds(WATCH);hand_before={x:before[x] for x in ("IK_L_hand_anim_const","IK_R_hand_anim_const")}
            report=matcher.match(target);after=worlds(WATCH)
            attach_errors={x:err(before[x],after[x]) for x in WATCH}
            attach=max(attach_errors.values())
            hand=max(err(hand_before[x],after[x]) for x in hand_before)
            # Continue operating the destination rig with correction held.
            final_before=matcher.worlds()
            if target==0:cmds.setAttr("DIANA_SPINE_P5_MIDDLE_OP_FK_CTRL.rotateY",cmds.getAttr("DIANA_SPINE_P5_MIDDLE_OP_FK_CTRL.rotateY")+3)
            elif target==1:cmds.setAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX",cmds.getAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX")+1)
            else:cmds.setAttr("DIANA_SPINE_P5_SHOULDER_OP_FK_CTRL.rotateZ",cmds.getAttr("DIANA_SPINE_P5_SHOULDER_OP_FK_CTRL.rotateZ")+3)
            cmds.dgdirty(allPlugs=True);cmds.refresh(force=True)
            operation_motion=max(err(final_before[p],matcher.matrix(n)) for p,n in matcher.FINALS.items())
            result.append({"pose":index,"from":source,"to":target,"match":report,
                           "attachment_error":attach,"attachment_errors":attach_errors,"world_hand_error":hand,
                           "post_snap_operation_motion":operation_motion,
                           "pass":report["success"] and attach<=1e-3 and hand<=1e-3 and operation_motion>1e-6})
    return result


def lifecycle(base):
    pose(base,1,0);first=matcher.match(0);first_values=correction.values(0)
    # Re-snap overwrites, rather than multiplies, the old target correction.
    cmds.setAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX",cmds.getAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX")+1)
    cmds.setAttr(matcher.MODE,1);second=matcher.match(0);second_values=correction.values(0)
    active_refusal=correction.safe_reset(0,force=False)
    cmds.setAttr(matcher.MODE,1);inactive_reset=correction.safe_reset(0,force=False)
    return {"first":first,"second":second,"correction_changed":first_values!=second_values,
            "active_reset":active_refusal,"inactive_reset":inactive_reset,
            "pass":first["success"] and second["success"] and first_values!=second_values and
                   not active_refusal["reset"] and inactive_reset["reset"]}


def animation_test(base):
    reset(base);before_nodes=set(cmds.ls(type="animCurve") or [])
    schedule=((1,0),(13,1),(25,2),(37,0),(49,2),(61,1),(73,0))
    snap_reports=[]
    for frame,mode in schedule:
        cmds.currentTime(frame,e=True)
        if frame==1:cmds.setAttr(matcher.MODE,mode)
        else:snap_reports.append(matcher.match(mode,key=True))
        cmds.setKeyframe("DIANA_SPINE_IK_UPPER_CTRL.translateX",time=frame,value=base["DIANA_SPINE_IK_UPPER_CTRL.translateX"]+(frame%7))
        cmds.setKeyframe("DIANA_SPINE_P5_MIDDLE_OP_FK_CTRL.rotateY",time=frame,value=(frame%9)-4)
    invalid=[];flips=[];previous=None;switches={x[0] for x in schedule}
    for frame in range(1,74):
        cmds.currentTime(frame,e=True);cmds.dgdirty(allPlugs=True);cmds.refresh(force=True);current=matcher.worlds()
        if any(not math.isfinite(v) for m in current.values() for v in m):invalid.append(frame)
        if previous and frame not in switches:
            for p in p9.PARTS:
                qa=om.MTransformationMatrix(om.MMatrix(previous[p])).rotation(asQuaternion=True);qb=om.MTransformationMatrix(om.MMatrix(current[p])).rotation(asQuaternion=True)
                angle=math.degrees(2*math.acos(min(1.0,abs((qa*qb.inverse()).w))))
                if angle>90:flips.append({"frame":frame,"part":p,"degrees":angle})
        previous=current
    curves=sorted(set(cmds.ls(type="animCurve") or [])-before_nodes)
    return {"frames":73,"snaps":snap_reports,"invalid":invalid,"flips":flips,"curves":curves,
            "pass":all(x["success"] for x in snap_reports) and not invalid and not flips}


def main():
    cmds.file(SOURCE,o=True,f=True,prompt=False);cmds.file(rename=SCENE);cmds.file(save=True,type="mayaAscii",force=True)
    source_cycles=cycles();source_world=worlds(tuple(matcher.FINALS.values())+WATCH);skins=skin_state();equipment=equipment_state()
    layers_before=sorted(cmds.ls(type="animLayer") or [])
    key_nodes=("Terminal.Spine_Mode","DIANA_SPINE_IK_HIP_CTRL","DIANA_SPINE_IK_UPPER_CTRL")
    keys_before=key_state(key_nodes)
    p5.build();[p5i.integrate_part(x) for x in p5i.ORDER];p5b.capture_manifest();p5b.integrate_side("L");p5b.integrate_side("R")
    protected={n:conns(n) for n in ("back_spine_curve","RIG_spineStretch_MD","DIANA_SPINE_INDEPENDENT_IK_CURVE","Terminal")}
    p9.build()
    protected_after_build=all(conns(n)==v for n,v in protected.items())
    keys_after_build=key_state(key_nodes)
    rerun=rerun_test()
    base_plugs=["DIANA_SPINE_IK_HIP_CTRL.translateX","DIANA_SPINE_IK_UPPER_CTRL.translateX","DIANA_SPINE_IK_UPPER_CTRL.rotateZ"]
    base_plugs += ["DIANA_SPINE_P5_{}_OP_FK_CTRL.rotate{}".format(part,axis)
                   for part in p9.PARTS for axis in "XYZ"]
    base={plug:cmds.getAttr(plug) for plug in base_plugs}
    snap_cases=cases(base);life=lifecycle(base);anim=animation_test(base)
    new_cycles=sorted(cnodes(cycles())-cnodes(source_cycles))
    result={"cases":snap_cases,"lifecycle":life,"animation":anim,"rerun_safety":rerun,"new_cycle_nodes":new_cycles,
            "skin_equal":skin_state()==skins,"equipment_equal":equipment_state()==equipment,
            "protected_connections_equal":protected_after_build,
            "existing_keys_equal_after_build":keys_after_build==keys_before,
            "animation_layers_equal":sorted(cmds.ls(type="animLayer") or [])==layers_before}
    result["pre_reload_pass"]=all(x["pass"] for x in snap_cases) and life["pass"] and anim["pass"] and rerun["pass"] and not new_cycles and result["skin_equal"] and result["equipment_equal"] and result["protected_connections_equal"] and result["existing_keys_equal_after_build"] and result["animation_layers_equal"]
    cmds.file(save=True,type="mayaAscii",force=True);cmds.file(SCENE,o=True,f=True,prompt=False)
    reload={"root":cmds.objExists(p9.ROOT),"cycles":sorted(cnodes(cycles())-cnodes(source_cycles)),"skin":skin_state()==skins,"equipment":equipment_state()==equipment}
    reload["pass"]=reload["root"] and not reload["cycles"] and reload["skin"] and reload["equipment"]
    # Remove only Phase 9 test animation curves, then rollback all phases.
    for curve in anim["curves"]:
        if cmds.objExists(curve):cmds.delete(curve)
    for plug,value in base.items():
        if cmds.objExists(plug) and not cmds.connectionInfo(plug,isDestination=True):cmds.setAttr(plug,value)
    cmds.setAttr(matcher.MODE,0);[correction.clear(m) for m in p9.MODES]
    rb9=p9r.rollback();rb5b=p5br.rollback();rb5=p5r.rollback();after=worlds(tuple(matcher.FINALS.values())+WATCH)
    rb_error=max(err(source_world[n],after[n]) for n in source_world)
    rollback={"phase9":rb9,"phase5b":rb5b,"phase5":rb5,"matrix_error":rb_error,
              "skin":skin_state()==skins,"equipment":equipment_state()==equipment,
              "cycles":sorted(cnodes(cycles())-cnodes(source_cycles))}
    rollback["pass"]=not rb9["remaining"] and not rb5b["remaining"] and not rb5["remaining"] and rb_error<=1e-4 and rollback["skin"] and rollback["equipment"] and not rollback["cycles"]
    result["save_reload"]=reload;result["rollback"]=rollback;result["source_scene_modified"]=False
    result["phase9_complete"]=result["pre_reload_pass"] and reload["pass"] and rollback["pass"]
    with open(OUTPUT,"w",encoding="utf-8") as s:json.dump(result,s,indent=2,ensure_ascii=False,sort_keys=True)
    cmds.file(save=True,type="mayaAscii",force=True);print("[DIANA SPINE P9] complete:",result["phase9_complete"])
    return result


if __name__=="__main__":
    try:main()
    except Exception:
        with open(TRACEBACK,"w",encoding="utf-8") as s:s.write(traceback.format_exc())
        raise
    finally:maya.standalone.uninitialize()
