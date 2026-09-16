import os
import json
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from collections import defaultdict

from utils import (
    load_all_episodes, fetch_danmaku_xml, load_cache, save_cache,
    parse_temporary_chars, PERMANENT_NAMES, print_lock
)
from classifier import classify_episode
from parser_danmaku import parse_xml_to_danmaku_list
from handlers.drama_handler import DramaHandler
from handlers.solo_handler import SoloHandler
from handlers.song_handler import SongHandler
from report_writer import ReportWriter

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:05.2f}"

def write_subtitle(path, lines):
    with open(path, 'w', encoding='utf-8') as f:
        for time, content, color in lines:
            f.write(f"{format_time(time)} - {content}\n")

def process_episode(episode, config, report_writer, table_dir):
    table = episode["table_name"]
    filename = episode["filename"]
    soundid = episode["soundid"]
    temp_raw = episode["temporary_chars_raw"]

    etype = classify_episode(filename, temp_raw, config)
    known_roles = PERMANENT_NAMES + parse_temporary_chars(temp_raw)

    xml = load_cache(soundid, config["cache_hours"])
    if xml is None:
        xml = fetch_danmaku_xml(soundid, config)
        save_cache(soundid, xml)
    danmaku_list = parse_xml_to_danmaku_list(xml)
    total_dm = len(danmaku_list)
    duration = danmaku_list[-1][0] if danmaku_list else 0.0

    if etype == "song":
        handler = SongHandler(config)
        output_subdir = "歌曲类_待人工处理"
    elif etype == "solo":
        handler = SoloHandler(config)
        output_subdir = "单人福利"
    else:
        handler = DramaHandler(config)
        output_subdir = "正剧"

    result = handler.process(episode, danmaku_list, known_roles)
    final_lines = result["final_lines"]
    official_ids = result["official_ids"]
    extra = result["report_extra"]

    out_dir = table_dir / output_subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{filename}.txt"

    # 正剧ID过多检查
    id_exceeds = False
    if etype == "drama":
        max_ids = config.get("drama_max_official_ids", 20)
        if len(official_ids) > max_ids:
            id_exceeds = True
            out_dir = table_dir / "正剧_ID过多_待复核"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"{filename}.txt"
            if not extra.get("reason"):
                extra["reason"] = f"官方ID过多({len(official_ids)}个)"
            else:
                extra["reason"] += f"；官方ID过多({len(official_ids)}个)"

    write_subtitle(out_file, final_lines)

    locked_no_id = False
    if etype == "solo" and len(final_lines) == 0:
        empty_dir = table_dir / "单人福利_空字幕"
        empty_dir.mkdir(exist_ok=True)
        shutil.move(str(out_file), str(empty_dir / f"{filename}.txt"))
        if extra.get("locked_role") and not official_ids:
            locked_no_id = True

    summary = f"类型:{etype}"
    if etype == "solo" and extra.get("locked_role"):
        summary += f" 锁定:{extra['locked_role']}"
    perm_counts = extra.get("perm_id_counts", {})
    temp_role_count = extra.get("temp_role_count", 0)

    report_writer.add_row(
        table_name=table,
        filename=filename,
        soundid=soundid,
        temp_raw=temp_raw,
        duration=duration,
        total_dm=total_dm,
        official_cnt=len(final_lines),
        official_ids=official_ids,
        summary=summary,
        reason=extra.get("reason"),
        exceeds_15=extra.get("exceeds_15", False),
        locked_no_id=locked_no_id,
        temp_role_count=temp_role_count,
        perm_counts=perm_counts
    )

    with print_lock:
        status = f"✅ {filename} | {etype} | 官方弹幕:{len(final_lines)}"
        if id_exceeds:
            status += " | ⚠️ ID过多已移入复核文件夹"
        print(status)

def process_table(table_name, episodes, config):
    table_dir = Path(config["output_root"]) / table_name
    table_dir.mkdir(parents=True, exist_ok=True)

    report_path = table_dir / "异常报告.csv"
    report = ReportWriter(str(report_path))

    with ThreadPoolExecutor(max_workers=config["max_workers"]) as executor:
        futures = [executor.submit(process_episode, ep, config, report, table_dir) for ep in episodes]
        for f in as_completed(futures):
            f.result()

    report.save()
    print(f"📊 表格 [{table_name}] 处理完成，报告已保存至 {report_path}")

def main():
    with open("config.json", 'r', encoding='utf-8') as f:
        config = json.load(f)

    all_episodes = load_all_episodes(config["table_folder"])

    tables_dict = defaultdict(list)
    for ep in all_episodes:
        tables_dict[ep["table_name"]].append(ep)

    print(f"📋 共加载 {len(all_episodes)} 个有效剧集，分属 {len(tables_dict)} 张表格")

    for table_name, episodes in tables_dict.items():
        print(f"\n🎬 开始处理表格：{table_name}（共 {len(episodes)} 集）")
        process_table(table_name, episodes, config)

    print("\n🎉 全部完成！")

if __name__ == "__main__":
    main()