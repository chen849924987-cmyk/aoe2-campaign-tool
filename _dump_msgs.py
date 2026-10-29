# -*- coding: utf-8 -*-
"""导出场景 Messages 六字段源文本: python _dump_msgs.py <scen> <out.txt>"""
import sys, io
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import grab_any, msgs_rw

src, out = sys.argv[1], sys.argv[2]
g = grab_any.grab_any(src)
off, _, _ = grab_any.pick_anchor(g.data, g.tv)
mf, _ = msgs_rw.read_fields(g.data, limit_off=off)
with open(out, "w", encoding="utf-8") as f:
    for k in ("instructions", "hints", "victory", "loss", "history", "scouts"):
        f.write("==== %s (len=%d) ====\n%r\n\n" % (k, len(mf[k]), mf[k]))
print("dumped msgs ->", out, "| sizes:", {k: len(mf[k]) for k in mf})
