# -*- coding: utf-8 -*-
"""触发器任务文本扫描器：检查任务栏/悬浮窗触发器 description/short_description 残留英文。

背景（2026-09-05 Modu Chanyu 踩坑）：目标列表(任务栏)文本=触发器 description
（display_as_objective=1），右上角悬浮窗=同字段（display_on_screen=1），分节标题=
make_header=1。只翻效果 message 的管线会整体漏掉这一层，且既有 fullcheck 不覆盖。

版本自适应：trigger 3.9（头26B，flag 偏移 obj=9/header=14/screen=19）与
4.5/4.7/4.9（头27B，obj=10/header=15/screen=20）。

用法:
  python trigdesc_scan.py <场景文件或目录> [...]        # 扫描残留英文
  python trigdesc_scan.py --work <场景文件> <输出.txt>   # 导出翻译工作单(repr 全文)
判定：先剥掉 <...> 动态占位符/颜色标签，再查 [A-Za-z]{2,}；有汉字的行不算残留。
"""
import sys, os, re, glob

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

FLAGS_39 = {"obj": 9, "header": 14, "screen": 19}
FLAGS_4X = {"obj": 10, "header": 15, "screen": 20}


def scan_file(path):
    """返回 (bad_list, n_triggers, err)。bad_list 元素: (ti, flags, field, text)"""
    try:
        data, tv, secs = grab(path)
        if data is None:
            return None, 0, "grab failed (old format?)"
        rw = get_blob_rw(tv)
        off, _, cnt = find_triggers_offset(data, tv or 3.9)[0]
        doc = rw.parse_blob(data[off:])
    except Exception as ex:
        return None, 0, "parse error: %s" % ex
    flags_off = FLAGS_4X if (tv is not None and float(tv) >= 4.0) else FLAGS_39
    bad = []
    for ti, t in enumerate(doc["triggers"]):
        h = t["head_raw"]
        fl = []
        if h[flags_off["obj"]]:
            fl.append("OBJ")
        if h[flags_off["screen"]]:
            fl.append("SCREEN")
        if h[flags_off["header"]]:
            fl.append("HEADER")
        if not fl:
            continue
        for fld in ("description", "short_description"):
            v = t[fld].decode("utf-8", "replace").rstrip("\x00")
            if not v.strip() or CJK.search(v):
                continue
            if not EN.search(PLACEHOLDER.sub("", v)):
                continue  # 纯占位符/数字/符号
            bad.append((ti, "+".join(fl), fld, v))
    return bad, len(doc["triggers"]), None


def iter_scenarios(args):
    for a in args:
        if os.path.isdir(a):
            # os.walk 不做通配符解释，目录名含 [936] 等也安全
            for root, _dirs, files in os.walk(a):
                for fn in sorted(files):
                    if fn.lower().endswith(".aoe2scenario"):
                        yield os.path.join(root, fn)
        else:
            yield a


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == "--work":
        bad, n, err = scan_file(sys.argv[2])
        if err:
            print("ERROR:", err)
            sys.exit(1)
        with open(sys.argv[3], "w", encoding="utf-8") as f:
            for ti, fl, fld, v in bad:
                f.write("t%d|%s|%s|%r\n" % (ti, fl, fld, v))
        print("work file: %d entries -> %s" % (len(bad), sys.argv[3]))
        return
    total = 0
    for p in iter_scenarios(sys.argv[1:]):
        bad, n, err = scan_file(p)
        if err is not None:
            print("=== %s :: UNSUPPORTED (%s)" % (os.path.basename(p), err))
            continue
        total += len(bad)
        print("=== %s (triggers=%d) bad=%d" % (os.path.basename(p), n, len(bad)))
        for ti, fl, fld, v in bad:
            print("  t%d [%s] %s: %r" % (ti, fl, fld, v[:120]))
    print("TOTAL BAD:", total)


if __name__ == "__main__":
    main()
