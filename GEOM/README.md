GEOM/README (plain text)

目的:
  意味空間Sの距離計算モジュール。geometry_strict.py を含む。
  3モード: line / geo / strict

各モードの概要:
  line   : 線形近似の速い距離（おおまかな評価）
  geo    : Bezier近似 + 数値勾配。速度/精度バランス。対話での既定。
  strict : 研究用の厳密寄り。Γ(クリストッフェル)をステップ内で再計算するRK4射撃法。
           steps多めで高コスト。LAB_STRICTでのみ使用可能。

実装メモ（strict）:
  - rk4_step内で unembed→christoffel を各サブステップ再評価（収束性向上）
  - 3次元座標 + 速度の6D状態を射撃。誤差が閾値以下で命中判定。
  - SPD安定化のため計量対角へ +1e-3 を加算（数値安定）

正規化距離:
  d_norm = d / d(ref)  ; ref = (0,0,1,0) → (1,1,0,1)

精度要件（SPEC準拠）:
  geo vs strict の距離 MAPE ≤ 8%（サンプル100）

性能ヒント:
  - strictの steps/iters は重い。bench/ を参照してTATと相談。
  - 対話実用は geo で十分。strictはオフライン検証・論文図表用。

テスト/ベンチ:
  - tests/test_conformance.py … SPD/ゲート動作
  - bench/acc_geo_vs_strict.py … 近似誤差
  - bench/speed_strict.py … 速度
