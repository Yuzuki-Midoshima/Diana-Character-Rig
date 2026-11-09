# Diana Spine RC セットアップ

## 動作環境

- Autodesk Maya 2026 / Python 3
- 外部Pythonパッケージ不要
- リポジトリの `scripts` ディレクトリを `PYTHONPATH` に追加

## 完成RCを開く

`dist/Character_spine37_SPINE_RC01.ma` をMaya 2026で開く。RCにはPhase 5、5-B、9のDGネットワークが保存されている。Matcher UIだけはリポジトリ内Pythonを使用する。

```python
from Spine import diana_spine_phase10_ui
diana_spine_phase10_ui.show()
```

## 元シーンからRCを再構築する

PowerShellからMaya 2026のmayapyで実行する。

```powershell
& 'C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe' `
  'scripts\Spine\diana_spine_phase10_build_rc.py' `
  --source 'D:\project\Character_spine37.ma' `
  --output-scene 'D:\project\Character_spine37_SPINE_RC01.ma'
```

- 入出力は必ず別ファイルにする。
- 出力名には `_SPINE_RC` が必要。
- 出力が既に存在する場合は安全停止する。意図的に置換する場合だけ `--replace` を追加する。
- 元シーンのSHA-256、mtime、既存animation curve、skinCluster、脚・Facial・装備接続を構築前後で検証する。
- manifestは `Character_spine37_phase10_rc_manifest.json` に出力される。

## 検証

```powershell
& 'C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe' `
  'scripts\Spine\diana_spine_phase10_validate_rc.py'
```

検証はRC本体を変更せず、一時コピーで360フレームと3回の保存・再読込を行う。結果は `Character_spine37_phase10_validation.json` に保存される。

## ZIP配布

`diana_spine_phase10_package.py`を通常のPythonまたはmayapyで実行する。RC、必要なSpine Python、manifest、検証JSON、説明書を相対パス付きZIPへ格納する。

```powershell
& 'C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe' `
  'scripts\Spine\diana_spine_phase10_package.py'
```

受取側はZIPを展開し、展開先の `scripts` をMayaのPythonパスへ追加する。

## 既知の読込警告

元シーン由来の `nodeGraphEditorInfo`、Bow UIの `intValue=None`、UUID警告がMaya Standaloneで表示される。RC追加ノード由来ではなく、数値評価、保存・再読込、DG差分検証は合格している。

