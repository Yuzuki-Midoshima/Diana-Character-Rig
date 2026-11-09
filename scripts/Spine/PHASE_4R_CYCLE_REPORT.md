# Diana Spine Phase 4-R: DG Cycle Analysis

## Result

The Phase 4 cycle has been identified. The production FK hierarchy already has a valid downstream path back into `MODE1_FINAL_MM` through the legacy spine curve, stretch network, IK spine joints, and live-driver network. Parenting a production FK control below a Follow transform driven by MODE1 adds the reverse edge and closes the cycle.

The analysis was run in the rolled-back `Character_spine37_PHASE4_VALIDATION.ma`. No production node was edited. Non-selected `choice` and `condition` branches were traversed without filtering by selector values.

## Concrete cycle

The shortest LOWER path is representative:

```text
lower_fk_Spine_anim.translate
  -> back_spine_cv_1_cls_Handle_parent_Constraint_1.targetTranslate
  -> back_spine_cv_1_cls_Handle.translate/worldMatrix
  -> DIANA_SPINE_CV1_FK_SPACE_MM
  -> DIANA_SPINE_CV1_FK_DCM
  -> DIANA_SPINE_CV1_FK_RESULT
  -> DIANA_SPINE_CV1_MODE0_COND.colorIfTrue
  -> DIANA_SPINE_CV1_MODE_RESULT
  -> back_spine_curve_Shape.controlPoints[1]
  -> back_spine_curve_Shape.worldSpace
  -> RIG_curveInfo1.inputCurve
  -> RIG_spineStretch_MD.outputX
  -> IK_back_spine_jnt_1.scaleX/worldMatrix
  -> DIANA_SPINE_HIP_IK_WORLD_POS_DCM
  -> DIANA_SPINE_HIP_IK_POSITION_PMA
  -> DIANA_SPINE_hip_IK_DEFORM_DRV
  -> DIANA_SPINE_DEFORM_HIP_LIVE_DRIVER_DCM
  -> DIANA_SPINE_DEFORM_HIP_MODE1_POSITION_DELTA
  -> DIANA_SPINE_DEFORM_HIP_MODE1_FINAL_POSITION
  -> DIANA_SPINE_DEFORM_HIP_MODE1_POS_CM
  -> DIANA_SPINE_DEFORM_HIP_MODE1_FINAL_MM
```

Phase 4 added the closing path:

```text
MODE1_FINAL_MM
  -> P4_*_FOLLOW_MODE_CHOICE
  -> P4_*_FOLLOW.offsetParentMatrix
  -> production FK parentMatrix/worldMatrix
  -> legacy FK-dependent path above
  -> MODE1_FINAL_MM
```

HIP reaches LOWER through `hip_fk_Spine_anim_jnt.scale -> lower_fk_Spine_anim.inverseScale`. MIDDLE and SHOULDER additionally reach `Terminal.Spine_Mode` through their DAG descendants. `Terminal.Spine_Mode` drives the CV conditions even when MODE0 is not selected, so selector state does not remove the dependency.

## Why the return path exists

The legacy `back_spine_curve` remains a shared deformation source:

- Its CVs retain FK-mode inputs from the production FK hierarchy.
- `back_spine_curve_Shape.worldSpace` drives `RIG_curveInfo1.inputCurve`.
- The same worldSpace drives `back_spine_ik_Handle.inCurve`.
- It also drives `DIANA_SPINE_DEFORM_NEUTRAL_CURVE_INFO.inputCurve`.
- Stretch drives the IK spine joint chain used by the MODE1 live-driver position network.

This path is necessary to preserve the original FK spline behavior and stretch calculation. It becomes invalid only when MODE1 is made an ancestor driver of those same FK controls.

## Independent IK curve re-audit

`DIANA_SPINE_INDEPENDENT_IK_CURVE` has four CVs. OpenMaya plug-level upstream traversal found seven plugs per CV and no production FK controller nodes.

Each CV is driven by its corresponding `DIANA_SPINE_CV*_DRV -> SPACE_MM -> DELTA_DCM -> DELTA_RESULT -> INDEPENDENT_CV*_ADD` path. IK control paths are now detected after canonicalizing short and full DAG paths.

One residual dependency exists: every independent CV space matrix reads `back_spine_curve.worldInverseMatrix[0]`. This is the legacy curve transform's coordinate-space basis, not its FK-driven shape/CV data. Therefore the independent curve is independent of production FK animation values at plug level, but it is not completely self-contained with respect to the legacy transform. A future production implementation should replace this basis with an independent parent/world-space basis before claiming full isolation.

Node-level traversal reports apparent FK paths through `Terminal.Spine_Mode` and IK-control visibility. Plug-level traversal rejects those as data paths to the CV plugs; they are an expected false positive of node-level graph collapsing.

## Minimum cut points

For Follow-parenting approach A, the minimum conceptual cut is between the FK-dependent legacy curve and every IK/MODE1 consumer. In this scene that is not one connection; at least these consumers must be replaced or duplicated:

1. `back_spine_curve_Shape.worldSpace -> RIG_curveInfo1.inputCurve`
2. `back_spine_curve_Shape.worldSpace -> back_spine_ik_Handle.inCurve`
3. `back_spine_curve_Shape.worldSpace -> DIANA_SPINE_DEFORM_NEUTRAL_CURVE_INFO.inputCurve`

Because MODE0 still needs the legacy curve, simply reconnecting these plugs globally would break original FK behavior. A complete separation requires separate FK and IK spline/stretch chains and a downstream result switch. That is larger and riskier than adding an independent operation-control layer.

For the recommended approach, the minimal change is instead to avoid the closing edge: never parent or matrix-drive production FK controls from MODE1. Use independent operation controls whose local rotate drives only the new MODE2 result.
