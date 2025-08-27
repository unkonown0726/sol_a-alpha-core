import json, os, sys
from core.wise_partner_core_v52_plus import WisePartnerAgent, Profile, load_card_from_json_str
def read_hex(p): return bytes.fromhex(open(p,"r",encoding="utf-8").read().strip())
def main():
    if len(sys.argv)<2: 
        print("Usage: python scripts/run_strict.py <signed_card.json>"); sys.exit(2)
    home=os.path.expanduser("~"); base=os.getenv("SOLA_HOME", os.path.join(home,".sola"))
    card_secret=read_hex(os.path.join(base,"card_secret.hex")); ck_secret=read_hex(os.path.join(base,"ck_secret.hex"))
    prof = Profile.LAB_STRICT if os.getenv("WPCORE_STRICT","0")=="1" else Profile.DESKTOP
    agent=WisePartnerAgent(seed=7, card_secret=card_secret, ck_secret=ck_secret, profile=prof)
    signed=open(sys.argv[1],"r",encoding="utf-8").read()
    print("card strict-activate:", agent.cards_activate(load_card_from_json_str(signed), mode="strict"))
    print(agent.respond("テストです。調子はどう？", explain=True, metric_mode=("strict" if prof==Profile.LAB_STRICT else "geo")))
    ck=agent.checkpoint("manual"); print("checkpoint signed:", agent.last_checkpoint_ok())
if __name__=="__main__": main()
