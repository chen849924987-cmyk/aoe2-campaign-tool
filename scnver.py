# -*- coding: utf-8 -*-
"""探测 .aoe2scenario 场景版本（1.54/1.56/...），无需安装 AoE2ScenarioParser。

用法: python scnver.py <file1> [file2 ...]
原理: AoE2 DE 场景文件头部未压缩，前 8 字节即 ASCII 版本串（如 "1.57\\x00\\x00\\x00\\x00"），
直接读取即可。少数其他封装（zlib 包装流）作为回退：解压后开头 8 字节同样取版本串。
注意场景主体的 deflate 流是 raw 格式且解压结果不含版本串，不要走解压路线找版本。
"""
import sys, zlib
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CHECK_BYTES = (0x01, 0x5E, 0x9C, 0xDA)  # zlib 包装流 FLG 合法值（常见压缩级别）
CHUNK = 400000  # 回退试探解压的输入上限（足够覆盖版本串）


def _ver_from(out):
    s = out[:8].rstrip(b"\x00").decode("ascii", "ignore")
    return s if s.startswith("1.") else None


def _probe_zlib(data):
    """回退：扫描 zlib 包装流（0x78 + check 字节），解压取版本串。"""
    i = data.find(b"\x78")
    while i != -1:
        if i + 1 < len(data) and data[i + 1] in CHECK_BYTES:
            try:
                v = _ver_from(zlib.decompressobj().decompress(data[i:i + CHUNK]))
                if v:
                    return v
            except Exception:
                pass
        i = data.find(b"\x78", i + 1)
    return None


def probe(path):
    """返回形如 '1.56' 的场景版本串；识别失败返回 None。"""
    with open(path, "rb") as f:
        head = f.read(8)
        v = _ver_from(head)
        if v:
            return v
        data = head + f.read()
    return _probe_zlib(data)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for p in sys.argv[1:]:
        name = p.replace("\\", "/").rsplit("/", 1)[-1]
        print("%-60s scenario_version=%s" % (name, probe(p)))
