# AoE2 DE Campaign Translate Tool (trigger 3.9, 4.5, 4.7 & 4.9)

[中文](#中文说明) | [English](#english)

<a id="中文说明"></a>
## 中文说明

针对 **Age of Empires II: Definitive Edition** 创意工坊战役的文本提取 /
翻译 / 回写工具链，覆盖官方 AoE2ScenarioParser 0.8.4 不支持、0.8.5 可读但
无法字节级保真回写的触发器布局：

| scenario 版本 | trigger 数据版本 | 实战验证 |
|---|---|---|
| 1.54–1.55 | **3.9**  | *Alexander the Great (2P Co-Op)* 全 6 关 |
| 1.56       | **4.5**  | *Kaesong [936] (2P Co-Op)* 单关 + *[RoR] The Story of Exodus (2P Co-Op)* 全 5 关（效果 77 int） |
| 1.57–1.58  | **4.7**  | *Modu Chanyu (2P Co-Op)* 全 5 关 |
| 1.58(后期) | **4.9**  | *Jarls of Jelling [Redone] (2P Co-Op)* 全 3 关 + *[Redone] The Golden Horde - II (2P Co-Op)* 全 3 关（= 4.7 + 效果区 2 个新 int，共 85；效果类型可 >95） |

> **ASP 支持口径注**（2026-08-31 实测，详见仓库外 `_asp_probe*.py` / `_asp_live_test*.py`）：
> AoE2ScenarioParser README 的"支持 1.36→1.58"指**场景版本**——它按场景版本选
> `versions/DE/v<场景版本>/structure.json` 布局（v1.56=77 / v1.57=83 / v1.58=85 效果 int），
> 与文件里 trigger_version 数值无关。0.8.5 可正确**读取** 4.5/4.7/4.9（message 与本工具链
> 逐条一致）；但 3.9 属于 1.54 场景的"旧结构"，被 `_validate_latest_trigger_data_version`
> 硬拦（`UnsupportedVersionError`，任何 ASP 版本皆然），且 ASP 写回经重新压缩无法做
> MD5 级保真验证——故本工具链对全部版本均按字节级读写实现。

提取 / 回写 / 验证全流程**自动识别版本**；每个文件的 Triggers 段布局模型均通过
逐字节 roundtrip（解析→重建与原文件完全一致）验证。

### 更新日志 / Changelog

**2026-09-05（晚）**
- 新增 **`langcheck.py`**：新订阅战役语言体检一条龙（ASP 三层中文占比统计，os.walk 规避方括号路径坑；ASP 硬拦的文件建议改用 `t39_extract.py`/`scnver.py` 兜底）。
- 实战验证扩充：*Itzcoatl [2P Co-Op]* 全 5 关（**4.9**，效果 85 int）、*[RoR] Ave Caesar (2P Co-Op)* 全 4 关（4.7，RoR `modes\Pompeii` 子树）、*Survive the Night (Coop)* 单关（4.7）、*Wallace 2 player coop campaign* 4 关（4.5 混版）——blob 链新增四役 11 关全绿。
- **trigger 4.1 澄清**：blob 头版本 double=4.1 常被 `%.2f` 误显为 "4.10"。场景 1.54 + trigger 4.1（*Aegidius* / *Cortes M5-M6* / *Wallace M3-M6* / *征服者战役合作版* 1.41 全 8 关）实测 **ASP 0.8.5 可读可写、roundtrip 保真**，走 ASP 旧链即可，无需字节级逆向；但**同进程混写 1.56 与 1.54+4.1 文件会触发 ASP 结构缓存污染**（`_eff_filler_1` 校验炸）——混版本 mod 必须逐文件单进程处理。
- 收尾门槛升级：部署回归一律 `audit_cn.py --summary`（三层）+ 旧格式 `_verifylocal2.py` 补充。
- 仓库新增 `skill/` 目录：沉淀完整工作流与坑位速查（pitfalls）/ 译名表（glossaries）/ 格式细节（format）。

**2026-09-05**
- `audit_cn.py` 修复 `======]HINTS[======` 分隔符误报；`trigdesc_scan.py` / `audit_cn.py` 三层审计上线（Modu Chanyu 任务栏/悬浮窗 86 条整体漏翻的教训）。

**2026-08-31**
- trigger **4.9** 支持（场景 1.58 后期版，效果 85 int = 4.7 + 2 新 int，效果类型可 >95）；ASP 支持口径查证结论入 README。

### 工作原理（parser-bypass）

对 3.9：ASP 0.8.5 实测仍在版本校验处抛 `UnsupportedVersionError`（1.54 场景的旧
结构被硬拦，任何 ASP 版本皆然）；对 4.5/4.7/4.9：ASP 0.8.5 起可正确读取，但其
写回经重新压缩、无法字节级保真。本工具链的思路：

1. **grab**（`t39_build.grab`）：猴子补丁 `_validate_latest_trigger_data_version`，
   在 parser 读完 FileHeader、拿到 **解压后的完整文件数据** 后借校验回调抛出自定义
   `Stop` 异常截获数据 —— 只用 parser 的解压/组装能力，跳过 Triggers 段解析。
2. **定位**（`analyze_t39.find_triggers_offset`）：在解压数据里搜索
   `<double 版本号>` + `魔数(1B)` + `触发器数(4B)` 锚点定位 Triggers 段起点
   （3.9 魔数=0，4.7 魔数=1，判据通用）。
3. **字节级读写**（`t39_blob_rw` / `t47_blob_rw`，`get_blob_rw(tv)` 按版本选择）：
   按逆向出的布局解析/重建 Triggers blob（`parse_blob` / `render_blob`，含逐字节
   roundtrip 自检）。各版主要差异：trigger 头 26B→27B、效果 60→77/83/85 int
   （4.5=77、4.7=83、4.9=85）、条件 29→35 int、版本门控 fill 字段并入固定 int 区；详见各模块 docstring。
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
| `trigdesc_scan.py` | 触发器**任务文本**扫描器：任务栏(display_as_objective)/右上角悬浮窗(display_on_screen)/分节标题(make_header) 的 description/short_description 残留英文检查 + `--work` 工作单导出（版本自适应） |
| `audit_cn.py`    | 部署回归审计：三层玩家可见文本（效果 message / 触发器任务文本 / Messages 六字段）英文残留一次查清（版本自适应，支持整目录 `--summary`） |
| `langcheck.py`   | **新订阅战役语言体检**：对 mod 目录（含 `modes\` 子树，方括号路径安全）全部场景按三层统计中文占比，逐文件输出 ENGLISH/MIXED——动工前判断"是不是英文战役"用 |
| `dict_common.py` | 通用字典模板（示例条目可改） |
| `skill/`         | 完整工作流技能包（SKILL.md + references/{pitfalls,glossaries,format}.md），可直接作为 AI Agent 技能使用 |

### 快速上手

```bash
pip install "AoE2ScenarioParser>=0.8.4"   # 0.8.4/0.8.5 实测均可用（只借解压/FileHeader 能力）

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

# 4) 部署后回归审计（三层：效果消息 / 任务栏+悬浮窗触发器文本 / Messages 六字段）
python audit_cn.py --summary "<local mod 目录>"     # 全绿才算完
#    ⚠️ 只翻效果 message 会整体漏掉任务栏/悬浮窗（触发器 description 字段，
#    t39_extract 导出的 desc/short 条目）——Modu Chanyu 全 5 关 86 条曾整体漏翻。
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
covering **trigger data versions 3.9 (scenario 1.54–1.55), 4.5 (scenario 1.56),
4.7 (scenario 1.57–1.58) and 4.9 (scenario 1.58 late)**. 3.9 is rejected outright by
AoE2ScenarioParser (old structure of scenario 1.54, `UnsupportedVersionError`, verified
on 0.8.5); 4.5/4.7/4.9 became readable in ASP 0.8.5 (layouts are selected per scenario
version), but ASP's re-compressing writer cannot guarantee byte-identical output.
The pipeline detects the version automatically. Battle-tested on all 6
missions of *"Alexander the Great (2P Co-Op)"* (3.9), all 5 missions of
*"Modu Chanyu (2P Co-Op)"* (4.7), *"Kaesong [936] (2P Co-Op)"* (4.5) and all
5 missions of *"[RoR] The Story of Exodus (2P Co-Op)"* (4.5, Return-of-Rome
mod with a `modes\<Mode>\` subtree layout).
Every supported file passes a byte-identical parse→rebuild roundtrip check.

**Parser bypass**: we monkey-patch `_validate_latest_trigger_data_version` to capture
the decompressed file right after the parser reads the FileHeader (with 3.9 the parser
aborts at that very check; for 4.x we bypass its object model in favour of byte-level
control), locate the Triggers section via a `<f64 version><u8 magic><i32>`
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
