# 场景格式与版本细节

## 版本对应表（场景版本串 = 解压数据头 12 字节；原始文件整体 zlib 压缩）

| 场景版本 | trigger 版本 | 布局 | 工具 | 实战验证 |
|---|---|---|---|---|
| ≤1.53 | ≤3.x 旧格式 | parser 可直接解析 | 旧链 batch/{dump,apply,verify}.py | Orkney/Lechfeld |
| 1.54–1.55 | **3.9** | 效果 60 int，头 26B | t39_blob_rw.py | Alexander/Bhoja 等 |
| 1.54 | **4.10** | 效果 int 数未知，**需逆向** | ❌ 暂不支持 | Aegidius/Cortes M5-M6 |
| 1.56 | **4.5** | 效果 77 int | t47_blob_rw.py | Kaesong/Exodus |
| 1.57–1.58 | **4.7** | 效果 83 int | t47_blob_rw.py | Modu/Edward/Viking 部分 |
| 1.58 后期 | **4.9** | 效果 85 int（=4.7+2），效果类型可 >95 | t47_blob_rw.py | Jarls/GH2/Calakmul 等 |

- **战役内可混版本**（如 Gonzalo M4=4.5 其余 3.9；Viking M1/2/4/6=4.5、M3/5=4.7）——工具按文件自适应，但 check 时扫一眼每关 tv= 打印。
- `t47_blob_rw.parse_blob` 从 blob 前 8 字节版本 double 自读版本选布局；未知版本抛 ValueError。

## 触发器头部标志位（任务栏/悬浮窗判定，audit_cn.py / trigdesc_scan.py 内置）

| 布局 | 头长 | display_as_objective(任务栏) | make_header(分节标题) | display_on_screen(悬浮窗) |
|---|---|---|---|---|
| 3.9 | 26B | head[9] | head[14] | head[19] |
| 4.x | 27B（多 1B execute_on_load） | head[10] | head[15] | head[20] |

## blob 布局（4.x；3.9 差异见 t39_blob_rw.py 头注释）

```
8B 版本 double | 1B 魔数 | 4B 触发器数
每触发器:
  头 27B: enabled(4) looping(1) execute_on_load(1) desc_stid(4) disp_as_obj(1)
          obj_order(4) make_header(1) short_stid(4) display_on_screen(1) unknown(5) mute(1)
  3 个 str32: description / name / short_description   ← name 是编辑器专用可跳过
  4B 效果数 | 效果×N | 4B×N 顺序
  4B 条件数 | 条件×M | 4B×M 顺序
效果 = EFF_INTS×s32 + str32 message + str32 sound + s32×max(ints[6],0) + str32 opt1 + str32 opt2
条件 = 35×s32 + str32 xs_function（3.9 为 29 int + fill）
尾部 = 4B×触发器数顺序数组 + 其余数据（变量等，原样保留）
```

- Messages 六字段（instructions/hints/victory/loss/history/scouts）不在 blob 里，是文件头部独立区段，str16 整段替换，保留 `======]HINTS[======` 记号。**hints 与 scouts 是两个独立字段，每关都要查**（Alexander 曾只翻 scouts 漏 hints）。
- msgs 可能不止 hints/scouts（victory/loss/history 因关而异）——dump 后先看全字段表再动笔。
- 场景文件 zlib(raw-deflate) 压缩：**不能对原始文件字节搜索中文验证**，必须解压后查。
- 中文字节判定：前 80-200 字节含 0xE4–0xE9。

## 效果类型语义（e["ints"][0]；对照 ASP master effects.json）

- 玩家可见（可翻）：3 send_chat / 20 display_instructions / 26 change_object_name / 37 display_timer(保留 %d) / 44 change_object_description / 48 change_civilization_name / 51 modify_attribute(单位改名) / 59 change_object_civilization_name / 60 change_object_player_name / 65 change_technology_name / 66 change_technology_description
- 内部（绝不翻）：55 script_call(XS 代码) / 56 change_variable / 81 load_key_value / 82 store_key_value
- 65/66 成对：拿不准 65 是否玩家可见时，看同触发器 66 是否已翻。

## AoE2ScenarioParser (ASP) 口径（为何不依赖它读写 Triggers）

- ASP "支持 1.36→1.58" 指**场景版本**（按 versions/DE/v<场景版本>/structure.json 选布局），与文件内 trigger_version 数值无关。0.8.5 可正确**读** 4.5/4.7/4.9。
- 3.9 属 1.54 场景旧结构，被 `_validate_latest_trigger_data_version` 硬拦（UnsupportedVersionError，任何 ASP 版本）。
- ASP 写回重压缩，无法 MD5 级保真——本工具链对全部版本用字节级 blob 读写（grab 借 ASP 解压到 FileHeader 即截停）。
- 结构定义权威来源：ASP GitHub master `versions/DE/v<版本>/structure.json` + `effects.json`；GitHub 直连不通用 CDN `https://cdn.jsdelivr.net/gh/KSneijders/AoE2ScenarioParser@master/...`。

## 新版本逆向流程（如 4.10）

1. `batch\_probe_ks.py` 方法：HDR×EFF×COND 全组合暴力扫描，roundtrip 可解析 + 类型/字符串合法性打分取唯一解（4.5 即 (27,77,35) 用此法锁定）。
2. 对照 ASP structure.json 静态核对字段数；放宽效果类型白名单（4.9 类型可 >95）。
3. 全部触发器 roundtrip identical 后才可进入翻译流程。
