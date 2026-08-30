# -*- coding: utf-8 -*-
"""trigger 3.9 blob 字节级读写器。

模型经 Alexander the Great 全部 175 触发器逐字节走查验证（_walk39.py）。
布局：
  8B 版本(double=3.9) | 1B 魔数(0) | 4B 触发器数
  每触发器:
    26B 头: enabled(4) looping(1) desc_stid(4) disp_as_obj(1) obj_order(4)
            make_header(1) short_stid(4) display_on_screen(1) unknown(5) mute(1)
    3 个 str32: trigger_description / trigger_name / short_description
    4B 效果数 | 效果×N | 4B×N 效果显示顺序
    4B 条件数 | 条件×M | 4B×M 条件显示顺序
  效果 = 60×s32 + [fill0 若sv62>=63] + [fill1 若sv62>=64]
         + str32 message + str32 sound + s32×max(nsel,0) + str32 msgopt1 + str32 msgopt2
  条件 = 29×s32 + [fill 若sv30>=31] + str32 xs_function
尾部: 4B×触发器数 顺序数组 + 其他数据
"""
import struct

HDR = 26
EFF_INTS = 60
COND_INTS = 29


class Reader:
    def __init__(self, buf):
        self.b = buf
        self.p = 0

    def i32(self, p=None):
        if p is None:
            p = self.p
        return struct.unpack_from("<i", self.b, p)[0]

    def u32(self, p=None):
        if p is None:
            p = self.p
        return struct.unpack_from("<I", self.b, p)[0]

    def take(self, n):
        v = self.b[self.p:self.p + n]
        self.p += n
        return v

    def s32v(self):
        v = self.i32()
        self.p += 4
        return v

    def byte(self):
        v = self.b[self.p]
        self.p += 1
        return v

    def take_bytes(self, n):
        return self.take(n)

    def str32(self):
        n = self.s32v()
        if n < 0:
            raise ValueError("negative str len %d @%d" % (n, self.p - 4))
        return self.take(n)


class Writer:
    def __init__(self):
        self.parts = []

    def s32(self, v):
        self.parts.append(struct.pack("<i", v))

    def u32(self, v):
        self.parts.append(struct.pack("<I", v))

    def byte(self, v):
        self.parts.append(bytes([v]))

    def raw(self, v):
        self.parts.append(v)

    def str32(self, v):
        self.s32(len(v))
        self.raw(v)

    def getvalue(self):
        return b"".join(self.parts)


def _read_effect(r):
    e = {}
    ints = [r.s32v() for _ in range(EFF_INTS)]
    e["ints"] = ints
    sv = ints[1]  # static_value_62
    e["fill0"] = r.take_bytes(4) if sv >= 63 else None
    e["fill1"] = r.take_bytes(4) if sv >= 64 else None
    e["message"] = r.str32()
    e["sound"] = r.str32()
    nsel = ints[6]  # number_of_units_selected
    e["ids"] = [r.s32v() for _ in range(max(nsel, 0))]
    e["opt1"] = r.str32()
    e["opt2"] = r.str32()
    return e


def _write_effect(w, e):
    for v in e["ints"]:
        w.s32(v)
    if e["fill0"] is not None:
        w.raw(e["fill0"])
    if e["fill1"] is not None:
        w.raw(e["fill1"])
    w.str32(e["message"])
    w.str32(e["sound"])
    for v in e["ids"]:
        w.s32(v)
    w.str32(e["opt1"])
    w.str32(e["opt2"])


def _read_condition(r):
    c = {}
    c["ints"] = [r.s32v() for _ in range(COND_INTS)]
    sv = c["ints"][1]  # static_value_30
    c["fill"] = r.take_bytes(4) if sv >= 31 else None
    c["xs"] = r.str32()
    return c


def _write_condition(w, c):
    for v in c["ints"]:
        w.s32(v)
    if c["fill"] is not None:
        w.raw(c["fill"])
    w.str32(c["xs"])


def parse_blob(blob):
    """解析 3.9 触发器 blob，返回 (结构dict, 元信息)。"""
    r = Reader(blob)
    doc = {}
    doc["version_bytes"] = r.take_bytes(8)
    doc["magic0"] = r.byte()  # 0x01
    doc["n_triggers_pos"] = r.p
    doc["n_triggers"] = r.s32v()
    doc["triggers"] = []
    for _ in range(doc["n_triggers"]):
        t = {}
        t["head_raw"] = r.take_bytes(HDR)
        t["desc_stid"] = struct.unpack_from("<i", t["head_raw"], 5)[0]
        t["description"] = r.str32()
        t["name"] = r.str32()
        t["short_description"] = r.str32()
        n_eff = r.s32v()
        t["effects"] = [_read_effect(r) for _ in range(n_eff)]
        t["eff_order"] = [r.s32v() for _ in range(n_eff)]
        n_cond = r.s32v()
        t["conditions"] = [_read_condition(r) for _ in range(n_cond)]
        t["cond_order"] = [r.s32v() for _ in range(n_cond)]
        doc["triggers"].append(t)
    doc["tail_order_start"] = r.p
    doc["tail_order"] = [r.s32v() for _ in range(doc["n_triggers"])]
    doc["rest"] = blob[r.p:]
    return doc


def render_blob(doc):
    w = Writer()
    w.raw(doc["version_bytes"])
    w.byte(doc["magic0"])
    w.s32(doc["n_triggers"])
    for t in doc["triggers"]:
        w.raw(t["head_raw"])
        w.str32(t["description"])
        w.str32(t["name"])
        w.str32(t["short_description"])
        w.s32(len(t["effects"]))
        for e in t["effects"]:
            _write_effect(w, e)
        for v in t["eff_order"]:
            w.s32(v)
        w.s32(len(t["conditions"]))
        for c in t["conditions"]:
            _write_condition(w, c)
        for v in t["cond_order"]:
            w.s32(v)
    for v in doc["tail_order"]:
        w.s32(v)
    w.raw(doc["rest"])
    return w.getvalue()


def roundtrip_selftest(blob):
    doc = parse_blob(blob)
    out = render_blob(doc)
    return out == blob, doc


if __name__ == "__main__":
    import sys, os, io
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import pickle
    data, tv = pickle.load(open("_t39_blob.bin", "rb"))
    from analyze_t39 import find_triggers_offset
    off, instr, cnt = find_triggers_offset(data, tv or 3.9)[0]
    blob = data[off:]
    same, doc = roundtrip_selftest(blob)
    print("roundtrip identical:", same)
    print("triggers:", len(doc["triggers"]))
    n_msg = sum(1 for t in doc["triggers"] for e in t["effects"] if e["message"])
    n_txt = sum(1 for t in doc["triggers"] if t["description"] or t["name"] or t["short_description"])
    print("effects with message:", n_msg, "| triggers with text:", n_txt)