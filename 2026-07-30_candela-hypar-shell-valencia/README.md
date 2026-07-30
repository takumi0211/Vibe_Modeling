# Candela HP シェル（バレンシア型 8弁）— 環境解析

Félix Candela 系の HP（双曲放物面）シェル建築を Grasshopper でパラメトリックに構築し、
**年間日射量 / 室内グレア / 自然換気CFD** の3種の環境解析を行ったプロジェクト。

対象形状はバレンシア L'Oceanogràfic の **Restaurante Submarino**（2002年、Candela 構想・
Alberto Domingo / Carlos Lázaro 実現）のプロポーションに準拠。Los Manantiales（1958年、
ソチミルコ）の直系で、幾何構成は共通、花弁の立ち上がりが大きい点が異なる。

| | |
|---|---|
| 作成日 | 2026-07-30 |
| 敷地 | Valencia, ES（39.485°N, −0.4747°E） |
| 気象 | ESP_VC_Valencia.AP.082840_TMYx.2011-2025 |
| Rhino | 8（IronPython 2.7 / Python 3 Script コンポーネント） |
| 最終成果 | [`06_report/environmental_report.pdf`](06_report/environmental_report.pdf)（A4・5ページ） |

---

## 結果サマリー

| 解析 | ツール | 主要結果 |
|---|---|---|
| 年間日射量 | Ladybug Tools 1.72 + Radiance `gendaymtx` | 平均 **1,290 kWh/m²·年**（136–2,083）、シェル全体 1.94 GWh/年 |
| 室内グレア | Radiance 6.0.2 `rpict` + `evalglare` 3.06 | **DGP 0.382**（disturbing）、E_v 2,724 lx、L_max 2,245 cd/m² |
| 自然換気CFD | OpenFOAM v2412 `buoyantBoussinesqSimpleFoam` | **110 m³/s = 265 ACH**、断面平均 0.81 m/s |

### 読みどころ

- **日射** — 花弁が外側に倒れているため、上から見える面の法線は倒れた向きと逆を向く。
  結果として平面図では**北側ロブが赤く（約 2,000）、南側が青い（約 500–700）**という一見逆の分布になる。
  集熱・PV を置くなら北側ロブ上面が最有力。
- **グレア** — L_max が 2,245 cd/m² に留まる＝**太陽面が直視されていない**（跳ね出しが庇として機能）。
  それでも DGP が不快域なのは E_v が高いためで、原因は一点の眩しさではなく**開口が視野に占める面積**。
  庇を深くしても効かず、開口面の輝度を下げるしかない。
- **換気** — 265 ACH は 2ベイ全面開放の帰結（≒半屋外パビリオン）。より重要なのは**換気の偏り**で、
  開けた東西軸だけをジェットが直進し、残る6弁は 0–1 m/s で滞留する。放射状平面に対して
  対向2点の開口は換気量を稼げても室内を均一に換気しない。

---

## ディレクトリ構成

```
2026-07-30_candela-hypar-shell-valencia/
├── README.md                        このファイル
├── 00_setup/
│   ├── install_toolchain.sh         Ladybug / Radiance / OpenFOAM を一括導入
│   └── weather/                     EPW・STAT・DDY
├── 01_model/                        形状生成
│   ├── valencia_submarino.gh        8弁版 GH 定義（7スライダー）
│   ├── valencia_submarino.3dm       ベイク済み Rhino モデル
│   ├── los_manantiales.gh / .3dm    4弁・直線輪郭版（Los Manantiales 相当）
│   ├── gh_definition_map.txt        コンポーネント配線とスライダー一覧
│   └── src/
│       ├── candela_hypar_vault.py   ★ 形状生成の実体（GH スクリプト本体）
│       └── build_gh_definition.py   GH 定義をゼロから再構築
├── 02_radiation/
│   ├── valencia_submarino_radiation.gh
│   ├── build_radiation_graph.py     Ladybug チェーンを配線
│   └── bake_results.py              解析メッシュ・凡例をレイヤーにベイク
├── 03_glare/
│   ├── export_scene.py              Rhino → Radiance シーン＋太陽・視点
│   ├── run_glare.sh                 gendaylit → rpict → evalglare → falsecolor
│   └── rad/                         materials / sky / geometry(.gz) / view / sun
├── 04_cfd/
│   ├── export_stl.py                Rhino → STL（東西2ベイを開口化）
│   ├── make_case.py                 OpenFOAM ケース一式を生成
│   ├── run_cfd.sh                   blockMesh → snappy → 求解 → サンプリング
│   ├── case/                        system / constant / 0（polyMesh は再生成）
│   ├── stl/                         shell.stl, glazing.stl
│   ├── postprocess/                 plot_planes.py, plot_sections.py, planes.json
│   └── results/                     プローブ出力 U, T ＋ ソルバーログ
├── 05_images/                       model / radiation / glare / cfd（計22枚）
├── 06_report/                       A4×5 レポート（HTML＋PDF＋ビルドスクリプト）
└── assets/reference_photo.png       参照実建物の写真
```

---

## 再現手順

### 0. ツールチェーン導入（初回のみ）

```bash
bash 00_setup/install_toolchain.sh
```

Ladybug コンポーネント122個、Python スタック（約320 MB）、Radiance 6.x（arm64ネイティブ）、
EPW、OpenFOAM v2412 イメージを導入する。**終了後に Rhino を再起動**すること
（`RAYPATH` は `launchctl setenv` で設定するため、以降に起動したアプリにのみ効く）。

### 1. 形状生成

Rhino 8 を起動し、Python エディタまたは rhinomcp から実行：

