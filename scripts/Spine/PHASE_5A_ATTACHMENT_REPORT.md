# Diana Spine Phase 5-A Attachment Dependency Report

## Status

**COMPLETE — audit and non-destructive proxy validation passed.**

The audit and proxy test ran in `Character_spine37_PHASE5A_VALIDATION.ma`. The original `Character_spine37.ma` was not modified. Production arm, neck, head, hair, spine, curve, and stretch connections were not changed.

## Existing attachment hierarchy

`shoulder_spine_anim` is the common production attachment parent for:

- `L_clavice_jnt`, `R_clavice_jnt`
- `L_clavice_anim`, `R_clavice_anim`
- `IK_L_elbow_anim`, `IK_R_elbow_anim`
- `neck_anim_pad`
- `Terminal`
- bust and helper nodes

The arm FK controls are descendants of the clavicle controls:

```text
shoulder_spine_anim
  +-- L_clavice_anim
  |     +-- L_arm_GRP
  |           +-- FK_L_arm_GRP
  |                 +-- FK_L_shoulder_anim -> FK_L_elbow_anim -> FK_L_wrist_anim
  +-- R_clavice_anim
        +-- R_arm_GRP
              +-- FK_R_arm_GRP
                    +-- FK_R_shoulder_anim -> FK_R_elbow_anim -> FK_R_wrist_anim
```

The arm IK hand controls are outside this hierarchy under `IK_arm_GRP`. Their const groups are driven by `L_ARM_IK_SPACE_PC` and `R_ARM_IK_SPACE_PC`. They must remain under the existing space-switch system.

`neck_root_jnt` is a child of `shoulder_fk_Spine_anim_jnt` and also has `neck_root_jnt_parent_Constraint_1`. `head_jnt` is downstream of the neck chain and has `head_jnt_parent_Constraint_1`. `Terminal.Head_Space` exposes `Local:World` and drives the existing head-space network.

Short-hair root joints are descendants of the head hierarchy and also use parent and scale constraints from their animation controls.

## Attachment classification

| Nodes | Class | Evidence |
|---|---|---|
| `L/R_clavice_jnt` | A: full shoulder transform | Direct children of `shoulder_spine_anim`; no local space constraint |
| `L/R_clavice_anim` and FK arm descendants | A: full shoulder transform | Direct attachment roots; FK controls inherit through their DAG |
| `IK_L/R_elbow_anim` | A, current behavior | Direct children of `shoulder_spine_anim`; pole-vector controls currently inherit the full shoulder transform |
| `IK_L/R_hand_anim_const` | E: space switch | Driven by `L/R_ARM_IK_SPACE_PC`; direct attachment would break world/local switching |
| `Ik_L/R_hand_anim` | E: space switch | Additional parent constraints exist on the animator controls |
| `neck_root_jnt` | A through existing neck network | Parent plus parentConstraint; Phase 5 motion test already showed correct following |
| `head_jnt` | E: Local/World head space | `Terminal.Head_Space` drives the head-space rotation network |
| short-hair root joints | E / head-local attachment | Head descendants with parent and scale constraints; should not receive a direct shoulder matrix |
| B: rotation-only | No confirmed direct candidate | Existing constraints must be inspected per target before any conversion |
| C: position-only | No confirmed direct candidate | No audited attachment used a position-only shoulder path |
| D: fixed world | Arm IK when its existing space switch selects World | This is a state of class E, not a separate direct connection |

## Final shoulder matrix

`DIANA_SPINE_DEFORM_SHOULDER_MODE_CHOICE.output` is a world-space result.

Evidence:

- MODE0 output matches `shoulder_fk_Spine_anim_jnt.worldMatrix[0]` with maximum difference `3.9317871e-05`.
- Extracted scale components are `[2.0, 2.0, 2.0]`.
- The output therefore already includes the rig's world scale.
- `shoulder_spine_anim` has local rotate pivot approximately `[0.0, 145.989029, 0.0]`.

The MODE_CHOICE output cannot be connected directly to a clavicle. A bind/rest offset is required:

```text
clavicleOffset = clavicleRestWorld × inverse(shoulderRestWorld)
attachmentWorld = clavicleOffset × finalShoulderWorld
```

This offset preserves clavicle position, rotation, handedness, Scale 2, and the effective shoulder-pivot relationship without baking the pivot into a second rotation.

## Proxy validation

Two world-rooted proxies were driven with:

```text
constant clavicleOffset
  -> multMatrix.matrixIn[0]
final shoulder MODE_CHOICE.output
  -> multMatrix.matrixIn[1]
multMatrix.matrixSum
  -> proxy.offsetParentMatrix
```

Tested cases:

- MODE0, MODE1, MODE2 rest poses
- MODE0 shoulder FK rotation
- MODE2 shoulder FK delta
- compound LOWER/MIDDLE/SHOULDER FK delta
- IK HIP X +5
- IK UPPER X +5
- IK UPPER Z rotation +10
- IK UPPER X +5 with MODE2 shoulder delta

Results:

- Maximum matrix error: `0.0`
- Maximum position error: `0.0`
- Maximum rotation error: `1.7075473e-06` degrees
- Maximum scale error: `0.0`
- New DG cycles: `0`
- Production restoration error: `3.9317871e-05`, below tolerance `1e-4`
- Remaining Phase 5-A proxy nodes: `0`
- Remaining temporary Phase 5 nodes: `0`

## Design conclusion

For clavicle and arm-FK attachment roots, `multMatrix + offsetParentMatrix` or an equivalent matrix input to a newly inserted non-production attachment layer is numerically valid. Directly connecting the final shoulder matrix to existing nodes is not approved by this phase.

Arm IK hand controls must use an additional target in their existing space-switch constraints or matrix equivalent. A direct shoulder OPM would destroy World-space behavior.

Neck/head/hair should retain their existing constraint and space networks. Their production paths already follow the final spine result where required; duplicating shoulder attachment would risk double transforms.
