# -*- coding: utf-8 -*-
"""Manifest-driven Phase 4 integration for the Diana spine validation scene."""
from __future__ import absolute_import, division, print_function

import datetime, json, os
import maya.cmds as cmds
import maya.api.OpenMaya as om

ROOT = "DIANA_SPINE_P4_INTEGRATION_GRP"
ORDER = ("LOWER", "MIDDLE", "SHOULDER", "HIP")
PARTS = {
    "HIP": "hip_fk_Spine_anim_jnt",
    "LOWER": "lower_fk_Spine_anim",
    "MIDDLE": "middle_fk_Spine_anim",
    "SHOULDER": "shoulder_fk_Spine_anim_jnt",
}
MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "Character_spine37_phase4_manifest.json")

def _matrix(plug):
    v = cmds.getAttr(plug); v = v[0] if len(v) == 1 and isinstance(v[0], (tuple, list)) else v
    return [float(x) for x in v]

def _source(plug):
    return cmds.connectionInfo(plug, sourceFromDestination=True) or ""

def _connections(node):
    raw = cmds.listConnections(node, s=True, d=True, c=True, p=True) or []
    return [{"plug": raw[i], "other": raw[i+1]} for i in range(0, len(raw)-1, 2)]

def _upstream(start):
    pending, seen = [start.split(".")[0]], set()
    while pending:
        node = pending.pop()
        if node in seen: continue
        seen.add(node)
        pending.extend(cmds.listConnections(node, s=True, d=False) or [])
    return seen

def preflight():
    scene = cmds.file(q=True, sn=True)
    if "PHASE4_VALIDATION" not in os.path.basename(scene):
        raise RuntimeError("Refusing non-validation scene: " + scene)
    if cmds.objExists(ROOT):
        raise RuntimeError("Phase 4 integration already exists")
    required = ["Terminal", "shoulder_spine_anim_pad", "shoulder_spine_anim"]
    for part, fk in PARTS.items():
        required += [fk, "DIANA_SPINE_DEFORM_{}_MODE1_FINAL_MM".format(part),
                     "DIANA_SPINE_DEFORM_{}_MODE_CHOICE".format(part)]
    missing = [n for n in required if not cmds.objExists(n)]
    if missing: raise RuntimeError("Missing nodes: " + ", ".join(missing))
    dependency = {}
    fk_set = set(PARTS.values())
    for part in PARTS:
        start = "DIANA_SPINE_DEFORM_{}_MODE1_FINAL_MM".format(part)
        upstream = _upstream(start)
        dependency[part] = {"upstream_count": len(upstream), "fk_hits": sorted(upstream & fk_set)}
    hits = {p:d["fk_hits"] for p,d in dependency.items() if d["fk_hits"]}
    if hits: raise RuntimeError("MODE1 depends on production FK: " + repr(hits))
    return dependency

def capture_manifest(path=MANIFEST_PATH):
    dependency = preflight()
    data = {"version":1, "created_utc":datetime.datetime.utcnow().isoformat()+"Z",
            "scene":cmds.file(q=True,sn=True), "dependency":dependency, "parts":{},
            "shoulder_pivot_local":cmds.xform("shoulder_spine_anim",q=True,os=True,rp=True),
            "skinClusters":{}, "downstream":{}, "created_nodes":[], "stages":[]}
    for part, fk in PARTS.items():
        choice = "DIANA_SPINE_DEFORM_{}_MODE_CHOICE".format(part)
        parent = (cmds.listRelatives(fk,p=True,fullPath=True) or [None])[0]
        attrs = {}
        for a in ("translate","rotate","scale","shear","rotateOrder"):
            if cmds.objExists(fk+"."+a): attrs[a] = cmds.getAttr(fk+"."+a)
        if cmds.nodeType(fk)=="joint": attrs["jointOrient"] = cmds.getAttr(fk+".jointOrient")
        data["parts"][part] = {"fk":fk,"parent":parent,"worldMatrix":_matrix(fk+".worldMatrix[0]"),
            "attrs":attrs,"mode_choice_inputs":{str(i):_source(choice+".input[{}]".format(i)) for i in range(3)},
            "mode1_connections":_connections("DIANA_SPINE_DEFORM_{}_MODE1_FINAL_MM".format(part)),
            "mode2_connections":_connections("DIANA_SPINE_DEFORM_{}_MODE2_FINAL_MM".format(part))}
    for sc in cmds.ls(type="skinCluster") or []:
        inf = cmds.skinCluster(sc,q=True,influence=True) or []
        if any("spine" in x.lower() or "back" in x.lower() for x in inf):
            data["skinClusters"][sc]={"influences":inf,"geometry":cmds.skinCluster(sc,q=True,geometry=True) or []}
    for n in ("shoulder_spine_anim","shoulder_fk_Spine_anim_jnt"):
        data["downstream"][n]=_connections(n)
    with open(path,"w",encoding="utf-8") as f: json.dump(data,f,indent=2,sort_keys=True,ensure_ascii=False)
    return data

def _register(root,node):
    i=len(cmds.getAttr(root+".p4Nodes",multiIndices=True) or [])
    cmds.connectAttr(node+".message","{}.p4Nodes[{}]".format(root,i))

