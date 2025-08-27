import random, statistics
from core.wise_partner_core_v52_plus import GeometryS

def randq():
    return {
        "project_success_prob": random.random(),
        "trust_level": random.random(),
        "stress_level": random.random(),
        "reality": random.random(),
    }

errs = []
for _ in range(100):
    Ls, _ = GeometryS.dist(randq(), randq(), "strict")
    Lg, _ = GeometryS.dist(randq(), randq(), "geo")
    if Ls > 0:
        errs.append(abs(Lg - Ls) / Ls)

print("MAPE:", round(statistics.mean(errs) * 100, 2), "%")

