# Diana Spine Phase 5-A Implementation Plan for Phase 5-B

## Recommended architecture

Create separate attachment outputs from the final shoulder matrix. Do not drive `shoulder_spine_anim`, production FK, Terminal, the old curve, or stretch network.

### Arm FK and clavicles

1. Capture left/right clavicle and clavicle-control rest-world matrices.
2. Calculate constant offsets relative to the MODE0 shoulder reference.
3. Create independent attachment drivers from `offset × finalShoulderWorld`.
4. Before touching production nodes, compare two integration options:
   - insert a parent-space matrix layer above the arm output roots without reparenting animator controls;
   - add the attachment delta to existing `offsetParentMatrix` inputs with captured local compensation.
5. Validate both clavicle skin joints and clavicle animator-control roots. They are parallel children and must not receive the same delta twice through an inherited path.

### Arm IK

1. Preserve `L_ARM_IK_SPACE_PC` and `R_ARM_IK_SPACE_PC`.
2. Add a final-shoulder attachment target only as an existing Space Switch option or replace the constraint internally with a manifest-backed `blendMatrix` equivalent.
3. Confirm World mode keeps the IK hand world matrix unchanged.
4. Confirm shoulder/local mode follows the new final shoulder output.
5. Treat `IK_L/R_elbow_anim` separately: current DAG behavior is full shoulder following, while hand controls are space-switched.

### Neck, head, and hair

1. Keep `neck_root_jnt_parent_Constraint_1` and `head_jnt_parent_Constraint_1` intact unless a separate audit proves replacement is necessary.
2. Preserve `Terminal.Head_Space` Local/World behavior.
3. Keep hair parent/scale constraints and head ancestry. Do not attach hair roots directly to the shoulder.
4. Validate head-local and world-head modes before and after any arm attachment change.

## Phase 5-B safety gates

- Fresh validation copy and manifest before changes.
- No production FK or legacy curve/stretch input changes.
- No connection from an attachment output back into MODE1 upstream nodes.
- LOWER, MIDDLE, SHOULDER, HIP staged validation.
- Arm FK full-follow test and IK World-space preservation test.
- Head Local/World and hair constraint tests.
- Scale 2 and Shoulder pivot validation.
- Save/reload and manifest rollback.
- No new cycleCheck entries, including inactive choice/condition/space-switch branches.

Production integration must stop if the arm control root and skin-joint root cannot be driven without double transformation or existing animation loss.
