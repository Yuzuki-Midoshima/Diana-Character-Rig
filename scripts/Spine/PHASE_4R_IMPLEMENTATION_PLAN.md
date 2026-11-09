# Diana Spine Phase 4-R Implementation Plan

## Status

Phase 4-R analysis and non-destructive topology validation are complete. Production integration is intentionally not performed.

## Proposed Phase 4-R2 sequence

1. Create a validation-scene copy from the original scene and capture a fresh manifest.
2. Create HIP/LOWER/MIDDLE/SHOULDER operation controls under a dedicated root outside the production FK DAG chain.
3. Match their shapes, rotateOrder, pivots, and visual locations to the production controls. Preserve Shoulder local pivot `Y=145.989` without parenting production shoulder nodes.
4. Drive each operation control's follow/zero layer from its corresponding `MODE1_FINAL_MM`, converted into the independent operation hierarchy's parent space.
5. Feed only the operation control's local rotate into a `composeMatrix`, respecting rotateOrder.
6. Build `operation local delta × MODE1 final` and validate it against the Phase 2/3 expected matrices at scale 2.
7. Connect the new result to `MODE_CHOICE.input[2]` one part at a time: LOWER, MIDDLE, SHOULDER, HIP. Record and retain old MODE2 sources.
8. Use `Terminal.Spine_Mode` only for visibility/channel-state presentation. Do not use mode selection as a cycle-isolation mechanism.
9. Validate no path from the new MODE2 result or operation controls reaches MODE1 upstream inputs.
10. Run pose, pivot, downstream-follow, skinCluster, cycle, save/reload, rerun, and rollback tests.

## Acceptance gates

- OpenMaya plug-level graph contains no production FK or operation-control path upstream of independent IK CV inputs except intentional control drivers.
- No operation control or follow layer is an ancestor of production FK, `Terminal`, legacy spine curves, joints, or skinned outputs.
- Maya emits no new cycle warning with all choice/condition branches connected.
- MODE0 matches the pre-integration manifest exactly within `1e-4`.
- MODE2 equals `FK local delta × MODE1 final` within `1e-4`.
- Scale-2 and Shoulder pivot errors remain within `1e-4`.
- Rollback restores all connections and matrices and leaves no Phase 4-R2 nodes.

## Optional future approach A

If the original production FK controls must visibly follow IK, first build separate FK and IK curve/stretch/IK-joint chains. Switch only their final deformation matrices downstream. Do not attempt Follow parenting until a plug-level audit proves that production FK has no path to MODE1.
