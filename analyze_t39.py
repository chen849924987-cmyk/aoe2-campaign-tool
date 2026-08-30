# -*- coding: utf-8 -*-
"""场景解压与 Triggers 段定位（trigger 3.9 / 4.x 通用）。
1) grab_blob: 猴子补丁 parser 的版本校验，读到 FileHeader 后截获解压数据
   （parser-bypass：只借解压/组装能力，不依赖 parser 支持新 trigger 版本）
2) find_triggers_offset: <f64 版本号><u8 魔数><i32 触发器数> 锚点定位
   （3.9 魔数=0，4.x 魔数=1，判据对两者通用）
3) get_blob_rw: 按版本返回字节级读写模块 t39_blob_rw / t47_blob_rw
"""
import sys, io, os, zlib, struct
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.helper.incremental_generator import IncrementalGenerator

_OUT = None


def _out():
    """调试输出文件按需创建，避免 import 本模块时产生副作用。"""
    global _OUT
    if _OUT is None:
        _OUT = open("_t39_analyze.txt", "w", encoding="utf-8")
    return _OUT


def P(*a):
    print(*a, file=_out())


class Stop(Exception):
    pass


def grab_blob(path):
    cap = {}

    def fake_validate(self, tv):
        cap["tv"] = tv
        cap["data"] = self._decompressed_file_data
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
    return cap.get("data"), cap.get("tv")


def find_triggers_offset(data, tv=3.9):
    """返回所有 (offset, magic, n_triggers) 锚点；trigger 3.9 / 4.x 通用。"""
    pat = struct.pack("<d", tv)
    best = []
    i = data.find(pat)
    while i != -1:
        if i + 13 <= len(data):
            instr = data[i + 8]
            (cnt,) = struct.unpack_from("<i", data, i + 9)
            if instr in (0, 1, -1) and 0 < cnt < 10000:
                best.append((i, instr, cnt))
        i = data.find(pat, i + 1)
    return best


def hexdump(b, start=0, length=256):
    out = []
    chunk = b[start:start + length]
    for off in range(0, len(chunk), 16):
        row = chunk[off:off + 16]
        hx = " ".join("%02x" % c for c in row)
        asc = "".join(chr(c) if 32 <= c < 127 else "." for c in row)
        out.append("%06x  %-47s  %s" % (start + off, hx, asc))
    return "\n".join(out)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("AOE_T39_PATH", "")
    data, tv = grab_blob(path)
    if data is None:
        P("no blob captured; tv=", tv)
        return
    P("blob size:", len(data), "trigger_version:", tv)
    hits = find_triggers_offset(data)
    P("anchors:", hits[:10])
    if not hits:
        P("no anchor found!")
        return
    off, instr, cnt = hits[0]
    P("Triggers section at 0x%x, instruction_start=%d, number_of_triggers=%d" % (off, instr, cnt))
    b = data[off:]
    P("\n===== first 0x180 bytes of Triggers section =====")
    P(hexdump(b, 0, 0x180))

    # 手工按 4.1 TriggerStruct 走 trigger 0（假设 trigger 0 可解析）
    pos = 13
    (enabled,) = struct.unpack_from("<I", b, pos); pos += 4
    (looping,) = struct.unpack_from("<b", b, pos); pos += 1
    (dstid,) = struct.unpack_from("<i", b, pos); pos += 4
    disp_obj = b[pos]; pos += 1
    (obj_order,) = struct.unpack_from("<I", b, pos); pos += 4
    make_header = b[pos]; pos += 1
    (sstid,) = struct.unpack_from("<i", b, pos); pos += 4
    disp_screen = b[pos]; pos += 1
    unknown5 = b[pos:pos + 5]; pos += 5
    mute = b[pos]; pos += 1

    def rstr32(b, p):
        (n,) = struct.unpack_from("<i", b, p)
        if n < 0 or n > 100000:
            raise ValueError("bad str len %d at 0x%x" % (n, p))
        s = b[p + 4:p + 4 + n]
        return s.decode("utf-8", "replace"), p + 4 + n

    desc, pos = rstr32(b, pos)
    name, pos = rstr32(b, pos)
    short, pos = rstr32(b, pos)
    (n_eff,) = struct.unpack_from("<i", b, pos); pos += 4
    P("\ntrigger0: enabled=%d looping=%d dstid=%d disp_obj=%d order=%d header=%d sstid=%d screen=%d unknown=%s mute=%d"
      % (enabled, looping, dstid, disp_obj, obj_order, make_header, sstid, disp_screen, unknown5.hex(), mute))
    P("trigger0: desc=%r name=%r short=%r n_eff=%d" % (desc, name, short, n_eff))
    P("pos after trigger0 header fields: 0x%x (section-rel)" % pos)
    P("\n===== 0x120 bytes at trigger0 end (should be trigger1 start) =====")
    P(hexdump(b, pos, 0x120))
    _out().close()
    print("written _t39_analyze.txt")


def get_blob_rw(tv):
    """按 trigger 数据版本返回 blob 读写模块：>=4.0 用 t47_blob_rw，否则 t39_blob_rw。"""
    if tv is not None and float(tv) >= 4.0:
        import t47_blob_rw
        return t47_blob_rw
    import t39_blob_rw
    return t39_blob_rw


if __name__ == "__main__":
    main()