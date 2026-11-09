# -*- coding: utf-8 -*-
"""Maya Standalone validation for the Diana Spine Phase 7 matcher."""
from __future__ import absolute_import, division, print_function

import json
import math
import os
import sys
import traceback

import maya.standalone
maya.standalone.initialize(name="python")
import maya.api.OpenMaya as om
import maya.cmds as cmds

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPTS not in sys.path: sys.path.insert(0, SCRIPTS)
from Spine import diana_spine_phase5_build as p5
from Spine import diana_spine_phase5_integrate as p5i
from Spine import diana_spine_phase5_rollback as p5r
from Spine import diana_spine_phase5b_integrate as p5b
from Spine import diana_spine_phase5b_rollback as p5br
from Spine import diana_spine_phase7_matcher as matcher

HERE = os.path.dirname(__file__)
SOURCE = r"C:/Users/draco/OneDrive/ドキュメント/maya/projects/JAM_rig/scenes/Character_spine37.ma"
SCENE = r"C:/Users/draco/OneDrive/ドキュメント/maya/projects/JAM_rig/scenes/Character_spine37_PHASE5B_PHASE7_VALIDATION.ma"
OUTPUT = os.path.join(HERE, "Character_spine37_phase7_validation.json")
TRACEBACK = os.path.join(HERE, "phase7_traceback.txt")
TRANSITIONS = ((0, 1), (1, 0), (0, 2), (2, 0), (1, 2), (2, 1))
POSES = (
    {"DIANA_SPINE_P5_LOWER_OP_FK_CTRL.rotateX": 8.0,
     "DIANA_SPINE_P5_MIDDLE_OP_FK_CTRL.rotateY": -6.0,
     "DIANA_SPINE_P5_SHOULDER_OP_FK_CTRL.rotateZ": 5.0,
     "DIANA_SPINE_IK_HIP_CTRL.translateX": 2.0,
     "DIANA_SPINE_IK_UPPER_CTRL.translateX": 4.0,
     "DIANA_SPINE_IK_UPPER_CTRL.rotateZ": 8.0},
    {"DIANA_SPINE_P5_HIP_OP_FK_CTRL.rotateZ": -5.0,
     "DIANA_SPINE_P5_LOWER_OP_FK_CTRL.rotateY": 7.0,
     "DIANA_SPINE_P5_MIDDLE_OP_FK_CTRL.rotateX": 9.0,
     "DIANA_SPINE_IK_HIP_CTRL.translateZ": 2.0,
     "DIANA_SPINE_IK_UPPER_CTRL.translateX": -3.0,
     "DIANA_SPINE_IK_UPPER_CTRL.rotateY": 6.0},
)
BASE_VALUES = {}


def matrix(node): return matcher._matrix(node)
def error(a, b): return max(abs(x-y) for x, y in zip(a, b))


def cycles():
    try: return sorted(set(cmds.cycleCheck(all=True, list=True) or []))
    except Exception: return []


def cycle_nodes(values): return {x.split(".", 1)[0] for x in values}


def reset_values():
    for plug in matcher._fk_plugs() + matcher._ik_plugs():
        source = matcher._source(plug)
        if not source: cmds.setAttr(plug, BASE_VALUES.get(plug, 0.0))
    cmds.setAttr(matcher.MODE_PLUG, 0)
    cmds.currentTime(1, edit=True); cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)


def apply_pose(mode, pose):
    reset_values()
    for plug, value in pose.items():
        if cmds.objExists(plug) and matcher._writable(plug):
            cmds.setAttr(plug, BASE_VALUES.get(plug, 0.0) + value)
    if mode == 1:
        for plug in matcher._fk_plugs(): cmds.setAttr(plug, 0.0)
    cmds.setAttr(matcher.MODE_PLUG, mode)
    cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)


def attachment_nodes():
    return ("L_clavice_jnt", "R_clavice_jnt", "FK_L_shoulder_anim", "FK_R_shoulder_anim",
            "IK_L_elbow_anim", "IK_R_elbow_anim", "IK_L_hand_anim_const", "IK_R_hand_anim_const",
            "neck_root_jnt", "head_jnt", "hair_short_back_jnt_1")


def worlds(nodes): return {x: matrix(x) for x in nodes}


def transition_cases():
    result = []
    for pose_index, pose in enumerate(POSES):
        for source, target in TRANSITIONS:
            apply_pose(source, pose)
            before_attachments = worlds(attachment_nodes())
            report = matcher.match(target, bake_nonzero_fk=True)
            after_attachments = worlds(attachment_nodes())
            attachment_error = max(error(before_attachments[x], after_attachments[x])
                                   for x in before_attachments) if report["success"] else None
            result.append({"pose": pose_index, "from": source, "to": target,
                           "match": report, "attachment_max_matrix_error": attachment_error,
                           "pass": bool(report["success"] and attachment_error <= 1.0e-3)})
    return result


