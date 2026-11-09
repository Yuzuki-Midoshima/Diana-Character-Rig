# -*- coding: utf-8 -*-
"""Staged MODE0/MODE2 integration for Phase 5."""
from __future__ import absolute_import, division, print_function

import json
import os
import maya.cmds as cmds

from . import diana_spine_phase5_build as build

ORDER = ("LOWER", "MIDDLE", "SHOULDER", "HIP")


def integrate_part(part, path=build.MANIFEST):
    part = part.upper()
    with open(path, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    expected = ORDER[len(manifest["stages"])]
    if part != expected:
        raise RuntimeError("Expected {}, got {}".format(expected, part))
    choice = "DIANA_SPINE_DEFORM_{}_MODE_CHOICE".format(part)
    destinations = {
        "0": choice + ".input[0]",
        "2": choice + ".input[2]",
    }
    new_sources = {
        "0": "DIANA_SPINE_P5_{}_MODE0_FINAL_MM.matrixSum".format(part),
        "2": "DIANA_SPINE_P5_{}_MODE2_FINAL_MM.matrixSum".format(part),
    }
    old = {}
    for index in ("0", "2"):
        destination = destinations[index]
        old[index] = cmds.connectionInfo(destination, sourceFromDestination=True) or ""
        if old[index]:
            cmds.disconnectAttr(old[index], destination)
        cmds.connectAttr(new_sources[index], destination)
    manifest["stages"].append({"part": part, "old": old,
                               "new": new_sources})
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=False, sort_keys=True)
    return manifest["stages"][-1]


if __name__ == "__main__":
    for item in ORDER:
        integrate_part(item)
