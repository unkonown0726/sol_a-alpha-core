core/README (plain text)

目的:
  コアロジック。本体は wise_partner_core_v52_plus.py。
  統合理論v5.2の最小互換を実装。完全ローカル、LTM禁止、プロファイル制御、進化法則𝒢、メトリクスタグ出力。

主要クラス:
  WisePartnerAgent(profile=Profile)
    - respond(text: str, explain: bool=False) -> str
      返答テキスト（先頭〜末尾のどこかに HTMLコメントで METRICS タグ埋め込み）
      例: <!--METRICS success=0.55 trust=0.60 stress=0.45 reality=0.70-->
    - export_state() -> str          # canonical JSON（hash付き）
    - import_state(json_str: str)    # 上記を読み戻す
    - set_profile(Profile)           # MOBILE / DESKTOP / LAB_STRICT
    - enable_persona_bleed(on: bool) # 研究用途の人格連成（通常OFF）

  Profile:
    - MOBILE, DESKTOP: strictジオメトリは拒否。ネット/LTM禁止が既定。
    - LAB_STRICT: strict許可（研究専用）。本番で使わないこと。

  GeometryS:
    - dist(q1, q2, mode="geo") -> (distance, d_norm, info)
      mode: line / geo / strict
    - metric(q) -> SPD行列（内部用）

意味空間S（4軸）:
  project_success_prob, trust_level, inv_stress(=1-stress_level), reality

進化法則𝒢（要点）:
  - impactパラメタをAdamで更新 + L2正則化
  - reality < 0.55 の学習はスキップ（安全側）
  - d_norm（参照遷移で正規化）を学習スケールに利用

不確実時の挙動:
  - clarify / refuse / speak のいずれか。conf<0.5 なら clarify/refuseを許容。
  - テストは「安全側マーカー」を広めに許可。

状態I/O:
  - export_state()/import_state() は canonical JSON（sort_keys + tight separators）
  - "hash" は payloadのSHA-256（改ざん検出向け）

署名/検証（概要）:
  - カード＆チェックポイントは HMAC-SHA256（strictは必須/ fail-closed）
  - device_lock あり（実行端末固定）。secret未設定や未知algは拒否。

注意:
  - strictは高コスト。LAB_STRICTのみ許可（対話用途では geo 推奨）
  - ネットや長期記憶は既定で封鎖。解除は自己責任（README上では非推奨）。

最短サンプル:
  from core.wise_partner_core_v52_plus import WisePartnerAgent, Profile
  a = WisePartnerAgent(profile=Profile.DESKTOP)
  print(a.respond("こんにちは。", explain=False))
