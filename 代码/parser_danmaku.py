import xml.etree.ElementTree as ET
import re
from collections import defaultdict
from utils import clean_text, PERMANENT_NAMES

def parse_xml_to_danmaku_list(xml_content: str):
    root = ET.fromstring(xml_content)
    danmakus = []
    for d in root.findall('d'):
        p_attr = d.get('p')
        if not p_attr:
            continue
        parts = p_attr.split(',')
        time = float(parts[0])
        uid = parts[6]
        color = parts[3]
        content = d.text or ""
        danmakus.append((time, uid, color, content))
    return danmakus

def extract_formatted(uid, content, known_roles):
    content = content.strip()
    # 冒号形式
    if '：' in content or ':' in content:
        for sep in ('：', ':'):
            if sep in content:
                parts = content.split(sep, 1)
                role_candidate = clean_text(parts[0])
                if role_candidate in known_roles:
                    return role_candidate, True
    # 【】形式
    m = re.match(r"^【(.+?)】", content)
    if m:
        role_candidate = clean_text(m.group(1))
        if role_candidate in known_roles:
            return role_candidate, True
    return None, False

def should_filter(content: str) -> bool:
    c = clean_text(content).upper()
    if c in ("LASER", "MANTA"):
        return True
    for perm in PERMANENT_NAMES:
        if c == perm * 2 or c == perm * 3:
            return True
    return False

def collect_stats(danmaku_list, known_roles):
    formatted_counts = defaultdict(lambda: defaultdict(int))
    uid_to_all = defaultdict(list)

    for time, uid, color, content in danmaku_list:
        uid_to_all[uid].append((time, content, color))
        role, is_fmt = extract_formatted(uid, content, known_roles)
        if is_fmt:
            formatted_counts[uid][role] += 1

    return formatted_counts, uid_to_all