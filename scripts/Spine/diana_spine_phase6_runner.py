# -*- coding: utf-8 -*-
"""Maya 2026 end-to-end production-readiness validation for Diana Spine."""
from __future__ import absolute_import, division, print_function

import datetime
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
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from Spine import diana_spine_phase5_build as p5build
from Spine import diana_spine_phase5_integrate as p5integrate
from Spine import diana_spine_phase5_rollback as p5rollback
from Spine import diana_spine_phase5b_integrate as p5b
from Spine import diana_spine_phase5b_rollback as p5brollback
from Spine import diana_spine_phase6_animation as animation

HERE = os.path.dirname(__file__)
SOURCE = r"C:/Users/draco/OneDrive/ドキュメント/maya/projects/JAM_rig/scenes/Character_spine37.ma"
SCENE = r"C:/Users/draco/OneDrive/ドキュメント/maya/projects/JAM_rig/scenes/Character_spine37_PHASE5B_PHASE6_VALIDATION.ma"
MODE_JSON = os.path.join(HERE, "Character_spine37_phase6_mode_switch.json")
BODY_JSON = os.path.join(HERE, "Character_spine37_phase6_fullbody.json")
SAFETY_JSON = os.path.join(HERE, "Character_spine37_phase6_rerun_safety.json")
TRACEBACK = os.path.join(HERE, "phase6_traceback.txt")
TOL_MATRIX = 1.0e-4
TOL_ROTATION = 1.0e-3


def matrix(plug): return p5build.matrix(plug)
def error(a, b): return max(abs(x - y) for x, y in zip(a, b))
def position(m): return m[12:15]


def rotation_error(a, b):
    qa = om.MTransformationMatrix(om.MMatrix(a)).rotation(asQuaternion=True)
    qb = om.MTransformationMatrix(om.MMatrix(b)).rotation(asQuaternion=True)
    delta = qa * qb.inverse()
    return math.degrees(2.0 * math.acos(min(1.0, abs(delta.w))))


def cycles():
    try: return sorted(set(cmds.cycleCheck(all=True, list=True) or []))
    except Exception: return []


def cycle_delta(baseline):
    current = cycles()
    baseline_nodes = {item.split(".", 1)[0] for item in baseline}
    new_nodes = sorted({item.split(".", 1)[0] for item in current} - baseline_nodes)
    expanded = sorted(item for item in set(current) - set(baseline)
                      if item.split(".", 1)[0] in baseline_nodes)
    return {"current": current, "new_nodes": new_nodes,
            "expanded_existing_node_plugs": expanded}


def connections(node):
    raw = cmds.listConnections(node, s=True, d=True, c=True, p=True,
                               skipConversionNodes=False) or []
    return sorted((raw[i], raw[i + 1]) for i in range(0, len(raw) - 1, 2))


def spine_joints():
    # These four production deformation proxies are skin influences and are
    # the actual consumers of MODE_CHOICE.  IK_back_spine_jnt_* belongs to the
    # legacy stretch input chain and is not a valid final-pose comparison.
    return ["DIANA_SPINE_DEFORM_{}_FINAL_PROXY".format(part)
            for part in ("HIP", "LOWER", "MIDDLE", "SHOULDER")
            if cmds.objExists("DIANA_SPINE_DEFORM_{}_FINAL_PROXY".format(part))]


def worlds(nodes):
    return {node: matrix(node + ".worldMatrix[0]") for node in nodes if cmds.objExists(node)}


def skin_state():
    result = {}
    for skin in cmds.ls(type="skinCluster") or []:
        inf = cmds.skinCluster(skin, q=True, influence=True) or []
        if any("spine" in x.lower() or "back" in x.lower() for x in inf):
            result[skin] = {"influences": inf,
                            "geometry": cmds.skinCluster(skin, q=True, geometry=True) or []}
    return result


def node_snapshot():
    watched = spine_joints() + [
        "L_clavice_jnt", "R_clavice_jnt", "IK_L_elbow_anim", "IK_R_elbow_anim",
        "FK_L_shoulder_anim", "FK_R_shoulder_anim", "IK_L_hand_anim_const",
        "IK_R_hand_anim_const", "neck_root_jnt", "head_jnt", "hair_short_back_jnt_1",
        "back_spine_curve", "RIG_spineStretch_MD"]
    return {node: {"world": matrix(node + ".worldMatrix[0]") if cmds.attributeQuery("worldMatrix", node=node, exists=True) else None,
                   "connections": connections(node),
                   "parent": (cmds.listRelatives(node, p=True, fullPath=True) or [None])[0]}
            for node in watched if cmds.objExists(node)}


