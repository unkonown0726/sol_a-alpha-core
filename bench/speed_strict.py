import time, random
from core.wise_partner_core_v52_plus import GeometryS

def randq():
    return {
        "project_success_prob": random.random(),
        "trust_level": random.random(),
        "stress_level": random.random(),
        "reality": random.random(),
    }

N = 30
t0 = time.time()
for _ in range(N):
    GeometryS.dist(randq(), randq(), mode="strict")
dt = time.time() - t0
print(f"strict {N} pairs: {dt:.2f}s  per={dt/N:.3f}s")

