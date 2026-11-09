# -*- coding: utf-8 -*-
"""End-to-end Maya Standalone runner for Phase 5 validation."""
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

from Spine import diana_spine_phase5_build as build
from Spine import diana_spine_phase5_validate as validate
from Spine import diana_spine_phase5_rollback as rollback

SOURCE = r"C:/Users/draco/OneDrive/ドキュメント/maya/projects/JAM_rig/scenes/Character_spine37.ma"
VALIDATION = r"C:/Users/draco/OneDrive/ドキュメント/maya/projects/JAM_rig/scenes/Character_spine37_PHASE5_VALIDATION.ma"
TRACEBACK = os.path.join(os.path.dirname(__file__), "phase5_traceback.txt")


def _matrix(node):
    return build.matrix(node + ".worldMatrix[0]")


def main():
    if not os.path.exists(SOURCE):
        raise RuntimeError("Source scene missing: " + SOURCE)
    cmds.file(SOURCE, open=True, force=True, prompt=False)
    cmds.file(rename=VALIDATION)
    cmds.file(save=True, type="mayaAscii", force=True)

    result = validate.run()
    cmds.file(save=True, type="mayaAscii", force=True)

    cmds.file(VALIDATION, open=True, force=True, prompt=False)
    result = validate.post_reload()

    before_rollback = {part: _matrix(fk) for part, fk in build.PARTS.items()}
    rollback_result = rollback.rollback()
    after_rollback = {part: _matrix(fk) for part, fk in build.PARTS.items()}
    with open(build.MANIFEST, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    restored_sources = {}
    for part, data in manifest["parts"].items():
        restored_sources[part] = {}
        for index in ("0", "2"):
            actual = build.source(
                "DIANA_SPINE_DEFORM_{}_MODE_CHOICE.input[{}]".format(part, index))
            restored_sources[part][index] = {
                "actual": actual,
                "expected": data["choice_inputs"][index],
                "pass": actual == data["choice_inputs"][index],
            }
    rollback_validation = {
        "result": rollback_result,
        "fk_world_errors": {
            part: max(abs(a - b) for a, b in zip(before_rollback[part], after_rollback[part]))
            for part in build.PARTS
        },
        "restored_sources": restored_sources,
    }
    rollback_validation["pass"] = (
        not rollback_result["remaining"] and
        not rollback_result["root_exists"] and
        max(rollback_validation["fk_world_errors"].values()) <= validate.TOLERANCE and
        all(item["pass"] for part in restored_sources.values() for item in part.values()))
    with open(validate.OUTPUT, "r", encoding="utf-8") as stream:
        result = json.load(stream)
    result["rollback"] = rollback_validation
    result["production_source_untouched"] = True
    result["all_pass"] = bool(result["all_pass"] and rollback_validation["pass"])
    with open(validate.OUTPUT, "w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, sort_keys=True)
    cmds.file(save=True, type="mayaAscii", force=True)
    print("[DIANA SPINE P5] all_pass:", result["all_pass"])
    print("[DIANA SPINE P5] validation:", VALIDATION)
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
