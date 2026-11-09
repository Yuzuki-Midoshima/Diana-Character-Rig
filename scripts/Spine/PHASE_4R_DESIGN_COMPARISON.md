# Diana Spine Phase 4-R: Design Comparison

| Criterion | A. Fully separate FK return path | B. Independent operation FK Proxy | C. MODE2-only independent FK layer |
|---|---|---|---|
| DG cycle risk | Medium after a complete split; high during migration | Low | Lowest |
| Existing FK animation | Preserved if MODE0 chain is untouched | Preserved on production FK; proxy has separate channels | Preserved in MODE0; separate MODE2 channels |
| Animator workflow | Original controls can follow IK | Familiar visible controls, but a second control set | Cleanest technically; requires explicit MODE2 controls/UI |
| Existing-rig changes | Very high: duplicate/reroute curve, IK handle, stretch and switch results | Low to medium: new controls and MODE2 input only | Low: new delta controls and MODE2 input only |
| Shoulder/neck/arm/hair risk | High because deformation chain changes | Low; proxy must never parent downstream production nodes | Lowest; existing shoulder output remains untouched |
| Complexity | High | Medium | Low to medium |
| Rollback | Difficult | Easy: restore MODE2 plugs and delete proxy group | Easiest: restore MODE2 plugs and delete layer |

## Recommendation

Use a B/C hybrid: independent, animator-visible MODE2 operation controls implemented as a MODE2-only local-delta layer.

- Production FK controls stay in their original hierarchy and continue to operate MODE0.
- Operation controls follow `MODE1_FINAL_MM` visually, but are not ancestors of production FK, Terminal, legacy curves, joints, or skin outputs.
- Their local rotate channels are the only input to the new delta compose matrices.
- MODE2 remains `operation FK local delta × MODE1 final`.
- MODE1 shows the operation controls following IK with delta channels zeroed or non-keyable; MODE2 enables their rotate channels.
- Neck, head, arms, hair, jointOrient, Shoulder pivot, and skinCluster outputs remain on the existing deformation result path.

This does not make the original production FK shapes follow IK. It provides a separate, safe operation set in IK/IK+FK modes. Achieving literal motion of the production controls requires approach A and a full spline-chain separation.
