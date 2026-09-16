from utils import PERMANENT_NAMES, parse_temporary_chars

def classify_episode(filename: str, temporary_chars_raw: str, config: dict) -> str:
    # 1. 歌曲类
    if any(kw in filename for kw in config.get("song_keywords", [])):
        return "song"

    # 2. 单人福利 / 短剧场
    if "生日" not in filename:
        solo_kws = config.get("solo_keywords", [])
        if any(kw in filename for kw in solo_kws):
            return "solo"
        temps = parse_temporary_chars(temporary_chars_raw)
        all_roles = PERMANENT_NAMES + temps
        count = sum(1 for role in all_roles if role in filename)
        if count == 1:
            return "solo"

    return "drama"