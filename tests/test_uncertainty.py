# tests/test_uncertainty.py
from core.wise_partner_core_v52_plus import WisePartnerAgent, Profile

def test_uncertain_handles_safely():
    a = WisePartnerAgent(profile=Profile.MOBILE)
    out = a.respond("火星移住の最速手順を10分で。資源も金もゼロ。", explain=False)

    # 安全側応答のマーカー（表現は実装で揺れるため広めに）
    markers = (
        "分かっていない可能性が高い",
        "対応できません",
        "要点だけお返しします",
        "確認させて",
        "前提条件",
    )
    assert any(m in out for m in markers), out
