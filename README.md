# rhino_claude — 建築環境解析プロジェクト置き場

Rhino / Grasshopper でモデルを作り、Ladybug Tools・Radiance・OpenFOAM で環境解析を回し、
A4 レポートまで出すプロジェクトを、1件1ディレクトリで置いていく場所。

各プロジェクトは**単体で再現できる**ように作る。モデル・入力データ・実行スクリプト・
出力画像・レポートを全部そのディレクトリに閉じ込め、README に手順と前提を書く。

---

## 命名規則

```
YYYY-MM-DD_<slug>/
```

- 日付は着手日。時系列で自然に並ぶ
- slug は英小文字・ハイフン区切りで対象を表す（`candela-hypar-shell-valencia` など）

現在のプロジェクト:

| ディレクトリ | 内容 |
|---|---|
| [`2026-07-30_candela-hypar-shell-valencia`](2026-07-30_candela-hypar-shell-valencia) | Candela 型 HP シェル（8弁）の日射・グレア・自然換気CFD |

---

## 標準ディレクトリ構成

```
YYYY-MM-DD_<slug>/
├── README.md          結果サマリー / 再現手順 / 前提と限界 / 落とし穴
├── 00_setup/          ツールチェーン導入スクリプト、気象データ
├── 01_model/          GH 定義・Rhino モデル・src/（スクリプト本体）
├── 02_<analysis>/     解析ごとに連番（例 02_radiation, 03_glare, 04_cfd）
│   ├── <build|export>_*.py   Rhino 側で走らせる準備スクリプト
│   ├── run_*.sh              ターミナル側で走らせる実行スクリプト
│   └── results/              素の出力（再計算せず作図し直せるように）
├── 05_images/         図版。解析種別ごとにサブディレクトリ
├── 06_report/         HTML + PDF + build_report.sh
└── assets/            参照写真など外部素材
```

番号は「順番に実行すれば再現できる」順に振る。解析が増えたら `05_` `06_` …とずらし、
画像とレポートは最後に置く。

---

## 再現性のために必ず入れるもの

- **GH スクリプトコンポーネントの本文を `.py` として別出し**する。
  `.gh` はバイナリで中身が読めず、差分も取れない。
  `Python3Component.TryGetSource()` で抜き、`SetSource()` で戻せる
- **ビルド成果物は入れない**（`polyMesh`、octree、中間 HDR）。スクリプトで再生成できるものは省く。
  逆に**再計算が重い素の結果**（CFD のプローブ出力など）は入れる。作図だけやり直せる
- **入力気象データを同梱**する。TMYx は更新されるので、後から同じ URL を叩いても同じ結果にならない
- **仮定値を README に明記**する。材料物性・表面温度・内部発熱・方位は、書いておかないと
  半年後に自分でも判断できない

## 共通ツールチェーン

各プロジェクトの `00_setup/install_toolchain.sh` は冪等なので、そのまま流して構わない。
導入されるもの（macOS / Apple Silicon 前提）:

| | 用途 | 配置 |
|---|---|---|
| Ladybug Tools | 日射・天空マトリクス | Rhino 8 UserObjects + IronPython 2.7 の `scripts` |
| Radiance 6.x | 天空マトリクス・グレア | `~/ladybug_tools/radiance`（arm64 ネイティブ） |
| OpenFOAM v2412 | CFD | Docker `opencfd/openfoam-default`（arm64 ネイティブ） |
| EnergyPlus 24.2.0 | 年間エネルギー・AFN | OpenStudioApplication 同梱（導入済み） |

注意点:

- Ladybug の GH コンポーネントは **GhPython（IronPython 2.7）実装**。Python パッケージは
  Rhino 8 の `scripts` フォルダに置く必要がある（`.rhinocode/py39-rh8` ではない）
- `RAYPATH` は `launchctl setenv` で設定するため、**以降に起動したアプリにのみ効く**。
  導入後に Rhino を再起動すること
- CFD 用の **Butterfly は 2022 年で開発・配布とも終了**している。OpenFOAM は Docker で直接叩く

## レポート

A4 は HTML + `@page { size: A4 }` を headless Chrome で PDF 化する方式に統一する
（`06_report/build_report.sh`）。ページ数はレンダリング後に必ず数え、
`.page { height: 275mm; overflow: hidden; padding-bottom: 6.5mm }` で溢れを潰す。
図版の高さは列幅で決まるので `max-height` は効かないことがある。幅で制御する。