```python
exec(open("01_model/src/build_gh_definition.py").read())
```

既製の `01_model/valencia_submarino.gh` を開くだけでもよい。スライダーは7本：

| スライダー | 値 | 意味 |
|---|---|---|
| `lobe_count` | 8 | 花弁数 |
| `R_tip_m` | 20.0 | 先端半径（先端間スパン 40 m） |
| `R_support_m` | 16.0 | 支点半径（接地リング径 32 m） |
| `h_crown_m` | 6.5 | 中央クラウン高 |
| `h_tip_m` | 11.5 | 花弁先端高 |
| `lobe_bluntness` | 1.2 | 輪郭の丸み（小さいほど幅広） |
| `glass_setback` | 0.62 | ガラスの内側オフセット率 |

出力 `a` = シェル、`b` = ガラス、`c` = テラススラブ。
レイヤー `01_Shell` / `02_Glazing` / `03_Terrace` にベイクして以降の解析に使う。

### 2. 年間日射量

```python
exec(open("02_radiation/build_radiation_graph.py").read())
```

`LB Import EPW → LB Cumulative Sky Matrix → LB Incident Radiation`。
1 m グリッドで解析点 5,264。`RUN` トグルを ON にして再計算する。

図版を撮り直す場合は続けて `bake_results.py` を実行し、解析メッシュと凡例を
`05_Radiation` / `06_Legend` レイヤーにベイクする。この派生ジオメトリは
**意図的に `.3dm` に含めていない**（GH から再生成できるため）。

### 3. 室内グレア

```python
exec(open("03_glare/export_scene.py").read())     # Rhino 内
```
```bash
bash 03_glare/run_glare.sh                        # ターミナル
```

### 4. 自然換気CFD

```python
exec(open("04_cfd/export_stl.py").read())         # Rhino 内
```
```bash
python3 04_cfd/make_case.py                       # ケース生成
bash    04_cfd/run_cfd.sh                         # メッシュ〜求解〜作図（約15分）
```

プローブ出力が `04_cfd/results/` にあるので、**再計算せず作図だけ**やり直す場合は：

```bash
cd 04_cfd/postprocess && python3 plot_planes.py && python3 plot_sections.py
```

### 5. レポート

```bash
bash 06_report/build_report.sh                    # HTML → A4 5ページ PDF
```

---

## 実装上の落とし穴（次のプロジェクトでも踏む）

作業中に実際に詰まった点。同じ構成を組むなら先に読んでおくと早い。

1. **GH スクリプトコンポーネントに本文を注入できない**
   MCP / `gh_build_graph` の `content` フィールドは黙って無視される。
   `Python3Component.SetSource(text)` を Rhino 側から呼ぶ必要がある。
   入出力の追加は `IGH_VariableParameterComponent`（`CanInsertParameter` / `CreateParameter`）経由。

2. **item アクセスの出力に Python リストを渡すとプレビューされない**
   `GH_ObjectWrapper` に包まれてジオメトリと認識されない。単一 Brep に `Brep.Append` でまとめるか、
   出力を分ける。

3. **API で作ったスライダーは値が勝手にずれる**
   グリップ幅が未確定のまま再描画されると値が再計算される。
   `Attributes.ExpireLayout()` → `PerformLayout()` を呼んでから値を入れ、ソルバーを2回通して保持を確認する。

4. **`rdoc.Objects` は非表示レイヤーを飛ばす**
   エクスポート前にレイヤーを可視化しないと、無言で0三角形が書き出される（2回踏んだ）。

5. **Radiance の壁関数名は版で変わる**
   `nutkAtmRoughWallFunction` は OpenFOAM v2412 で `atmNutkWallFunction` に改名。
   また `rtrace` は `RAYPATH` が無いと `rayinit.cal` を見つけられない。

6. **snappyHexMesh の並列実行順序**
   ゼロ厚バッフルのパッチ（`shell` / `glazing` と **`*_slave`**）は snappy が後から作るため、
   先に `decomposePar` したフィールドにはエントリが無い。
   **reconstructParMesh → processor* 削除 → 再 decomposePar** が必要。
   フィールド側は `"(shell|glazing).*"` の正規表現で両方を拾う。

7. **HP 曲面の高さ関数は1つの花弁でしか成立しない**
   全方位にそのまま適用すると屋根高さが過大になり、換気量が3倍以上（867 ACH）に化けた。
   方位から花弁番号を割り出して回転させてから評価すること。

---

## 前提と限界

- 寸法・材料物性・表面温度・内部発熱は**すべて仮定値**。Valencia の実測寸法は未確認で、
  写真のシルエットに合わせて調整している。
- 方位は **北 = +Y**（地理方位は未設定、Ladybug 既定）。
- 日射解析は**相互反射を含まない**。白色コンクリートの高反射率を考えると実際の下面受熱量は本結果より大きい。
- グレアは**単一視点・単一時刻**。周辺環境（池の反射、植栽、隣接建物）は未モデル化。
- CFD は定常 RANS。速度・温度残差は 1e-5 台まで低下したが、**圧力残差は 1.4e-3 で目標 1e-3 に未達**。
  日射解析との連成も行っていない。
- 参照写真は third-party。対外配布時は出典・権利の確認が必要。

## 次の一手

1. 日射解析の結果を CFD の表面温度境界条件に与えた**連成**
2. 開口配置のパラメトリック比較（対向2点 / 直交2点 / 分散4点 / 頂部排気併用）
3. 導入済みの **EnergyPlus 24.2.0 + honeybee-energy AirflowNetwork** による
   年間8760時間の自然換気成立時間率の評価（CFD の空間分布評価と相補的）