def key_protection_test():
    reset_values(); cmds.currentTime(5, edit=True)
    plugs = ("DIANA_SPINE_P5_LOWER_OP_FK_CTRL.rotateX",
             "DIANA_SPINE_IK_UPPER_CTRL.translateX")
    for plug in plugs:
        cmds.setKeyframe(plug, time=1, value=2.0)
        cmds.setKeyframe(plug, time=10, value=6.0)
    before = {p: list(zip(cmds.keyframe(p, q=True, timeChange=True) or [],
                          cmds.keyframe(p, q=True, valueChange=True) or [])) for p in plugs}
    cmds.setAttr(matcher.MODE_PLUG, 1)
    report = matcher.match(2)
    after = {p: list(zip(cmds.keyframe(p, q=True, timeChange=True) or [],
                         cmds.keyframe(p, q=True, valueChange=True) or [])) for p in plugs}
    outside_equal = all([(t, v) for t, v in before[p] if t != 5] ==
                        [(t, v) for t, v in after[p] if t != 5] for p in plugs)
    for plug in plugs: cmds.cutKey(plug, clear=True)
    reset_values()
    return {"match": report, "before": before, "after": after,
            "outside_current_frame_equal": outside_equal,
            "pass": report["success"] and outside_equal}


def undo_redo_test():
    reset_values(); cmds.setAttr(matcher.MODE_PLUG, 1)
    before = matcher._worlds(); before_mode = cmds.getAttr(matcher.MODE_PLUG)
    report = matcher.match(2)
    snapped = matcher._worlds()
    cmds.undo(); cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
    undo_error = max(error(before[x], matrix(x)) for x in before)
    undo_mode = cmds.getAttr(matcher.MODE_PLUG)
    cmds.redo(); cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
    redo_error = max(error(snapped[x], matrix(x)) for x in snapped)
    redo_mode = cmds.getAttr(matcher.MODE_PLUG)
    return {"match": report, "undo_error": undo_error, "undo_mode": undo_mode,
            "redo_error": redo_error, "redo_mode": redo_mode,
            "pass": report["success"] and undo_error <= 1e-4 and before_mode == undo_mode and
                    redo_error <= 1e-4 and redo_mode == 2}


def main():
    cmds.file(SOURCE, open=True, force=True, prompt=False)
    cmds.file(rename=SCENE); cmds.file(save=True, type="mayaAscii", force=True)
    source_nodes = set(cmds.ls()); source_cycles = cycles()
    source_world = worlds(matcher.FINAL_NODES + attachment_nodes())
    p5.build()
    for part in p5i.ORDER: p5i.integrate_part(part)
    p5b.capture_manifest(); p5b.integrate_side("L"); p5b.integrate_side("R")
    BASE_VALUES.update({plug: cmds.getAttr(plug)
                        for plug in matcher._fk_plugs() + matcher._ik_plugs()})
    reset_values()

    cases = transition_cases()
    keys = key_protection_test()
    undo = undo_redo_test()
    current_cycles = cycles()
    new_cycle_nodes = sorted(cycle_nodes(current_cycles) - cycle_nodes(source_cycles))
    result = {"version": 1, "tolerances": {"position": matcher.POS_TOL,
                                             "rotation_degrees": matcher.ROT_TOL,
                                             "attachment_matrix": 1e-3},
              "cases": cases, "key_protection": keys, "undo_redo": undo,
              "new_cycle_nodes": new_cycle_nodes}
    result["all_snap_pass"] = all(x["pass"] for x in cases)

    # Save/reload a known successful zero-delta IK -> IK+FK state.
    reset_values(); cmds.setAttr(matcher.MODE_PLUG, 1); reload_match = matcher.match(2)
    saved_world = matcher._worlds()
    cmds.file(save=True, type="mayaAscii", force=True)
    cmds.file(SCENE, open=True, force=True, prompt=False)
    reload_error = max(error(saved_world[x], matrix(x)) for x in saved_world)
    save_reload = {"match": reload_match, "matrix_error": reload_error,
                   "mode": cmds.getAttr(matcher.MODE_PLUG),
                   "pass": reload_match["success"] and reload_error <= 1e-4 and
                           cmds.getAttr(matcher.MODE_PLUG) == 2}

    reset_values(); p5b_rb = p5br.rollback(); p5_rb = p5r.rollback()
    after_world = worlds(matcher.FINAL_NODES + attachment_nodes())
    rollback_error = max(error(source_world[x], after_world[x]) for x in source_world)
    rollback = {"phase5b": p5b_rb, "phase5": p5_rb, "matrix_error": rollback_error,
                "remaining_phase_nodes": sorted(set(cmds.ls("DIANA_SPINE_P5*")) - set()),
                "new_cycle_nodes": sorted(cycle_nodes(cycles()) - cycle_nodes(source_cycles))}
    rollback["pass"] = (not p5b_rb["remaining"] and not p5_rb["remaining"] and
                        rollback_error <= 1e-4 and not rollback["new_cycle_nodes"])
    result["save_reload"] = save_reload
    result["rollback"] = rollback
    result["source_scene_modified"] = False
    result["phase7_complete"] = bool(result["all_snap_pass"] and keys["pass"] and undo["pass"] and
                                      not new_cycle_nodes and save_reload["pass"] and rollback["pass"])
    with open(OUTPUT, "w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, sort_keys=True)
    cmds.file(save=True, type="mayaAscii", force=True)
    print("[DIANA SPINE P7] complete:", result["phase7_complete"])
    return result


if __name__ == "__main__":
    try: main()
    except Exception:
        with open(TRACEBACK, "w", encoding="utf-8") as stream: stream.write(traceback.format_exc())
        raise
    finally: maya.standalone.uninitialize()

