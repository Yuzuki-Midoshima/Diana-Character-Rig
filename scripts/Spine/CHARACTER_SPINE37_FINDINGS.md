# Character_spine37 Phase 1 findings

Audit date: 2026-11-03 (Maya 2026.3)

Source report: `Character_spine37_audit.json`

## Safety result

- The scene was already modified before the audit.
- The modified flag was still set afterward and was **not changed by the audit**.
- No node, attribute, selection, time, or connection was changed by the audit.
- All 15 explicitly required named nodes were present; 752 matching Spine-related
  nodes were captured.
- Evaluation Manager mode was `off` (DG/serial), and cycle checking was enabled.

## Confirmed MODE2 double-application risk

All four current MODE2 rotation chains begin with an FK **world matrix** and then
append IK swing and twist:

| Part | MODE2 `matrixIn[0]` |
| --- | --- |
| HIP | `hip_fk_Spine_anim_jnt.worldMatrix` |
| LOWER | `lower_fk_Spine_anim.worldMatrix` |
| MIDDLE | `middle_fk_Spine_anim.worldMatrix` |
| SHOULDER | `shoulder_fk_Spine_anim_jnt.worldMatrix` |

Each is followed by `MODE2_SWING_CM.outputMatrix` and `TWIST_CM.outputMatrix`.
Consequently, making those FK world matrices follow IK and retaining this MODE2
chain would include the IK-follow rotation once in the FK world matrix and again
in swing/twist. The existing MODE2 input topology must not be retained when FK
controls are made to follow IK.

The three existing local-delta tests use the more promising order:

```text
FK local rotate composeMatrix
    -> multMatrix.matrixIn[0]
MODE1 final IK matrix
    -> multMatrix.matrixIn[1]
```

Their outputs currently drive only test transforms' `offsetParentMatrix`; they
do not drive production FK controls or deformation choices.

## Confirmed transform facts

- LOWER and MIDDLE FK controls use rotate order 2 (`ZXY`).
- SHOULDER FK joint has `jointOrient = (0, 0, 90)`.
- The audited FK world matrices contain uniform scale 2 on all three axes.
- Existing `offsetParentMatrix` values on the audited production FK nodes are
  identity.
- `shoulder_spine_anim.rotatePivot` is `(0, 145.98902893066406, 0)` in local
  space while its translate channels are zero. It cannot be treated as a normal
  origin-centred transform.
- `shoulder_spine_anim_pad` has approximately -146.194 local X translation and
  -90 Z rotation. Shoulder handling must preserve this pad/joint/pivot setup.

## Confirmed downstream dependencies

- `shoulder_spine_anim` supplies transform data to left/right arm IK space,
  head position/rotation constraints, and legacy back-spine CV constraints.
- The shoulder FK joint scale participates in `neck_root_jnt.inverseScale`.
- Spine influences are present in `body_BAKED_skinCluster`,
  `hair_short_skinCluster27`, and `skinCluster40`.
- `Terminal.Spine_Mode` is an unconnected enum (`FK:IK:IK+FK`), currently value
  2, and drives Spine CV conditions, four deformation choices, visibility,
  arm-group choices, and final display logic.

## Repository/scene difference

The complete Spine DG system exists in the Maya scene but has no corresponding
implementation source in the repository. The repository previously contained
only Pivot Transfer and Equipment Manager code. The scene is therefore the
current source of truth, and all builder/rollback work must validate its input
topology before making changes.

## Recommended Phase 2/3 direction

1. Do not connect live drivers directly to production FK controls yet.
2. Build a separate proxy hierarchy that mirrors the exact FK parent spaces,
   rotate orders, jointOrient, scale-2 inheritance, and shoulder pivot.
3. Use MODE1 final as the single IK base. Convert it to the appropriate parent
   space for each proxy instead of injecting independent world matrices into an
   already parented chain.
4. Treat existing FK rotate channels as the animator delta. Compose the delta
   once with MODE1; do not also append MODE2 swing/twist.
5. Compare both candidate multiplication orders numerically against expected
   local-axis behavior. The existing test order is evidence, not yet proof,
   because jointOrient and the shoulder pivot still require explicit tests.
6. Run proxy tests in both DG mode and the intended production Evaluation
   Manager mode before production integration.

No production integration is authorized by this finding alone.
