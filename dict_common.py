# -*- coding: utf-8 -*-
"""通用字典模板：跨关卡复用的条目（任务栏头/系统消息/单位说明/英雄警告/通用改名）。

规则：
  1. 前缀匹配 + 顺序敏感：长条目、带 <cost> 的说明条目放前面，短改名条目放最后。
  2. 同一对白因颜色标签不同会有多条变体（<PURPLE>/</YELLOW>...），逐条收录。
  3. 译文一律使用半角括号 ( )——全角 （） 游戏字体缺字形，显示为乱码方框。
  4. <cost> <Hp> <Attack> <PURPLE> <color> %d <变量> 等占位符/标签原样保留。
"""

T_COMMON = [
    # 任务栏头
    ("\u2022 Main Objective(s):", "\u2022 主要目标："),
    ("\r\u2022 Side Objective(s):", "\r\u2022 次要目标："),
    ("MAIN OBJECTIVE", "主要目标"),
    ("SECONDARY OBJECTIVE", "次要目标"),
    # 通用系统消息（示例，按你的战役增删）
    ("-- A Player has been defeated. Mission is lost! --", "-- 有玩家已被击败。任务失败！ --"),
    ("<RED>-- Side Objective Failed! --\rCo-Op partner must not be defeated.", "<RED>-- 次要目标失败！ --\r合作队友不可被击败。"),
    ("- Co-Op partner must not be defeated.", "- 合作队友不可被击败。"),
    ("- · Co-Op partner must not be defeated.", "- · 合作队友不可被击败。"),
    # 英雄状态警告（把 HeroName 换成实际人名/颜色）
    ("<PURPLE>WARNING: HeroName is in danger.", "<PURPLE>警告：英雄陷入危险。"),
    ("<PURPLE>WARNING: HeroName is critical.", "<PURPLE>警告：英雄伤势严重。"),
    ("<PURPLE>WARNING: HeroName is near death.", "<PURPLE>警告：英雄濒临死亡。"),
    # 改名类（放最后）
    ("HeroName", "英雄"),
]

# 内部标记字面量（ translate.py 会自动跳过匹配失败项，这里仅作文档提示，禁止翻译）：
# resp / faction / treaty / shrine / depot / city / dock / market / relic / morale /
# wonder / difficulty / battle / flank / Kills / barding / siege / roxane ...