# -*- coding: utf-8 -*-
"""End-to-end Maya Standalone runner for Phase 5-B."""
from __future__ import absolute_import, division, print_function

import json
import os
import sys
import traceback

import maya.standalone
maya.standalone.initialize(name="python")
import maya.cmds as cmds

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPTS not in sys.path: sys.path.insert(0, SCRIPTS)

from Spine import diana_spine_phase5_build as p5build
from Spine import diana_spine_phase5_integrate as p5integrate
from Spine import diana_spine_phase5_rollback as p5rollback
from Spine import diana_spine_phase5b_integrate as integrate
from Spine import diana_spine_phase5b_rollback as rollback
from Spine import diana_spine_phase5b_validate as validate

SOURCE = r"C:/Users/draco/OneDrive/ドキュメント/maya/projects/JAM_rig/scenes/Character_spine37.ma"
VALIDATION = r"C:/Users/draco/OneDrive/ドキュメント/maya/projects/JAM_rig/scenes/Character_spine37_PHASE5B_VALIDATION.ma"
TRACEBACK = os.path.join(os.path.dirname(__file__), "phase5b_traceback.txt")


def _matrix(node): return p5build.matrix(node + ".worldMatrix[0]")
def _error(a, b): return max(abs(x - y) for x, y in zip(a, b))


def _cycles():
    try: return sorted(set(cmds.cycleCheck(all=True, list=True) or []))
    except Exception: return []


def _connections(node):
    raw = cmds.listConnections(node, s=True, d=True, c=True, p=True,
                               skipConversionNodes=False) or []
    return sorted((raw[i], raw[i + 1]) for i in range(0, len(raw) - 1, 2))


def _snapshot():
    nodes = ["L_clavice_jnt", "R_clavice_jnt", "L_clavice_anim", "R_clavice_anim",
             "IK_L_elbow_anim", "IK_R_elbow_anim", "neck_root_jnt", "head_jnt",
             "hair_short_back_jnt_1", "shoulder_spine_anim"]
    nodes.extend(cmds.ls("*back_spine_jnt*", type="joint") or [])
    return {node: {"world": _matrix(node), "connections": _connections(node),
                   "parent": (cmds.listRelatives(node, p=True, fullPath=True) or [None])[0]}
            for node in nodes if cmds.objExists(node)}


def _skin_snapshot():
    result = {}
    for skin in cmds.ls(type="skinCluster") or []:
        influences = cmds.skinCluster(skin, q=True, influence=True) or []
        if any("spine" in item.lower() or "back" in item.lower()
               for item in influences):
            result[skin] = {
                "influences": influences,
                "geometry": cmds.skinCluster(skin, q=True, geometry=True) or [],
            }
    return result


def _stage_check(side, before_cycles, baseline_world):
    current_cycles = _cycles()
    roots = integrate.SIDE_DATA[side]["roots"]
    errors = {node: _error(_matrix(node), baseline_world[node]) for node in roots}
    result = {"side": side, "baseline_errors": errors,
              "new_cycles": sorted(set(current_cycles) - set(before_cycles)),
              "pass": max(errors.values()) <= validate.TOL_MATRIX and
                      not (set(current_cycles) - set(before_cycles))}
    print("[DIANA SPINE P5B] stage check:", json.dumps(result, sort_keys=True))
    return result


def _downstream_test(before):
    for part in ("HIP", "LOWER", "MIDDLE", "SHOULDER"):
        cmds.setAttr("DIANA_SPINE_P5_{}_OP_FK_CTRL.rotate".format(part), 0, 0, 0)
    cmds.setAttr("Terminal.Spine_Mode", 1)
    old = cmds.getAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX")
    base = {n: _matrix(n) for n in ("neck_root_jnt", "head_jnt", "hair_short_back_jnt_1")}
    cmds.setAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX", old + 5)
    cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
    moved = {n: _matrix(n) for n in base}
    cmds.setAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX", old)
    cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
    restored = {n: _matrix(n) for n in base}
    targets = {n: {"motion": _error(base[n], moved[n]),
                   "restore_error": _error(base[n], restored[n]),
                   "connections_equal": _connections(n) == before[n]["connections"]}
               for n in base}
    passed = (targets["neck_root_jnt"]["motion"] > 1e-6 and
              targets["head_jnt"]["motion"] > 1e-6 and
              all(x["restore_error"] <= validate.TOL_MATRIX and x["connections_equal"]
                  for x in targets.values()))
    return {"targets": targets, "pass": passed}


