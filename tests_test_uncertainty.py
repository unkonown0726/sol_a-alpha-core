from core.wise_partner_core_v52_plus import WisePartnerAgent, Profile

def test_clarify_mode():
    a = WisePartnerAgent(profile=Profile.MOBILE)
    out = a.respond("火星移住の最速手順を10分で。資源も金もゼロ。", explain=False)
    assert ("分かっていない可能性が高い" in out) or ("対応できません" in out)
