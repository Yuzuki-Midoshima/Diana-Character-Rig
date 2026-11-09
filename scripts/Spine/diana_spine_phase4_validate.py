# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
import datetime, json, math, os
import maya.cmds as cmds
import maya.api.OpenMaya as om
from Spine import diana_spine_phase4 as p4

TOL=1e-4
RESULT_PATH=os.path.join(os.path.dirname(__file__),"Character_spine37_phase4_validation.json")
def mat(p):
 v=cmds.getAttr(p); v=v[0] if len(v)==1 and isinstance(v[0],(tuple,list)) else v; return [float(x) for x in v]
def err(a,b): return max(abs(x-y) for x,y in zip(a,b))
def mm(a,b): return list(om.MMatrix(a)*om.MMatrix(b))
def scale(a): return [math.sqrt(sum(a[r*4+c]**2 for c in range(3))) for r in range(3)]
def case(label,mode):
 cmds.setAttr("Terminal.Spine_Mode",mode); cmds.dgdirty(allPlugs=True)
 out={"label":label,"mode":mode,"parts":{}}
 for part,fk in p4.PARTS.items():
  actual=mat(fk+".worldMatrix[0]")
  if mode==0: expected=_manifest["parts"][part]["worldMatrix"]
  elif mode==1: expected=mat("DIANA_SPINE_DEFORM_{}_MODE1_FINAL_MM.matrixSum".format(part))
  else: expected=mm(mat("DIANA_SPINE_P4_{}_FK_DELTA_CM.outputMatrix".format(part)),mat("DIANA_SPINE_DEFORM_{}_MODE1_FINAL_MM.matrixSum".format(part)))
  e=err(actual,expected); s=scale(actual)
  out["parts"][part]={"matrix_error":e,"scale":s,"scale2_error":max(abs(x-2) for x in s),"pass":e<=TOL}
 out["shoulder_pivot_world"]=cmds.xform("shoulder_spine_anim",q=True,ws=True,rp=True)
 out["pass"]=all(x["pass"] for x in out["parts"].values()); return out
def snapshot_values():
 plugs=["Terminal.Spine_Mode"]
 for n in ["DIANA_SPINE_IK_HIP_CTRL","DIANA_SPINE_IK_UPPER_CTRL"]: plugs += [n+".translate",n+".rotate"]
 for n in p4.PARTS.values(): plugs += [n+".rotate"]
 d={}
 for x in plugs:
  v=cmds.getAttr(x); d[x]=list(v[0]) if isinstance(v,list) and v and isinstance(v[0],tuple) else v
 return d
def restore(d):
 for x,v in d.items(): cmds.setAttr(x,*v) if isinstance(v,list) else cmds.setAttr(x,v)
def run(manifest_path=p4.MANIFEST_PATH,result_path=RESULT_PATH):
 global _manifest
 if not os.path.exists(manifest_path): p4.capture_manifest(manifest_path)
 with open(manifest_path,"r",encoding="utf-8") as f:_manifest=json.load(f)
 saved=snapshot_values(); report={"generated_utc":datetime.datetime.utcnow().isoformat()+"Z","tolerance":TOL,"stages":[],"cases":[]}
 try:
  for part in p4.ORDER:
   stage=p4.integrate_part(part,manifest_path); c=case("stage_"+part+"_mode0",0)
   stage["mode0_validation"]=c; report["stages"].append(stage)
   if not c["pass"]: raise RuntimeError(part+" MODE0 failed")
  report["cases"].append(case("mode0_baseline",0)); report["cases"].append(case("mode1_initial",1)); report["cases"].append(case("mode2_initial",2))
  tests=[("ik_hip_x5",1,"DIANA_SPINE_IK_HIP_CTRL","translate",(5,0,0)),("ik_upper_x5",1,"DIANA_SPINE_IK_UPPER_CTRL","translate",(5,0,0)),("ik_rotate",1,"DIANA_SPINE_IK_UPPER_CTRL","rotate",(10,15,5)),("twist",1,"DIANA_SPINE_IK_UPPER_CTRL","rotate",(0,25,0)),("fk_lower",2,p4.PARTS["LOWER"],"rotate",(12,8,-5)),("fk_middle",2,p4.PARTS["MIDDLE"],"rotate",(-9,6,11)),("fk_shoulder",2,p4.PARTS["SHOULDER"],"rotate",(7,-10,13))]
  for label,mode,node,attr,delta in tests:
   restore(saved); base=cmds.getAttr(node+"."+attr)[0]; cmds.setAttr(node+"."+attr,*[base[i]+delta[i] for i in range(3)]); report["cases"].append(case(label,mode))
 finally: restore(saved)
 report["all_pass"]=all(c["pass"] for c in report["cases"]) and all(s["mode0_validation"]["pass"] for s in report["stages"])
 report["skinClusters_unchanged"]={n:(cmds.objExists(n) and (cmds.skinCluster(n,q=True,influence=True) or [])==v["influences"]) for n,v in _manifest["skinClusters"].items()}
 report["shoulder_pivot_local"]=cmds.xform("shoulder_spine_anim",q=True,os=True,rp=True)
 report["shoulder_pivot_local_error"]=max(abs(a-b) for a,b in zip(report["shoulder_pivot_local"],_manifest["shoulder_pivot_local"]))
 with open(result_path,"w",encoding="utf-8") as f:json.dump(report,f,indent=2,sort_keys=True,ensure_ascii=False)
 print("[DIANA SPINE P4] pass:",report["all_pass"]); return report
