# Diana Spine RC アニメーター操作ガイド

## Matcherを開く

Maya Script EditorのPythonタブで実行する。

```python
from Spine import diana_spine_phase10_ui
diana_spine_phase10_ui.show()
```

UIには現在モード、Correction状態、次の操作が表示される。

- **Snap to FK**: 現在姿勢を保ってMODE0へ切替
- **Snap to IK**: 現在姿勢を保ってMODE1へ切替
- **Snap to IK + FK**: 現在姿勢を保ってMODE2へ切替
- **Reset inactive corrections**: 現在使っていないモードのCorrectionだけをゼロ化
- **Safe reset current correction**: 現在モードが非ゼロCorrectionなら姿勢変化を防ぐため拒否

## モード別操作

- MODE0 FK: `DIANA_SPINE_P5_*_OP_FK_CTRL`でHIP / LOWER / MIDDLE / SHOULDERを操作する。
- MODE1 IK: IK HIP / UPPERとTWISTを操作する。操作FKはIK姿勢へ追従する。
- MODE2 IK+FK: IK姿勢へ操作FKのローカル回転を追加する。

## キーとCorrection

Snap後のCorrectionは姿勢維持に必要な値であり、内部ノードを直接編集しない。Matcherをキー登録ワークフローで呼ぶ場合は次を使用する。

```python
from Spine import diana_spine_phase9_matcher
diana_spine_phase9_matcher.match(1, key=True)  # IKへSnapしてキー登録
```

Snap後もIK HIP / UPPER、TWIST、FK追加回転を通常どおり操作できる。再Snap時は切替先の古いCorrectionをゼロ評価してから新しい値へ置換するため、補正が累積しない。

active modeのCorrectionを無条件にResetすると姿勢が変わるため、UIはResetを拒否する。必要な場合は先に姿勢を別モードへSnapするか、アニメーションとしてベイクしてからinactive correctionをResetする。

## Undo

1回のSnapは1つのUndo chunkである。失敗時はMatcher自身が操作前の値とキーを復元する。

