# -*- coding: utf-8 -*-
"""Delete only registered Phase 5-A proxy nodes."""
from __future__ import absolute_import, division, print_function
import maya.cmds as cmds
from . import diana_spine_phase5a_proxy as proxy


def remove():
    nodes = []
    if cmds.objExists(proxy.REGISTRY):
        nodes = cmds.listConnections(proxy.REGISTRY + ".nodes", s=True, d=False) or []
    nodes = [x for x in nodes if cmds.objExists(x)]
    if nodes:
        cmds.delete(nodes)
    if cmds.objExists(proxy.REGISTRY):
        cmds.delete(proxy.REGISTRY)
    return {"remaining": cmds.ls("DIANA_SPINE_P5A_*") or [],
            "root_exists": cmds.objExists(proxy.ROOT)}


if __name__ == "__main__":
    print(remove())
