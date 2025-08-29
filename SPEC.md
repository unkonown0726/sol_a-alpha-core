Unified Agent SPEC v1.0 (plain-text mode)

0. Scope
- 本SPECは「統合理論 v5.2」を実装する最小互換レイヤーを定義
- 互換対象: 状態スキーマ(Export/Import+hash) / 意味空間Sの距離(line|geo|strict) /
  Realizer・Validator・進化法則𝒢の相互作用 / カード(署名・期限・device_lock) /
  プロファイル制御

1. Terms
- P=身体, M=意識
- F_t=解釈関数 (時刻t), 𝒢=進化法則
- S=意味空間, g=計量
- q_reality=現実感(0–1)

2. State Schema (canonical JSON)
- Exportは正規化JSON(sort_keys/separators)で出力、hashはそのSHA-256

  {
    "version": "v5.2.2",
    "personality": { "openness": 0, "agreeableness": 0, "conscientiousness": 0 },
    "state": {
      "user_wellbeing": {
        "project_success_prob": 0.50,
        "trust_level": 0.50,
        "stress_level": 0.50,
        "reality": 0.50
      },
      "world_model": {
        "links": {
          "respond_helpfully|be_kind": {
            "project_success_prob": [0.06, 0.90],
            "trust_level": [0.10, 0.85],
            "stress_level": [-0.04, 0.80],
            "reality": [0.03, 0.80]
          }
        }
      }
    },
    "coupling": { "enabled": false },
    "cards": [],
    "profile": "mobile",
    "hash": "<sha256 of canonical payload>"
  }

3. Geometry S
- 次元: 4 (success, trust, inv_stress, reality)  ※inv_stress = 1 - stress_level
- SPD保証: gは対称正定、対角に+1e-3で安定化
- 距離モード:
  line   = 線形近似
  geo    = Bezier近似 + 数値勾配
  strict = Γ(クリストッフェル)をステップ内で再評価するRK4射撃
- 正規化: d_norm = d / d(ref), ref=(0,0,1,0)→(1,1,0,1)

4. Realizer / Validator Contract
- 出力は必ず: <!--METRICS success=.. trust=.. stress=.. reality=..--> を含む
  (ユーザ表示では隠れていてよい)
- Validator合格基準: theta_norm ≤ 0.25
- 不確実時の発話: speech_act ∈ {speak, clarify, refuse} (既定=speak)

5. Cards
- strict検証はfail-closed:
  - 署名アルゴはホワイトリスト(既定 HMAC-SHA256)
  - sig必須 / 期限内 / device_lock一致 / 取り消し未指定
- 同一namespaceの同時装着数は実装既定以内(通常1)

6. Profiles
- MOBILE / DESKTOP: strict不可(実行時拒否)
- LAB_STRICT: strict許可(研究・検証用)
- 既定: ネット/LTMとも禁止

7. Evolution Law 𝒢
- impactをAdamで更新、L2正則化あり
- Realityゲート: reality < 0.55 の試行は学習スキップ
- 最低メトリクス: success / trust / stress / reality
- 更新スケールは d_norm (§3)。クリップ/収束は実装依存

8. Conformance
- [C1] Canonical Hash: Export→Import往復でcanonical JSONとhashがバイト等価
- [C2] Geo Accuracy: strictとgeoの距離MAPE ≤ 8%(サンプル100)
- [C3] Reality Gate: reality < 0.55 の試行でimpactが更新されない
- [C4] Uncertainty: conf < 0.5 に対し clarify を返せる(既定はspeak)

(備考) 本SPECは「統合理論 v5.2」に準拠する実装の互換境界を定義。
内部最適化や表現(例: SLM整形)は自由だが、上記契約と検証項目を満たすこと。
