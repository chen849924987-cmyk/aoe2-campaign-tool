---
name: aoe2-campaign-translate
description: 帝国时代2决定版(AoE2:DE)创意工坊战役汉化完整工作流：版本探测→文本导出→字典翻译→字节级构建→部署本地mod→三层审计。只要用户提到帝国时代2/AoE2/aoe2/战役翻译/汉化/本地化/.aoe2scenario/创意工坊mod中文化，或抱怨战役里任务栏、悬浮窗、对白、提示还有英文，或遇到汉化mod变回英文/从列表消失，就使用本技能。覆盖 trigger 3.9/4.5/4.7/4.9 与旧格式(≤3.x)。
---

# 帝国时代2战役翻译（AoE2:DE 创意工坊战役汉化）

把订阅的英文战役 mod 汉化成中文：只改屏幕文字（简报/目标/提示/对白字幕/改名），
**语音无法汉化**。核心原则：**字节级读写保真**（不用 parser 写回，重压缩不可验证）、
**三层文本全覆盖**、**部署后三层审计全绿才算完**。

## 环境与资产（本机固定路径）

| 资产 | 路径 |
|---|---|
| 工具链（git 仓库） | `D:\工作\帝国时代2战役翻译手册\aoe2-campaign-tool\` |
| 批量工作流引擎与字典 | `D:\工作\帝国时代2战役翻译手册\aoe2-translate\batch\` |
| 游戏 mods 目录 | `C:\Users\84992\Games\Age of Empires 2 DE\76561199180119163\mods\` |
| 进度/剩余战役/译名 | `D:\工作\帝国时代2战役翻译手册\待办清单-剩余战役.md` |
| 权威经验文档 | `D:\工作\帝国时代2战役翻译手册\汉化经验总结.md` |
| 依赖 | `pip install "AoE2ScenarioParser>=0.8.4"`（只借解压能力，版本 0.8.4/0.8.5 均可） |

动笔前先读《待办清单》确认该战役状态（是否已开工/已完成/译名表是否已有）；
同系列战役沿用已有译名（详见 `references/glossaries.md`）。

## 三层文本模型（最重要的认知）

玩家可见文本分三层，**缺一层就是漏翻**（2026-09-05 Modu 全 5 关任务栏+悬浮窗
86 条整体漏翻的教训——只翻效果消息的管线和检查器都过了，用户实测才暴露）：

| 层 | 存储位置 | 游戏内表现 | 导出/检查 |
|---|---|---|---|
| 1. 效果 message | 触发器效果的 message 字段（类型白名单见下） | 对白字幕、弹窗、计时器标签、改名、科技名/说明 | `t39_extract.py` |
| 2. 触发器任务文本 | 触发器自身的 `description` / `short_description`，头部标志 display_as_objective / display_on_screen / make_header 置位才显示 | **任务栏(目标列表)** 与 **右上角悬浮窗** | `trigdesc_scan.py --work` |
| 3. Messages 六字段 | 文件头部独立区段（非 trigger blob） | 开场简报/提示/胜负/历史 | dump 脚本逐字段 |

效果类型存于 `e["ints"][0]`（不是 `e["type"]`）：
- **可翻**：3=聊天, 20=显示文本, 26=单位改名, 37=计时器, 44=单位说明, 48=文明改名, 51=属性改名, 59/60=文明/玩家名改名, 65=科技名, 66=科技说明
- **绝不可翻（内部）**：55=XS脚本调用, 56=change_variable, 81/82=key_value；以及 `resp`/`faction`/`Kills` 等内部标记字面量
- 65/66 成对铁律：同触发器里名字和说明要么都翻要么都不翻，否则购买面板"英文名+中文说明"穿帮

## 标准工作流（blob 链，trigger 3.9/4.5/4.7/4.9 自适应）

```bash
cd D:\工作\帝国时代2战役翻译手册\aoe2-campaign-tool

# 1) 版本确认（也可直接读文件头 12 字节）+ roundtrip 自检，PASSED 才继续
python scnver.py "<场景.aoe2scenario>"
python selftest.py "<场景.aoe2scenario>"

# 2) 导出效果文本 + 任务文本工作单
python t39_extract.py "<场景>" texts.json          # 含 desc/short/eff_msg 条目
python trigdesc_scan.py --work "<场景>" work.txt   # 任务栏/悬浮窗全文（repr）

# 3) 写字典 mydict.py（T_M 列表，见下方"字典规范"）+ msgs 模块（MSGS dict）

# 4) 构建（匹配→blob重建→Messages替换→重压缩→自验证一条龙）
python translate.py "<场景>" texts.json mydict out.aoe2scenario [msgs模块]

# 5) 部署到 mods\local（绝不是 subscribed！）
python deploy.py out.aoe2scenario "<mod名> 简体中文汉化" "[目标场景文件名]" "[子树]"
#   多关战役每关必须显式传目标文件名；RoR mod 传子树如 modes\Pompeii\resources\_common\scenario