def main():
    cmds.file(SOURCE, open=True, force=True, prompt=False)
    cmds.file(rename=VALIDATION); cmds.file(save=True, type="mayaAscii", force=True)
    production_before = _snapshot()
    skins_before = _skin_snapshot()
    baseline_cycles = _cycles()
    p5build.build()
    for part in p5integrate.ORDER: p5integrate.integrate_part(part)
    integrate.capture_manifest()
    baseline_world = {node: _matrix(node) for spec in integrate.SIDE_DATA.values()
                      for node in spec["roots"]}
    stages = []
    integrate.integrate_side("L"); stages.append(_stage_check("L", baseline_cycles, baseline_world))
    if not stages[-1]["pass"]:
        with open(validate.OUTPUT, "w", encoding="utf-8") as stream:
            json.dump({"all_pass": False, "stages": stages}, stream, indent=2,
                      ensure_ascii=False, sort_keys=True)
        raise RuntimeError("Left attachment stage failed")
    integrate.integrate_side("R"); stages.append(_stage_check("R", baseline_cycles, baseline_world))
    if not stages[-1]["pass"]:
        with open(validate.OUTPUT, "w", encoding="utf-8") as stream:
            json.dump({"all_pass": False, "stages": stages}, stream, indent=2,
                      ensure_ascii=False, sort_keys=True)
        raise RuntimeError("Right attachment stage failed")
    result = validate.run()
    result["stages"] = stages
    result["downstream"] = _downstream_test(production_before)
    spine_mode0 = {node: _error(data["world"], _matrix(node))
                   for node, data in production_before.items()
                   if "back_spine_jnt" in node}
    result["protection"] = {
        "skin_clusters_equal": _skin_snapshot() == skins_before,
        "skin_cluster_count": len(skins_before),
        "spine_joint_mode0_errors": spine_mode0,
        "spine_joint_max_error": max(spine_mode0.values()) if spine_mode0 else 0.0,
    }
    result["protection"]["pass"] = (
        result["protection"]["skin_clusters_equal"] and
        result["protection"]["spine_joint_max_error"] <= validate.TOL_MATRIX)
    result["all_pass"] = bool(result["all_pass"] and result["downstream"]["pass"] and
                              result["protection"]["pass"])
    with open(validate.OUTPUT, "w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, sort_keys=True)
    if not result["all_pass"]:
        rollback.rollback(); p5rollback.rollback()
        cmds.file(save=True, type="mayaAscii", force=True)
        return result

    cmds.file(save=True, type="mayaAscii", force=True)
    cmds.file(VALIDATION, open=True, force=True, prompt=False)
    save_reload = {"p5b_root": cmds.objExists(integrate.ROOT),
                   "p5_root": cmds.objExists(p5build.ROOT),
                   "opm_sources": {node: integrate.source(node + ".offsetParentMatrix")
                                   for spec in integrate.SIDE_DATA.values() for node in spec["roots"]}}
    save_reload["pass"] = (save_reload["p5b_root"] and save_reload["p5_root"] and
                           all("DIANA_SPINE_P5B_" in x for x in save_reload["opm_sources"].values()))
    rb = rollback.rollback(); p5rb = p5rollback.rollback()
    production_after = _snapshot()
    restore = {node: {"world_error": _error(data["world"], production_after[node]["world"]),
                      "connections_equal": data["connections"] == production_after[node]["connections"],
                      "parent_equal": data["parent"] == production_after[node]["parent"]}
               for node, data in production_before.items()}
    rollback_pass = (not rb["remaining"] and not p5rb["remaining"] and
                     all(x["world_error"] <= validate.TOL_MATRIX and
                         x["connections_equal"] and x["parent_equal"] for x in restore.values()))
    with open(validate.OUTPUT, "r", encoding="utf-8") as stream: result = json.load(stream)
    result["save_reload"] = save_reload
    result["rollback"] = {"phase5b": rb, "phase5": p5rb,
                          "production": restore, "pass": rollback_pass}
    result["source_scene_modified"] = False
    result["phase5b_complete"] = bool(result["all_pass"] and save_reload["pass"] and rollback_pass)
    result["all_pass"] = result["phase5b_complete"]
    with open(validate.OUTPUT, "w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, sort_keys=True)
    cmds.file(save=True, type="mayaAscii", force=True)
    print("[DIANA SPINE P5B] complete:", result["phase5b_complete"])
    return result


if __name__ == "__main__":
    try:
        main()
    except Exception:
        try:
            if cmds.objExists(integrate.REGISTRY): rollback.rollback()
            if cmds.objExists(p5build.REGISTRY): p5rollback.rollback()
            if "PHASE5B" in cmds.file(q=True, sn=True): cmds.file(save=True, type="mayaAscii", force=True)
        except Exception:
            pass
        with open(TRACEBACK, "w", encoding="utf-8") as stream:
            stream.write(traceback.format_exc())
        raise
    finally:
        maya.standalone.uninitialize()
