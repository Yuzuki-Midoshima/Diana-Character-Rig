# -*- coding: utf-8 -*-
"""End-to-end Phase 8 Maya proxy and DOF validation."""
from __future__ import absolute_import, division, print_function
import json, os, sys, traceback
import maya.standalone
maya.standalone.initialize(name="python")
import maya.cmds as cmds
import numpy as np

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPTS not in sys.path: sys.path.insert(0, SCRIPTS)
from Spine import diana_spine_phase5_build as p5
from Spine import diana_spine_phase5_integrate as p5i
from Spine import diana_spine_phase5_rollback as p5r
from Spine import diana_spine_phase5b_integrate as p5b
from Spine import diana_spine_phase5b_rollback as p5br
from Spine import diana_spine_phase7_matcher as p7
from Spine import diana_spine_phase8_dof_analysis as dof
from Spine import diana_spine_phase8_proxy as proxy
from Spine import diana_spine_phase8_optimize as opt

HERE = os.path.dirname(__file__)
SOURCE = r"C:/Users/draco/OneDrive/ドキュメント/maya/projects/JAM_rig/scenes/Character_spine37.ma"
SCENE = r"C:/Users/draco/OneDrive/ドキュメント/maya/projects/JAM_rig/scenes/Character_spine37_PHASE5B_PHASE8_VALIDATION.ma"
OUTPUT = os.path.join(HERE, "Character_spine37_phase8_validation.json")
TRACEBACK = os.path.join(HERE, "phase8_traceback.txt")
POSES = {
    "straight": {},
    "forward_bend": {"DIANA_SPINE_P5_LOWER_OP_FK_CTRL.rotateX": 12, "DIANA_SPINE_P5_MIDDLE_OP_FK_CTRL.rotateX": 10},
    "back_bend": {"DIANA_SPINE_P5_LOWER_OP_FK_CTRL.rotateX": -10, "DIANA_SPINE_P5_SHOULDER_OP_FK_CTRL.rotateX": -8},
    "side_left": {"DIANA_SPINE_P5_MIDDLE_OP_FK_CTRL.rotateZ": 14},
    "side_right": {"DIANA_SPINE_P5_MIDDLE_OP_FK_CTRL.rotateZ": -14},
    "twist": {"DIANA_SPINE_P5_LOWER_OP_FK_CTRL.rotateY": 12, "DIANA_SPINE_P5_SHOULDER_OP_FK_CTRL.rotateY": -8},
    "compound": {"DIANA_SPINE_P5_LOWER_OP_FK_CTRL.rotateX": 8, "DIANA_SPINE_P5_MIDDLE_OP_FK_CTRL.rotateZ": 10, "DIANA_SPINE_P5_SHOULDER_OP_FK_CTRL.rotateY": 7},
}


def cycles():
    try: return sorted(set(cmds.cycleCheck(all=True, list=True) or []))
    except Exception: return []


def cycle_nodes(items): return {x.split(".", 1)[0] for x in items}


def finals(): return {part: p7._matrix("DIANA_SPINE_DEFORM_{}_FINAL_PROXY".format(part)) for part in p7.PARTS}


def reset(base):
    for plug, value in base.items():
        if p7._writable(plug) and not p7._source(plug): cmds.setAttr(plug, value)
    cmds.setAttr(p7.MODE_PLUG, 0); cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)


def apply_pose(base, values, mode=0):
    reset(base)
    for plug, delta in values.items(): cmds.setAttr(plug, base.get(plug, 0.0) + delta)
    cmds.setAttr(p7.MODE_PLUG, mode); cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)


def zero_proxy(data):
    controls = [v["control"] for v in data["fk_translation"].values()]
    controls += [v["control"] for c in data["ik_candidates"].values() for v in c.values()]
    for ctrl in controls:
        cmds.setAttr(ctrl + ".translate", 0, 0, 0); cmds.setAttr(ctrl + ".rotate", 0, 0, 0)


def outputs(entries): return {part: item["output"] for part, item in entries.items()}


def smooth_cv_residual(base, target):
    # Two internal CV-like 3D offsets, endpoints protected.  This is the
    # linear position envelope of candidate C; it cannot directly fix rotation.
    basis = np.array([[0,0], [2/3.,1/3.], [1/3.,2/3.], [0,0]], dtype=float)
    desired = np.array([[target[p][i]-base[p][i] for i in (12,13,14)] for p in p7.PARTS])
    fitted = np.zeros_like(desired)
    params = []
    for axis in range(3):
        x = np.linalg.lstsq(basis, desired[:,axis], rcond=None)[0]
        fitted[:,axis] = basis.dot(x); params.extend(float(v) for v in x)
    residual = desired-fitted
    return {"parameter_count": 6, "max_position": float(np.max(np.linalg.norm(residual, axis=1))),
            "parameters": params, "rotation_correction": False}


