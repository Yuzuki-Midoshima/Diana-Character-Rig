# Diana Spine Phase 10 Release Candidate 最終レポート

## ステータス

**`phase10_complete=True`**

Maya 2026の新規StandaloneセッションでRCを構築し、別の新規セッションで最終検証した。元の `Character_spine37.ma` は変更していない。完成RCはロールバックせず保持している。

## Release Candidate

- シーン: `dist/Character_spine37_SPINE_RC01.ma`
- サイズ: `31,990,268 bytes`（約30.51 MiB）
- RC SHA-256: `9f53ad5457bbefc2f039bf8877a3a920e0788d92d6488ff92f127ee7710cb5e7`
- 元シーンSHA-256（前後一致）: `6858f5c3315925f4260f8bc18df3bbf0102340158ae87c11ba4c1734876af5b8`

## 検証結果

許容値は位置 `1e-3`、回転 `1e-3 degree`。

- 6方向Snap: PASS
- 最大位置誤差: `5.90221124448794e-14`
- 最大回転誤差: `2.4148365394514667e-06 degree`
- 全身Attachment最大行列誤差: `1.4210854715202004e-13`
- Snap後のFK / IK / IK+FK操作: PASS
- Correction保持、再Snap、active Reset拒否、inactive Reset: PASS
- Undo / Redo: PASS、復元誤差0
- 手IK World固定 / Body追従: PASS
- 腕FK/IK切替属性 `L/R_arm_settings_anim.FKIK`: PASS
- 脚FK、Reverse Foot、Facial eye control: PASS
- skinCluster、既存キー、脚、Facial、装備接続: 構築前後一致
- Animation Layer: PASS

## 360フレーム耐久

- 評価フレーム: 360
- 複数FK / IK / IK+FK切替: PASS
- Twist、大きな前後屈・側屈、腕FK/IK操作、キー補間: PASS
- 不正行列: 0
- 予期しない90度超の回転反転: 0
- Phase 9由来の新規DG循環ノード: 0
- 保存・再読込: 3回連続PASS

既存リグには元からcycleCheckで検出される腕・Bow等のノード群があるため、Phase 5-B manifestの既存集合を基準にノード名で差分判定した。Phase 9 / 10追加ノードを含む新規循環はない。

## 配布・再現性

- Maya 2026の別セッションからリポジトリ内スクリプトのみで構築: PASS
- 外部Pythonパッケージ: なし
- 入出力パスはCLI引数で指定可能
- 必須ノードとRCファイル名をpreflightで検証
- 既存RCへの通常再実行は安全停止。置換は明示的な `--replace` が必要
- Phase 9の二重実行は安全停止
- Animator UI: `diana_spine_phase10_ui.show()`
- ZIP作成: `diana_spine_phase10_package.py`

## 読込時の既知警告

Maya Standaloneは元シーン由来の `nodeGraphEditorInfo`、Bow UIの `intValue=None`、UUID警告を出力する。RC機能、数値評価、保存・再読込には影響しなかった。

本番の元シーンへの自動反映は行っていない。