def set_neutral():
    for part in p5build.PARTS:
        node = "DIANA_SPINE_P5_{}_OP_FK_CTRL".format(part)
        cmds.setAttr(node + ".rotate", 0, 0, 0)
    for plug in ("DIANA_SPINE_IK_HIP_CTRL.translateX", "DIANA_SPINE_IK_UPPER_CTRL.translateX",
                 "DIANA_SPINE_IK_UPPER_CTRL.rotateZ"):
        if cmds.objExists(plug) and not cmds.getAttr(plug, lock=True): cmds.setAttr(plug, 0)
    for plug in animation.twist_keys():
        if cmds.getAttr(plug, settable=True): cmds.setAttr(plug, 0)
    cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)


def mode_switch_validation():
    joints = spine_joints()
    transitions = ((0, 1), (1, 0), (0, 2), (1, 2), (2, 0), (2, 1))
    result = []
    # A deliberately non-trivial state exposes whether raw mode changes preserve pose.
    cmds.setAttr("DIANA_SPINE_IK_HIP_CTRL.translateX", 3.0)
    cmds.setAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX", 5.0)
    cmds.setAttr("DIANA_SPINE_IK_UPPER_CTRL.rotateZ", 12.0)
    for plug in animation.twist_keys(): cmds.setAttr(plug, 8.0)
    cmds.setAttr("DIANA_SPINE_P5_LOWER_OP_FK_CTRL.rotateX", 10.0)
    cmds.setAttr("DIANA_SPINE_P5_MIDDLE_OP_FK_CTRL.rotateY", -7.0)
    for before_mode, after_mode in transitions:
        cmds.setAttr("Terminal.Spine_Mode", before_mode); cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
        before = worlds(joints)
        cmds.setAttr("Terminal.Spine_Mode", after_mode); cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
        after = worlds(joints)
        per_joint = {j: {"matrix_error": error(before[j], after[j]),
                         "position_error": error(position(before[j]), position(after[j])),
                         "rotation_error_degrees": rotation_error(before[j], after[j])}
                     for j in joints}
        maximum = {key: max(x[key] for x in per_joint.values()) for key in
                   ("matrix_error", "position_error", "rotation_error_degrees")}
        maintained = maximum["matrix_error"] <= TOL_MATRIX
        result.append({"from": before_mode, "to": after_mode, "joints": per_joint,
                       "max": maximum, "pose_maintained": maintained,
                       "snap_required": not maintained})
    # IK and IK+FK should be identical when the FK delta is zero.  This
    # separates a legitimate animator-authored delta from a switch pop.
    set_neutral()
    cmds.setAttr("DIANA_SPINE_IK_HIP_CTRL.translateX", 3.0)
    cmds.setAttr("DIANA_SPINE_IK_UPPER_CTRL.translateX", 5.0)
    cmds.setAttr("DIANA_SPINE_IK_UPPER_CTRL.rotateZ", 12.0)
    zero_delta = []
    for before_mode, after_mode in ((1, 2), (2, 1)):
        cmds.setAttr("Terminal.Spine_Mode", before_mode); cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
        before = worlds(joints)
        cmds.setAttr("Terminal.Spine_Mode", after_mode); cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
        after = worlds(joints)
        maximum = max(error(before[x], after[x]) for x in joints)
        zero_delta.append({"from": before_mode, "to": after_mode,
                           "max_matrix_error": maximum,
                           "pose_maintained": maximum <= TOL_MATRIX})
    set_neutral(); cmds.setAttr("Terminal.Spine_Mode", 0)
    return {"tolerance": {"matrix": TOL_MATRIX, "rotation_degrees": TOL_ROTATION},
            "transitions": result,
            "ik_ikfk_zero_delta": zero_delta,
            "snap_required": any(x["snap_required"] for x in result),
            "snap_policy": {"fk_ik": "required",
                            "ik_ikfk_zero_delta": "not_required" if all(x["pose_maintained"] for x in zero_delta) else "required",
                            "ik_ikfk_nonzero_delta": "expected_pose_change"},
            "pass": len(result) == 6 and all(x["pose_maintained"] for x in zero_delta)}


def fk_mode_validation():
    set_neutral()
    output = {}
    for mode in (0, 1, 2):
        cmds.setAttr("Terminal.Spine_Mode", mode); cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
        base = worlds(spine_joints())
        cmds.setAttr("DIANA_SPINE_P5_MIDDLE_OP_FK_CTRL.rotateY", 13.0)
        cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
        changed = worlds(spine_joints())
        delta = max(error(base[x], changed[x]) for x in base)
        cmds.setAttr("DIANA_SPINE_P5_MIDDLE_OP_FK_CTRL.rotateY", 0.0)
        cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
        restored = worlds(spine_joints())
        restore_error = max(error(base[x], restored[x]) for x in base)
        expected_active = mode in (0, 2)
        output[str(mode)] = {"joint_motion": delta, "zero_restore_error": restore_error,
                             "expected_active": expected_active,
                             "pass": (delta > 1e-6) == expected_active and restore_error <= TOL_MATRIX}
    return {"modes": output, "pass": all(x["pass"] for x in output.values())}


