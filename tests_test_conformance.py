from core.wise_partner_core_v52_plus import GeometryS, WisePartnerAgent, Profile

def test_spd():
    # g が対称正定（各方向の二次形式が正）
    for q in (
        {"project_success_prob":0.0,"trust_level":0.0,"stress_level":1.0,"reality":0.0},
        {"project_success_prob":1.0,"trust_level":1.0,"stress_level":0.0,"reality":1.0},
        {"project_success_prob":0.2,"trust_level":0.9,"stress_level":0.7,"reality":0.4},
    ):
        g = GeometryS.metric(q)
        for v in ([1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1],[0.3,-0.7,0.2,0.1]):
            qf = sum(v[i]*g[i][j]*v[j] for i in range(4) for j in range(4))
            assert qf > 0

def test_g_reality_gate():
    a = WisePartnerAgent(profile=Profile.DESKTOP)
    key = "respond_helpfully|be_kind"
    before = dict(a.state.user_wellbeing.__dict__)
    after = {**before, "reality": 0.40}  # 低 reality→学習スキップ想定
    a._g_update_links(key, before, after, 0.1, ["project_success_prob","trust_level","stress_level","reality"])
    # 影響が暴走していない（ゲートで抑止）ことだけ確認
    for met, (imp, conf) in a.state.world_model.links[key].items():
        assert abs(imp) <= 0.2  # クリップ域内
