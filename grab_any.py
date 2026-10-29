# -*- coding: utf-8 -*-
"""统一场景抓取：ASP 对象层优先，失败时手动解压兜底（1.59 / 1.54 ASP 硬拦文件）。

背景（2026-10-26 六新役实战）：
  - 场景 1.59（trigger 5.0）超出 ASP 0.8.5 支持范围（最高 1.58），
    from_file 直接 UnknownScenarioStructureError；
  - 部分 1.54+trigger3.9 文件 ASP 对象层解析炸 NoneType/EndOfFile（Tang/Merchants/Macedon），
    但 blob 层（t39_blob_rw）完全正常——ASP 硬拦 ≠ 文件坏；
  - 兜底路径只依赖 zlib 解压 + 版本锚点扫描，与 ASP 完全解耦。

grab_any(path) -> Grab(data, tv, sections, zoff, mode)
  data     解压后全量字节
  tv       trigger blob 版本 double（手动路径从锚点自读；ASP 路径来自 parser）
  sections ASP sections dict（手动路径为 None——Messages 用 msgs_rw 手动读写）
  zoff     raw-deflate 流起点（重压缩打包直接用，免二次搜索）
  mode     "asp" | "manual"
"""
import io
import os
import sys
import struct
import zlib

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


class Grab:
    __slots__ = ("data", "tv", "sections", "zoff", "mode")

    def __init__(self, data, tv, sections, zoff, mode):
        self.data = data
        self.tv = tv
        self.sections = sections
        self.zoff = zoff
        self.mode = mode


def manual_decompress(path):
    """不依赖 ASP：定位 raw-deflate 流并解压。返回 (raw, data, zoff)。"""
    raw = open(path, "rb").read()
    for o in range(0, min(0x800, len(raw))):
        try:
            d = zlib.decompressobj(-15)
            out = d.decompress(raw[o:])
            out += d.flush()
            if len(out) > 4096 and d.eof:
                return raw, out, o
        except Exception:
            continue
    raise ValueError("no raw-deflate stream found in first 0x800 bytes: %s" % path)


def scan_anchors(data):
    """扫描疑似 trigger blob 头：版本 double 2..6 + magic(0/1/-1) + 合理触发器数。"""
    hits = []
    n = len(data)
    for i in range(0, n - 13):
        v = struct.unpack_from("<d", data, i)[0]
        if not (2.0 <= v <= 6.0):
            continue
        if abs(v * 100 - round(v * 100)) > 1e-6:  # 排除 4.0999... 类脏 double
            continue
        instr = data[i + 8]
        (cnt,) = struct.unpack_from("<i", data, i + 9)
        if instr in (0, 1, 255) and 0 < cnt < 10000:
            hits.append((i, v, instr, cnt))
    return hits


def _asp_grab(path):
    """ASP 对象层抓取（t39_build.grab），失败抛异常。"""
    import t39_build
    data, tv, sections = t39_build.grab(path)
    if data is None:
        raise ValueError("asp grab returned None")
    # zoff：ASP 路径也照常找压缩流起点
    raw = open(path, "rb").read()
    zoff = find_compress_start(raw, data)
    return Grab(data, tv, sections, zoff, "asp")


def find_compress_start(raw, data):
    """在原始文件中定位 raw-deflate 流起点（解压结果须等于 data）。"""
    for o in range(0, min(0x800, len(raw))):
        try:
            d = zlib.decompressobj(-15)
            out = d.decompress(raw[o:])
            out += d.flush()
            if out == data:
                return o
        except Exception:
            continue
    raise ValueError("compress stream start not found")


def pick_anchor(data, tv):
    """选 trigger blob 锚点：逐个候选试 parse，返回 (off, magic, cnt)。

    parse 是结构级校验（错锚点几乎必炸）；全部失败才抛。
    """
    from analyze_t39 import find_triggers_offset, get_blob_rw
    rw = get_blob_rw(tv)
    hits = find_triggers_offset(data, tv)
    if not hits:
        raise ValueError("no trigger anchor for tv=%s" % tv)
    last_err = None
    for off, instr, cnt in hits[:8]:
        try:
            rw.parse_blob(data[off:])
            return off, instr, cnt
        except Exception as e:
            last_err = e
    raise ValueError("no parsable anchor for tv=%s: %s" % (tv, last_err))


def grab_any(path):
    """统一抓取入口。ASP 失败（版本不支持/结构错误）自动走手动路径。"""
    try:
        return _asp_grab(path)
    except Exception:
        pass
    raw, data, zoff = manual_decompress(path)
    anchors = scan_anchors(data)
    if not anchors:
        raise ValueError("manual path: no trigger anchor found in %s" % path)
    tv = None
    off = None
    last_err = None
    for i, v, instr, cnt in anchors[:6]:
        try:
            off2, _, _ = pick_anchor(data, v)
            tv, off = v, off2
            break
        except Exception as e:
            last_err = e
    if tv is None:
        raise ValueError("manual path: no parsable anchor: %s" % last_err)
    return Grab(data, tv, None, zoff, "manual")


def pack(raw, zoff, new_data, dst):
    """按原压缩流起点重压缩写出。返回输出文件字节数。"""
    deflate = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
    packed = deflate.compress(new_data) + deflate.flush()
    open(dst, "wb").write(raw[:zoff] + packed)
    return zoff + len(packed)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    for p in sys.argv[1:]:
        try:
            g = grab_any(p)
        except Exception as e:
            print("%-56s GRAB FAILED: %s" % (os.path.basename(p), e))
            continue
        if g.tv is None or float(g.tv) < 3.9:
            # trigger 3.5/3.6 = 老格式，blob 链不支持，走 batch 旧链（ASP 对象层）
            print("%-56s mode=%-6s tv=%-5s OLD-FORMAT (use old chain: batch\\dump+apply)"
                  % (os.path.basename(p), g.mode, g.tv))
            continue
        from analyze_t39 import get_blob_rw
        off, _, cnt = pick_anchor(g.data, g.tv)
        rw = get_blob_rw(g.tv)
        doc = rw.parse_blob(g.data[off:])
        ok = rw.render_blob(doc) == g.data[off:]
        print("%-56s mode=%-6s scen_tv=%-5s triggers=%-4d roundtrip %s"
              % (os.path.basename(p), g.mode, g.tv, len(doc["triggers"]), "OK" if ok else "FAILED"))


if __name__ == "__main__":
    main()
