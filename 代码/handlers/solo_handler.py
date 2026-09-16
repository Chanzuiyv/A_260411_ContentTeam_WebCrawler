from .base_handler import BaseHandler
from parser_danmaku import collect_stats, should_filter
from utils import PERMANENT_NAMES, parse_temporary_chars
from collections import Counter

class SoloHandler(BaseHandler):
    def process(self, episode, danmaku_list, known_roles):
        filename = episode["filename"]
        temps = parse_temporary_chars(episode["temporary_chars_raw"])
        all_roles = PERMANENT_NAMES + temps

        locked_role = None
        found_roles = [r for r in all_roles if r in filename]
        if len(found_roles) == 1:
            locked_role = found_roles[0]

        formatted_counts, uid_to_all = collect_stats(danmaku_list, known_roles)
        official_ids = set()

        if locked_role:
            uid_format_counts = {}
            for uid, role_dict in formatted_counts.items():
                cnt = role_dict.get(locked_role, 0)
                if cnt > 0:
                    uid_format_counts[uid] = cnt
            if uid_format_counts:
                max_cnt = max(uid_format_counts.values())
                best_uids = [u for u, c in uid_format_counts.items() if c == max_cnt]
                first_occurrence = {}
                for t, uid, col, c in danmaku_list:
                    if uid in best_uids and uid not in first_occurrence:
                        first_occurrence[uid] = t
                official_ids.add(min(best_uids, key=lambda u: first_occurrence[u]))
        else:
            for uid in formatted_counts.keys():
                official_ids.add(uid)

        final_lines = []
        for uid in official_ids:
            for t, c, col in uid_to_all.get(uid, []):
                if should_filter(c):
                    continue
                final_lines.append((t, c, col))

        limit = self.config.get("song_duplicate_limit", 3)
        content_counter = Counter(c for _, c, _ in final_lines)
        final_lines = [(t, c, col) for t, c, col in final_lines if content_counter[c] <= limit]
        final_lines.sort(key=lambda x: x[0])

        reason = None
        if len(final_lines) == 0:
            reason = "无官方ID" if not official_ids else "全部被过滤"

        return {
            "official_ids": list(official_ids),
            "final_lines": final_lines,
            "report_extra": {
                "official_id_count": len(official_ids),
                "locked_role": locked_role,
                "total_official_ids": len(official_ids),
                "reason": reason,
                "exceeds_15": len(final_lines) > 15,
                "temp_role_count": 0
            }
        }