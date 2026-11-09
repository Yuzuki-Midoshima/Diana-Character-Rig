# -*- coding: utf-8 -*-
"""Restore Phase 5 connections and delete only registered Phase 5 nodes."""
from __future__ import absolute_import, division, print_function

import json
import maya.cmds as cmds
from . import diana_spine_phase5_build as build


def rollback(path=build.MANIFEST):
    with open(path, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    for part, data in manifest["parts"].items():
        choice = "DIANA_SPINE_DEFORM_{}_MODE_CHOICE".format(part)
        for index in ("0", "2"):
            destination = choice + ".input[{}]".format(index)
            current = cmds.connectionInfo(destination, sourceFromDestination=True) or ""
            if current:
                cmds.disconnectAttr(current, destination)
            original = data["choice_inputs"][index]
            if original:
                cmds.connectAttr(original, destination, force=True)
    nodes = []
    if cmds.objExists(build.REGISTRY):
        nodes = cmds.listConnections(build.REGISTRY + ".nodes", s=True, d=False) or []
    nodes = [x for x in nodes if cmds.objExists(x)]
    if nodes:
        cmds.delete(nodes)
    if cmds.objExists(build.REGISTRY):
        cmds.delete(build.REGISTRY)
    return {"remaining": cmds.ls("DIANA_SPINE_P5_*") or [],
            "root_exists": cmds.objExists(build.ROOT)}


if __name__ == "__main__":
    print(rollback())