def _node(root,t,n):
    x=cmds.createNode(t,n=n); _register(root,x); return x

def _identity(root,prefix):
    n=_node(root,"fourByFourMatrix",prefix+"_IDENTITY_FBF")
    for i in range(4): cmds.setAttr("{}.in{}{}".format(n,i,i),1)
    return n

def _constant_matrix(root, name, values):
    n=_node(root,"fourByFourMatrix",name)
    for r in range(4):
        for c in range(4): cmds.setAttr("{}.in{}{}".format(n,r,c),values[r*4+c])
    return n

def integrate_part(part, path=MANIFEST_PATH):
    part=part.upper()
    if part not in PARTS: raise ValueError(part)
    if not os.path.exists(path): capture_manifest(path)
    with open(path,"r",encoding="utf-8") as f: manifest=json.load(f)
    expected=ORDER[len(manifest["stages"])] if len(manifest["stages"])<4 else None
    if part != expected: raise RuntimeError("Expected stage {}, got {}".format(expected,part))
    if not cmds.objExists(ROOT):
        root=cmds.createNode("transform",n=ROOT); cmds.addAttr(root,ln="p4Nodes",at="message",multi=True)
    root=ROOT; fk=PARTS[part]; prefix="DIANA_SPINE_P4_"+part
    original_parent=(cmds.listRelatives(fk,p=True,fullPath=False) or [None])[0]
    follow=cmds.createNode("transform",n=prefix+"_FOLLOW",p=original_parent); _register(root,follow)
    cmds.parent(fk,follow,relative=True)
    delta=_node(root,"composeMatrix",prefix+"_FK_DELTA_CM")
    cmds.connectAttr(fk+".rotate",delta+".inputRotate")
    if cmds.objExists(delta+".inputRotateOrder"): cmds.connectAttr(fk+".rotateOrder",delta+".inputRotateOrder")
    # Never consume fk.matrix after parenting: Maya treats that as a feedback
    # dependency through the follow parent. Split the build-time local matrix
    # into animator delta and a constant rest component instead.
    delta_now=om.MMatrix(_matrix(delta+".outputMatrix"))
    local_now=om.MMatrix(_matrix(fk+".matrix"))
    rest=list(delta_now.inverse()*local_now)
    rest_node=_constant_matrix(root,prefix+"_FK_REST_LOCAL_FBF",rest)
    predicted=_node(root,"multMatrix",prefix+"_FK_LOCAL_PREDICT_MM")
    cmds.connectAttr(delta+".outputMatrix",predicted+".matrixIn[0]")
    cmds.connectAttr(rest_node+".output",predicted+".matrixIn[1]")
    inv=_node(root,"inverseMatrix",prefix+"_FK_LOCAL_INV")
    cmds.connectAttr(predicted+".matrixSum",inv+".inputMatrix")
    mode1="DIANA_SPINE_DEFORM_{}_MODE1_FINAL_MM.matrixSum".format(part)
    desired=_node(root,"multMatrix",prefix+"_IKFK_WORLD_MM")
    cmds.connectAttr(delta+".outputMatrix",desired+".matrixIn[0]"); cmds.connectAttr(mode1,desired+".matrixIn[1]")
    m1local=_node(root,"multMatrix",prefix+"_MODE1_FOLLOW_LOCAL_MM")
    parent_inverse=original_parent+".worldInverseMatrix[0]"
    for i,s in enumerate((inv+".outputMatrix",mode1,parent_inverse)): cmds.connectAttr(s,m1local+".matrixIn[{}]".format(i))
    m2local=_node(root,"multMatrix",prefix+"_MODE2_FOLLOW_LOCAL_MM")
    for i,s in enumerate((inv+".outputMatrix",desired+".matrixSum",parent_inverse)): cmds.connectAttr(s,m2local+".matrixIn[{}]".format(i))
    choice=_node(root,"choice",prefix+"_FOLLOW_MODE_CHOICE"); cmds.connectAttr("Terminal.Spine_Mode",choice+".selector")
    ident=_identity(root,prefix); cmds.connectAttr(ident+".output",choice+".input[0]"); cmds.connectAttr(m1local+".matrixSum",choice+".input[1]"); cmds.connectAttr(m2local+".matrixSum",choice+".input[2]")
    cmds.connectAttr(choice+".output",follow+".offsetParentMatrix")
    dst="DIANA_SPINE_DEFORM_{}_MODE_CHOICE.input[2]".format(part); old=_source(dst)
    if old: cmds.disconnectAttr(old,dst)
    cmds.connectAttr(desired+".matrixSum",dst)
    manifest["stages"].append({"part":part,"follow":follow,"original_parent":original_parent,"old_mode2_source":old,"new_mode2_source":desired+".matrixSum"})
    manifest["created_nodes"]=sorted(set((cmds.listConnections(root+".p4Nodes",s=True,d=False) or [])+[root]))
    with open(path,"w",encoding="utf-8") as f: json.dump(manifest,f,indent=2,sort_keys=True,ensure_ascii=False)
    return manifest["stages"][-1]
