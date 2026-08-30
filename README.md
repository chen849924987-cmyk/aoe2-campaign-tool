# AoE2 DE Campaign Translate Tool (trigger 3.9, 4.5 & 4.7)

[中文](#中文说明) | [English](#english)

<a id="中文说明"></a>
## 中文说明

针对 **Age of Empires II: Definitive Edition** 创意工坊战役的文本提取 /
翻译 / 回写工具链，覆盖官方 AoE2ScenarioParser 0.8.4 不支持的新版触发器：

| scenario 版本 | trigger 数据版本 | 实战验证 |
|---|---|---|
| 1.54–1.55 | **3.9**  | *Alexander the Great (2P Co-Op)* 全 6 关 |
| 1.56       | **4.5**  | *Kaesong [936] (2P Co-Op)* 单关 + *[RoR] The Story of Exodus (2P Co-Op)* 全 5 关（效果 77 int） |
| 1.57–1.58  | **4.7**  | *Modu Chanyu (2P Co-Op)* 全 5 关 |

提取 / 回写 / 验证全流程**自动识别版本**；每个文件的 Triggers 段布局模型均通过
逐字节 roundtrip（解析→重建与原文件完全一致）验证。

### 工作原理（parser-bypass）

`AoE2ScenarioParser 0.8.4` 解析 trigger 3.9/4.7 时会直接抛异常退出。本工具链的思路：

1. **grab**（`t39_build.grab`）：猴子补丁 `_validate_latest_trigger_data_version`，
   在 parser 读完 FileHeader、拿到 **解压后的完整文件数据** 后借校验回调抛出自定义
   `Stop` 异常截获数据 —— 只用 parser 的解压/组装能力，跳过 Triggers 段解析。
2. **定位**（`analyze_t39.find_triggers_offset`）：在解压数据里搜索
   `<double 版本号>` + `魔数(1B)` + `触发器数(4B)` 锚点定位 Triggers 段起点
   （3.9 魔数=0，4.7 魔数=1，判据通用）。
3. **字节级读写**（`t39_blob_rw` / `t47_blob_rw`，`get_blob_rw(tv)` 按版本选择）：
   按逆向出的布局解析/重建 Triggers blob（`parse_blob` / `render_blob`，含逐字节
   roundtrip 自检）。各版主要差异：trigger 头 26B→27B、效果 60→77/83 int
   （4.5=77、4.7=83）、条件 29→35 int、版本门控 fill 字段并入固定 int 区；详见各模块 docstring。
4. **回写**（`t39_build.build`）：替换 blob → 字节定位 Messages 区段（str16 字段，
   支持开场提示/侦察报告等）→ 重新 raw-deflate 压缩 → 截取原文件头部拼接输出。

### 文件

| 文件 | 作用 |
|---|---|
| `analyze_t39.py` | grab 解压数据（parser-bypass）、定位 Triggers 段、按版本选择读写器 |
| `t39_blob_rw.py` | trigger 3.9 blob 的字节级解析/重建（核心） |
| `t47_blob_rw.py` | trigger 4.5/4.7（场景 1.56+）blob 的字节级解析/重建（核心，按版本自适应效果 int 数） |
| `t39_extract.py` | 导出全部可翻译文本为 JSON（版本自适应） |
| `t39_build.py`   | 把翻译写回战役文件（含 Messages 区段替换，版本自适应） |
| `translate.py`   | 通用引擎：字典匹配 → build → 自验证（版本自适应） |
| `deploy.py`      | 部署场景到 `mods\local`：保持原文件名 + MD5 校验 + 自动补 info.json（缺失时游戏 Mod 列表不显示） |
| `scnver.py`      | 场景版本探测（纯 zlib，无需安装 parser） |
| `selftest.py`    | roundtrip 自检：验证工具对给定场景的支持是否完整 |
| `dict_common.py` | 通用字典模板（示例条目可改） |
| `_test_dict.py`  | 最小字典示例 |

### 快速上手

```bash
pip install AoE2ScenarioParser==0.8.4

# 0) 看场景版本 / 先自检工具对该文件的支持（逐字节 roundtrip）
python scnver.py "战役.aoe2scenario"
python selftest.py "战役.aoe2scenario"

# 1) 导出文本（3.9/4.7 自动识别）
python t39_extract.py "战役.aoe2scenario" texts.json

# 2) 建字典 mydict.py（见 dict_common.py 模板），然后一键翻译+回写+验证
python translate.py "战役.aoe2scenario" texts.json mydict out.aoe2scenario [msgs]

# 3) 部署（保持原场景文件名 + MD5 校验 + 自动补 info.json）
python deploy.py out.aoe2scenario "<mod名> 简体中文汉化"
#    多关战役：每关都必须显式传目标场景文件名（否则报错/静默覆盖）：
python deploy.py m2_out.aoe2scenario "<mod名> 简体中文汉化" "Mission 2.aoe2scenario"
#    RoR 类 mod：场景在 modes\<Mode>\ 子树下，本地 mod 必须镜像同样子树。
#    源路径含 modes\ 时自动提取；源是构建产物时用第 4 参显式指定：
python deploy.py m1_out.aoe2scenario "<mod名> 简体中文汉化" "Mission 1.aoe2scenario" "modes\Pompeii\resources\_common\scenario"
#    本地 mod 必须有 info.json 才会出现在游戏 Mod 列表（deploy.py 自动生成）；
#    每个新 mod 首次部署后：游戏内 Mods → 本地 mods 启用 → 重启游戏。
#    （不要动 mods/subscribed —— 创意工坊会还原订阅文件）
```

### ⚠️ 翻译红线

- **全角括号 `（）`(U+FF08/FF09) 游戏内显示为乱码方框**，一律用半角 `( )`；
  中文逗号句号等标点正常。
- 效果类型存于 `e["ints"][0]`（非 `e["type"]`）：20=显示文本、51=单位改名、
  48=文明改名（可翻）；**56=内部标记，绝不可翻**。
  `resp`/`faction`/`treaty`/`shrine`/`Kills`... 等短字面量是触发器变量名，别动。
- `<cost>` `<Hp>` `<PURPLE>` `%d` 等占位符/颜色标签原样保留。

<a id="english"></a>
## English

Text extraction / translation / rebuild toolchain for AoE2 DE workshop campaigns,
covering **trigger data versions 3.9 (scenario 1.54–1.55), 4.5 (scenario 1.56)
and 4.7 (scenario 1.57–1.58)** — none of them supported by AoE2ScenarioParser
0.8.4. The pipeline detects the version automatically. Battle-tested on all 6
missions of *"Alexander the Great (2P Co-Op)"* (3.9), all 5 missions of
*"Modu Chanyu (2P Co-Op)"* (4.7), *"Kaesong [936] (2P Co-Op)"* (4.5) and all
5 missions of *"[RoR] The Story of Exodus (2P Co-Op)"* (4.5, Return-of-Rome
mod with a `modes\<Mode>\` subtree layout).
Every supported file passes a byte-identical parse→rebuild roundtrip check.

**Parser bypass**: we monkey-patch `_validate_latest_trigger_data_version` to capture
the decompressed file right after the parser reads the FileHeader (it aborts later on
new trigger versions), locate the Triggers section via a `<f64 version><u8 magic><i32>`
anchor, then parse/rebuild the blob byte-by-byte (`t39_blob_rw.py` / `t47_blob_rw.py`,
layout documented in their docstrings, verified by byte-identical roundtrip). Messages
section (hints/scouts, str16 fields) is located by raw byte search and replaced before
re-deflating.

**Translation gotchas**: full-width parentheses `（）` render as tofu boxes in game —
always use ASCII `( )`. Effect type lives at `e["ints"][0]` (20=display text,
51=unit rename, 48=civ rename are translatable; 56=internal marker is not).
Short literals like `resp`/`faction`/`treaty`/`Kills` are trigger variables — keep them.

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer / 免责声明

> 本项目为非官方的玩家自制 Mod 工具，与 Microsoft、World's Edge、Forgotten Empires
> 无任何隶属、赞助或认可关系。*Age of Empires* 是 Microsoft 的商标，此处仅为描述
> 兼容性之用途（nominative use）。本仓库不含、不分发任何游戏资源或战役文件。
>
> Unofficial fan-made modding tool. Not affiliated with, endorsed by, or sponsored
> by Microsoft, World's Edge, or Forgotten Empires. *Age of Empires* is a trademark
> of Microsoft, used here only to describe compatibility. This repository contains
> no game assets or campaign files.

## 致谢 / Credits

- [AoE2ScenarioParser](https://github.com/KSneijders/AoE2ScenarioParser) by KSneijders
- Kickstarter: *Alexander the Great (2P Co-Op)* 等优秀工坊战役的作者们
