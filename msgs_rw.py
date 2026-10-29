# -*- coding: utf-8 -*-
"""Messages 区段手动读写（ASP 对象层不可用时的兜底路径）。

线格式（2026-10-26 以 ASP 0.9.8 为 oracle 在 1.59 文件上逐字节验证）：
  6 × u32  字符串表 ID（instructions/hints/victory/loss/history/scouts）
  6 × str16 = u16 长度 + UTF-8 字节（无结束符）
六字段顺序固定：instructions, hints, victory, loss, history, scouts。

定位：Messages 区段在 trigger blob 之前；在 [0, trigger_off) 内滑窗试解析，
要求六字段全部为合法文本（ok_text）且至少一个非空——取首个通过者。
假阳性防护：u16 长度上限 + 文本校验；实测 6×0xfffffffe 签名在数据其他位置
也会出现（Henry M1 @0x1010），纯签名定位不可靠。
"""
import struct

FIELDS = ("instructions", "hints", "victory", "loss", "history", "scouts")
MAX_FIELD = 0x40000  # 单字段 256KB 上限（防二进制误配）


def ok_text(b):
    """文本合法性（Messages 专用，比 blob 版严格）：
    空/全 \\x00 合法；否则必须严格 utf-8（不退 latin-1，防二进制误配）；
    要求 ≥98% 可打印（\\r\\n\\t\\x00 计入合法）。"""
    if not b or not b.strip(b"\x00"):
        return True
    try:
        s = b.decode("utf-8")
    except UnicodeDecodeError:
        return False
    good = sum(1 for c in s if c.isprintable() or c in "\r\n\t\x00")
    return good >= len(s) * 0.98


def try_parse(buf, pos):
    """在 pos 试解析 Messages 区段。成功返回 (ids, fields_bytes, consumed)；失败 None。"""
    if pos + 24 > len(buf):
        return None
    ids = struct.unpack_from("<6I", buf, pos)
    # 字符串表 ID 严格约束：实测 1.48/1.51/1.53/1.54/1.59 全部为 6×(-2)。
    # AI 脚本等大文本块的二进制前缀（[0x290a,0,...] / 6×0x300 / 6×-1）必须排除。
    if any(x != 0xFFFFFFFE for x in ids):
        return None
    q = pos + 24
    fields = []
    for _ in FIELDS:
        if q + 2 > len(buf):
            return None
        (L,) = struct.unpack_from("<H", buf, q)
        if L > MAX_FIELD or q + 2 + L > len(buf):
            return None
        b = buf[q + 2:q + 2 + L]
        if not ok_text(b):
            return None
        fields.append(b)
        q += 2 + L
    if all(not b.strip(b"\x00") for b in fields):
        return None  # 六字段全空 = 不是 Messages
    # 简报铁律：hints 或 scouts 至少一个非空（AI 脚本块文本集中在错误字段）
    if not fields[1].strip(b"\x00") and not fields[5].strip(b"\x00"):
        return None
    # DE 消息正文用 \r 换行：至少一个非空字段含 \r
    if not any(b"\r" in b for b in fields):
        return None
    return ids, fields, q - pos


def locate(data, limit_off=None):
    """定位 Messages 区段。返回 (start, ids, fields, consumed)；找不到返回 None。

    limit_off: 搜索上界（一般传 trigger blob 偏移——Messages 必在其前）。
    严格约束（6×-2 ID + hints/scouts 非空 + 含 \\r）下正常只命中唯一真区段；
    仍保留"文本量最大者优先"作多候选兜底。
    """
    end = len(data) if limit_off is None else min(limit_off, len(data))
    best = None
    best_len = -1
    pos = 0
    while pos < end - 26:
        r = try_parse(data, pos)
        if r is not None:
            ids, fields, consumed = r
            total = sum(len(b) for b in fields)
            if total > best_len:
                best, best_len = (pos, ids, fields, consumed), total
        pos += 1
    return best


def read_fields(data, limit_off=None):
    """便捷接口：返回 ({field: str}, locate结果)。"""
    r = locate(data, limit_off)
    if r is None:
        raise ValueError("Messages section not located")
    start, ids, fields, consumed = r
    return {f: fields[i].decode("utf-8", "replace") for i, f in enumerate(FIELDS)}, r


def render(ids, fields_bytes):
    """重建 Messages 区段字节（ids=6 元组，fields_bytes=6 元组字节串）。"""
    out = struct.pack("<6I", *ids)
    for b in fields_bytes:
        out += struct.pack("<H", len(b)) + b
    return out


def replace_translated(data, trans, limit_off=None):
    """把翻译后的六字段写进 data，返回 (new_data, start, old_len)。

    trans: {field: 新文本}，未提供的字段保持原文。文本以 utf-8 编码写入。
    """
    r = locate(data, limit_off)
    if r is None:
        raise ValueError("Messages section not located")
    start, ids, fields, consumed = r
    new_fields = []
    for i, f in enumerate(FIELDS):
        if f in trans and trans[f] is not None:
            new_fields.append(trans[f].encode("utf-8"))
        else:
            new_fields.append(fields[i])
    new_sec = render(ids, new_fields)
    return data[:start] + new_sec + data[start + consumed:], start, consumed
