# Diana Spine FK/IK integration

This directory starts with a read-only audit. No production controller or
deformation connection is changed by the current code.

## Repository finding

As of 2026-11-03, the repository contains no existing Spine implementation and
no references to `Spine_Mode`, `MODE1_FINAL`, `MODE2`, the independent IK curve,
or the live drivers. The supplied node description therefore appears to refer
to Maya-scene data that is not represented in this repository. Scene facts must
be captured before an integration network is designed or installed.

## Run the audit in Maya 2026

Add the repository's `scripts` directory to `sys.path`, then run:

```python
from Spine import diana_spine_audit
report = diana_spine_audit.run(
    r"C:\temp\diana_spine_audit.json"
)
```

Omit the path to keep the report in memory only. The audit reads nodes,
attributes, matrices, pivots, connections, skinCluster membership, evaluation
mode, and the scene's modified flag. It does not create nodes, set attributes,
change selection or time, or alter connections. A JSON output path must point
to an existing directory.

## Information still required from the scene

- Complete incoming/outgoing plugs for every `DIANA_SPINE_*` node.
- Exact hierarchy, world/local matrices, rotate orders, jointOrient values,
  offsetParentMatrix values, pivots, and inherited scale for the FK chain.
- The node types and multiplication order of every MODE1 and MODE2 matrix node.
- The driven joints and their parent spaces, bindPose relationships, and
  downstream neck/head/arm/hair connections.
- Whether FK rotate channels are keyed, connected, constrained, locked, or
  referenced, and whether zero values represent the IK-follow rest offset.
- Twist source, aim/up-vector convention, and expected behavior at tangent/up
  degeneracy.
- Namespace/reference usage and whether multiple Diana rigs can coexist.
- Required pose-matching behavior when `Terminal.Spine_Mode` changes.

## Provisional design direction (not yet installed)

The safest candidate is to separate **follow space** from **animator delta**:

1. Keep MODE0 on the existing FK world-matrix path without rewiring it.
2. Derive IK base matrices from the already independent MODE1/live-driver
   network.
3. Convert each IK base into the relevant parent space before driving a proxy
   follow group. Do not feed independent world matrices directly through the
   existing FK parent chain.
4. Read the animator's existing local FK rotate channels as a delta matrix.
   Compose that delta exactly once with the IK base for MODE2. MODE2 must not
   consume an FK world matrix that already contains IK follow.
5. Validate this on a separate proxy hierarchy first, including scale 2,
   shoulder rotate-pivot compensation, rotate order, jointOrient, twist, and
   matrix multiplication order.

`offsetParentMatrix` directly on animated controls is not the first choice: its
interaction with the existing hierarchy and local channels can be valid, but
it makes inherited transforms and mode switching harder to reason about. A
dedicated follow/offset layer or proxy hierarchy is easier to inspect and roll
back. The final choice remains conditional on the audit report.

## Planned safety model

Future builders should default to dry-run, use uniquely named nodes, record
every pre-existing destination/source pair before changing it, refuse partial
or unexpected scenes, and write a rollback manifest. No builder should delete
existing joints, controllers, skinClusters, meshes, weights, or animation.
