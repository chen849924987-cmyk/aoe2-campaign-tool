#!/usr/bin/env python3
"""langcheck.py — 新订阅战役语言体检（2026-09-05 新增）

用法:
    python langcheck.py "<mod场景目录或mod根目录>" [更多目录...]

对目录下全部 *.aoe2scenario（含 modes\\ 子树递归）用 ASP 读取，逐文件输出:
    scen=<场景版本> | msgs <中文>/<总数> | trig <中文>/<总数>（触发器 desc/short/效果 message）
全 0 CN = 英文战役，需要翻译；部分 CN = 混合/已翻译，先看残留再定。

坑位规避:
- 路径含方括号（如 538372_Itzcoatl [2P Co-Op]）时 glob 会当字符类吞掉匹配 →
  一律用 os.walk 递归，不用 glob（pitfalls.md "路径方括号" 坑的 scan 版）。
- ASP 对 1.54 场景可能因 execute_on_load(1.55+) 属性硬拦（如 Wallace M5/M7、
  Survive the Night）——报 UnsupportedAttributeError 不代表读不了，改用
  t39_extract.py / scnver.py / selftest.py 确认；语言判断可用 _langcheck 的
  t39 导出兜底。
- ASP 读接口: scn.message_manager / scn.trigger_manager.triggers（0.8.5 无
  object_manager 属性）。
"""
import re, sys, os, io, contextlib

from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

AOE2DEScenario = AoE2DEScenario
AOE2DEScenario._validate_latest_trigger_data_version = lambda self, v: None

CJK = re.compile(r'[\u4e00-\u9fff]')


def stat(s):
    if not isinstance(s, str) or not s:
        return (0, 0)
    return (1, 1 if CJK.search(s) else 0)


def scan_file(f):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        scn = AoE2DEScenario.from_file(f, game_version='DE')
        sv = scn.scenario_version
        mm = scn.message_manager
        m_tot = m_cn = 0
        for a in dir(mm):
            if a.startswith('_'):
                continue
            x, y = stat(getattr(mm, a, None))
            m_tot += x
            m_cn += y
        t_tot = t_cn = 0
        for t in scn.trigger_manager.triggers:
            for attr in ('description', 'short_description'):
                x, y = stat(getattr(t, attr, '') or '')
                t_tot += x
                t_cn += y
            for e in t.effects:
                msg = getattr(e, 'message', None)
                if isinstance(msg, str) and msg:
                    x, y = stat(msg)
                    t_tot += x
                    t_cn += y
    return sv, m_cn, m_tot, t_cn, t_tot


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for root in sys.argv[1:]:
        print(f'### {root}')
        for dirpath, dirnames, filenames in os.walk(root):
            for fn in sorted(filenames):
                if not fn.endswith('.aoe2scenario'):
                    continue
                f = os.path.join(dirpath, fn)
                try:
                    sv, m_cn, m_tot, t_cn, t_tot = scan_file(f)
                    verdict = 'ENGLISH' if (m_cn == 0 and t_cn == 0) else 'MIXED/CN'
                    print(f'  {fn} | scen={sv} | msgs {m_cn}/{m_tot} CN | trig {t_cn}/{t_tot} CN | {verdict}')
                except Exception as ex:
                    print(f'  {fn} | ERROR: {type(ex).__name__} {str(ex)[:90]}')
        sys.stdout.flush()


if __name__ == '__main__':
    main()
