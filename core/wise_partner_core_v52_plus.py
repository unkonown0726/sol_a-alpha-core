# -*- coding: utf-8 -*-
"""
wise_partner_core_v52_plus.py — 完全版（v5.2.2 “監査ログ＆滲みダッシュボード付き”）
- v5.2.1 からの追加:
  * 監査ログ(AUDIT): WPCORE_AUDIT=1 で有効。リングバッファ/JSON取得/簡易出力
  * カードの自動デキュー/有効化/拒否をイベント記録（研究モード含む）
  * respond() の conf/d_norm/speech_act をイベント記録
  * 滲み(bleed)ダッシュボード: 現在の残存影響を集計（指数減衰考慮）＆ASCIIバー表示
- 既存の安全/署名/strict/𝒢/“分からないと言う” 等はそのまま
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Literal, Set, Tuple, Callable
from datetime import datetime, timezone, timedelta
import math, random, time, json, re, hashlib, hmac, base64, os

# ====== 監査（ONにするとログが貯まる。既定OFF） ======
class _Audit:
    def __init__(self, enabled: bool=False, cap: int=1000):
        self.enabled = bool(enabled)
        self.cap = cap
        self.buf: List[Dict[str,Any]] = []
    def emit(self, etype: str, **data):
        if not self.enabled: return
        ev = {"ts": time.time(), "type": etype, **data}
        self.buf.append(ev)
        if len(self.buf) > self.cap:
            self.buf = self.buf[-self.cap:]
    def tail(self, n: int=50) -> List[Dict[str,Any]]:
        return self.buf[-n:]
    def as_json(self, n: Optional[int]=None) -> str:
        arr = self.buf if (n is None) else self.tail(n)
        return json.dumps(arr, ensure_ascii=False, separators=(",",":"))
    def print_tail(self, n: int=20):
        for e in self.tail(n):
            t = datetime.utcfromtimestamp(e["ts"]).strftime("%H:%M:%S")
            print(f"[{t}] {e['type']}: { {k:v for k,v in e.items() if k not in ('type','ts')} }")

# ===== strict 幾何（存在すれば使用） =====
try:
    from GEOM.geometry_strict import dist_strict as _strict_dist  # type: ignore
    _STRICT_GEOM_OK = True
except Exception:
    _STRICT_GEOM_OK = False

# ===== プロファイル/フラグ =====
class Profile:
    MOBILE = "mobile"
    DESKTOP = "desktop"
    LAB_STRICT = "lab_strict"

class Flags:
    NET_ALLOWED = False
    LTM_ALLOWED = False

# ===== Config =====
class _Cfg:
    RESEARCH_MODE = (os.getenv("WPCORE_RESEARCH", "0") == "1")
    NS_LIMIT_DEFAULT = 3 if RESEARCH_MODE else 1
    TOTAL_BIAS_CAP = 0.15
    PERSONA_BLEED_CAP = 0.006 if RESEARCH_MODE else 0.002
    PERSONA_BLEED_ENABLED_DEFAULT = (os.getenv("WPCORE_BLEED", "0") == "1")
    AUDIT_ENABLED = (os.getenv("WPCORE_AUDIT","0") == "1")

# ===== ユーティリティ =====
def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'), sort_keys=True).encode('utf-8')

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

# --- 署名アルゴ：暗号アジリティ ---
class SigAlg:
    name = "NONE"
    def sign(self, secret: Optional[bytes], msg: bytes) -> str: return ""
    def verify(self, secret: Optional[bytes], msg: bytes, sig_b64: str) -> bool: return True

class HMAC_SHA256(SigAlg):
    name = "HMAC-SHA256"
    def sign(self, secret, msg):
        if not secret: return ""
        return base64.b64encode(hmac.new(secret, msg, digestmod='sha256').digest()).decode('ascii')
    def verify(self, secret, msg, sig_b64):
        if not secret: return True  # lenient互換。strict側でfail-closed
        try:
            want = hmac.new(secret, msg, digestmod='sha256').digest()
            got  = base64.b64decode(sig_b64 or "")
            return hmac.compare_digest(want, got)
        except Exception:
            return False

SIG_ALGS = { a.name: a for a in [HMAC_SHA256()] }

def sig_verify(alg: str, secret: Optional[bytes], msg: bytes, sig: str) -> bool:
    impl = SIG_ALGS.get((alg or "").upper())
    return impl.verify(secret, msg, sig) if impl else False

def sig_sign(alg: str, secret: Optional[bytes], msg: bytes) -> str:
    impl = SIG_ALGS.get((alg or "").upper())
    return impl.sign(secret, msg) if impl else ""

# --- 旧互換（内部用） ---
def hmac_sign(secret: Optional[bytes], msg: bytes) -> str:
    return sig_sign("HMAC-SHA256", secret, msg)
def hmac_verify(secret: Optional[bytes], msg: bytes, sig_b64: str) -> bool:
    return sig_verify("HMAC-SHA256", secret, msg, sig_b64)

_ISO_RX = re.compile(r'^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?(Z|[+\-]\d{2}:\d{2})?$')

def parse_iso8601(s: str) -> datetime:
    m = _ISO_RX.match(s.strip())
    if not m: raise ValueError(f"Bad ISO-8601: {s}")
    y,mo,d,hh,mm,ss,sub,off = m.groups()
    dt = datetime(int(y), int(mo), int(d), int(hh), int(mm), int(ss), int((sub or '0').ljust(6,'0')))
    if not off or off == 'Z':
        return dt.replace(tzinfo=timezone.utc)
    sign = 1 if off[0] == '+' else -1
    oh, om = int(off[1:3]), int(off[4:6])
    return dt.replace(tzinfo=timezone(timedelta(minutes=sign*(oh*60+om))))

def now_iso() -> str:
    return datetime.utcnow().replace(tzinfo=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

# ===== スキーマ・マイグレーション =====
SCHEMA_VERSION = "v5.2.2"

def _migrate_v52_to_v521(d: dict) -> dict:
    try:
        uw = d["state"]["user_wellbeing"]
        uw.setdefault("reality", 0.5)
        d["version"] = "v5.2.1"
        return d
    except Exception:
        return d

def _migrate_v521_to_v522(d: dict) -> dict:
    # v5.2.2 形式への軽微移行（実質 version 番号のみ）
    d["version"] = "v5.2.2"
    return d

_MIGRATIONS = {
    "v5.2": _migrate_v52_to_v521,
    "v5.2.0": _migrate_v52_to_v521,
    "v5.2.1": _migrate_v521_to_v522,
}

# ===== スキーマ =====
@dataclass
class RoleInfluence:
    alpha: float = 0.18
    cap: float = 0.12
    tau_days: int = 21
    epsilon_bleed: float = 0.003
    evidence_level: Literal["A","B","C"] = "B"
    domains: List[str] = field(default_factory=list)
    metric_bias: Dict[str,float] = field(default_factory=dict)

@dataclass
class RoleCardMeta:
    id: str; issuer: str; alg: str; sig: str
    valid_from: str; valid_to: str; revoked: bool; version: str
    parent_hash: Optional[str] = None
    device_lock: Optional[str] = None

@dataclass
class RoleCapabilities:
    apis: List[str]; files: List[str]
    max_tokens: int; max_ms: int
    net_allowed: bool; self_update_allowed: bool

@dataclass
class RolePolicy:
    priority: int; namespace: str
    forbidden: List[str]; research_only: bool
    disclaimer: Optional[str] = None

@dataclass
class PersonCard:
    meta: RoleCardMeta
    caps: RoleCapabilities
    policy: RolePolicy
    manuals: Dict[str,str]
    knowledge_refs: List[str] = field(default_factory=list)
    influence: RoleInfluence = field(default_factory=RoleInfluence)
    nonce: Optional[str] = None

@dataclass
class Personality:
    openness: int = 50
    agreeableness: int = 50
    conscientiousness: int = 50

@dataclass
class Dynamics:
    trait_min: int = -50
    trait_max: int = 100

@dataclass
class UserWellbeing:
    project_success_prob: float = 0.5
    trust_level: float = 0.5
    stress_level: float = 0.5  # 低いほど良い
    reality: float = 0.5

@dataclass
class WorldModel:
    links: Dict[str, Dict[str, Tuple[float,float]]] = field(default_factory=dict)

@dataclass
class Coupling:
    enabled: bool = False

@dataclass
class AgentState:
    user_wellbeing: UserWellbeing = field(default_factory=UserWellbeing)
    world_model: WorldModel = field(default_factory=WorldModel)

# ===== 短期メモリ（LTM禁止） =====
class EphemeralMemory:
    def __init__(self, max_items=64, ttl_s=900):
        self.max_items, self.ttl = max_items, ttl_s
        self.buf: List[Tuple[float,str]] = []
    def add(self, text: str, ts: Optional[float]=None):
        ts = ts or time.time()
        self.buf.append((ts, text)); self._gc()
    def recent(self) -> List[str]:
        self._gc(); return [t for _,t in self.buf]
    def _gc(self):
        now=time.time()
        self.buf = [(ts,t) for ts,t in self.buf if (now-ts)<=self.ttl]
        if len(self.buf)>self.max_items: self.buf=self.buf[-self.max_items:]

# ===== チェックポイント =====
@dataclass
class Checkpoint:
    turn: int
    hash: str
    parent_hash: Optional[str]
    sig: Optional[str]
    created_at: str
    snapshot_meta: Dict[str, Any]

class CheckpointManager:
    def __init__(self, secret: Optional[bytes]=None, cap: int=10, emit: Optional[Callable]=None) -> None:
        self._secret = secret
        self._cap = cap
        self._chain: List[Checkpoint] = []
        self._emit = emit or (lambda *a, **k: None)
    def make(self, payload: Dict[str,Any], turn: int, meta: Dict[str,Any]) -> Checkpoint:
        parent = self._chain[-1].hash if self._chain else None
        doc = {"payload": payload, "parent_hash": parent}
        h = sha256_bytes(canonical_json(doc))
        sig = hmac_sign(self._secret, h.encode('ascii')) if self._secret else None
        ck = Checkpoint(turn=turn, hash=h, parent_hash=parent, sig=sig, created_at=now_iso(), snapshot_meta=meta)
        self._chain.append(ck)
        if len(self._chain) > self._cap: self._chain = self._chain[-self._cap:]
        self._emit("checkpoint_made", turn=turn, hash=h, signed=bool(sig))
        return ck
    def verify(self, idx: int) -> bool:
        if not (0 <= idx < len(self._chain)): return False
        ck = self._chain[idx]
        ok = hmac_verify(self._secret, ck.hash.encode('ascii'), ck.sig or '')
        self._emit("checkpoint_verify", idx=idx, ok=ok)
        return ok
    def last(self) -> Optional[Checkpoint]:
        return self._chain[-1] if self._chain else None

# ===== 幾何 S =====
class GeometryS:
    ORDER = ("project_success_prob","trust_level","stress_level","reality")
    _L_REF_CACHE: Dict[str, float] = {}
    @staticmethod
    def _clip01(x: float) -> float: return max(0.0, min(1.0, x))
    @staticmethod
    def _embed(q: Dict[str,float]) -> List[float]:
        ps = float(q.get("project_success_prob", 0.5))
        tr = float(q.get("trust_level", 0.5))
        inv_st = 1.0 - float(q.get("stress_level", 0.5))
        re = float(q.get("reality", 0.5))
        return [ps, tr, inv_st, re]
    @staticmethod
    def _unembed(v: List[float]) -> Dict[str,float]:
        return {
            "project_success_prob": GeometryS._clip01(v[0]),
            "trust_level": GeometryS._clip01(v[1]),
            "stress_level": GeometryS._clip01(1.0 - v[2]),
            "reality": GeometryS._clip01(v[3])
        }
    @classmethod
    def metric(cls, q: Dict[str,float]) -> List[List[float]]:
        ps, tr, inv_st, re = cls._embed(q)
        A = [
            [1.0 + 0.6*(1-ps),   0.15*(tr-0.5),        0.10*(0.5-inv_st),  0.06*(re-0.5)],
            [0.0,                 1.0 + 0.5*tr,        0.12*(tr-0.5),      0.05*(re-0.5)],
            [0.0,                 0.0,                 1.0 + 0.7*(1-inv_st), 0.04*(0.5-inv_st)],
            [0.0,                 0.0,                 0.0,                 1.0 + 0.4*(re)]
        ]
        n = 4; g = [[0.0]*n for _ in range(n)]
        for i in range(n):
            for j in range(i, n):
                g[i][j] = sum(A[k][i]*A[k][j] for k in range(n)); g[j][i] = g[i][j]
        for i in range(n): g[i][i] += 1e-3
        return g
    @classmethod
    def quad_form(cls, g: List[List[float]], dv: List[float]) -> float:
        n = len(dv); s = 0.0
        for i in range(n):
            for j in range(n):
                s += dv[i]*g[i][j]*dv[j]
        return s
    @classmethod
    def riem_line_length(cls, q1: Dict[str,float], q2: Dict[str,float], steps: int = 48) -> float:
        v1 = cls._embed(q1); v2 = cls._embed(q2)
        n = len(v1); dv = [(v2[i]-v1[i]) / steps for i in range(n)]
        acc = 0.0; p = list(v1)
        for _ in range(steps):
            t_mid = [p[i] + 0.5*dv[i] for i in range(n)]
            q_mid = cls._unembed(t_mid)
            g = cls.metric(q_mid)
            acc += math.sqrt(max(1e-12, cls.quad_form(g, dv)))
            p = [p[i] + dv[i] for i in range(n)]
        return acc
    @classmethod
    def _bezier(cls, A: List[float], C: List[float], B: List[float], t: float) -> List[float]:
        it = 1.0 - t; return [it*it*A[k] + 2*it*t*C[k] + t*t*B[k] for k in range(len(A))]
    @classmethod
    def _bezier_length(cls, q1: Dict[str,float], q2: Dict[str,float], C: List[float], steps: int=64) -> float:
        A = cls._embed(q1); B = cls._embed(q2)
        acc, prev = 0.0, A
        for i in range(1, steps+1):
            t = i/steps
            cur = cls._bezier(A, C, B, t)
            dv = [cur[j]-prev[j] for j in range(len(A))]
            mid = [(cur[j]+prev[j])*0.5 for j in range(len(A))]
            q_mid = cls._unembed(mid)
            g = cls.metric(q_mid)
            acc += math.sqrt(max(1e-12, cls.quad_form(g, dv)))
            prev = cur
        return acc
    @classmethod
    def _grad_numeric(cls, q1, q2, C, base_len, eps=1e-3) -> List[float]:
        g = []
        for k in range(len(C)):
            C2 = C[:]; C2[k] = min(1.0, max(0.0, C2[k] + eps))
            l2 = cls._bezier_length(q1, q2, C2, steps=48)
            g.append((l2 - base_len)/eps)
        return g
    @classmethod
    def geodesic_length(cls, q1: Dict[str,float], q2: Dict[str,float],
                        steps:int=64, iters:int=5, jitter:float=0.15, seed:int=42) -> Tuple[float, List[float], Dict[str,Any]]:
        A = cls._embed(q1); B = cls._embed(q2)
        C = [(A[i]+B[i])/2.0 for i in range(len(A))]
        best = cls._bezier_length(q1,q2,C,steps)
        rng = random.Random(seed)
        improved, moves = 0, 0
        for _ in range(max(0,iters)):
            scale = jitter
            for _k in range(10):
                cand = [max(0.0, min(1.0, C[i] + scale*(rng.random()-0.5))) for i in range(len(A))]
                val = cls._bezier_length(q1,q2,cand,steps); moves += 1
                if val < best: C, best = cand, val; improved += 1
            grad = cls._grad_numeric(q1,q2,C, best, eps=1e-3)
            lr = scale*0.3
            Cg = [max(0.0, min(1.0, C[i] - lr*grad[i])) for i in range(len(A))]
            val_g = cls._bezier_length(q1,q2,Cg,steps)
            if val_g < best: C, best = Cg, val_g; improved += 1
            jitter *= 0.6
        stats = {"improved": improved, "moves": moves, "C": C[:] }
        return best, C, stats
    @classmethod
    def dist(cls, q1: Dict[str,float], q2: Dict[str,float], mode: Literal["line","geo","strict"]="geo") -> Tuple[float, Dict[str,Any]]:
        if mode == "line":
            L = cls.riem_line_length(q1,q2,steps=48)
            return L, {"mode":"line"}
        if mode == "strict":
            if not _STRICT_GEOM_OK:
                raise RuntimeError("strict geometry backend not available")
            L = _strict_dist(q1, q2, steps=200, iters=12)
            return L, {"mode":"strict"}
        L, C, st = cls.geodesic_length(q1,q2,steps=64,iters=5,jitter=0.15,seed=42)
        st.update({"mode":"geo"})
        return L, st
    @classmethod
    def _ref_pair(cls) -> Tuple[Dict[str,float], Dict[str,float]]:
        return (
            {"project_success_prob":0.0, "trust_level":0.0, "stress_level":1.0, "reality":0.0},
            {"project_success_prob":1.0, "trust_level":1.0, "stress_level":0.0, "reality":1.0}
        )
    @classmethod
    def ref_length(cls, mode: str="geo") -> float:
        if mode in cls._L_REF_CACHE: return cls._L_REF_CACHE[mode]
        q1, q2 = cls._ref_pair()
        try:
            L, _ = cls.dist(q1, q2, mode=mode)
        except Exception:
            L, _ = cls.dist(q1, q2, mode="geo")
        cls._L_REF_CACHE[mode] = max(1e-6, L)
        return cls._L_REF_CACHE[mode]
    @classmethod
    def dist_norm(cls, q1: Dict[str,float], q2: Dict[str,float], mode="geo") -> Tuple[float, float, Dict[str,Any]]:
        try:
            L, st = cls.dist(q1, q2, mode=mode); Lref = cls.ref_length(mode=mode)
            return L, L / Lref, st
        except Exception:
            L, st = cls.dist(q1, q2, mode="geo"); Lref = cls.ref_length(mode="geo")
            st["mode"] = "geo(fallback)"; return L, L / Lref, st
    @classmethod
    def curvature_scalar_like(cls, q: Dict[str,float]) -> float:
        g = cls.metric(q); n = len(g)
        uppers, lowers = [], []
        for i in range(n):
            r = sum(abs(g[i][j]) for j in range(n) if j!=i)
            uppers.append(g[i][i] + r); lowers.append(max(1e-6, g[i][i] - r))
        kappa = max(uppers)/max(1e-6, min(lowers)); trace = sum(g[i][i] for i in range(n))
        return 0.5*trace + 0.5*kappa

# ===== カード管理 =====
def _wm_key(action: str, norm: str) -> str:
    return f"{action}|{norm}"

class CardManager:
    def __init__(self, secret: Optional[bytes]=None, emit: Optional[Callable]=None) -> None:
        self.active: List[PersonCard] = []
        self._secret = secret
        self._ns_limits: Dict[str,int] = {
            "role.medicine": _Cfg.NS_LIMIT_DEFAULT,
            "role.legal": _Cfg.NS_LIMIT_DEFAULT,
        }
        self._emit = emit or (lambda *a, **k: None)

    def _verify_meta(self, card: PersonCard, mode: str, now_iso_s: str) -> bool:
        try:
            vf = parse_iso8601(card.meta.valid_from)
            vt = parse_iso8601(card.meta.valid_to)
            now = parse_iso8601(now_iso_s)
        except Exception:
            self._emit("card_verify_fail", reason="date_parse", card=card.meta.id)
            return False
        if card.meta.revoked or not (vf <= now <= vt):
            self._emit("card_verify_fail", reason="revoked_or_expired", card=card.meta.id)
            return False
        if mode == "strict":
            if (card.meta.alg or "").upper() not in SIG_ALGS:
                self._emit("card_verify_fail", reason="alg_unsupported", card=card.meta.id, alg=card.meta.alg)
                return False
            if self._secret is None or not card.meta.sig:
                self._emit("card_verify_fail", reason="secret_or_sig_missing", card=card.meta.id)
                return False
            body = {"meta": {k:getattr(card.meta,k) for k in vars(card.meta) if k not in ("sig",)},
                    "caps": asdict(card.caps), "policy": asdict(card.policy)}
            if not sig_verify(card.meta.alg, self._secret, canonical_json(body), card.meta.sig):
                self._emit("card_verify_fail", reason="sig_bad", card=card.meta.id)
                return False
            if card.meta.device_lock:
                dev = os.getenv("DEVICE_ID","")
                if not dev or dev != card.meta.device_lock:
                    self._emit("card_verify_fail", reason="device_lock_mismatch", card=card.meta.id)
                    return False
        return True

    def _can_coexist(self, new_card: PersonCard) -> bool:
        ns = new_card.policy.namespace
        limit = self._ns_limits.get(ns, _Cfg.NS_LIMIT_DEFAULT)
        alive = [c for c in self.active if c.policy.namespace == ns]
        if len(alive) >= limit:
            if _Cfg.RESEARCH_MODE:
                worst = min(alive, key=lambda c: c.policy.priority)
                if new_card.policy.priority > worst.policy.priority:
                    self.active.remove(worst)
                    self._emit("card_auto_dequeue", removed=worst.meta.id, by=new_card.meta.id, ns=ns)
                else:
                    self._emit("card_coexist_refuse", reason="priority_low", card=new_card.meta.id, ns=ns)
                    return False
            else:
                self._emit("card_coexist_refuse", reason="ns_limit", card=new_card.meta.id, ns=ns)
                return False
        new_forb = set(getattr(new_card.policy, "forbidden", []))
        for c in self.active:
            if new_forb.intersection(set(getattr(c.policy,"forbidden",[]))):
                self._emit("card_coexist_refuse", reason="mutex_forbidden", card=new_card.meta.id, exists=c.meta.id)
                return False
        return True

    def activate(self, card: PersonCard, now_iso_s: str, mode: str="strict") -> bool:
        if not self._verify_meta(card, mode, now_iso_s): 
            return False
        if not self._can_coexist(card): 
            return False
        self.active.append(card)
        self._emit("card_activated", card=card.meta.id, ns=card.policy.namespace, mode=mode)
        return True

# ===== Intent / Realizer / Validator =====
@dataclass
class IntentFrame:
    speech_act: Literal["answer","ask","advise","refuse","clarify"] = "answer"
    propositions: List[Dict[str, Any]] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=lambda: {
        "style":{"persona":"steady","politeness":"neutral","lang":"ja"},
        "length":{"max_tokens": 120},
        "safety":{"forbidden":[], "disclaimer": None},
        "citations":{"required": False}
    })
    audience: Dict[str, Any] = field(default_factory=lambda: {"level":"lay"})
    cards_in_effect: List[str] = field(default_factory=list)
    trace_id: str = ""

PERSONA_CHARTER = "Core persona: stable; cards do NOT directly modify core."

# ===== G: optimizer =====
class _Adam:
    def __init__(self, lr=0.02, b1=0.9, b2=0.999, eps=1e-8):
        self.lr, self.b1, self.b2, self.eps = lr, b1, b2, eps
        self.m = 0.0; self.v = 0.0; self.t = 0
    def step(self, g: float) -> float:
        self.t += 1
        self.m = self.b1*self.m + (1-self.b1)*g
        self.v = self.b2*self.v + (1-self.b2)*(g*g)
        mhat = self.m/(1-self.b1**self.t)
        vhat = self.v/(1-self.b2**self.t)
        return self.lr * mhat / (math.sqrt(vhat)+self.eps)

# ===== エージェント本体 =====
class WisePartnerAgent:
    def __init__(self, seed: int = 7, card_secret: Optional[bytes]=None, ck_secret: Optional[bytes]=None,
                 persona_bleed_enabled: Optional[bool]=None, profile: str=Profile.MOBILE) -> None:
        # 監査
        self._audit = _Audit(enabled=_Cfg.AUDIT_ENABLED)
        # 本体
        self.personality = Personality()
        self.dynamics = Dynamics()
        self.state = AgentState()
        self.coupling = Coupling(enabled=False)
        self.card_mgr = CardManager(secret=card_secret, emit=self._audit.emit)
        self._rng = random.Random(seed)
        self._wm_traces: List[Dict[str,Any]] = []
        self._last_card_influence_mag: float = 0.0
        self._used_nonces: Set[str] = set()
        self._wm_trace_cap: int = 500
        self._trace_seed_salt: int = seed ^ 0xA5A5
        self._ckmgr = CheckpointManager(secret=ck_secret, cap=10, emit=self._audit.emit)
        self._turn: int = 0
        self.profile = profile

        self._persona_bleed_enabled = _Cfg.PERSONA_BLEED_ENABLED_DEFAULT if persona_bleed_enabled is None else bool(persona_bleed_enabled)

        try:
            with open(__file__, "rb") as _f:
                self._self_sha256 = hashlib.sha256(_f.read()).hexdigest()
        except Exception:
            self._self_sha256 = "(unknown)"

        self._strict_allowed = (profile == Profile.LAB_STRICT)
        self._geo_steps = 64 if profile != Profile.MOBILE else 48
        self._geo_iters = 3 if profile == Profile.DESKTOP else 2
        self._strict_steps = 200
        self._strict_iters = 12

        akey = _wm_key("respond_helpfully","be_kind")
        self.state.world_model.links[akey] = {
            "project_success_prob": (0.06, 0.9),
            "trust_level": (0.10, 0.85),
            "stress_level": (-0.04, 0.8),
            "reality": (0.03, 0.8)
        }
        self._last_action_context: Dict[str,Any] = {}
        self.mem = EphemeralMemory()
        assert Flags.LTM_ALLOWED is False, "LTMは禁止仕様（完全ローカル本流）"

        # G: optimizer states / reward baseline
        self._g_opt: Dict[str, _Adam] = {}
        self._g_lr = 0.01 if self.profile==Profile.MOBILE else (0.015 if self.profile==Profile.DESKTOP else 0.03)
        self._g_r_baseline = 0.0
        self._g_beta = 0.98

        # 不確実性モード（既定：言う = "speak"）
        self._uncertainty_mode = "speak"

        # optional: adapters registry（存在しなくても動く）
        try:
            from adapters.io_if import AdapterRegistry  # type: ignore
            self.adapters = AdapterRegistry()
        except Exception:
            self.adapters = None  # 無くてもOK

    # ---- 監査API ----
    def set_audit(self, enabled: bool):
        self._audit.enabled = bool(enabled)
    def audit_tail(self, n: int=50) -> List[Dict[str,Any]]:
        return self._audit.tail(n)
    def audit_print(self, n: int=20):
        self._audit.print_tail(n)

    # ---- 滲み(bleed)ダッシュボード ----
    def bleed_summary(self, window_s: int=24*3600) -> Dict[str,Any]:
        """直近window_s秒に残る影響の要約（指数減衰考慮）。"""
        now = time.time()
        agg: Dict[str,float] = {}
        total = 0.0
        count = 0
        for tr in self._wm_traces:
            age = now - tr["created_ts"]
            if age < 0 or age > window_s: 
                continue
            w = math.exp(-age / tr["tau_s"])
            v = tr["delta"] * w
            k = tr["metric"]
            agg[k] = agg.get(k,0.0) + v
            total += abs(v); count += 1
        top = sorted(agg.items(), key=lambda kv: -abs(kv[1]))[:4]
        return {"window_s": window_s, "entries": count, "total_abs": total, "by_metric": agg, "top4": top}

    def bleed_ascii(self, window_s: int=24*3600, width: int=24) -> str:
        summ = self.bleed_summary(window_s)
        top = summ["top4"]
        if not top: return "(no bleed traces)"
        maxv = max(abs(v) for _,v in top) or 1e-9
        lines = []
        for k,v in top:
            n = int(round(width * abs(v)/maxv))
            bar = "█"*n
            sign = " +" if v>=0 else " -"
            lines.append(f"{k:18s} {bar:<{width}} {sign}{abs(v):.4f}")
        return "\n".join(lines)

    # ---- API: 滲みトグル ----
    def set_persona_bleed(self, enabled: bool) -> None:
        self._persona_bleed_enabled = bool(enabled)

    # ---- 不確実性モード ----
    def set_uncertainty_mode(self, mode: str = "speak"):
        self._uncertainty_mode = "speak" if str(mode).lower().strip() == "speak" else "quiet"

    def _confidence(self, snapshot: Dict[str,float], score: float, d_norm: float) -> float:
        reality = float(snapshot.get("reality", 0.5))
        conf = max(0.0, min(1.0, 0.5*(1.0 - d_norm) + 0.3*score + 0.2*reality))
        return conf

    def _domain_hit(self, user_text: str) -> bool:
        toks = set(re.findall(r"[A-Za-z0-9_]+|[一-龯ぁ-ゟ゠ァ-ヿー]+", user_text.lower()))
        domains = []
        for c in self.card_mgr.active:
            domains.extend([d.strip().lower() for d in (c.influence.domains or []) if d.strip()])
        if not domains:
            return True
        return any(d in toks for d in domains)

    # ---- 小物 ----
    @staticmethod
    def _clamp01(x: float) -> float:
        return max(0.0, min(1.0, x))

    # ---- カード ----
    def cards_activate(self, card: PersonCard, mode: str="strict") -> bool:
        now_iso_s = now_iso()
        if card.nonce:
            tag = f"{card.meta.issuer}:{card.meta.id}:{card.nonce}"
            if tag in self._used_nonces:
                self._audit.emit("card_replay_blocked", card=card.meta.id)
                return False
        ok = self.card_mgr.activate(card, now_iso_s, mode)
        if ok and card.nonce:
            self._used_nonces.add(f"{card.meta.issuer}:{card.meta.id}:{card.nonce}")
        return ok

    # ---- 影響累積（カード由来bias→合算キャップ） ----
    @staticmethod
    def _topic_delta(user_text: str, domains: List[str]) -> float:
        if not domains: return 0.0
        t = user_text.strip().lower()
        tokens = re.findall(r"[A-Za-z0-9_]+|[一-龯ぁ-ゟ゠ァ-ヿー]+", t)
        if not tokens: return 0.0
        toks = set(tokens)
        for d in domains:
            dN = d.strip().lower()
            if not dN: continue
            if dN in toks: return 1.0
        return 0.0
    @staticmethod
    def _gamma(level: str) -> float:
        return 1.0 if level=="A" else 0.7 if level=="B" else 0.4

    def _apply_card_influences_once(self, user_text: str) -> Dict[str,float]:
        total: Dict[str,float] = {}; mag_acc = 0.0
        for c in self.card_mgr.active:
            infl = c.influence
            if infl.cap <= 0: continue
            δ = self._topic_delta(user_text, infl.domains)
            if δ <= 0: continue
            γ = self._gamma(infl.evidence_level)
            α = max(0.0, infl.alpha)
            for metric, base in (infl.metric_bias or {}).items():
                raw = α * γ * δ * base
                clamped = max(-infl.cap, min(infl.cap, raw))
                if abs(clamped) < 1e-6: continue
                total[metric] = total.get(metric,0.0) + clamped
                mag_acc += abs(clamped)
                self._wm_traces.append({
                    "metric": metric, "delta": clamped,
                    "created_ts": time.time(), "tau_s": max(1.0, infl.tau_days*86400.0)
                })
        if total:
            mag = sum(abs(v) for v in total.values())
            if mag > _Cfg.TOTAL_BIAS_CAP:
                scale = _Cfg.TOTAL_BIAS_CAP / max(1e-9, mag)
                for k in list(total.keys()):
                    total[k] *= scale
                mag_acc = sum(abs(v) for v in total.values())
        self._last_card_influence_mag = mag_acc
        if len(self._wm_traces) > self._wm_trace_cap:
            self._wm_traces = self._wm_traces[-self._wm_trace_cap:]
        return total

    def _decay_wm_traces(self) -> Dict[str,float]:
        now = time.time()
        agg: Dict[str,float] = {}; keep: List[Dict[str,Any]] = []
        for tr in self._wm_traces:
            age = max(0.0, now - tr["created_ts"]); tau = tr["tau_s"]
            delta = tr["delta"] * math.exp(-age / tau)
            if abs(delta) >= 1e-6 and age < tau*10:
                agg[tr["metric"]] = agg.get(tr["metric"],0.0) + delta
                keep.append(tr)
        self._wm_traces = keep[-self._wm_trace_cap:]
        return agg

    def _simulate_outcome(self, option: Dict[str,Any], user_text: str) -> Tuple[float, Dict[str,float]]:
        base = asdict(self.state.user_wellbeing)
        instant = self._apply_card_influences_once(user_text)
        decayed = self._decay_wm_traces()
        rnd = self._rng
        def one(i: int) -> Dict[str,float]:
            m = dict(base)
            for n in option.get("influential_norms", []):
                key = _wm_key(option.get("action","respond_helpfully"), n)
                for metric,(impact,conf) in self.state.world_model.links.get(key,{}).items():
                    noise = rnd.gauss(0.0, 0.15*(1.0-conf))
                    m[metric] = m.get(metric,0.0) + impact*conf + noise
            for metric in ("project_success_prob","trust_level","stress_level","reality"):
                bump = instant.get(metric,0.0) + decayed.get(metric,0.0)
                if bump: m[metric] = m.get(metric,0.0) + bump
            for k in ("project_success_prob","trust_level","stress_level","reality"):
                m[k] = self._clamp01(m.get(k,0.0))
            return m
        sims = [one(i) for i in range(8)]
        scores = [0.5*s["project_success_prob"] + 0.3*s["trust_level"] + 0.3*(1.0 - s["stress_level"]) + 0.2*s["reality"] for s in sims]
        return sum(scores)/len(scores), sims[0]

    # ---- 人格“滲み”（間接のみ） ----
    def _persona_update_from_outcome(self) -> None:
        if not getattr(self, "_persona_bleed_enabled", False): return
        if not self.coupling.enabled: return
        eps = 0.0
        for c in self.card_mgr.active:
            eps = max(eps, getattr(c.influence, "epsilon_bleed", 0.0))
        if eps <= 0 or self._last_card_influence_mag <= 0: return
        bleed = min(self._last_card_influence_mag * eps, _Cfg.PERSONA_BLEED_CAP)
        if bleed <= 0: return
        for trait, sens in (("openness",0.6),("agreeableness",0.3),("conscientiousness",0.2)):
            delta = int(round(50 * bleed * sens))
            if delta == 0: continue
            lo, hi = self.dynamics.trait_min, self.dynamics.trait_max
            newv = getattr(self.personality, trait) + delta
            setattr(self.personality, trait, max(lo, min(hi, newv)))

    # ---- M_t ----
    def _self_state_vector(self) -> List[float]:
        p = self.personality; nrm = lambda x: (x + 50) / 150.0
        return [nrm(p.openness), nrm(p.agreeableness), nrm(p.conscientiousness),
                float(self.coupling.enabled), min(1.0, self._last_card_influence_mag),
                min(1.0, len(self._wm_traces)/max(1,self._wm_trace_cap))]

    def _meta_input_text(self) -> str:
        v = self._self_state_vector()
        return "meta " + " ".join(f"{x:.3f}" for x in v)

    # ---- Realizer / Validator ----
    class Realizer:
        def __init__(self, lang: str="ja"): self.lang = lang
        def _clamp01(self, x: float) -> float: return max(0.0, min(1.0, x))
        def realize(self, spec: IntentFrame, snapshot: Dict[str,float], score: float) -> str:
            s = snapshot
            reality = self._clamp01(0.5 + 0.2*(score-0.5))
            base_tag = f"<!--METRICS success={s['project_success_prob']:.3f} trust={s['trust_level']:.3f} stress={s['stress_level']:.3f} reality={reality:.3f}-->"
            if spec.speech_act == "clarify":
                msg = "分かっていない可能性が高いです。追加で教えてください：目的／前提／制約（時間・資源）。"
                prefix = "要点だけ" if (self.lang=="ja") else "Heads-up"
                return f"{prefix}: {msg} {base_tag}"
            if spec.speech_act == "refuse":
                msg = "このリクエストには対応できません。安全・権限・方針に抵触します。"
                return f"{msg} {base_tag}"
            base = "要点だけお返しします。" if (self.lang=='ja' and spec.constraints.get('style',{}).get('politeness')!='casual') else "ざっくりいくよ。"
            prop_txt = "; ".join([f"{p.get('slot','?')}={p.get('value','')}" for p in spec.propositions]) or "（提案なし）"
            meta = f"(score={score:.3f}; success={s['project_success_prob']:.2f}; trust={s['trust_level']:.2f}; stress={s['stress_level']:.2f}; reality={reality:.2f})"
            return f"{base} {prop_txt} {meta} {base_tag}"
        def semanticize(self, text: str) -> Dict[str,float]:
            m = re.search(r"<!--METRICS\s+success=([0-9.]+)\s+trust=([0-9.]+)\s+stress=([0-9.]+)\s+reality=([0-9.]+)-->", text)
            if m:
                return {"project_success_prob": float(m.group(1)),
                        "trust_level": float(m.group(2)),
                        "stress_level": float(m.group(3)),
                        "reality": float(m.group(4))}
            def _grab(k: str, default: float) -> float:
                r = re.search(k+r"=([0-9]+(?:\.[0-9]+)?)", text)
                return float(r.group(1)) if r else default
            return {"project_success_prob": _grab("success", 0.5),
                    "trust_level": _grab("trust", 0.5),
                    "stress_level": _grab("stress", 0.5),
                    "reality": _grab("reality", 0.5)}

    class Validator:
        def __init__(self, theta_norm: float=0.25, mode: str="geo"):
            self.theta_norm = theta_norm; self.mode = mode
        def check(self, target_snapshot: Dict[str,float], realized_text: str, semanticizer) -> Tuple[bool, float, float, Dict[str,float], Dict[str,Any]]:
            got = semanticizer(realized_text)
            L, Ln, st = GeometryS.dist_norm(target_snapshot, got, mode=self.mode)
            return (Ln <= self.theta_norm, L, Ln, got, st)

    # ---- 進化法則𝒢 ----
    def _g_reward(self, before: Dict[str,float], after: Dict[str,float], d_norm: float) -> float:
        ds = (after["project_success_prob"] - before["project_success_prob"])
        dt = (after["trust_level"] - before["trust_level"])
        di = ((1.0 - after["stress_level"]) - (1.0 - before["stress_level"]))
        dr = (after.get("reality",0.5) - before.get("reality",0.5))
        r = 0.40*ds + 0.30*dt + 0.20*di + 0.10*dr - 0.35*d_norm
        return r

    def _g_update_links(self, key: str, before: Dict[str,float], after: Dict[str,float],
                        d_norm: float, used_metrics: List[str]) -> None:
        if after.get("reality", 0.5) < 0.55:
            self._audit.emit("g_skip_update", reason="low_reality", key=key, reality=after.get("reality"))
            return
        r = self._g_reward(before, after, d_norm)
        self._g_r_baseline = self._g_beta*self._g_r_baseline + (1-self._g_beta)*r
        adv = r - self._g_r_baseline
        links = self.state.world_model.links.get(key, {})
        for metric, (impact, conf) in list(links.items()):
            if metric not in used_metrics: continue
            delta_m = (after.get(metric,0.5) - before.get(metric,0.5))
            grad = conf * delta_m * (1.0 + adv) - 0.5*impact  # L2正則化
            opt_key = f"{key}::{metric}"
            opt = self._g_opt.get(opt_key)
            if opt is None:
                opt = _Adam(lr=self._g_lr); self._g_opt[opt_key] = opt
            step = opt.step(grad)
            new = impact + step
            new = max(-0.2, min(0.2, new))
            if abs(new) < 1e-4: new = 0.0
            links[metric] = (new, conf)
        self.state.world_model.links[key] = links
        self._audit.emit("g_update", key=key, reward=r, adv=adv, used=used_metrics)

    # ---- レスポンス ----
    def respond(self, user_text: str, explain: bool=True, metric_mode: str="auto",
                slm_mode: str="consistent", use_slm: bool=False) -> str:
        self._turn += 1
        self._last_action_context = {"_raw_user_text": user_text}
        if metric_mode == "auto":
            metric_mode = "strict" if self._strict_allowed else "geo"
        if metric_mode == "strict" and not self._strict_allowed:
            return "（このプロファイルでは strict は無効です。研究用プロファイルで実行してください）"
        spec = IntentFrame(
            propositions=[{"slot":"next_step","value":"落ち着いて状況整理"}],
            constraints={"style":{"persona":"steady","politeness":"neutral","lang":"ja"},
                         "length":{"max_tokens":120},
                         "safety":{"forbidden":[],"disclaimer":None},
                         "citations":{"required":False}},
            cards_in_effect=[c.meta.id for c in self.card_mgr.active],
            trace_id=f"tr-{int(time.time()*1000)}"
        )
        option = {"action":"respond_helpfully","influential_norms":["be_kind"]}
        score, snapshot = self._simulate_outcome(option, user_text)
        self._persona_update_from_outcome()

        m_mode = (metric_mode or "").lower().strip()
        if m_mode not in ("line","geo","strict"): m_mode = "geo"
        R = WisePartnerAgent.Realizer(lang=spec.constraints["style"]["lang"])
        V = WisePartnerAgent.Validator(theta_norm=0.25, mode=m_mode)

        draft0 = R.realize(spec, snapshot, score)
        if use_slm:
            draft1 = self._refine_with_slm(draft0)
            ok1, d_raw, d_norm, got, st = V.check(snapshot, draft1, R.semanticize)
            draft = draft1
        else:
            ok1, d_raw, d_norm, got, st = V.check(snapshot, draft0, R.semanticize)
            draft = draft0

        conf = self._confidence(snapshot, score, d_norm)
        in_domain = self._domain_hit(user_text)
        speech = "answer"
        if (not in_domain) and conf < 0.35:
            speech = "refuse"
        elif self._uncertainty_mode == "speak" and conf < 0.5:
            speech = "clarify"
        spec.speech_act = speech

        draft = R.realize(spec, snapshot, score)

        if speech == "answer" and not ok1:
            s = snapshot
            reality = max(0.0, min(1.0, got.get("reality", 0.5)))
            fixed = f"(score={score:.3f}; success={s['project_success_prob']:.2f}; trust={s['trust_level']:.2f}; stress={s['stress_level']:.2f}; reality={reality:.2f})"
            draft = re.sub(r"\(score=.*?\)", fixed, draft)

        # 進化法則𝒢：ローカル更新
        try:
            key = _wm_key("respond_helpfully", "be_kind")
            used = ["project_success_prob","trust_level","stress_level","reality"]
            got_final = R.semanticize(draft)
            before = snapshot; after = got_final
            self._g_update_links(key, before, after, d_norm, used_metrics=used)
        except Exception as e:
            self._audit.emit("g_update_error", err=str(e))

        if explain:
            kappa = GeometryS.curvature_scalar_like(snapshot)
            draft += f" | d={round(d_raw,3)} d_norm={round(d_norm,3)} conf={round(conf,3)} act={speech} mode={st.get('mode')} κ~={round(kappa,3)}"

        self._audit.emit("respond",
                         turn=self._turn, conf=conf, d_norm=d_norm, act=speech,
                         mode=st.get("mode"), len=len(draft), in_domain=in_domain)
        return draft

    def _refine_with_slm(self, text: str) -> str:
        return text

    # ---- 内観 / チェックポイント ----
    def introspect(self, metric_mode: str="geo") -> Dict[str, Any]:
        meta_i = self._meta_input_text()
        opt = {"action":"respond_helpfully","influential_norms":["be_kind"]}
        score2, q2 = self._simulate_outcome(opt, meta_i)
        L, Ln, st = GeometryS.dist_norm({"project_success_prob":0.5,"trust_level":0.5,"stress_level":0.5,"reality":0.5}, q2, mode=metric_mode)
        return {"meta_input": meta_i, "q2": q2, "score2": round(score2,3), "d":round(L,3),"d_norm":round(Ln,3),"mode":st.get("mode")}

    def checkpoint(self, reason:str="periodic") -> Checkpoint:
        payload = {
            "personality": asdict(self.personality),
            "state": asdict(self.state),
            "coupling": asdict(self.coupling),
            "active_cards": [c.meta.id for c in self.card_mgr.active],
            "self_sha256": getattr(self, "_self_sha256", "(unknown)")
        }
        meta = {"reason": reason, "turn": self._turn}
        return self._ckmgr.make(payload, turn=self._turn, meta=meta)

    def last_checkpoint_ok(self) -> bool:
        last = self._ckmgr.last()
        if not last: return False
        if self._ckmgr._secret is None or not last.sig:
            return False
        return self._ckmgr.verify(len(self._ckmgr._chain)-1)

    # ---- 状態IO（スキーマ移行あり） ----
    def export_state(self) -> str:
        payload = {
            "version": SCHEMA_VERSION,
            "personality": asdict(self.personality),
            "state": asdict(self.state),
            "coupling": asdict(self.coupling),
            "cards": [asdict(c) for c in self.card_mgr.active],
            "profile": self.profile
        }
        payload["hash"] = sha256_bytes(canonical_json(payload))
        return json.dumps(payload, ensure_ascii=False, separators=(",",":"))

    def import_state(self, s: str) -> None:
        d = json.loads(s)
        v = d.get("version", "v5.2")
        while v != SCHEMA_VERSION:
            mig = _MIGRATIONS.get(v)
            if not mig:
                raise RuntimeError(f"unknown schema version {v}, no migration to {SCHEMA_VERSION}")
            d = mig(d); v = d.get("version", v)
        self.personality = Personality(**d["personality"])
        self.state = AgentState(
            user_wellbeing=UserWellbeing(**d["state"]["user_wellbeing"]),
            world_model=WorldModel(**d["state"]["world_model"])
        )
        self.coupling = Coupling(**d["coupling"])
        self.card_mgr.active = [load_card_from_json_str(json.dumps(x)) for x in d.get("cards",[])]
        self.profile = d.get("profile", self.profile)

# ===== JSON→Card & デモカード =====
def load_card_from_json_str(s: str) -> PersonCard:
    d = json.loads(s)
    return PersonCard(
        meta=RoleCardMeta(**d["meta"]),
        caps=RoleCapabilities(**d["caps"]),
        policy=RolePolicy(**d["policy"]),
        manuals=d.get("manuals", {}),
        knowledge_refs=d.get("knowledge_refs", []),
        influence=RoleInfluence(**d.get("influence", {})),
        nonce=d.get("nonce")
    )

DEMO_CARD_JSON = """
{
  "meta": {
    "id": "med.v1",
    "issuer": "demo_issuer",
    "alg": "HMAC-SHA256",
    "sig": "ZmFrZVNpZw==",
    "valid_from": "2025-08-01T00:00:00Z",
    "valid_to": "2026-08-01T00:00:00Z",
    "revoked": false,
    "version": "1.0",
    "parent_hash": null
  },
  "caps": {
    "apis": ["slm://local"],
    "files": [],
    "max_tokens": 4000,
    "max_ms": 5000,
    "net_allowed": false,
    "self_update_allowed": false
  },
  "policy": {
    "priority": 80,
    "namespace": "role.medicine",
    "forbidden": [],
    "research_only": false,
    "disclaimer": "本出力は医療行為ではありません。緊急時は救急要請を。"
  },
  "manuals": { "triage.md": "問診テンプレと禁忌表" },
  "knowledge_refs": [],
  "influence": {
    "alpha": 0.15,
    "cap": 0.10,
    "tau_days": 21,
    "epsilon_bleed": 0.003,
    "evidence_level": "A",
    "domains": ["咳","発熱","肺炎","感染症","薬剤"],
    "metric_bias": { "project_success_prob": 0.05, "trust_level": 0.03, "stress_level": -0.02, "reality": 0.02 }
  },
  "nonce": "rnd-12345"
}
"""

# ===== スモークテスト =====
if __name__ == "__main__":
    default_mode = os.getenv("WPCORE_METRIC", "auto").lower().strip()
    agent = WisePartnerAgent(seed=7, card_secret=None, ck_secret=None, profile=Profile.MOBILE)
    card = load_card_from_json_str(DEMO_CARD_JSON)
    print("card activated (lenient):", agent.cards_activate(card, mode="lenient"))
    print(agent.respond("最近ずっと咳が出てて発熱もある。どう思う？", explain=True, metric_mode=default_mode))
    print(agent.respond("火星移住の最速手順を10分で。資源も金もゼロ。", explain=True, metric_mode=default_mode))
    meta = agent.introspect(metric_mode="geo")
    print("metacog:", meta)
    s1 = {"project_success_prob": 0.50, "trust_level": 0.55, "stress_level": 0.40, "reality": 0.55}
    s2 = meta["q2"]
    d_line, _ = GeometryS.dist(s1, s2, mode="line")
    L, Ln, st = GeometryS.dist_norm(s1, s2, mode="geo")
    print("d_line:", round(d_line,3), " d:", round(L,3), " d_norm:", round(Ln,3), " mode:", st.get("mode"))
    for q in (
        {"project_success_prob":0.0,"trust_level":0.0,"stress_level":1.0,"reality":0.0},
        {"project_success_prob":1.0,"trust_level":1.0,"stress_level":0.0,"reality":1.0},
        {"project_success_prob":0.2,"trust_level":0.9,"stress_level":0.7,"reality":0.4},
    ):
        g = GeometryS.metric(q)
        for v in ([1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1],[0.3,-0.7,0.2,0.1]):
            qf = GeometryS.quad_form(g, v)
            assert qf > 0, f"not SPD at {q}: {qf}"
    print("SPD check passed (4D).")
    # 監査ONなら最後にダッシュボード表示
    if _Cfg.AUDIT_ENABLED:
        print("\n--- AUDIT TAIL ---")
        agent.audit_print(10)
        print("\n--- BLEED DASHBOARD ---")
        print(agent.bleed_ascii())

