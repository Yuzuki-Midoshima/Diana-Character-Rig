# Diana Spine Phase 5-B Report

## Status

**COMPLETE** — Maya 2026 Standaloneで検証用コピーを構築し、段階統合、DG評価、保存・再読込、ロールバックまで合格した。`Character_spine37.ma`は変更していない。

## Final design

- `L/R_clavice_jnt` と `IK_L/R_elbow_anim` は、最終肩行列から算出したワールド行列を親空間へ変換し、`offsetParentMatrix`で駆動する。
- 駆動対象自身の `parentInverseMatrix` は使用せず、実親の `worldInverseMatrix` を使用する。これによりTransform評価クラスタ内の自己循環を防ぐ。
- `L/R_clavice_anim` は直接駆動しない。既存の `DIANA_SPINE_L/R_arm_GRP_FINAL_FOLLOW_MM` が腕FKを最終肩行列へ追従させており、親の鎖骨コントローラーも駆動すると二重追従になるため。
- 手IKのBodyターゲットを既存parentConstraintに追加し、従来のWorldターゲットと `IK_Space` 接続は維持する。

## Validation result

許容誤差は行列・位置・スケール `1e-4`、回転 `1e-3 degree` とした。

- MODE0 / MODE1 / MODE2、IK HIP/UPPER移動、IK回転、FK追加回転: PASS
- Attachment最大行列誤差: `1.1368683772161603e-13`
- 最大位置誤差: `1.1368683772161603e-13`
- 最大回転誤差: `2.4148365394514667e-06 degree`
- 最大スケール誤差: `6.661338147750939e-16`
- 腕FKの統合前Phase 5応答との誤差: 左右とも `0.0`
- 腕FKローカルチャンネル行列誤差: 左右とも `0.0`
- 手IK World Space誤差: 左右とも `0.0`
- 手IK Body Space誤差: 左右とも `2.8421709430404007e-14`
- 新規DG循環: `0`
- Spine joint MODE0最大誤差: `3.7282891014456254e-05`
- Spine/Back関連skinCluster 3個のgeometry/influence: 一致
- 首・頭の追従と復元: PASS
- 髪の既存接続と姿勢復元: PASS。このIK UPPERテストではワールド運動は発生せず、既存空間挙動を維持した。
- 保存・再読込: PASS
- Phase 5-B / Phase 5ロールバック: PASS、残存ノード `0`

## Scene-load notes

元シーン読込時に、既存の `nodeGraphEditorInfo`、Bow UIの `intValue=None`、再読込時UUID重複の警告がMayaから出力された。Phase 5-BのDGノードとは無関係で、検証コピーの読込・評価・ロールバックは完了した。

## Deliverables

- `diana_spine_phase5b_integrate.py`: manifest取得と左右段階統合
- `diana_spine_phase5b_validate.py`: 行列、腕FK、手IK space、DG循環検証
- `diana_spine_phase5b_rollback.py`: 制約ターゲット、OPM接続、新規ノードの復元
- `diana_spine_phase5b_runner.py`: 別名保存、段階実行、再読込、ロールバックのE2E実行
- `Character_spine37_phase5b_manifest.json`: 変更前接続・行列・制約ターゲット
- `Character_spine37_phase5b_validation.json`: 最終検証結果

Phase 5-B完了後の検証シーンはロールバック済みであり、元シーンへの反映は行っていない。
