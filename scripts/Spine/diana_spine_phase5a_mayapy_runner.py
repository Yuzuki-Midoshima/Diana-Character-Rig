# -*- coding: utf-8 -*-
"""Maya Standalone end-to-end Phase 5-A audit/proxy runner."""
from __future__ import absolute_import, division, print_function

import json
import os
import sys
import traceback

import maya.standalone
maya.standalone.initialize(name="python")
import maya.cmds as cmds

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from Spine import diana_spine_phase5_build as p5build
from Spine import diana_spine_phase5_integrate as p5integrate
from Spine import diana_spine_phase5_rollback as p5rollback
from Spine import diana_spine_phase5a_audit as audit
from Spine import diana_spine_phase5a_proxy_cleanup as cleanup
from Spine import diana_spine_phase5a_validate as validate

SOURCE = r"C:/Users/draco/OneDrive/ドキュメント/maya/projects/JAM_rig/scenes/Character_spine37.ma"
VALIDATION = r"C:/Users/draco/OneDrive/ドキュメント/maya/projects/JAM_rig/scenes/Character_spine37_PHASE5A_VALIDATION.ma"
TRACEBACK = os.path.join(os.path.dirname(__file__), "phase5a_traceback.txt")


def _cycles():
    try:
        return sorted(set(cmds.cycleCheck(all=True, list=True) or []))
    except Exception:
        return []


def _snapshot():
    nodes = ["L_clavice_jnt", "R_clavice_jnt", "neck_root_jnt", "head_jnt",
             "hair_short_back_jnt_1", "shoulder_spine_anim",
             "shoulder_fk_Spine_anim_jnt"]
    return {node: p5build.matrix(node + ".worldMatrix[0]")
            for node in nodes if cmds.objExists(node)}


def main():
    cmds.file(SOURCE, open=True, force=True, prompt=False)
    cmds.file(rename=VALIDATION)
    cmds.file(save=True, type="mayaAscii", force=True)
    production_before = _snapshot()
    baseline_cycles = _cycles()
    audit_result = audit.run()

    p5build.build()
    for part in p5integrate.ORDER:
        p5integrate.integrate_part(part)
    result = validate.run(baseline_cycles=baseline_cycles)
    proxy_cleanup = cleanup.remove()
    p5_cleanup = p5rollback.rollback()
    production_after = _snapshot()
    restore_errors = {node: max(abs(a - b) for a, b in zip(values, production_after[node]))
                      for node, values in production_before.items()}
    result["cleanup"] = {
        "proxy": proxy_cleanup,
        "phase5": p5_cleanup,
        "production_world_errors": restore_errors,
        "remaining_proxy_nodes": cmds.ls("DIANA_SPINE_P5A_*") or [],
        "remaining_phase5_nodes": cmds.ls("DIANA_SPINE_P5_*") or [],
    }
    result["cleanup"]["pass"] = (
        not result["cleanup"]["remaining_proxy_nodes"] and
        not result["cleanup"]["remaining_phase5_nodes"] and
        max(restore_errors.values()) <= validate.TOLERANCE_MATRIX)
    result["production_modified"] = False
    result["source_scene_saved"] = False
    result["phase5a_complete"] = bool(result["all_pass"] and result["cleanup"]["pass"])
    with open(validate.OUTPUT, "w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, sort_keys=True)
    cmds.file(save=True, type="mayaAscii", force=True)
    print("[DIANA SPINE P5A] complete:", result["phase5a_complete"])
    print("[DIANA SPINE P5A] audit nodes:", len(audit_result["nodes"]))
    return result


if __name__ == "__main__":
    try:
        main()
    except Exception:
        with open(TRACEBACK, "w", encoding="utf-8") as stream:
            stream.write(traceback.format_exc())
        raise
    finally:
        maya.standalone.uninitialize()
