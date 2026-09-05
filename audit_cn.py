# -*- coding: utf-8 -*-
"""本地 mod 汉化全面审计：三层玩家可见文本的英文残留检查（版本自适应 3.9/4.5/4.7/4.9）。

三层（2026-09-05 Modu 踩坑后定型——此前各 fullcheck 只查第 1 层，任务栏/悬浮窗整体漏翻）：
  1. 效果 message（类型白名单：3/20/26/37/44/48/51/59/60/65/66；55/56/81/82 为内部）
  2. 触发器 description/short_description（仅 display_as_objective / display_on_screen /
     make_header 置位的触发器——任务栏与右上角悬浮窗）
  3. Messages 六字段（instructions/hints/victory/loss/history/scouts）逐行检查

判定：剥掉 <...> 占位符后查 [A-Za-z]{2,}，同一行/同一条无汉字即算残留。

用法:
  python audit_cn.py <场景文件或目录> [...]     # 逐文件报告
  python audit_cn.py --summary <目录> [...]     # 只输出汇总行（每文件一层计数）
"""
import sys, os, re

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from t39_build import grab
from analyze_t39 import find_triggers_offset, get_blob_rw

CJK = re.compile(r"[\u4e00-\u9fff]")
EN = re.compile(r"[A-Za-z]{2,}")
PLACEHOLDER = re.compile(r"<[^<>]*>")
SEPARATOR = re.compile(r"^[=\-*\d\s.:;|\[\]]+$")
TRANSABLE = {3, 20, 26, 37, 44, 48, 51, 59, 60, 65, 66}
FIELDS = ("ascii_instructions", "ascii_hints", "ascii_victory", "ascii_loss",
          "ascii_history", "ascii_scouts")
FLAGS_39 = {"obj": 9, "header": 14, "screen": 19}
FLAGS_4X = {"obj": 10, "header": 15, "screen": 20}


def _has_en(s):
    return bool(EN.search(PLACEHOLDER.sub("", s))) and not CJK.search(s)


def audit_file(path):
    """返回 (residual_dict, n_triggers, err)。residual_dict: {layer: [(loc, text)]}"""
    try:
        data, tv, secs = grab(path)
        if data is None:
            return None, 0, "grab failed (old format?)"
        rw = get_blob_rw(tv)
        off, _, cnt = find_triggers_offset(data, tv or 3.9)[0]
        doc = rw.parse_blob(data[off:])
    except Exception as ex:
        return None, 0, "parse error: %s" % ex
    res = {"effects": [], "trigdesc": [], "msgs": []}
    for ti, t in enumerate(doc["triggers"]):
        for ei, e in enumerate(t["effects"]):
            m = e["message"]
            if not m.strip(b"\x00"):
                continue
            if e["ints"][0] not in TRANSABLE:
                continue
            s = m.decode("utf-8", "replace").rstrip("\x00")
            if _has_en(s):
                res["effects"].append(("t%d.eff%d [%d]" % (ti, ei, e["ints"][0]), s))
        h = t["head_raw"]
        fo = FLAGS_4X if (tv is not None and float(tv) >= 4.0) else FLAGS_39
        if h[fo["obj"]] or h[fo["header"]] or h[fo["screen"]]:
            for fld in ("description", "short_description"):
                v = t[fld]
                if not v.strip(b"\x00"):
                    continue
                s = v.decode("utf-8", "replace").rstrip("\x00")
                if _has_en(s):
                    res["trigdesc"].append(("t%d.%s" % (ti, fld), s))
    msgs = secs.get("Messages") if isinstance(secs, dict) else None
    if msgs is not None:
        for fl in FIELDS:
            v = getattr(msgs, fl, "") or ""
            if not v.strip("\x00 \r\n"):
                continue
            for ln in v.replace("\r", "\n").split("\n"):
                if ln.strip() and _has_en(ln) and not SEPARATOR.match(ln):
                    res["msgs"].append(("msgs.%s" % fl, ln.strip()))
    return res, len(doc["triggers"]), None


def iter_scenarios(args):
    for a in args:
        if os.path.isdir(a):
            for root, _dirs, files in os.walk(a):
                for fn in sorted(files):
                    if fn.lower().endswith(".aoe2scenario"):
                        yield os.path.join(root, fn)
        else:
            yield a


def main():
    summary_only = False
    args = sys.argv[1:]
    if args and args[0] == "--summary":
        summary_only = True
        args = args[1:]
    grand = {"effects": 0, "trigdesc": 0, "msgs": 0}
    unsupported = 0
    for p in iter_scenarios(args):
        res, n, err = audit_file(p)
        tag = os.path.basename(p)
        if err is not None:
            print("%-58s UNSUPPORTED (%s)" % (tag, err))
            unsupported += 1
            continue
        c1, c2, c3 = len(res["effects"]), len(res["trigdesc"]), len(res["msgs"])
        for k in grand:
            grand[k] += len(res[k])
        if summary_only:
            print("%-58s trig=%-4d eff=%-3d obj=%-3d msgs=%-3d %s"
                  % (tag, n, c1, c2, c3,
                     "OK" if not (c1 or c2 or c3) else "<-- RESIDUAL"))
            continue
        print("=== %s (triggers=%d) eff=%d obj=%d msgs=%d"
              % (tag, n, c1, c2, c3))
        for layer in ("effects", "trigdesc", "msgs"):
            for loc, s in res[layer][:15]:
                print("  [%s] %s: %r" % (layer, loc, s[:100]))
            if len(res[layer]) > 15:
                print("  ... +%d more [%s]" % (len(res[layer]) - 15, layer))
    print("TOTAL: effects=%d trigdesc=%d msgs=%d unsupported=%d"
          % (grand["effects"], grand["trigdesc"], grand["msgs"], unsupported))


if __name__ == "__main__":
    main()
