# Diana Spine Phase 4 Production Integration Report

## Status

**INCOMPLETE — validation copy rolled back.**

The production scene `Character_spine37.ma` was not overwritten. Integration was attempted only in `Character_spine37_PHASE4_VALIDATION.ma`. Although the staged numerical validation passed, Maya reported a DG cycle containing a newly created Phase 4 node. This violates the completion criteria, so the integrated scene was not saved and the validation scene was restored from the manifest.

## Implemented deliverables

- `diana_spine_phase4.py`: manifest capture, dependency preflight, staged Follow Layer and MODE2 construction.
- `diana_spine_phase4_validate.py`: staged and pose-case numerical validation.
- `diana_spine_phase4_rollback.py`: connection, hierarchy, and node rollback.
- `Character_spine37_phase4_manifest.json`: pre-integration matrices, TRS, hierarchy, connections, downstream relationships, and skinCluster state.
- `Character_spine37_phase4_validation.json`: numerical validation output from the final attempted network.
- `Character_spine37_phase4_final_status.json`: authoritative final status and rollback verification.

## Confirmed numerical behavior

The final attempted matrix network used the Phase 2/3 result:

`FK local delta × MODE1 final`

The staged run completed all four parts in the required order: LOWER, MIDDLE, SHOULDER, HIP. Ten pose cases and four MODE0 stage checks passed numerically.

- Maximum matrix error: `2.8421709430404e-14`
- Maximum scale-2 error: `8.88178419700125e-16`
- Shoulder local pivot error: `0.0`
- MODE0 stage checks: all passed
- skinCluster comparison: unchanged
- Numerical tolerance: `1.0e-4`

These results confirm the matrix order and the local-delta extraction, but do not establish a valid production graph because the DG cycle criterion failed.

## Blocking DG issue

Maya emitted a cycle warning containing:

`DIANA_SPINE_P4_HIP_FOLLOW_MODE_CHOICE.output`

The warning chain also traversed existing spine stretch and live-driver nodes. Three progressively isolated variants were tested:

1. Reading the production FK matrix directly caused feedback through the Follow Layer.
2. Reconstructing the local FK delta removed that direct read, but using the Follow transform's `parentInverseMatrix` created self-feedback.
3. Replacing it with the original parent's `worldInverseMatrix` passed numerical tests, but Maya still found a cycle through the broader production spine graph.

Maya dependency evaluation includes inactive choice/condition branches in cycle analysis. Therefore, mode selection alone cannot safely isolate a Follow Layer that reparents the production FK controls while existing upstream spine paths still consume those controls.

## Rollback result

Rollback was executed from the manifest after the cycle was detected.

- Remaining `DIANA_SPINE_P4_*` nodes: `0`
- MODE2 input source restored for HIP, LOWER, MIDDLE, SHOULDER: yes
- Maximum FK world-matrix restoration error: `0.0`
- Original scene overwritten: no
- Integrated validation scene saved: no
- Save/reload test: intentionally not performed on an invalid cyclic integration

## Required next design step

The next attempt must break the structural dependency before moving production FK controls. The safest candidates are:

1. Keep production FK controls in their original hierarchy and create separate IK-follow display/proxy controls, switching visibility and input ownership by mode.
2. Decouple legacy FK-dependent curve/stretch inputs from production FK world matrices, then prove the replacement IK driver path is independent before inserting Follow Layers.
3. Use a presentation layer that follows MODE1 but never contributes to the deformation or MODE1 upstream graph; retain original FK channels as the only MODE2 local-delta source.

No Phase 4 production setup should be promoted until Maya reports no new DG cycle and the full save/reload suite passes.
