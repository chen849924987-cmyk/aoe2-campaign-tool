# -*- coding: utf-8 -*-
"""从 Triggers blob 提取全部可翻译文本 -> JSON 条目表（trigger 3.9 / 4.x 自适应）。

条目键: (trigger_idx, field) field ∈ {name, desc, short, eff<i>.msg}
用法: python t39_extract.py <scenario_path> [out.json]
"""
import sys, os, io, json
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# grab_blob 内部用 parser 读版本号，需要放行 3.9 校验
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

AoE2DEScenario._validate_latest_trigger_data_version = lambda self, v: None

from analyze_t39 import grab_blob, find_triggers_offset, get_blob_rw


def extract(scen_path):
    """版本自适应：3.9 与 4.x 场景均可；导出前先做逐字节 roundtrip 自检。"""
    data, tv = grab_blob(scen_path)
    rw = get_blob_rw(tv)
    off, instr, cnt = find_triggers_offset(data, tv or 3.9)[0]
    blob = data[off:]
    doc = rw.parse_blob(blob)
    assert rw.render_blob(doc) == blob, "roundtrip failed (tv=%s)" % tv
    items = []
    for ti, t in enumerate(doc["triggers"]):
        for field, key in (("name", "name"), ("desc", "description"), ("short", "short_description")):
            v = t[key]
            if v.strip(b"\x00"):
                items.append({
                    "id": "t%d.%s" % (ti, field),
                    "trigger": ti,
                    "field": field,
                    "orig": v.decode("utf-8", errors="replace"),
                })
        for ei, e in enumerate(t["effects"]):
            if e["message"].strip(b"\x00"):
                items.append({
                    "id": "t%d.eff%d.msg" % (ti, ei),
                    "trigger": ti,
                    "field": "eff_msg",
                    "orig": e["message"].decode("utf-8", errors="replace"),
                })
    return doc, items


def encode_map(s):
    return s.encode("utf-8", errors="replace")


if __name__ == "__main__":
    SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get(
        "AOE_T39_PATH",
        r"C:\Users\84992\Games\Age of Empires 2 DE\76561199180119163\mods\subscribed"
        r"\316138_Alexander the Great (2P Co-Op)\resources\_common\scenario"
        r"\Alexander the Great - 1 (Co-Op).aoe2scenario")
    OUT = sys.argv[2] if len(sys.argv) > 2 else "_t39_texts.json"
    doc, items = extract(SRC)
    json.dump(items, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("exported %d text items -> %s" % (len(items), OUT))
    for it in items[:15]:
        print("%-18s | %s" % (it["id"], it["orig"][:70]))