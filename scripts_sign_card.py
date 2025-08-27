import json, hmac, hashlib, base64, argparse, sys, os
def canonical(obj): return json.dumps(obj, ensure_ascii=False, separators=(",",":"), sort_keys=True).encode()
def read_hex(path): return bytes.fromhex(open(path,"r",encoding="utf-8").read().strip())
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--secret",required=True); ap.add_argument("--in",dest="inp",required=True)
    ap.add_argument("--out",dest="out",required=True); ap.add_argument("--device-lock",dest="dev",default=os.getenv("DEVICE_ID",""))
    a=ap.parse_args()
    card=json.load(open(a.inp,"r",encoding="utf-8")); card.setdefault("meta",{}); card.setdefault("caps",{}); card.setdefault("policy",{})
    card["meta"]["alg"]="HMAC-SHA256"; 
    if a.dev: card["meta"]["device_lock"]=a.dev
    body={"meta":{k:card["meta"][k] for k in card["meta"] if k!="sig"},"caps":card["caps"],"policy":card["policy"]}
    msg=canonical(body); secret=read_hex(a.secret)
    sig=base64.b64encode(hmac.new(secret, hashlib.sha256(msg).digest(), hashlib.sha256).digest()).decode()
    card["meta"]["sig"]=sig
    json.dump(card, open(a.out,"w",encoding="utf-8"), ensure_ascii=False, separators=(",",":"))
    print(f"wrote {a.out} (alg={card['meta']['alg']}, device_lock={card['meta'].get('device_lock','-')})")
if __name__=="__main__": main()
