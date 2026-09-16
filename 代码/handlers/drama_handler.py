from .base_handler import BaseHandler
from collections import defaultdict
from parser_danmaku import collect_stats, should_filter
from utils import PERMANENT_NAMES, parse_temporary_chars

class DramaHandler(BaseHandler):
    def process(self, episode, danmaku_list, known_roles):
        perm_min = self.config.get("drama_permanent_min", 10)
        temp_min = self.config.get("drama_temp_min", 1)

        formatted_counts, uid_to_all = collect_stats(danmaku_list, known_roles)
        temps = parse_temporary_chars(episode["temporary_chars_raw"])
        official_ids = set()

        # ---------- 非常驻角色（简单收录：达到最低次数即加入）----------
        for uid, role_dict in formatted_counts.items():
            for role, cnt in role_dict.items():
                if role in temps and cnt >= temp_min:
                    official_ids.add(uid)

        # ---------- 常驻角色（高可信，只有达到10次才收录）----------
        perm_role_uids = defaultdict(set)
        for uid, role_dict in formatted_counts.items():
            for role, cnt in role_dict.items():
                if role in PERMANENT_NAMES and cnt >= perm_min:
                    perm_role_uids[role].add(uid)
        for uids in perm_role_uids.values():
            official_ids.update(uids)

        # ---------- 收集弹幕（相同内容只留一条）----------
        final_lines = []
        seen = set()
        for uid in official_ids:
            for t, c, col in uid_to_all.get(uid, []):
                if should_filter(c):
                    continue
                key = (uid, c)
                if key in seen:
                    continue
                seen.add(key)
                final_lines.append((t, c, col))
        final_lines.sort(key=lambda x: x[0])

        # ---------- 统计信息 ----------
        perm_id_counts = {role: len(perm_role_uids.get(role, [])) for role in PERMANENT_NAMES}
        reason = None
        if len(official_ids) > self.config.get("drama_max_official_ids", 20):
            reason = f"官方ID过多({len(official_ids)}个)"
        for role, cnt in perm_id_counts.items():
            if cnt >= 3:
                reason = (reason or "") + f"{role}关联{cnt}个ID；"
        if len(final_lines) == 0:
            reason = (reason or "") + ("无官方ID" if not official_ids else "全部被过滤")

        # 计算非常驻角色官方ID数量
        temp_official_count = len([uid for uid in official_ids 
                                   if any(formatted_counts[uid].get(r, 0) >= temp_min for r in temps)])

        return {
            "official_ids": list(official_ids),
            "final_lines": final_lines,
            "report_extra": {
                "official_id_count": len(official_ids),
                "perm_id_counts": perm_id_counts,
                "temp_role_count": temp_official_count,
                "total_official_ids": len(official_ids),
                "reason": reason
            }
        }