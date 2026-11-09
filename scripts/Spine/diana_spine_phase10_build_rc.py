# -*- coding: utf-8 -*-
"""Build the Diana Spine release candidate without modifying the source scene."""
from __future__ import absolute_import, division, print_function
import argparse, hashlib, json, os, sys, time

import maya.standalone
maya.standalone.initialize(name="python")
import maya.cmds as cmds

SCRIPTS=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO=os.path.dirname(SCRIPTS)
if SCRIPTS not in sys.path:sys.path.insert(0,SCRIPTS)
from Spine import diana_spine_phase5_build as p5
from Spine import diana_spine_phase5_integrate as p5i
from Spine import diana_spine_phase5b_integrate as p5b
from Spine import diana_spine_phase9_integrate as p9

SOURCE=r"C:/Users/draco/OneDrive/ドキュメント/maya/projects/JAM_rig/scenes/Character_spine37.ma"
RC=os.path.join(REPO,"dist","Character_spine37_SPINE_RC01.ma")
OUTPUT=os.path.join(os.path.dirname(__file__),"Character_spine37_phase10_rc_manifest.json")


def sha256(path):
    digest=hashlib.sha256()
    with open(path,"rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):digest.update(chunk)
    return digest.hexdigest()


def cycles():
    try:return sorted(set(cmds.cycleCheck(all=True,list=True) or []))
    except Exception:return []


def animation_fingerprint():
    payload=[]
    for node in sorted(cmds.ls(type="animCurve") or []):
        payload.append((node,cmds.keyframe(node,q=True,timeChange=True) or [],cmds.keyframe(node,q=True,valueChange=True) or [],
                        sorted(cmds.listConnections(node,s=False,d=True,p=True) or [])))
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest(),len(payload)


def scene_fingerprint(tokens,types=("transform","joint","parentConstraint","orientConstraint","scaleConstraint")):
    nodes=[]
    for kind in types:nodes.extend(cmds.ls(type=kind) or [])
    nodes=sorted(set(n for n in nodes if any(t in n.lower() for t in tokens)))
    payload=[]
    for node in nodes:
        links=cmds.listConnections(node,s=True,d=True,c=True,p=True,skipConversionNodes=False) or []
        payload.append((node,sorted(links)))
    return {"node_count":len(nodes),"sha256":hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()}


def skin_fingerprint():
    payload=[]
    for node in sorted(cmds.ls(type="skinCluster") or []):
        payload.append((node,cmds.skinCluster(node,q=True,influence=True) or [],cmds.skinCluster(node,q=True,geometry=True) or []))
    return {"count":len(payload),"sha256":hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()}


def build(source=SOURCE,rc=RC,output=OUTPUT,replace=False):
    source=os.path.abspath(source);rc=os.path.abspath(rc)
    if os.path.normcase(source)==os.path.normcase(rc):raise RuntimeError("RC output must differ from source")
    if "_SPINE_RC" not in os.path.basename(rc).upper():raise RuntimeError("RC filename must contain _SPINE_RC")
    if not os.path.isfile(source):raise RuntimeError("Source scene not found: "+source)
    if os.path.exists(rc) and not replace:raise RuntimeError("RC already exists; refusing overwrite (use --replace explicitly): "+rc)
    os.makedirs(os.path.dirname(rc),exist_ok=True)
    before_hash=sha256(source);before_stat=os.stat(source)
    cmds.file(source,o=True,f=True,prompt=False)
    baseline_cycles=cycles()
    source_animation=animation_fingerprint()
    source_protected={"legs":scene_fingerprint(("leg","knee","ankle","foot","toe")),
                      "facial":scene_fingerprint(("face","facial","jaw","eye","brow","mouth")),
                      "equipment":scene_fingerprint(("weapon","equipment","sword","gun","bow_follow")),
                      "skin":skin_fingerprint()}
    cmds.file(rename=rc);cmds.file(save=True,type="mayaAscii",force=True)
    p5.build();[p5i.integrate_part(part) for part in p5i.ORDER]
    p5b.capture_manifest();p5b.integrate_side("L");p5b.integrate_side("R")
    p9.build()
    rc_animation=animation_fingerprint()
    rc_protected={"legs":scene_fingerprint(("leg","knee","ankle","foot","toe")),
                  "facial":scene_fingerprint(("face","facial","jaw","eye","brow","mouth")),
                  "equipment":scene_fingerprint(("weapon","equipment","sword","gun","bow_follow")),
                  "skin":skin_fingerprint()}
    created_cycles=sorted(set(cycles())-set(baseline_cycles))
    if created_cycles:raise RuntimeError("New DG cycles: "+", ".join(created_cycles))
    cmds.file(save=True,type="mayaAscii",force=True)
    after_hash=sha256(source);after_stat=os.stat(source)
    result={"version":1,"created_epoch":time.time(),"source":source,"source_sha256_before":before_hash,
            "source_sha256_after":after_hash,"source_size":before_stat.st_size,
            "source_mtime_before":before_stat.st_mtime,"source_mtime_after":after_stat.st_mtime,
            "source_unchanged":before_hash==after_hash and before_stat.st_mtime==after_stat.st_mtime,
            "rc_scene":rc,"rc_sha256":sha256(rc),"rc_size_bytes":os.path.getsize(rc),
            "maya_version":cmds.about(version=True),"new_cycles":created_cycles,
            "existing_animation":{"source_fingerprint":source_animation[0],"rc_fingerprint":rc_animation[0],
                                  "source_curve_count":source_animation[1],"rc_curve_count":rc_animation[1],
                                  "unchanged":source_animation==rc_animation},
            "protected_subsystems":{"source":source_protected,"rc":rc_protected,"unchanged":source_protected==rc_protected},
            "roots":{"phase5":cmds.objExists(p5.ROOT),"phase5b":cmds.objExists(p5b.ROOT),"phase9":cmds.objExists(p9.ROOT)},
            "external_python_packages":[],"phase10_build_complete":False}
    result["phase10_build_complete"]=result["source_unchanged"] and result["existing_animation"]["unchanged"] and result["protected_subsystems"]["unchanged"] and all(result["roots"].values()) and not created_cycles
    with open(output,"w",encoding="utf-8") as stream:json.dump(result,stream,indent=2,ensure_ascii=False,sort_keys=True)
    print("[DIANA SPINE P10 BUILD] complete:",result["phase10_build_complete"])
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--source",default=SOURCE);parser.add_argument("--output-scene",default=RC);parser.add_argument("--replace",action="store_true")
    args=parser.parse_args()
    try:build(args.source,args.output_scene,replace=args.replace)
    finally:maya.standalone.uninitialize()
