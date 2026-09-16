import os
import re
import time
import json
import threading
import requests
import csv
from pathlib import Path
from datetime import datetime, timedelta

print_lock = threading.Lock()
PERMANENT_NAMES = ['顾子尧', '夏予扬', '乔殊', '林致', '柏闻', '季少一', '江恪', '许向安', '许向宁']

# ------------------ 文本清洗 ------------------
def clean_text(text: str) -> str:
    text = str(text)
    text = text.replace(" ", "").replace("　", "")
    text = re.sub(r"[\"'「」『』“”‘’]", "", text)
    text = re.sub(r"[\[\(\<].*?[\]\)\>]", "", text)
    return text.strip()

# ------------------ 非常驻角色解析 ------------------
def parse_temporary_chars(raw: str) -> list:
    if not raw or str(raw).strip().lower() in ("", "没有", "none"):
        return []
    s = str(raw).replace("、", ",").replace(" ", ",")
    parts = [p.strip() for p in s.split(",") if p.strip()]
    return [clean_text(p) for p in parts]

# ------------------ 缓存管理 ------------------
def get_cache_path(soundid: str) -> Path:
    import tempfile
    return Path(tempfile.gettempdir()) / f"danmaku_cache_{soundid}.xml"

def load_cache(soundid: str, cache_hours: int):
    path = get_cache_path(soundid)
    if not path.exists():
        return None
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    if datetime.now() - mtime > timedelta(hours=cache_hours):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def save_cache(soundid: str, content: str):
    path = get_cache_path(soundid)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

# ------------------ 网络请求 ------------------
def fetch_danmaku_xml(soundid: str, config: dict) -> str:
    url = f"https://www.missevan.com/sound/getdm?soundid={soundid}"
    retries = config.get("request_retries", 3)
    for i in range(retries):
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(1)

# ------------------ 读取表格 ------------------
def safe_read_csv(path):
    for enc in ('utf-8-sig', 'gbk', 'utf-8'):
        try:
            with open(path, 'r', encoding=enc) as f:
                return list(csv.DictReader(f))
        except:
            continue
    return []

def load_all_episodes(table_folder: str) -> list:
    episodes = []
    for fname in os.listdir(table_folder):
        full = os.path.join(table_folder, fname)
        name, ext = os.path.splitext(fname)
        if ext.lower() not in ('.csv', '.xls', '.xlsx', '.txt'):
            continue
        rows = safe_read_csv(full)
        for row in rows:
            sid = str(row.get("soundid", "")).strip()
            if not sid or sid == "没有" or not sid.isdigit():
                continue
            fname_val = str(row.get("filename", "")).strip()
            tmp = str(row.get("temporary_chars", "")).strip()
            episodes.append({
                "table_name": name,
                "filename": fname_val,
                "soundid": sid,
                "temporary_chars_raw": tmp
            })
    return episodes