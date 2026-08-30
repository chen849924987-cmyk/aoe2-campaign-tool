# -*- coding: utf-8 -*-
"""部署翻译后的场景到 mods\\local，并确保本地 mod 能被游戏识别。

背景（Kaesong 2026-08-30 踩坑）：本地 mod 文件夹若缺 info.json，游戏的
Mod 管理器根本不显示它——无法启用，进游戏永远加载英文订阅版。场景文件
本身再正确也没用。本脚本 copy2 部署 + MD5 校验 + 自动补 info.json。

用法：
  python deploy.py <翻译后的场景文件> "<mod文件夹名>" [目标场景文件名] [子树]

- 目标文件名解析优先级：显式第3参数 > 目标目录里已有的唯一 .aoe2scenario >
  源文件名兜底。战役注册表按精确文件名加载场景，**绝不能改名部署**；
  目标目录已有多个场景文件时必须显式指定，否则报错退出。
- 子树镜像（Exodus/RoR 2026-08-30 踩坑）：RoR 类 mod 的场景不在
  resources\\_common\\scenario 直下，而在 modes\\<Mode>\\resources\\_common\\scenario
  子树。本脚本从源路径自动提取该子树并在本地 mod 内镜像，无需手工干预。
- 源目录含多个场景（多关战役）且未显式指定目标名时直接报错——防止第 2 关
  起沿用第 1 关文件名造成静默覆盖。
- 游戏 user 目录：环境变量 AOE2_USER_DIR，或改下方 USER_DIR 常量。

部署后游戏内操作：Mods → 本地 mods → 启用该 mod → 重启游戏。
"""
import hashlib
import json
import os
import shutil
import sys

try:  # Windows 控制台中文输出
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

USER_DIR = r"C:\Users\84992\Games\Age of Empires 2 DE\76561199180119163"


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    src, mod = sys.argv[1], sys.argv[2]
    user = os.environ.get("AOE2_USER_DIR", USER_DIR)
    if not os.path.isfile(src):
        print("源文件不存在:", src)
        sys.exit(1)

    mod_root = os.path.join(user, "mods", "local", mod)

    # 子树镜像：RoR 类 mod 场景在 modes\<Mode>\resources\_common\scenario，
    # 普通 mod 在 resources\_common\scenario。自动从源路径提取（modes 优先）；
    # 源是构建产物时可用第4参数显式指定子树。
    src_dir = os.path.dirname(os.path.abspath(src))
    norm_parts = [p for p in os.path.normpath(src_dir).split(os.sep)]
    low = [p.lower() for p in norm_parts]
    i_modes = low.index("modes") if "modes" in low else None
    i_res = low.index("resources") if "resources" in low else None
    start = i_modes if i_modes is not None else i_res
    if start is not None:
        subtree = os.path.join(*norm_parts[start:])
    else:
        subtree = os.path.join("resources", "_common", "scenario")
    if len(sys.argv) > 4:  # 显式子树覆盖（构建产物部署 RoR mod 时必须）
        subtree = sys.argv[4]
    dst_dir = os.path.join(mod_root, subtree)
    os.makedirs(dst_dir, exist_ok=True)

    # 源目录场景数自检：多场景战役必须显式指定目标文件名（防静默覆盖）
    src_scen = [fn for fn in os.listdir(src_dir)
                if fn.lower().endswith(".aoe2scenario")]
    if len(src_scen) > 1 and len(sys.argv) <= 3:
        print("源目录含 %d 个场景文件（多关战役），必须显式指定目标文件名:" % len(src_scen))
        for fn in src_scen:
            print("  -", fn)
        sys.exit(1)

    # 目标文件名解析：战役按精确文件名加载场景，绝不能改名部署。
    # ⚠️ 不要用 glob：mod 目录名里的 [936]/[RoR] 会被 glob 当字符类，返回空！
    # os.listdir 不做通配符解释。
    existing = sorted(fn for fn in os.listdir(dst_dir)
                      if fn.lower().endswith(".aoe2scenario"))
    if len(sys.argv) > 3:
        target = sys.argv[3]
    elif len(existing) == 1:
        target = os.path.basename(existing[0])
        print("[提示] 沿用目标目录已有场景文件名:", target)
    elif len(existing) > 1:
        print("目标目录已有多个场景文件，必须显式指定目标文件名：")
        for p in existing:
            print("  -", os.path.basename(p))
        sys.exit(1)
    else:
        target = os.path.basename(src)
    dst = os.path.join(dst_dir, target)
    shutil.copy2(src, dst)

    # info.json 自检：缺失则生成最小合法四字段（Author/CacheStatus/Description/Title）
    info = os.path.join(mod_root, "info.json")
    if not os.path.exists(info):
        with open(info, "w", encoding="utf-8") as f:
            json.dump({"Author": "Unpublished", "CacheStatus": 1,
                       "Description": "No Description", "Title": mod},
                      f, ensure_ascii=False)
        print("[修复] info.json 原本缺失，已生成:", info)

    a, b = md5(src), md5(dst)
    print("部署到 :", dst)
    print("MD5    :", b, "(一致)" if a == b else "(不一致! 源=%s)" % a)
    if a != b:
        sys.exit(1)
    print("OK — 游戏内: Mods → 本地 mods → 启用 [%s] → 重启游戏" % mod)


if __name__ == "__main__":
    main()
