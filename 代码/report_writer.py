import csv
import os
from utils import PERMANENT_NAMES

HEADERS = [
    "表格名称", "剧集文件名", "soundid", "请求URL", "非常驻角色原文",
    "剧集近似时长", "弹幕总数", "官方弹幕数", "官方ID列表", "判定依据摘要",
    "异常原因", "单人福利超15条", "锁定角色无ID", "非常驻角色官方ID数"
] + [f"{role}关联ID数" for role in PERMANENT_NAMES]

class ReportWriter:
    def __init__(self, path):
        self.path = path
        self.rows = []

    def add_row(self, table_name, filename, soundid, temp_raw, duration, total_dm, official_cnt,
                official_ids, summary, reason, exceeds_15, locked_no_id, temp_role_count, perm_counts):
        row = {
            "表格名称": table_name,
            "剧集文件名": filename,
            "soundid": soundid,
            "请求URL": f"https://www.missevan.com/sound/getdm?soundid={soundid}",
            "非常驻角色原文": temp_raw,
            "剧集近似时长": f"{duration:.1f}" if duration else "",
            "弹幕总数": total_dm,
            "官方弹幕数": official_cnt,
            "官方ID列表": ",".join(official_ids),
            "判定依据摘要": summary,
            "异常原因": reason or "",
            "单人福利超15条": "是" if exceeds_15 else "",
            "锁定角色无ID": "是" if locked_no_id else "",
            "非常驻角色官方ID数": temp_role_count
        }
        for role in PERMANENT_NAMES:
            row[f"{role}关联ID数"] = perm_counts.get(role, 0)
        self.rows.append(row)

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS)
            writer.writeheader()
            writer.writerows(self.rows)