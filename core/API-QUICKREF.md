API QUICK REF (core)  v5.2.2

目的:
  WisePartnerAgent を最短で使うための最小APIメモ。
  迷ったら API-DETAILS.md を読む。

インポート:
    from core.wise_partner_core_v52_plus import WisePartnerAgent, Profile, GeometryS

エージェント生成:
    a = WisePartnerAgent(profile=Profile.DESKTOP)
    # Profiles:
    #   MOBILE / DESKTOP : strict不可（既定、ネット/LTM OFF）
    #   LAB_STRICT       : 研究専用。strict許可（本番禁止）

応答を得る:
    text = a.respond("こんにちは。計画を3つに分けて。", explain=False)
    # explain=True で内部の思考ログ（可視化用）も含める

METRICSタグ（契約）:
  返答のどこかにHTMLコメント形式で埋め込まれる:
    <!--METRICS success=0.55 trust=0.60 stress=0.45 reality=0.70-->
  * 値は 0..1。ログ/可視化はここから機械抽出する。

永続人格（状態I/O）:<br>

    s = a.export_state()     # canonical JSON（"hash"付き）
    a.import_state(s)        # バイト等価に復元。hash不一致は例外

距離関数（意味空間Sの距離）:<br>

    q1 = {"project_success_prob":0.4,"trust_level":0.5,"stress_level":0.6,"reality":0.7}
    q2 = {"project_success_prob":0.6,"trust_level":0.7,"stress_level":0.4,"reality":0.8}
    d, d_norm, info = GeometryS.dist(q1, q2, mode="geo")
    # mode: line / geo(既定) / strict(研究用/LAB_STRICTのみ)
    # d_norm は参照遷移で正規化した距離。学習や閾値は d_norm を使う前提。

外部KPIで学習させる（任意）:<br>

    from core.reward_bridge import RewardBridge
    rb = RewardBridge(a)
    before = {"project_success_prob":0.40,"trust_level":0.45,"stress_level":0.60,"reality":0.65}
    after  = {"project_success_prob":0.55,"trust_level":0.60,"stress_level":0.45,"reality":0.72}
    rb.report("todo_plan", before, after)
    # reality<0.55 のデータは 𝒢 のゲートで自動スキップ（安全側）

エラー/落ち方（ざっくり）:
  - Profile が strict非対応なのに strict 要求 → RuntimeError
  - 署名/検証失敗（strict時, secret未設定/署名不正/期限切れ等） → RuntimeError（fail-closed）
  - import_state の hash 不一致 → ValueError
  - 入力が曖昧/危険 → clarify/refuse系の安全返答にフォールバック（例外は投げない）

スレッド/プロセス:
  - 状態を持つので並列はプロセス分離推奨。
  - プロセス間の移送は export_state / import_state でOK。

実運用ノート:
  - 対話は mode="geo" 固定で十分。strictはオフライン検証用。
  - ネット/LTMは既定でOFF。どうしても必要なら自己責任で拡張。

終わり。
