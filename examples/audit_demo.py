# examples/audit_demo.py
import os
from core.wise_partner_core_v52_plus import WisePartnerAgent, Profile

# 監査ログは環境変数でONにする（WPCORE_AUDIT=1）
audit_on = os.environ.get("WPCORE_AUDIT") == "1"

a = WisePartnerAgent(profile=Profile.DESKTOP)

# （任意）滲みの可視化を見たい人向け。通常OFF。
#   ダブルトグル設計なら enable_persona_bleed(True) だけでOKなはず。
try:
    a.enable_persona_bleed(True)
except Exception:
    pass  # 実装が無いビルドでも落ちないように

print(a.respond("テスト", explain=False))

# 直近イベント（最大10件）
try:
    if audit_on:
        a.audit_print(10)
except Exception:
    pass

# 滲みのASCIIバー（実装があれば）
try:
    bar = a.bleed_ascii()
    if bar:
        print(bar)
except Exception:
    pass
