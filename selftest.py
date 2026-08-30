# -*- coding: utf-8 -*-
"""roundtrip 自检：验证本工具对给定场景的 Triggers 段支持是否完整。

用法: python selftest.py <file1> [file2 ...]
对每个文件: grab 解压 -> 定位 Triggers 段 -> parse -> rebuild -> 与原数据逐字节比对。
全部通过返回退出码 0。建议在提取/翻译前先跑一遍。
"""
import sys, os
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
AoE2DEScenario._validate_latest_trigger_data_version = lambda self, v: None

from analyze_t39 import grab_blob, find_triggers_offset, get_blob_rw

NO_ANCHOR = "NO_ANCHOR"


def check(path):
    """返回 (roundtrip_ok, tv, n_triggers)；grab 失败返回 None。"""
    data, tv = grab_blob(path)
    if data is None:
        return None
    hits = find_triggers_offset(data, tv or 3.9)
    if not hits:
        return (NO_ANCHOR, tv, 0)
    off, magic, cnt = hits[0]
    rw = get_blob_rw(tv)
    blob = data[off:]
    doc = rw.parse_blob(blob)
    return (rw.render_blob(doc) == blob, tv, cnt)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    allok = True
    for p in sys.argv[1:]:
        name = p.replace("\\", "/").rsplit("/", 1)[-1]
        r = check(p)
        if r is None:
            print("%-60s GRAB FAILED (parser error)" % name)
            allok = False
        elif r[0] == NO_ANCHOR:
            print("%-60s trigger %.1f | NO ANCHOR FOUND" % (name, r[1]))
            allok = False
        else:
            ok, tv, cnt = r
            print("%-60s trigger %.1f | triggers=%-4d roundtrip %s"
                  % (name, tv, cnt, "OK" if ok else "FAILED"))
            allok = allok and ok
    print("SELFTEST", "PASSED" if allok else "FAILED")
    sys.exit(0 if allok else 1)
