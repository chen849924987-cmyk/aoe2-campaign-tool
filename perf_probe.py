# -*- coding: utf-8 -*-
"""合作役性能体检：统计场景中与模拟/寻路开销相关的硬指标。

背景（2026-09-05 Modu M2 卡顿诊断）：用户反馈 2P 合作役后期编队下令双方卡死。
排查证明该役并非"虚空产单位"——预置 0 个地图外单位、仅 8 条 Create Object、
无 XS 脚本；真实开销来源是 220x220 大地图 + 约 1 万预置对象（近 9000 GAIA 树木/
草地 + 千余建筑，仅 p3 就 486 块城墙）+ 4 个持续运行的内置 AI（后期兵力膨胀）。
AoE2 DE 联机为 lockstep 确定性模拟，任何一端的重帧都会让双方同步卡住，这是
"双方一起卡死"的机制原因。

用法: python perf_probe.py <scenario1> [scenario2 ...]
     python perf_probe.py --dir <mods目录>          # 逐文件子进程体检整个目录

坑位（2026-09-06 实测）：ASP 在同一进程内先后解析不同版本的 1.54/1.57 场景时，
全局状态会被先解析的旧版本污染，导致后续 1.55+ 文件误报
UnsupportedAttributeError('execute_on_load')。批处理必须逐文件起独立子进程。
"""
import sys, os, io, collections, subprocess

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, __import__("os").path.dirname(__file__))
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.units import UnitInfo
from AoE2ScenarioParser.datasets.other import OtherInfo
from AoE2ScenarioParser.datasets.buildings import BuildingInfo

AoE2DEScenario._validate_latest_trigger_data_version = lambda self, v: None

UNIT_IDS = {m.value[0] for m in UnitInfo}
OTHER_IDS = {m.value[0] for m in OtherInfo}
BLD_IDS = {m.value[0] for m in BuildingInfo}


def probe(path):
    scn = AoE2DEScenario.from_file(path)
    ms = scn.map_manager.map_size
    kind = collections.Counter()
    offmap = 0
    for u in scn.unit_manager.get_all_units():
        c = u.unit_const
        k = ("movable" if c in UNIT_IDS else
             "building" if c in BLD_IDS else
             "gaia_obj" if c in OTHER_IDS else "unknown")
        kind[(int(u.player), k)] += 1
        if u.x < 0 or u.y < 0 or u.x > ms or u.y > ms:
            offmap += 1
    print("=" * 60)
    print("file:", path.replace("\\", "/").split("/")[-1])
    print(f"map: {ms}x{ms} | objects: {sum(kind.values())} | off-map: {offmap}")
    if "--csv" in sys.argv:
        s = scn.sections["PlayerDataTwo"]
        ai_n = ai_rules = 0
        for n, f in zip(s.ai_names, s.ai_files):
            if not n:
                continue
            try:
                txt = f.get_data_as_bytes().decode("utf-8", errors="replace")
                ai_rules += sum(1 for l in txt.splitlines()
                                if l.strip().lower().startswith("(defrule"))
                ai_n += 1
            except Exception:
                pass
        tm = scn.trigger_manager.triggers
        print("CSV|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}".format(
            sum(kind.values()), ms, kind.get((0, "movable"), 0)
            + sum(v for (p, k), v in kind.items() if k == "movable"),
            sum(v for (p, k), v in kind.items() if k == "building"),
            sum(v for (p, k), v in kind.items() if k == "gaia_obj"),
            len(tm), sum(len(t.effects) for t in tm), ai_n, ai_rules, offmap))
        return
    players = sorted({p for p, _ in kind})
    for p in players:
        row = {k: kind.get((p, k), 0) for k in ("movable", "building", "gaia_obj", "unknown")}
        if any(row.values()):
            print(f"  p{p}: movable={row['movable']} bld={row['building']} "
                  f"gaia={row['gaia_obj']} unknown={row['unknown']}")
    tm = scn.trigger_manager.triggers
    create_eff = sum(1 for t in tm for e in t.effects if e.effect_type == 3)
    looping = sum(1 for t in tm if getattr(t, "looping", False))
    print(f"triggers: {len(tm)} (looping {looping}) | effects: "
          f"{sum(len(t.effects) for t in tm)} (create_object {create_eff})")
    s = scn.sections["PlayerDataTwo"]
    for n, f in zip(s.ai_names, s.ai_files):
        if not n:
            continue
        try:
            txt = f.get_data_as_bytes().decode("utf-8", errors="replace")
            rules = sum(1 for l in txt.splitlines()
                        if l.strip().lower().startswith("(defrule"))
            print(f"  AI: {n} ({len(txt)} B, ~{rules} defrules)")
        except Exception as e:
            print(f"  AI: {n} (unreadable: {e})")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--csv"]
    if args and args[0] == "--dir":
        base = args[1]
        files = []
        for root, _, names in os.walk(base):
            files += [os.path.join(root, n) for n in names if n.endswith(".aoe2scenario")]
        for i, f in enumerate(sorted(files)):
            r = subprocess.run([sys.executable, __file__, f, "--csv"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            line = next((l for l in r.stdout.splitlines() if l.startswith("CSV|")), None)
            if line:
                print(f"{line}|{f}", flush=True)
            else:
                print(f"SKIP|{os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(f))))}"
                      f"|{os.path.basename(f)}", flush=True)
    else:
        if len(args) < 1:
            sys.exit(__doc__)
        for p in args:
            probe(p)
