# Diana Spine Phase 8 Implementation Proposal

## Recommended production design

### MODE0

Phase 5の操作FK rotate deltaとは別に、4部位それぞれのSnap Translation Deltaを追加する。

```text
FK snap translate + animator FK rotate
    -> local correction matrix
    -> existing production FK world
    -> MODE0 final
```

- production FKのtranslateは変更しない
- 既存FKアニメーションを保持
- Snap Translationは専用非表示Transformまたは専用属性で保持
- HIP/LOWER/MIDDLE/SHOULDERすべてに3軸が必要

### MODE1 / MODE2

推奨は **D: snap-only downstream correction layer**。

```text
existing MODE1 or verified MODE2
    -> snap-only per-part correction matrix
    -> final deformation / attachment output
```

- 既存MODE1、独立IKカーブ、Stretch、LIVE_DRIVERは変更しない
- 補正は既存IKの下流に限定
- Attachmentは補正後の最終肩行列を引き続き参照
- Snap時のみ補正チャンネルへキーを作成
- IKコントローラーの既存キーを書き換えない

## Why not A/B/C alone

A/Bは位置の一部しか増やせず、FKが持つ独立回転を再現できない。CはIKカーブとの整合性は高いが、回転補正がなく、旧カーブ/Stretchへの依存を作るとPhase 4-Rの循環リスクが戻る。

## Minimum versus robust DOF

- 理論最小: MODE2 rank 23/24のため、姿勢ごとのSVD null directionに沿う1 scalar correction
- 実用最小: 最終行列に対するper-part correctionを用意し、Matcherが必要な成分だけキー化
- 実装上の推奨: 4 x TR（24 channels）を用意し、不要チャンネルは0のまま保持

## Production integration gate

Phase 9で本番統合する前に、次を必須とする。

1. FK Translation DeltaとIK correctionをそれぞれ別のchoice入力で一部位ずつ統合
2. LOWER -> MIDDLE -> SHOULDER -> HIPの段階検証
3. MODE0の既存FKゼロポーズ一致
4. SnapキーのUndo/削除/ロールバック
5. Attachment、Arm Space、Head Space、skinCluster、装備の再検証
6. choiceの非選択分岐を含むDG循環検査

Phase 8ではこのproduction統合を行っていない。

