# -*- coding: utf-8 -*-
"""将翻译文本写回 3.9/4.x 战役（版本自适应）：blob 重建 -> 替换解压数据 -> 重压缩打包。

用法:
  python t39_build.py <src.scx> <texts.json> <out.scx>
texts.json: t39_extract.py 导出的条目，含可选 "trans" 字段（空/缺省=保持原文）。
"""
import sys, os, io, json, zlib
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
AoE2DEScenario._validate_latest_trigger_data_version = lambda self, v: None

from t39_blob_rw import parse_blob, render_blob  # 保留旧导入以兼容既有用法
from analyze_t39 import find_triggers_offset, get_blob_rw

CP1252 = "cp1252"


def grab(path):
    cap = {}

    class Stop(Exception):
        pass

    def fake_validate(self, tv):
        cap["tv"] = tv
        cap["data"] = self._decompressed_file_data
        cap["sections"] = dict(self.sections)
        raise Stop()

    orig = AoE2DEScenario._validate_latest_trigger_data_version
    AoE2DEScenario._validate_latest_trigger_data_version = fake_validate
    try:
        try:
            AoE2DEScenario.from_file(path, game_version="DE")
        except Stop:
            pass
    finally:
        AoE2DEScenario._validate_latest_trigger_data_version = orig
    return cap["data"], cap["tv"], cap.get("sections", {})


def find_compress_start(raw, data):
    """在原始文件中定位 raw-deflate 流起点（解压结果须等于 data）。"""
    for o in range(0, min(0x400, len(raw))):
        try:
            d = zlib.decompressobj(-15)
            out = d.decompress(raw[o:])
            out += d.flush()
            if out == data:
                return o
        except Exception:
            continue
    raise ValueError("compress stream start not found")


def build(src, texts_json, dst, msgs_trans=None):
    data, tv, sections = grab(src)
    rw = get_blob_rw(tv)  # 3.9 -> t39_blob_rw, 4.x -> t47_blob_rw
    off, instr, cnt = find_triggers_offset(data, tv or 3.9)[0]
    blob = data[off:]

    items = json.load(open(texts_json, encoding="utf-8"))
    mapping = {}
    for it in items:
        tr = it.get("trans")
        if tr and tr != it["orig"]:
            mapping[it["id"]] = tr

    doc = rw.parse_blob(blob)
    applied = 0
    for ti, t in enumerate(doc["triggers"]):
        for field, key in (("name", "name"), ("desc", "description"), ("short", "short_description")):
            v = t[key]
            if not v.strip(b"\x00"):
                continue
            tid = "t%d.%s" % (ti, field)
            if tid in mapping:
                t[key] = _encode_field(mapping[tid], v)
                applied += 1
        for ei, e in enumerate(t["effects"]):
            if not e["message"].strip(b"\x00"):
                continue
            tid = "t%d.eff%d.msg" % (ti, ei)
            if tid in mapping:
                e["message"] = _encode_field(mapping[tid], e["message"])
                applied += 1

    new_blob = rw.render_blob(doc)
    new_data = data[:off] + new_blob + data[off + len(blob):]

    # ---- Messages section 替换（若提供翻译）----
    if msgs_trans:
        msgs = sections["Messages"]
        old_bytes = msgs.get_data_as_bytes()
        midx = new_data.find(old_bytes)
        if midx < 0:
            raise ValueError("Messages section bytes not located")
        for k, v in msgs_trans.items():
            setattr(msgs, k, v)
        new_msgs = msgs.get_data_as_bytes()
        new_data = new_data[:midx] + new_msgs + new_data[midx + len(old_bytes):]
        print("messages replaced @0x%x: %d -> %d bytes" % (midx, len(old_bytes), len(new_msgs)))

    raw = open(src, "rb").read()
    x = find_compress_start(raw, data)
    deflate = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
    packed = deflate.compress(new_data) + deflate.flush()
    open(dst, "wb").write(raw[:x] + packed)
    print("applied %d translations | blob %d -> %d bytes | file %d -> %d bytes"
          % (applied, len(blob), len(new_blob), len(raw), len(raw[:x]) + len(packed)))
    return applied


def _blob_end(data, off):
    """blob 长度：解析一遍得到终点（tail_order 结束即 rest 起点，rest 原样保留）。"""
    doc = parse_blob(data[off:])
    return len(data) - off  # rest 全保留，等价替换整段


def _encode_field(text, old):
    """翻译文本 -> bytes (UTF-8)；保留原字符串的 \\x00 结尾习惯。"""
    b = text.encode("utf-8", errors="replace")
    if old.endswith(b"\x00") and not b.endswith(b"\x00"):
        b += b"\x00"
    return b


if __name__ == "__main__":
    SRC = sys.argv[1]
    TEXTS = sys.argv[2]
    DST = sys.argv[3]
    build(SRC, TEXTS, DST)