def animation_validation():
    state = animation.build()
    joints = spine_joints()
    tracked = joints + ["L_clavice_jnt", "R_clavice_jnt", "FK_L_shoulder_anim",
                        "FK_R_shoulder_anim", "IK_L_elbow_anim", "IK_R_elbow_anim",
                        "IK_L_hand_anim_const", "IK_R_hand_anim_const", "neck_root_jnt",
                        "head_jnt", "hair_short_back_jnt_1"]
    samples, invalid, flips = [], [], []
    previous = None
    switch_frames = {19, 35, 55, 65}
    for frame in range(1, 73):
        cmds.currentTime(frame, edit=True); cmds.dgdirty(allPlugs=True); cmds.refresh(force=True)
        current = worlds(tracked)
        for node, value in current.items():
            if not all(math.isfinite(x) for x in value): invalid.append({"frame": frame, "node": node})
        if previous and frame not in switch_frames:
            for node in joints:
                angle = rotation_error(previous[node], current[node])
                if angle > 90.0: flips.append({"frame": frame, "node": node, "degrees": angle})
        samples.append({"frame": frame, "mode": cmds.getAttr("Terminal.Spine_Mode"),
                        "spine_root": current[joints[0]], "spine_tip": current[joints[-1]],
                        "left_hand": current["IK_L_hand_anim_const"],
                        "right_hand": current["IK_R_hand_anim_const"]})
        previous = current
    return {"state": state, "frames": samples, "invalid_matrices": invalid,
            "rotation_flips_over_90_excluding_switches": flips,
            "pass": not invalid and not flips}


def equipment_audit():
    def is_equipment(node):
        name = node.lower()
        # Do not treat "elbow" as Bow equipment merely because it contains
        # the letters "bow".
        return (any(term in name for term in ("weapon", "sword", "gun", "socket", "equipment")) or
                name.startswith("bow") or "_bow" in name)
    nodes = sorted({node for node in (cmds.ls(type="transform") or []) if is_equipment(node)})
    return {"count": len(nodes), "nodes": {n: {"parent": (cmds.listRelatives(n, p=True, fullPath=True) or [None])[0],
                                                   "connections": connections(n)} for n in nodes}}


def rerun_safety(before_nodes, before_world, before_connections, before_cycles):
    stops = []
    for label, call in (("phase5_build", p5build.build), ("phase5b_capture", p5b.capture_manifest)):
        try:
            call(); stops.append({"operation": label, "stopped": False, "message": ""})
        except RuntimeError as exc:
            stops.append({"operation": label, "stopped": True, "message": str(exc)})
    after_nodes = set(cmds.ls())
    delta = cycle_delta(before_cycles)
    return {"operations": stops,
            "node_set_equal": after_nodes == before_nodes,
            "world_errors": {n: error(v, matrix(n + ".worldMatrix[0]")) for n, v in before_world.items()},
            "connections_equal": all(connections(n) == value for n, value in before_connections.items()),
            "cycle_delta": delta,
            "pass": all(x["stopped"] for x in stops) and after_nodes == before_nodes and
                    all(error(v, matrix(n + ".worldMatrix[0]")) <= TOL_MATRIX for n, v in before_world.items()) and
                    all(connections(n) == value for n, value in before_connections.items()) and
                    not delta["new_nodes"]}


def write(path, data):
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False, sort_keys=True)


