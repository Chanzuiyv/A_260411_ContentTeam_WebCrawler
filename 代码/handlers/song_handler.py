from .base_handler import BaseHandler

class SongHandler(BaseHandler):
    def process(self, episode, danmaku_list, known_roles):
        return {
            "official_ids": [],
            "final_lines": [],
            "report_extra": {
                "official_id_count": 0,
                "reason": "歌曲类_空文件待处理",
                "temp_role_count": 0
            }
        }