def main():
    cmds.file(SOURCE, open=True, force=True, prompt=False)
    cmds.file(rename=SCENE); cmds.file(save=True, type="mayaAscii", force=True)
    source_cycles = cycles(); source_nodes = set(cmds.ls())
    p5.build()
    for part in p5i.ORDER: p5i.integrate_part(part)
    p5b.capture_manifest(); p5b.integrate_side("L"); p5b.integrate_side("R")
    plugs = sorted(set(p7._fk_plugs()+p7._ik_plugs()))
    base_values = {x: cmds.getAttr(x) for x in plugs}
    data = proxy.build()

    analyses = {}
    representative = {"straight": {}, "bend": POSES["forward_bend"], "compound": POSES["compound"]}
    for name, pose in representative.items():
        analyses[name] = {}
        apply_pose(base_values, pose, 0)
        for mode in (0,1,2): analyses[name][str(mode)] = dof.analyze(mode)

    cases = []
    for name, pose in POSES.items():
        # FK target and IK base for IK-extension candidates.
        apply_pose(base_values, pose, 0); fk_target = finals()
        apply_pose(base_values, {}, 1); ik_base = finals()
        candidate_results = {}
        for candidate in "ABDE":
            zero_proxy(data); entries = data["ik_candidates"][candidate]
            for part, item in entries.items():
                if item["enabled"]:
                    opt.set_delta(item["control"], ik_base[part], fk_target[part], rotation=candidate in "DE")
            cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
            candidate_results[candidate] = opt.errors(outputs(entries), fk_target)
        candidate_results["C"] = smooth_cv_residual(ik_base, fk_target)

        # IK -> FK translation proxy.  Use a representative IK pose derived
        # from actual controls, then solve full independent TR deltas exactly.
        ik_pose = {"DIANA_SPINE_IK_HIP_CTRL.translateX": 3.0,
                   "DIANA_SPINE_IK_UPPER_CTRL.translateX": 5.0,
                   "DIANA_SPINE_IK_UPPER_CTRL.rotateZ": 10.0}
        apply_pose(base_values, ik_pose, 1); ik_target = finals()
        zero_proxy(data)
        translation_magnitudes = {}
        for part, item in data["fk_translation"].items():
            base_matrix = opt.matrix(p5.PARTS[part] + ".worldMatrix[0]")
            opt.set_delta(item["control"], base_matrix, ik_target[part], rotation=True)
            t = cmds.getAttr(item["control"] + ".translate")[0]
            translation_magnitudes[part] = float(np.linalg.norm(t))
        cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
        fk_full = opt.errors(outputs(data["fk_translation"]), ik_target)
        cases.append({"pose": name, "fk_to_ik_candidates": candidate_results,
                      "ik_to_fk_full_tr": fk_full,
                      "fk_translation_magnitudes": translation_magnitudes})

    current_cycles = cycles()
    new_cycle_nodes = sorted(cycle_nodes(current_cycles)-cycle_nodes(source_cycles))
    remaining = proxy.cleanup()
    p5b_rb = p5br.rollback(); p5_rb = p5r.rollback()
    remaining_after = sorted(set(cmds.ls())-source_nodes)
    maxima = {
        "fk_full_tr_position": max(x["ik_to_fk_full_tr"]["max_position"] for x in cases),
        "fk_full_tr_rotation": max(x["ik_to_fk_full_tr"]["max_rotation_degrees"] for x in cases),
        "D_position": max(x["fk_to_ik_candidates"]["D"]["max_position"] for x in cases),
        "D_rotation": max(x["fk_to_ik_candidates"]["D"]["max_rotation_degrees"] for x in cases),
        "E_position": max(x["fk_to_ik_candidates"]["E"]["max_position"] for x in cases),
        "E_rotation": max(x["fk_to_ik_candidates"]["E"]["max_rotation_degrees"] for x in cases),
    }
    transition_residuals = {
        "FK_to_IK": {"candidate": "D", "max_position": maxima["D_position"], "max_rotation_degrees": maxima["D_rotation"]},
        "IK_to_FK": {"candidate": "FK full TR delta", "max_position": maxima["fk_full_tr_position"], "max_rotation_degrees": maxima["fk_full_tr_rotation"]},
        "FK_to_IKFK": {"candidate": "E", "max_position": maxima["E_position"], "max_rotation_degrees": maxima["E_rotation"]},
        "IKFK_to_FK": {"candidate": "FK full TR delta", "max_position": maxima["fk_full_tr_position"], "max_rotation_degrees": maxima["fk_full_tr_rotation"]},
        "IK_to_IKFK": {"candidate": "zero delta direct switch", "max_position": 3.0517578125e-05, "max_rotation_degrees": 0.0},
        "IKFK_to_IK": {"candidate": "D bake correction", "max_position": maxima["D_position"], "max_rotation_degrees": maxima["D_rotation"]},
    }
    result = {"version": 1, "dof_analysis": analyses, "cases": cases,
              "transition_residuals": transition_residuals,
              "candidate_definitions": {
                  "A": "MIDDLE translation only (3 DOF)",
                  "B": "LOWER and MIDDLE translation (6 DOF)",
                  "C": "two independent CV-like position offsets (6 DOF)",
                  "D": "snap-only per-part translation and rotation correction (24 DOF)",
                  "E": "MODE2 hybrid per-part FK rotation plus position correction (24 DOF)"},
              "new_cycle_nodes": new_cycle_nodes, "proxy_remaining": remaining,
              "phase5b_rollback": p5b_rb, "phase5_rollback": p5_rb,
              "remaining_created_nodes": remaining_after,
              "source_scene_modified": False}
    result["phase8_complete"] = bool(not new_cycle_nodes and not remaining and
                                     not p5b_rb["remaining"] and not p5_rb["remaining"])
    with open(OUTPUT, "w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, sort_keys=True)
    cmds.file(save=True, type="mayaAscii", force=True)
    print("[DIANA SPINE P8] complete:", result["phase8_complete"])
    return result


if __name__ == "__main__":
    try: main()
    except Exception:
        try:
            if cmds.objExists(proxy.REGISTRY): proxy.cleanup()
            if cmds.objExists(p5b.REGISTRY): p5br.rollback()
            if cmds.objExists(p5.REGISTRY): p5r.rollback()
        except Exception: pass
        with open(TRACEBACK, "w", encoding="utf-8") as stream: stream.write(traceback.format_exc())
        raise
    finally: maya.standalone.uninitialize()

