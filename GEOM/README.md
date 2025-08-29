GEOM/README (plain text)

目的:
  -  意味空間 S(4軸) の「距離」を計算するモジュール。対話の安定性と 𝒢(進化法則) の学習スケールに直結。
   - 3モード: line / geo / strict

前提となる4軸（qの成分）:
  -  project_success_prob, trust_level, stress_level, reality   ※ すべて 0..1
   - 内部では inv_stress = 1 - stress_level を使う（低いほど良い方向に揃えるため）

最短クイックスタート:
  -  from core.wise_partner_core_v52_plus import GeometryS
  -  q1 = {"project_success_prob":0.4,"trust_level":0.5,"stress_level":0.6,"reality":0.7}
  -  q2 = {"project_success_prob":0.6,"trust_level":0.7,"stress_level":0.4,"reality":0.8}
  -  d, d_norm, info = GeometryS.dist(q1, q2, mode="geo")<br>
  ※d: 距離、d_norm: 正規化距離、info: デバッグ情報（実験向け。スキーマに依存しないこと）

モード概要（何をいつ使う？）:
  -  line  : 線形近似の速いやつ。粗いが超軽量。スクリーニングやUI反応を滑らかにしたい時。
   - geo   : ベジェ近似 + 数値勾配。速度/精度のバランスが良く、対話の既定。まずこれ。
  -  strict: 研究用の厳密寄り。Γ(クリストッフェル)をサブステップごとに再計算するRK4射撃法。<br>
         ※Profile.LAB_STRICT のみ有効。本番UIでは使わないで（重い）。

d_norm（正規化距離）とは:
  -  素の距離 d を「参照遷移」の距離で割ってスケールを揃えたもの。
   - 参照: (success,trust,inv_stress,reality) = (0,0,1,0) → (1,1,0,1)
   - 𝒢の学習レート計算や閾値判断は d_norm を使う前提。

strict の中身（数式少なめ版）:
  - 状態: 位置 x(3次元に埋め込んだ座標) と速度 v の6次元ベクトル
  - 計量 g(q) は SPD（対角に +1e-3 して数値安定化）
  - Γ(クリストッフェル) を「ステップの途中点でも」再評価して RK4（4次のRunge–Kutta）で積分
  - “射撃法”: 初期速度を調整して目標へ撃ち込む。誤差が閾値以下なら命中→距離確定
  - だから重い。だから研究専用。

精度期待値（SPEC準拠）:
   - geo vs strict の距離の MAPE（平均絶対百分率誤差） ≤ 8%（サンプル100）<br>
  → 実機では bench/acc_geo_vs_strict.py を実行して確認できる

返り値:
   - (d: float, d_norm: float, info: dict)
  -  info は実装内のデバッグ用（例: mode, steps, iters, converged 等が入ることがある）。
  -  将来変わる可能性があるのでキーに依存しないこと。研究ノート向け。

よくある落とし穴:
  - LAB_STRICT 以外のプロファイルで strict を呼ぶ → RuntimeError（仕様どおり拒否）
  - q の値域が 0..1 を外れている → 距離が暴れる。入出力アダプタで正規化してから渡す
  - strict が収束しない → steps/iters/tol を緩める or 初期速度推定を増やす（実装の定数を調整）
  - 距離が毎回違う → それ、simulate系(別所)の乱数。GEOMの距離は決定的（RNGを使わない）

性能ノブ（重いと感じたら）:
  - 対話は基本 mode="geo" 固定。strict はオフライン検証や図表作成に限定
  - bench/speed_strict.py で1対の計算時間を把握してから steps/iters を決める
  - エージェント側で「距離評価の頻度」を落とす（全フレームで測らない）

テストとベンチ（ローカルで実行）:
  -  PYTHONPATH=. python bench/speed_strict.py
  -  PYTHONPATH=. python bench/acc_geo_vs_strict.py
  -  PYTHONPATH=. pytest -q tests/test_conformance.py

FAQ（超短縮）:<br>

  Q. strict で“Γを中で再評価”って必要？<br>
  A. 必要。評価しないとRK4の利点が死に、収束が悪化する（ここは修正済み）。<br>

  Q. d_norm と d、どっちをログる？<br>
  A. 学習や比較には d_norm。生データのレポートには d も併記すると親切。<br>

  Q. 実装を速くしたい<br>
  A. まず geo を使う。strictの高速化は“数値解析の沼”なので bench を回してから判断。<br>

最後に:
   - GEOMは「距離の黒子」。ユーザーには見せないが、学習と安定性の土台になる。
  -  迷ったら mode="geo"、重い処理はオフライン strict、これでだいたい勝てる。
