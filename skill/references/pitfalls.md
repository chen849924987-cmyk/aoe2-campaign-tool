# 坑位速查表（症状 → 根因 → 处置）

全部为实战踩过的坑。遇到症状先查此表，别从头排查。

## 游戏内表现类

| 症状 | 根因 | 处置 |
|---|---|---|
| 战役变回英文 / 汉化 mod 从列表消失 | `mods\mod-status.json` 被游戏更新重置为 `Enabled:false`（不是文件丢了） | 关游戏 → 跑 `batch\_fixmodstatus.py`（自动备份+批量恢复）→ 先 `_verifylocal.py <场景>` 确认文件本身中文完好再动手翻 |
| 全角括号显示为方框乱码 | 游戏字体缺 U+FF08/FF09 字形 | 一律半角 `( )`；中文逗号句号冒号等正常 |
| 任务栏/悬浮窗英文，对白提示正常 | 触发器 description/short_description 层漏翻（管线/检查只覆盖了效果层） | `trigdesc_scan.py --work` 出工作单补翻；收尾跑 `audit_cn.py` 三层审计 |
| 购买面板"英文名+中文说明"穿帮 | 65(科技名)被当内部跳过而 66(说明)翻了 | 65/66 一律当玩家可见处理，成对入典 |
| 开场提示仍英文 | ascii_hints 与 ascii_scouts 是两个独立字段，只翻了其一 | 每关六字段逐一 dump 检查（victory/loss/history 也可能有） |
| 本地 mod 游戏里找不到 | 缺 `info.json`（Mod 列表不显示） | deploy.py 自动补；四字段 {Author, CacheStatus, Description, Title} |
| RoR mod 游戏读不到场景 | 场景在 `modes\<Mode>\resources\_common\scenario\` 子树，本地 mod 未镜像 | deploy.py 自动提取子树（modes 优先），或第 4 参显式指定 |
| 多关战役第 2 关起覆盖第 1 关 | deploy.py"沿用已有文件名"逻辑为单关设计 | 每关显式传目标场景文件名（现多场景未指定会直接报错） |
| 补齐未译关卡后已译关卡变回英文 | 整目录复制把翻译版覆盖回原版 | 只复制 CAMPS 表未列出的文件名，严禁 `Copy-Item` 整目录 |
| 间隔空格字幕（`1 2 3 6 A . D .`）排版破坏 | 直译丢空格 | 中文也加空格保持排版（"公 元 1 2 3 6 年"），入典 |

## 字典/匹配类

| 症状 | 根因 | 处置 |
|---|---|---|
| 键明明在字典里却 MISS | .py 字典里写了字面 `\\r`（双反斜杠），Python 读成反斜杠+r 两字符 | `python batch\_fix_esc.py <字典.py>`（幂等）；排查用 repr(key) vs repr(orig) 对首字符 |
| 只翻出前半截、丢尾注 | 合并消息（目标完成+尾注）没整条入典，前缀匹配截断 | 整条收录；引擎用最长前缀优先 |
| 短条目吞长条目 | 顺序匹配下短前缀先命中 | 长条目在前 / 用最长前缀优先引擎（`_camp.py` 链已内置） |
| 变体句反复 MISS | 同句带/不带颜色标签、`\r` 结尾差异、前导空格、单复数、英美拼写（Armour/Armor）、原文拼写错误 | 别猜，lint MISS 逐条对 repr，逐字复制入典 |
| lint 永远误报框架句 MISS | 只查战役字典，没并入通用字典（任务栏头/系统消息在 T_COMMON） | lint 必须计入通用字典条目 |
| 拆分 msgs 后 build 用旧定义 | `_<key>_msgs_cn.py` 还是旧完整文件而非 import 合并器（build 静默用旧版） | 拆分后必查合并器；build 后 `_verifymsgs.py <key> 1` 抽查产物 |

## 脚本/环境类

| 症状 | 根因 | 处置 |
|---|---|---|
| 命令超时但日志显示已完成 | 前台超时的进程并未被杀，仍会跑完写文件 | 先查日志/产物再重跑，勿重复劳动 |
| 后台作业秒死无日志 | `Start-Job` 挂瞬时会话；`-ArgumentList` 内双引号被 PowerShell 剥离 | 让脚本自写日志 + `Start-Process python <脚本> -WindowStyle Hidden`（不带 Redirect）；范例 `batch\_runcamp.py` |
| PowerShell 内嵌 python -c 多行必炸 | 转义剥离/here-string/GBK 控制台 | 超过一行的 Python 逻辑一律落 .py 文件；脚本开头 `sys.stdout.reconfigure(encoding="utf-8")` |
| 路径含 `[936]`/`[RoR]` 查无此文件 | PowerShell `Get-ChildItem` 和 Python glob 都把 `[]` 当通配符/字符类 | PS 用 `-LiteralPath`；Python 用 os.listdir / glob.escape |
| editor 插行后 SyntaxError | `insert_line` 定位在 `]),` 前破坏括号 | 结构化代码用锚点行 old/new 替换；插完 `py_compile` 验证 |
| batch 脚本 import 不到工具 | batch 在 `aoe2-translate\batch` 下，上跳一级不够 | `sys.path` 上跳**两级**再拼 `aoe2-campaign-tool` |
| md5sum 对比误报 DIFF | 路径含反斜杠时输出加 `\` 前缀，cut 截取带前缀 | 用 Python hashlib 对比，或剥前缀 |
| 中文路径作命令行参数失败 | bash/PS 传参编码损坏 | 路径解析放 Python 内部（os.listdir 父目录为 ASCII） |
| parser 拒绝覆盖源文件 | ASP 设计限制 | 写临时路径再 os.replace 回去 |
| json.load info.json 报错 | Description 含未转义双引号（坏 JSON 是常态） | 别硬解，新建合法 JSON 保留四字段 |
| 输出重定向后台跑日志为空 | Python stdout 块缓冲 | `python -u` + 脚本自写日志文件 |

## 判定口径类

- **is_internal 不能按"单词形态"一刀切**：类型 26/48/51/59/60 的小写单词改名也是玩家可见（Calakmul 的 engineer/chief 踩过）。现行规则：下划线标识符/全小写单词/INTERNAL_WORDS 白名单→内部；首字母大写单词与多词短语一律入典，真内部用 DICT_SKIP 声明。以 `_camp.py check` 效果类型为准（排除 55/56/81/82）。
- **旧链骨架的 None 也要过 verify**（Orkney Wolfdog/Wolfhound/Bridei 漏翻踩过；Santa Maria 的 Chieftain/Sangihe、Shimazu 的 Hikikomori/Daimyo/Challenges 同款）。None/空槽定性法：dump2 entries 查位置 → ASP 读效果 `effect_type`（26/48=改名要翻、65/66=科技名要翻、37=计时器保 %d、56=变量名保持英文）。
- **type56 变量名与 `<占位符>` 必须逐字一致**（Shimazu 13 条空串槽实为变量名踩过）：`conversions needed`/`Shipwrecks Found` 这类既是 change_variable 的变量名、又被任务栏文本以 `<...>` 引用——两边都保持英文原样，单翻任何一边都会断引用；中文变量名是否可解析未知，勿试。
- **骨架注释是截断预览**，完整原文以 `dump2.json` 的 `strings[].i → orig` 为权威（`_srcfor.py`，2026-09-05 已改索引直取零歧义）。
- **原场景已含中文时**，`<RED>` 等标签会骗过"含英文"判定——用 `re.search(r'[A-Za-z]{3,}', orig) 且无汉字` 过滤真英文。
- 翻完判定：lint 0 MISS + `audit_cn.py` 三层全绿 + fullcheck 无残留（除 55/56 外 SKIP 掉的可疑条目要留档复查）。
- 单关文本约 200-270 条，name 类约 40-50% 可跳过，实际 150-250 条/关；字典单次编辑 ≤45 条/块（编辑器 6000 字符上限）。

## 新批次坑位（2026-09-05 晚，5 战役 25 关实战）

| 症状 | 根因 | 处置 |
|---|---|---|
| 旧链 apply 写回炸 `ScenarioWritingError`→内层 `_eff_filler_1 ... Current version: 1.56` | **ASP 结构缓存跨版本污染**：同一进程先写 1.56 文件再处理 1.54+trigger4.1 文件，effect struct 上下文残留 1.56 | apply.py 已加 `--only <文件名子串>` 参数——**混版本 mod 必须逐文件单进程调用** |
| 逐文件 apply 后某几关又变回英文 | apply 每次 copytree 重建整个 `<mod> CN` 临时目录，后一次运行把前一次的翻译产物覆盖回英文 | **每关 apply 后立即把该关产物复制进正式本地 mod**，全部完成后再删临时目录 |
| blob 链报 `unsupported trigger version 4.10` | `%.2f` 显示假象——blob 头版本 double 实为 **4.1**（`b'ffffff\x10@'`），与 Aegidius/Cortes 同版 | 场景 1.54+blob 4.1 = 走旧链（ASP 可读写），别去逆向 4.10 布局；版本真相看 `python -c "import struct;print(struct.unpack('<d',blob[:8])[0])"` |
| 旧链 verify `ENGLISH_LEFT` 数百条 | 触发器 name（作者备注/变量名）不计入 skip 口径之外，作者备注 description（无 OBJ 标志，游戏不显示）有意保留英文 | 逐条核对：带 `[OBJ]/[OSCR]` 标志的必须译；无标志的 name/备注/计数器（`DocksDestroyed` 等 type56 显示名）保留英文是**正确终态** |
| `ascii_history` 漏翻（check 报 msgs residual） | 历史正文是独立字段，不在 hints 里；Ave Caesar 的 hints 内嵌 `==== HISTORY ====` 段 | msgs_cn 的 MSGS_LIST 每关六字段全给；分段标记翻成 `==== 历史 ====`，正文字段与 hints 尾段保持一致 |
| Bash 生成 .py 字典时 `\r` 变成真实 CR 或被吃掉 | 命令行→heredoc→python 多层转义剥离 | **字典/msgs 一律用 Write 工具直写文件**，绝不经 bash 内嵌代码生成 .py；已损坏的用字节级替换修（`b'"\r".join'`→backslash-r） |
| 新订阅 mod 不知道是不是英文 | — | `python aoe2-campaign-tool\langcheck.py <mod目录>`（ASP 三层中文占比体检，os.walk 防方括号坑）；ASP 硬拦的文件用 t39_extract/scnver 兜底 |
| 大 batch 表 mod 的 msgs/字典文件太大不好维护 | 单文件超编辑器上限 | 按 `_itz_dict.py` 模式：长句在前短名在后、DICT_SKIP 声明内部标记；msgs 按关组织 MSGS_LIST |

## langcheck 体检流（新订阅战役标准前置）

```bash
python aoe2-campaign-tool\langcheck.py "<subscribed 模块录>"   # 全 0 CN = 英文需翻
python aoe2-campaign-tool\scnver.py "<场景>"                    # 场景版本 → 定工具链
```
版本→工具链速查（2026-09-05 更新）：1.41~1.53=旧链；1.54 可含 3.9(blob) 或 4.1(旧链)；1.56=4.5；1.57=4.7；1.58=4.7/4.9——**同战役逐关探测，别只测 M1**（Wallace 7 关两种版本混装）。
