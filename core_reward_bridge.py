# 外部KPI→進化法則𝒢へのブリッジ（完全ローカル）
from typing import Dict, List, Optional
from core.wise_partner_core_v52_plus import WisePartnerAgent, GeometryS

def _key(task: str) -> str:
    return f"task:{task}|external"

class RewardBridge:
    def __init__(self, agent: WisePartnerAgent):
        self.agent = agent
    def report(self, task: str,
               before: Dict[str,float],
               after: Dict[str,float],
               metrics: Optional[List[str]] = None,
               d_norm: Optional[float] = None) -> None:
        """外部KPIを報告し、該当タスクのlinkを更新する。
        metrics: 更新対象。省略時は4軸。
        d_norm: 未指定ならgeoで算出。
        """
        if metrics is None:
            metrics=["project_success_prob","trust_level","stress_level","reality"]
        if d_norm is None:
            _, d_norm, _ = GeometryS.dist_norm(before, after, mode="geo")
        key = _key(task)
        # 初期化（無ければ空辞書）
        self.agent.state.world_model.links.setdefault(key, {})
        # 無信頼データは 𝒢 側で弾かれる（realityゲート）
        self.agent._g_update_links(key, before, after, d_norm, used_metrics=metrics)
