# -*- coding: utf-8 -*-
"""通用翻译引擎（3.9/4.x 自适应）：dump文本 -> 前缀字典匹配 -> 写回 -> 自验证。

用法:
  python translate.py <src.aoe2scenario> <texts.json> <dict_module> <out.aoe2scenario> [msgs_module]

  texts.json     extract.py 的导出（条目含可选 "trans" 字段，本工具自动填充）
  dict_module    字典模块名（不含.py），需提供 T_M 列表；可选缺省模块 dict_common.py 的 T_COMMON
  msgs_module    可选；Messages 区段翻译模块，需提供 MSGS = {"ascii_hints": ..., "ascii_scouts": ...}

字典格式（前缀匹配，顺序敏感——长条目在前）:
    T_M = [
        ("English prefix text", "中文翻译"),
        ...
    ]
"""
import sys, os, io, json, importlib
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from t39_build import build, grab
from analyze_t39 import find_triggers_offset, get_blob_rw


def normalize(s):
    """匹配前归一化：弯撇号转直撇号。"""
    return s.replace("\u2019", "'").replace("\u2018", "'")


def apply_dict(items, extra):
    hit, miss = 0, []
    for it in items:
        orig = normalize(it["orig"])
        for pref, tr in extra:
            if orig.startswith(normalize(pref)):
                it["trans"] = tr
                hit += 1
                break
        else:
            miss.append(it)
    return hit, miss


def verify(path):
    d, tv, secs = grab(path)
    rw = get_blob_rw(tv)
    fields = ("ascii_instructions", "ascii_hints", "ascii_victory", "ascii_loss", "ascii_history", "ascii_scouts")
    paren_ok = all("\uff08" not in getattr(secs["Messages"], a, "")
                   and "\uff09" not in getattr(secs["Messages"], a, "") for a in fields)
    off, _, _ = find_triggers_offset(d, tv or 3.9)[0]
    doc = rw.parse_blob(d[off:])
    cn = tot = 0
    for t in doc["triggers"]:
        for e in t["effects"]:
            if e["message"].strip(b"\x00"):
                tot += 1
                if any(0xE4 <= b <= 0xE9 for b in e["message"][:80]):
                    cn += 1
    return cn, tot, paren_ok


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(__doc__)
        sys.exit(1)
    SRC, JS, DICTMOD, DST = sys.argv[1:5]
    MSGMOD = sys.argv[5] if len(sys.argv) > 5 else None

    try:  # 可选通用字典
        from dict_common import T_COMMON
    except ImportError:
        T_COMMON = []
    extra = T_COMMON + getattr(importlib.import_module(DICTMOD), "T_M", [])

    items = json.load(open(JS, encoding="utf-8"))
    hit, miss = apply_dict(items, extra)
    json.dump(items, open(JS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("translated: %d / %d" % (hit, len(items)))
    for i in miss:
        print("  MISS %s | %s" % (i["id"], i["orig"][:70].replace("\r", "\\r")))

    msgs = None
    if MSGMOD:
        msgs = getattr(importlib.import_module(MSGMOD), "MSGS", None)
    build(SRC, JS, DST, msgs_trans=msgs)

    cn, tot, paren_ok = verify(DST)
    print("VERIFY: effects with Chinese: %d/%d | no fullwidth paren: %s" % (cn, tot, paren_ok))
    print("!! 提醒：翻译文本必须使用半角括号 ( )；全角 （） 在游戏内为乱码。")