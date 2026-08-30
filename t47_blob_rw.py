# -*- coding: utf-8 -*-
"""trigger 4.x（4.5/4.7）blob 字节级读写器。

4.7 模型经 Modu Chanyu M1 全部 114 触发器 roundtrip identical 验证（_probe47.py）；
4.5 模型经 Kaesong 全部 102 触发器 roundtrip identical + 暴力扫描唯一解验证
（batch/_probe_ks.py：HDR∈[25,28]×EFF∈[50,95]×COND∈[24,42] 全量可解析+类型/字符串
合法性打分，唯一幸存 (27,77,35)）。
字段名/字段顺序参考 AoE2ScenarioParser master 的 versions/DE/v1.57/structure.json
（GPL-3.0）——文件格式事实（偏移与字段序）不受版权保护，本模块为独立实现的原始代码。

版本对应关系（场景版本串 = 文件头前 8 字节）：
  - 场景 1.54/1.55 → trigger 3.9（t39_blob_rw）
  - 场景 1.56      → trigger 4.5：HDR=27，EFF_INTS=77，COND_INTS=35
  - 场景 1.57+     → trigger 4.7：HDR=27，EFF_INTS=83，COND_INTS=35
4.5→4.7 的差异 = 效果区多 6 个 int（decision_id、string_id_option1/2、variable2、
max_units_affected、hotkey、train_time、local_technology、disable_sound、object_group2、
object_type2、quantity_float(f32)、facet2、global_sound、issue_group_command、
queue_action、mutual_diplomacy、building_list、wall_x1..y2、unknown_2/3/4、
legacy_location_object_reference 中的一部分；其余为 4.5 已有）。条件与头部无差异。

与 3.9 布局差异：
  - trigger 头 26B → 27B：enabled 后多 1B execute_on_load
  - 效果 60 int → 77/83 int（static_value_62 变 static_value_74/81 等）
  - 条件 29 int → 35 int（static_value_30 变 static_value_33；新增 decision_id、
    decision_option、variable2、local_technology、object_group2、object_type2、
    unknown_2、unknown_4）
  - 3.9 的条件 fill 字段（sv>=63/64、sv>=31）在 4.x 中已并入固定 int 区，无 fill
  - 字符串区不变：message / sound / ids(数量=ints[6]) / opt1 / opt2

布局（4.5 与 4.7 仅效果 int 数不同）：
  8B 版本(double=4.5/4.7) | 1B 未知(0x01) | 4B 触发器数
  每触发器:
    27B 头: enabled(4) looping(1) execute_on_load(1) desc_stid(4) disp_as_obj(1)
            obj_order(4) make_header(1) short_stid(4) display_on_screen(1)
            unknown(5) mute(1)
    3 个 str32: description / name / short_description
    4B 效果数 | 效果×N | 4B×N 效果显示顺序
    4B 条件数 | 条件×M | 4B×M 条件显示顺序
  效果   = EFF_INTS×s32 + str32 message + str32 sound + s32×max(ints[6],0) + str32 opt1 + str32 opt2
  条件   = 35×s32 + str32 xs_function
  尾部   = 4B×触发器数 顺序数组 + 其他数据（变量等，原样保留）

parse_blob 从 blob 前 8 字节自读版本并选择 EFF_INTS，doc["eff_ints"] 记录；
render_blob 按各效果 ints 列表长度输出，无需额外配置。
"""
import struct

HDR = 27
EFF_INTS = 83       # trigger 4.7（场景 1.57+）
EFF_INTS_45 = 77    # trigger 4.5（场景 1.56）
COND_INTS = 35


def eff_ints_for(version_bytes):
    """按 blob 头 8 字节版本 double 选择效果 int 数。"""
    tv = struct.unpack("<d", version_bytes)[0]
    if abs(tv - 4.5) < 0.05:
        return EFF_INTS_45
    if abs(tv - 4.7) < 0.05:
        return EFF_INTS
    raise ValueError("unsupported trigger version %.2f —— 未知 4.x 布局，"
                     "需先做字节级布局探测（参考 batch/_probe_ks.py）" % tv)


class Reader:
    __slots__ = ("b", "p")

    def __init__(self, buf):
        self.b = buf
        self.p = 0

    def s32(self):
        v = struct.unpack_from("<i", self.b, self.p)[0]
        self.p += 4
        return v

    def take(self, n):
        v = self.b[self.p:self.p + n]
        self.p += n
        return v

    def str32(self):
        n = self.s32()
        if n < 0:
            raise ValueError("negative str len %d @%d" % (n, self.p - 4))
        return self.take(n)


class Writer:
    def __init__(self):
        self.parts = []

    def s32(self, v):
        self.parts.append(struct.pack("<i", v))

    def raw(self, v):
        self.parts.append(v)

    def str32(self, v):
        self.s32(len(v))
        self.raw(v)

    def getvalue(self):
        return b"".join(self.parts)


def _read_effect(r, eff_ints):
    e = {}
    e["ints"] = [r.s32() for _ in range(eff_ints)]
    e["message"] = r.str32()
    e["sound"] = r.str32()
    e["ids"] = [r.s32() for _ in range(max(e["ints"][6], 0))]  # number_of_units_selected
    e["opt1"] = r.str32()
    e["opt2"] = r.str32()
    return e


def _write_effect(w, e):
    for v in e["ints"]:
        w.s32(v)
    w.str32(e["message"])
    w.str32(e["sound"])
    for v in e["ids"]:
        w.s32(v)
    w.str32(e["opt1"])
    w.str32(e["opt2"])


def _read_condition(r):
    c = {}
    c["ints"] = [r.s32() for _ in range(COND_INTS)]
    c["xs"] = r.str32()
    return c


def _write_condition(w, c):
    for v in c["ints"]:
        w.s32(v)
    w.str32(c["xs"])


def parse_blob(blob):
    """解析 4.x 触发器 blob，返回结构 dict。版本从 blob 前 8 字节自读。"""
    r = Reader(blob)
    doc = {}
    doc["version_bytes"] = r.take(8)
    doc["eff_ints"] = eff_ints_for(doc["version_bytes"])
    doc["magic0"] = r.b[r.p:r.p + 1]
    r.p += 1
    doc["n_triggers"] = r.s32()
    doc["triggers"] = []
    for _ in range(doc["n_triggers"]):
        t = {}
        t["head_raw"] = r.take(HDR)
        t["desc_stid"] = struct.unpack_from("<i", t["head_raw"], 6)[0]
        t["description"] = r.str32()
        t["name"] = r.str32()
        t["short_description"] = r.str32()
        n_eff = r.s32()
        t["effects"] = [_read_effect(r, doc["eff_ints"]) for _ in range(n_eff)]
        t["eff_order"] = [r.s32() for _ in range(n_eff)]
        n_cond = r.s32()
        t["conditions"] = [_read_condition(r) for _ in range(n_cond)]
        t["cond_order"] = [r.s32() for _ in range(n_cond)]
        doc["triggers"].append(t)
    doc["tail_order"] = [r.s32() for _ in range(doc["n_triggers"])]
    doc["rest"] = blob[r.p:]
    return doc


def render_blob(doc):
    w = Writer()
    w.raw(doc["version_bytes"])
    w.raw(doc["magic0"])
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