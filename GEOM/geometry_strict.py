# GEOM/geometry_strict.py — strict幾何（4D対応 + Γ再評価RK4 + オプションキャッシュ）
from __future__ import annotations
from typing import Dict, List, Tuple
import math, random, os
from functools import lru_cache

_USE_CACHE = (os.getenv("GEOM_CACHE","0")=="1")

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def embed(q: Dict[str,float]) -> List[float]:
    return [float(q.get("project_success_prob",0.5)),
            float(q.get("trust_level",0.5)),
            1.0 - float(q.get("stress_level",0.5)),
            float(q.get("reality",0.5))]

def unembed(v: List[float]) -> Dict[str,float]:
    return {
        "project_success_prob": clamp01(v[0]),
        "trust_level": clamp01(v[1]),
        "stress_level": clamp01(1.0 - v[2]),
        "reality": clamp01(v[3])
    }

def metric_g(q: Dict[str,float]) -> List[List[float]]:
    ps = float(q.get("project_success_prob", 0.5))
    tr = float(q.get("trust_level", 0.5))
    inv_st = 1.0 - float(q.get("stress_level", 0.5))
    re = float(q.get("reality", 0.5))
    w1 = 1.0 + 0.6*(1.0 - ps)
    w2 = 1.0 + 0.5*(tr)
    w3 = 1.0 + 0.7*(1.0 - inv_st)
    w4 = 1.0 + 0.4*(re)
    rho12 = 0.15 * (tr - 0.5) * (1.0 - ps)
    rho23 = 0.12 * (tr - 0.5) * (1.0 - inv_st)
    rho13 = 0.10 * (0.5 - ps) * (0.5 - inv_st)
    rho14 = 0.06 * (re - 0.5) * (1.0 - ps)
    rho24 = 0.05 * (re - 0.5) * (tr)
    rho34 = 0.04 * (0.5 - inv_st) * (re - 0.5)
    def clip(r, wi, wj):
        lim = 0.35 * min(wi, wj)
        return max(-lim, min(lim, r))
    rho12 = clip(rho12, w1, w2)
    rho23 = clip(rho23, w2, w3)
    rho13 = clip(rho13, w1, w3)
    rho14 = clip(rho14, w1, w4)
    rho24 = clip(rho24, w2, w4)
    rho34 = clip(rho34, w3, w4)
    g = [
        [w1,  rho12, rho13, rho14],
        [rho12, w2,  rho23, rho24],
        [rho13, rho23,  w3, rho34],
        [rho14, rho24, rho34, w4],
    ]
    for i in range(4): g[i][i] += 1e-3
    return g

def mat_inv(a: List[List[float]]) -> List[List[float]]:
    n = len(a)
    m = [row[:] + [1.0 if i==j else 0.0 for j in range(n)] for i,row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-12: m[piv][col] = 1e-12
        if piv != col: m[col], m[piv] = m[piv], m[col]
        div = m[col][col]
        for j in range(2*n): m[col][j] /= div
        for r in range(n):
            if r==col: continue
            factor = m[r][col]
            if factor==0.0: continue
            for j in range(2*n):
                m[r][j] -= factor * m[col][j]
    inv = [row[n:] for row in m]
    return inv

def d_g(q: Dict[str,float], eps: float=1e-4) -> List[List[List[float]]]:
    base = embed(q); n = len(base); outs: List[List[List[float]]] = []
    for k in range(n):
        def shift(delta):
            v = base[:]; v[k] = clamp01(v[k] + delta); return unembed(v)
        g_plus  = metric_g(shift(+eps))
        g_minus = metric_g(shift(-eps))
        dg = [[(g_plus[i][j] - g_minus[i][j])/(2*eps) for j in range(n)] for i in range(n)]
        outs.append(dg)
    return outs

def _christoffel_core(q: Dict[str,float], eps: float=1e-4) -> List[List[List[float]]]:
    g = metric_g(q); ginv = mat_inv(g)
    dgi = d_g(q, eps=eps); n = len(g)
    Gamma = [[[0.0]*n for _ in range(n)] for __ in range(n)]
    for k in range(n):
        for i in range(n):
            for j in range(n):
                s = 0.0
                for ell in range(n):
                    term = dgi[i][j][ell] + dgi[j][i][ell] - dgi[ell][i][j]
                    s += ginv[k][ell] * term
                Gamma[k][i][j] = 0.5 * s
    return Gamma

def _quantize_vec(v: List[float], q: float=1e-3) -> Tuple[int,...]:
    return tuple(int(round(x/q)) for x in v)

if _USE_CACHE:
    @lru_cache(maxsize=10000)
    def _christoffel_cached(vq: Tuple[int,...]):
        v = [x*1e-3 for x in vq]
        return _christoffel_core(unembed(v))
    def christoffel(q: Dict[str,float], eps: float=1e-4) -> List[List[List[float]]]:
        vq = _quantize_vec(embed(q))
        return _christoffel_cached(vq)
else:
    def christoffel(q: Dict[str,float], eps: float=1e-4) -> List[List[List[float]]]:
        return _christoffel_core(q, eps)

def rk4_step(state: List[float], h: float) -> List[float]:
    n = len(state)//2
    def deriv(st):
        x = st[0:n]; v = st[n:2*n]
        q_here = unembed(x)
        Gamma = christoffel(q_here)
        dx = v
        dv = [0.0]*n
        for k in range(n):
            s = 0.0
            for i in range(n):
                for j in range(n):
                    s += Gamma[k][i][j]*v[i]*v[j]
            dv[k] = -s
        return dx + dv
    k1 = deriv(state)
    k2 = deriv([state[i] + 0.5*h*k1[i] for i in range(len(state))])
    k3 = deriv([state[i] + 0.5*h*k2[i] for i in range(len(state))])
    k4 = deriv([state[i] + h*k3[i] for i in range(len(state))])
    return [state[i] + (h/6.0)*(k1[i]+2*k2[i]+2*k3[i]+k4[i]) for i in range(len(state))]

def geodesic_shoot(q1: Dict[str,float], q2: Dict[str,float], steps: int=200, iters: int=12, lr: float=0.2) -> Tuple[float, List[List[float]]]:
    x0 = embed(q1); xT = embed(q2); n = len(x0)
    v = [xT[i]-x0[i] for i in range(n)]
    def integrate(v0):
        state = x0 + v0; path = [x0[:]]; L = 0.0; h = 1.0/steps
        for _ in range(steps):
            state = rk4_step(state, h)
            x_next = state[0:n]
            mid = [(x_next[i]+path[-1][i])*0.5 for i in range(n)]
            q_mid = unembed(mid)
            g = metric_g(q_mid)
            dx = [x_next[i]-path[-1][i] for i in range(n)]
            quad = 0.0
            for i in range(n):
                for j in range(n):
                    quad += dx[i]*g[i][j]*dx[j]
            L += math.sqrt(max(1e-12, quad))
            path.append(x_next[:])
        return L, path
    best_L, best_path = float("inf"), None
    for _ in range(iters):
        L, path = integrate(v)
        end = path[-1]
        err = [end[i]-xT[i] for i in range(n)]
        err_norm = math.sqrt(sum(e*e for e in err))
        if L < best_L:
            best_L, best_path = L, path
        if err_norm < 1e-4:
            break
        for i in range(n):
            v[i] -= lr * err[i]
        lr *= 0.9
    return best_L, best_path if best_path is not None else []

def dist_strict(q1: Dict[str,float], q2: Dict[str,float], steps: int=200, iters: int=12) -> float:
    L, _path = geodesic_shoot(q1, q2, steps=steps, iters=iters)
    return L