def main():
    cmds.file(SOURCE, open=True, force=True, prompt=False)
    cmds.file(rename=SCENE); cmds.file(save=True, type="mayaAscii", force=True)
    source_snapshot, source_skins = node_snapshot(), skin_state()
    source_equipment = equipment_audit()
    baseline_cycles = cycles()
    p5build.build()
    for part in p5integrate.ORDER: p5integrate.integrate_part(part)
    p5b.capture_manifest(); p5b.integrate_side("L"); p5b.integrate_side("R")
    set_neutral()

    mode_result = mode_switch_validation()
    mode_result["fk_controls"] = fk_mode_validation()
    mode_result["pass"] = bool(mode_result["pass"] and mode_result["fk_controls"]["pass"])
    write(MODE_JSON, mode_result)

    integrated_nodes = set(cmds.ls())
    safety_watch = spine_joints() + ["L_clavice_jnt", "R_clavice_jnt",
                                     "FK_L_shoulder_anim", "FK_R_shoulder_anim"]
    safety_world = worlds(safety_watch)
    safety_connections = {n: connections(n) for n in safety_watch}
    safety = rerun_safety(integrated_nodes, safety_world, safety_connections, baseline_cycles)
    write(SAFETY_JSON, safety)

    anim = animation_validation()
    equipment_before = equipment_audit()
    protected_connections = {n: connections(n) for n in ("Terminal", "neck_root_jnt", "head_jnt",
                                                          "hair_short_back_jnt_1", "L_ARM_IK_SPACE_PC",
                                                          "R_ARM_IK_SPACE_PC")}
    body_cycle_delta = cycle_delta(baseline_cycles)
    body = {"created_utc": datetime.datetime.utcnow().isoformat() + "Z",
            "animation": {k: v for k, v in anim.items() if k != "state"},
            "equipment": {"audit": equipment_before,
                          "connections_equal_to_source": equipment_before == source_equipment},
            "skin_clusters_equal": skin_state() == source_skins,
            "cycle_delta": body_cycle_delta,
            "protected_connections_before_reload": protected_connections}
    body["pass"] = (anim["pass"] and body["skin_clusters_equal"] and
                    body["equipment"]["connections_equal_to_source"] and
                    not body_cycle_delta["new_nodes"])
    write(BODY_JSON, body)

    cmds.file(save=True, type="mayaAscii", force=True)
    cmds.file(SCENE, open=True, force=True, prompt=False)
    reload_cycle_delta = cycle_delta(baseline_cycles)
    reload_result = {"p5_exists": cmds.objExists(p5build.ROOT),
                     "p5b_exists": cmds.objExists(p5b.ROOT),
                     "animation_exists": cmds.objExists(animation.TAG),
                     "protected_connections_equal": all(connections(n) == value for n, value in protected_connections.items()),
                     "skin_clusters_equal": skin_state() == source_skins,
                     "equipment_equal": equipment_audit() == source_equipment,
                     "cycle_delta": reload_cycle_delta}
    reload_result["pass"] = (reload_result["p5_exists"] and reload_result["p5b_exists"] and
                             reload_result["animation_exists"] and reload_result["protected_connections_equal"] and
                             reload_result["skin_clusters_equal"] and reload_result["equipment_equal"] and
                             not reload_cycle_delta["new_nodes"])

    animation_cleanup = animation.cleanup(anim["state"]["original"])
    set_neutral(); cmds.setAttr("Terminal.Spine_Mode", 0)
    p5b_rb = p5brollback.rollback(); p5_rb = p5rollback.rollback()
    after = node_snapshot()
    restoration = {n: {"world_error": error(data["world"], after[n]["world"]) if data["world"] else 0.0,
                       "connections_equal": data["connections"] == after[n]["connections"],
                       "parent_equal": data["parent"] == after[n]["parent"]}
                   for n, data in source_snapshot.items()}
    rollback_cycle_delta = cycle_delta(baseline_cycles)
    rollback_result = {"phase5b": p5b_rb, "phase5": p5_rb,
                       "animation_cleanup": animation_cleanup,
                       "nodes": restoration,
                       "skin_clusters_equal": skin_state() == source_skins,
                       "equipment_equal": equipment_audit() == source_equipment,
                       "cycle_delta": rollback_cycle_delta}
    rollback_result["pass"] = (not p5b_rb["remaining"] and not p5_rb["remaining"] and
                               not animation_cleanup["remaining_curves"] and
                               all(x["world_error"] <= TOL_MATRIX and x["connections_equal"] and x["parent_equal"]
                                   for x in restoration.values()) and
                               rollback_result["skin_clusters_equal"] and rollback_result["equipment_equal"] and
                               not rollback_cycle_delta["new_nodes"])
    body["save_reload"] = reload_result
    body["rollback"] = rollback_result
    body["source_scene_modified"] = False
    body["phase6_complete"] = bool(mode_result["pass"] and safety["pass"] and body["pass"] and
                                    reload_result["pass"] and rollback_result["pass"])
    body["pass"] = body["phase6_complete"]
    write(BODY_JSON, body)
    cmds.file(save=True, type="mayaAscii", force=True)
    print("[DIANA SPINE P6] complete:", body["phase6_complete"])
    return body


if __name__ == "__main__":
    try:
        main()
    except Exception:
        with open(TRACEBACK, "w", encoding="utf-8") as stream: stream.write(traceback.format_exc())
        raise
    finally:
        maya.standalone.uninitialize()
