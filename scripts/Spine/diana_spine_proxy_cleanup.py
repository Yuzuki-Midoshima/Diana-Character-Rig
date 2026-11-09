# -*- coding: utf-8 -*-
"""Remove only the disposable Diana Spine Phase 2/3 proxy network."""

from __future__ import absolute_import, print_function

import maya.cmds as cmds

from Spine import diana_spine_proxy


def remove():
    root = diana_spine_proxy.ROOT
    if not cmds.objExists(root):
        print("[DIANA SPINE P23] No proxy exists.")
        return []
    if not cmds.attributeQuery("dianaProxyVersion", node=root, exists=True):
        raise RuntimeError("Refusing to delete unrecognized node: " + root)
    nodes = cmds.listConnections(
        root + ".dianaProxyNodes", source=True, destination=False
    ) or []
    targets = sorted(set(nodes), key=lambda name: name.count("|"), reverse=True)
    # Deleting the root removes DAG children; registered DG nodes are explicit.
    dg_nodes = [name for name in targets if cmds.objExists(name) and not cmds.objectType(name, isAType="dagNode")]
    if dg_nodes:
        cmds.delete(dg_nodes)
    if cmds.objExists(root):
        cmds.delete(root)
    remaining = [name for name in targets if cmds.objExists(name)]
    if remaining:
        raise RuntimeError("Proxy cleanup incomplete: " + ", ".join(remaining))
    print("[DIANA SPINE P23] Proxy removed; production graph was not edited.")
    return targets