# 6) 收尾门槛（三层审计，全绿才算完）
python audit_cn.py --summary "<local mod 目录>"
python _mc_quickcheck.py "<部署场景>" "关键词1" "关键词2"   # 解压后字节抽查关键译名
```

多关大战役优先用批量引擎：`aoe2-translate\batch\_camp.py`（dump/lint/build/deploy/check
五合一，后台跑用 `_runcamp.py` 防超时；lint 必须补到 0 MISS）。大文件/批量任务可能超
30s 工具超时——超时≠失败，先查日志和产物再决定重跑。

**旧格式（≤3.x 与 1.54+trigger 4.1）**：parser 可直接解析，走 `aoe2-translate\batch\{dump,apply,verify}.py`
旧链；空槽完整原文用 `batch\_srcfor.py <id>` 从 dump2.json 恢复（勿信骨架截断注释）；
产物验证 `_verifylocal2.py`（blob 扫描器不支持旧格式，见 references/pitfalls.md）。
**混版本 mod 旧链铁律**：apply.py 必须加 `--only <文件名子串>` 逐文件单进程调用
（ASP 结构缓存跨版本污染：同进程先写 1.56 再碰 1.54+4.1 会炸 `_eff_filler_1`），
且**每关 apply 后立即复制该关产物进正式本地 mod**——apply 每次 copytree 重建
`<mod> CN` 临时目录，会把之前关卡的翻译覆盖回英文。

## 翻译红线（违反=游戏内乱码/穿帮）

1. **全角括号 `（）` 显示为乱码方框**（游戏字体缺字形）——一律半角 `( )`。中文逗号句号冒号正常。
2. **占位符/颜色标签原样保留**：`<cost>` `<Hp>` `<Attack>` `<PURPLE>` `%d` `<n>` `<food>%` `<!变量名, N>` `<Factions>` 等，只译英文正文。
3. **单位类型名勿翻**：未设自定义名的单位返回兵种类型名（Spearman/Tree Olive…），引擎按游戏语言本地化；只翻英雄/角色自定义名。
4. **前缀与换行结构保留**：目标文本 `+`主目标/`-`支线前缀；`\r` 换行；`======]HINTS[======` 分隔记号；`=]...[=` 作者风格标记。
5. **语音不可汉化**，字幕全翻是常态预期。
6. **原作者拼写错误逐字收录为字典键**（`calvary`/`moutain`/`partnet`/`equiped`、欧式千分位 `10.000`）——键必须逐字复制 dump 原文，翻译正文可纠正。

## 字典规范

- 前缀匹配（最长前缀优先防短吞长）；合并消息必须整条入典，否则只翻前半截丢尾注。
- 同一对白常有多变体：带/不带 `<颜色>` 标签、不同颜色、`\r` 结尾差异、前导空格——逐一收录，别猜，用 lint MISS 逐条对 repr。
- **`\r` 双反斜杠坑**：.py 字典里必须单反斜杠 `\r`；报"明明在字典里却 MISS"先跑 `python batch\_fix_esc.py <字典.py>`（幂等）。
- 弯撇号 `’` 匹配前归一化为 `'`（translate.py 已内置）。
- 译名统一：动笔前查 `references/glossaries.md` 与该战役简报既有译名。

## 部署与游戏侧

- 本地 mod 必须有 `info.json`（四字段 Author/CacheStatus/Title/Description）——deploy.py 自动补；缺它游戏 Mod 列表根本不显示。
- **绝不改 `mods\subscribed`**（创意工坊会还原）。
- 每个新 mod 首次部署后：游戏内 Mods→本地 启用一次并重启游戏。
- **"战役变回英文/汉化 mod 消失"先查 `mods\mod-status.json` 的 Enabled:false**（游戏更新会重置本地 mod 启用状态）：关游戏后跑 `batch\_fixmodstatus.py` 批量恢复，再排查其他。
- 混合战役"部分部署+原版补齐"：补齐时**只复制 CAMPS 未列出的文件名**，严禁整目录复制（会把已部署翻译版覆盖回英文）。
- 部署后核对 MD5 与构建产物一致。

## 排障与深读

- 症状→根因→处置速查表：读 `references/pitfalls.md`（覆盖编码/超时/路径方括号/后台运行/编辑器行号/**ASP 跨版本结构缓存污染/apply copytree 覆盖**等全部已踩坑）。
- 格式与布局细节（版本对应、blob 布局、头部偏移、ASP 口径）：读 `references/format.md`。
- 遇到未支持的 trigger 版本：先跑 `python -c "import struct;print(struct.unpack('<d',blob头8字节)[0])"` 确认真版本——`4.10` 往往是 `%.2f` 把 **4.1** 打出来的假象（1.54 场景+trigger 4.1 走旧链即可，无需逆向）。真新版本才按 `references/format.md` 的"新版本逆向流程"探测布局。
- **新订阅战役先体检**：`python aoe2-campaign-tool\langcheck.py <mod目录>`（ASP 三层中文占比，ENGLISH/MIXED 逐文件判定；路径方括号安全）。ASP 硬拦的文件（如 1.54 文件报 execute_on_load）用 `t39_extract.py`/`scnver.py` 兜底——**ASP 硬拦 ≠ 文件坏**。
- 汉化进度、剩余战役、各战役译名：读《待办清单-剩余战役.md》。
- SP→合作战役改编（另一主题）：读《合作战役改编调研.md》。

## 项目规则（每次任务收尾必须执行）

1. 更新工具/脚本：踩过的坑变成代码自检或自动化，不允许靠人肉记忆规避。
2. 更新《汉化经验总结.md》《待办清单-剩余战役.md》：新结论、新版本号、新坑位同步进对应章节；同战役译名表追加进 `references/glossaries.md`。
3. 不允许只口头总结，下次重踩。
