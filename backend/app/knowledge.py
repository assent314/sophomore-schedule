"""学习科学 / 神经科学规则库。

每条规则都是一个可执行排程的「规则卡」：
  id / name / category / summary / mechanism / scheduling_effect / evidence_strength / citations

证据分级说明
  strong    : 多项实验或元分析支持，效应稳定可复现
  moderate  : 有实验支持，但边界条件较多或部分结果存在争议
  emerging  : 机制有说法、证据初步或存在复现争议，仅作为启发式使用

注意：引用只写「作者 / 年份 / 标题 / 期刊」，不编造 DOI。
如需精确检索，可用 citations[].search_url（PubMed / Scholar 搜索链接）。
"""

from __future__ import annotations

from urllib.parse import quote

STRENGTH_LABEL = {"strong": "强证据", "moderate": "中等证据", "emerging": "初步证据"}

CATEGORY_LABEL = {
    "chrono": "昼夜节律与睡眠",
    "encoding": "记忆编码与复习",
    "attention": "注意与专注",
    "recovery": "恢复与运动",
    "motivation": "动机与习惯",
    "planning": "规划与执行偏差",
}

CATEGORY_COLOR = {
    "chrono": "#1a73e8",
    "encoding": "#6d4aff",
    "attention": "#0b8043",
    "recovery": "#e8710a",
    "motivation": "#c5221f",
    "planning": "#5f6368",
}

# 日历方块配色（前端使用）
EVENT_CATEGORY_COLOR = {
    "study": "#1a73e8",
    "work": "#6d4aff",
    "exercise": "#0b8043",
    "life": "#e8710a",
    "admin": "#5f6368",
    "rest": "#12b5cb",
    "social": "#c2185b",
    "fixed": "#3c4043",
}

EVENT_CATEGORY_LABEL = {
    "study": "学习",
    "work": "工作",
    "exercise": "运动",
    "life": "生活",
    "admin": "琐事",
    "rest": "休息",
    "social": "社交",
    "fixed": "固定",
}

KIND_LABEL = {
    "focus": "深度专注",
    "study": "学习",
    "admin": "事务",
    "exercise": "运动",
    "meal": "用餐",
    "rest": "休息",
    "break": "微休息",
    "social": "社交",
    "fixed": "固定安排",
    "commute": "通勤",
    "buffer": "缓冲",
}

KIND_CATEGORY = {
    "focus": "study",
    "study": "study",
    "admin": "admin",
    "exercise": "exercise",
    "meal": "life",
    "rest": "rest",
    "break": "rest",
    "social": "social",
    "fixed": "fixed",
    "commute": "fixed",
    "buffer": "admin",
}


def _cite(authors: str, year: str, title: str, venue: str, note: str = "") -> dict:
    q = quote(f"{authors} {year} {title}")
    return {
        "authors": authors,
        "year": year,
        "title": title,
        "venue": venue,
        "note": note,
        "search_url": f"https://pubmed.ncbi.nlm.nih.gov/?term={q}",
        "scholar_url": f"https://scholar.google.com/scholar?q={q}",
    }


RULES: list[dict] = [
    # ---------------- 昼夜节律与睡眠 ----------------
    {
        "id": "sleep_sufficiency",
        "name": "睡眠是记忆巩固的前提",
        "category": "chrono",
        "summary": "睡眠（尤其慢波睡眠与 REM）参与新记忆的巩固与整合。慢性睡眠不足会累积性损害警觉、工作记忆与情绪调节，此时强行安排高强度学习，投入产出比很差。",
        "mechanism": "睡眠中海马依赖的记忆被系统性重放并转移到新皮层；睡眠剥夺会降低海马 LTP 与突触可塑性，同时抬高杏仁核反应性。",
        "scheduling_effect": [
            "若前夜睡眠 < 6h：当天高认知负荷块总时长上限压到 3h，优先保留 1 个最重要的深度块",
            "若睡眠 < 7h：在上午安排 20min 小睡/闭目休息，并把机械性任务（抄写、整理、背单词）前移",
            "若连续 3 天睡眠 < 6h：先安排补觉（比平时早 60-90min 上床），当天的学习量下调 40%",
        ],
        "evidence_strength": "strong",
        "citations": [
            _cite("Walker MP, Stickgold R", "2006", "Sleep, memory, and plasticity", "Annual Review of Psychology 57:139-166"),
            _cite("Rasch B, Born J", "2013", "About sleep's role in memory", "Physiological Reviews 93(2):681-766"),
            _cite("Van Dongen HPA et al.", "2003", "The cumulative cost of additional wakefulness: dose-response effects on neurobehavioral functions and sleep physiology from chronic sleep restriction and total sleep deprivation", "SLEEP 26(2):117-126"),
        ],
    },
    {
        "id": "circadian_peak",
        "name": "昼夜节律窗口（认知高峰）",
        "category": "chrono",
        "summary": "觉醒度与核心体温存在昼夜波动。多数人的高认知负荷窗口在起床后约 2–4 小时到中午前；午后 13–15 点出现低谷；傍晚觉醒度回升。个体差异大（晨型/夜型），需用反馈校准。",
        "mechanism": "视交叉上核驱动的体温、皮质醇、去甲肾上腺素节律影响前额叶执行功能与注意资源。",
        "scheduling_effect": [
            "把当天最高优先级/最高认知负荷任务放进「个人能量峰值窗口」（默认 09:30–12:00）",
            "低谷段（默认 13:00–15:00）安排：机械性任务、整理、外出办事、午睡、轻度复习",
            "晚间 20:00–22:00 安排回顾/轻量检索练习，不安排全新高难内容",
            "晨型/夜型不同：晨型提前 1h，夜型后移 2–3h（以用户的精力反馈为准）",
        ],
        "evidence_strength": "strong",
        "citations": [
            _cite("Schmidt C et al.", "2007", "A time to think: circadian rhythms in human cognition", "Cognitive Neuropsychology 24(7):755-789"),
            _cite("Valdez P, Reilly T, Waterhouse J", "2008", "Rhythms of mental performance", "Mind, Brain, and Education"),
        ],
    },
    {
        "id": "sleep_consistency",
        "name": "作息规律性",
        "category": "chrono",
        "summary": "相对固定的起床时间比追求完美时长更能稳定节律；周末大幅补觉会造成「社会时差」，让周一效率下降。",
        "mechanism": "光暴露与固定起床时间共同锚定 SCN 节律；节律相位漂移会削弱睡眠质量与白天警觉度。",
        "scheduling_effect": [
            "起床时间视为硬约束，规划不发生成早于起床时间的方块",
            "周末/节假日起床时间与工作日的偏移不超过 1h（超出时在规划备注里提醒）",
            "每天第一块安排为低阻力的「启动块」（15–20min），降低执行门槛",
        ],
        "evidence_strength": "moderate",
        "citations": [
            _cite("Wittmann M et al.", "2006", "Social jetlag: misalignment of biological and social time", "Chronobiology International 23(1-2):497-509"),
        ],
    },
    # ---------------- 记忆编码与复习 ----------------
    {
        "id": "spaced_practice",
        "name": "间隔练习（分散效应）",
        "category": "encoding",
        "summary": "同一内容分散到多次、跨天学习，长期保持显著优于集中突击；间隔时长应按「测试日距离」反推。",
        "mechanism": "每次提取/编码之间的遗忘导致重新编码成本上升（desirable difficulty），反而加深记忆痕迹；集中重复产生熟悉感错觉。",
        "scheduling_effect": [
            "同一科目/主题每天只安排一次，跨天重复（如 D1 学新、D2 复习、D4 复习、D8 复习）",
            "距考试 > 1 个月：间隔 3–7 天；距考试 1–2 周：间隔 1–2 天；< 1 周：每天一次短复习",
            "把「学新内容」与「复习旧内容」排在一天中不同时段，形成双通道",
        ],
        "evidence_strength": "strong",
        "citations": [
            _cite("Cepeda NJ et al.", "2006", "Distributed practice in verbal recall tasks: a review and quantitative synthesis", "Psychological Bulletin 132(3):354-380"),
            _cite("Dunlosky J et al.", "2013", "Improving students' learning with effective learning techniques", "Psychological Science in the Public Interest 14(1):4-58"),
        ],
    },
    {
        "id": "retrieval_practice",
        "name": "检索练习（自我测试）",
        "category": "encoding",
        "summary": "合上书回忆/做题的长期效果优于重复阅读与画思维导图；重读带来的流畅感是误判。",
        "mechanism": "提取本身改变记忆的可及性（提取强度 vs 存储强度），失败提取后的反馈能强化正确路径。",
        "scheduling_effect": [
            "每个学习块的前 5min 用「回忆上次内容」开场，后 5min 用「闭卷自测」收尾",
            "复习块优先做成题/问答形式，而不是重看笔记",
            "在生成的方块 reason 中写明「本块以检索练习为主」",
        ],
        "evidence_strength": "strong",
        "citations": [
            _cite("Roediger HL, Karpicke JD", "2006", "Test-enhanced learning: taking memory tests improves long-term retention", "Psychological Science 17(3):249-255"),
            _cite("Karpicke JD, Blunt JR", "2011", "Retrieval practice produces more learning than elaborative studying with concept mapping", "Science 331(6018):772-775"),
        ],
    },
    {
        "id": "interleaving",
        "name": "交错练习",
        "category": "encoding",
        "summary": "把不同题型/相似概念混排练习，优于分块集中练同一类；短期正确率下降但迁移和辨别能力提升。",
        "mechanism": "交错迫使大脑每次重新选择策略，训练「识别该用哪个方法」这一元认知环节。",
        "scheduling_effect": [
            "同一科目的不同章节/题型尽量同一天混排，而非一周只做一章",
            "数学/物理类：安排「混合题型练习块」；语言类：安排「混合听说读写」块",
            "单块内交错比例不宜过高，初学者可先分块后交错",
        ],
        "evidence_strength": "moderate",
        "citations": [
            _cite("Rohrer D, Taylor K", "2007", "The shuffling of mathematics problems improves learning", "Instructional Science 35:481-498"),
            _cite("Kornell N, Bjork RA", "2008", "Learning concepts and categories: is spacing the 'enemy of induction'?", "Psychological Science 19(6):585-592"),
        ],
    },
    {
        "id": "elaborative_encoding",
        "name": "精细加工与自我解释",
        "category": "encoding",
        "summary": "追问「为什么」「它和我知道的东西怎么联系」能显著提升理解与迁移；单纯标记重点效果有限。",
        "mechanism": "把新材料与既有语义网络连接，形成更多提取路径（ elaboration ）。",
        "scheduling_effect": [
            "学习块内预留 5–10min 写「用自己的话解释一遍」",
            "对难点安排「向别人讲」或「写教学笔记」型任务",
            "笔记类任务单独成块，不塞进被动阅读块里",
        ],
        "evidence_strength": "moderate",
        "citations": [
            _cite("Chi MTH et al.", "1994", "Eliciting self-explanations improves understanding", "Cognitive Science 18(3):439-477"),
        ],
    },
    {
        "id": "generation_effect",
        "name": "生成效应（先想再看）",
        "category": "encoding",
        "summary": "先尝试自己生成答案/解法，再看标准答案，记忆与理解效果优于直接阅读。",
        "mechanism": "主动生成激活相关语义网络，为后续答案提供锚点；失败尝试本身也有益。",
        "scheduling_effect": [
            "新内容块开头安排 3–5min「先猜/先做一题」",
            "错题回顾块优先安排，且先重做再对答案",
        ],
        "evidence_strength": "moderate",
        "citations": [
            _cite("Slamecka NJ, Graf P", "1978", "The generation effect: delineation of a phenomenon", "Journal of Experimental Psychology: Human Learning and Memory 4(6):592-604"),
        ],
    },
    {
        "id": "context_variation",
        "name": "情境变化（编码多样性）",
        "category": "encoding",
        "summary": "在不同地点/时段学习同一内容，可增加提取线索多样性，提升在陌生考场环境下的表现；代价是当下熟悉感下降。",
        "mechanism": "编码特异性原则：多条情境线索 → 更多可用的提取路径。",
        "scheduling_effect": [
            "同一科目的不同复习块分配到不同时段（上午/下午/晚上）",
            "每周至少 1 次「换地方学习」块（如图书馆/咖啡馆）",
            "临近考试时反而要固定环境做题，做「情境匹配」训练",
        ],
        "evidence_strength": "moderate",
        "citations": [
            _cite("Smith SM, Rothkopf EZ", "1984", "Contextual enrichment and distribution of practice in the classroom", "Cognition and Instruction 1(3):341-358"),
            _cite("Bjork RA, Bjork EL", "2011", "Making things hard on yourself, but in a good way: creating desirable difficulties to enhance learning", "Psychology and the Real World"),
        ],
    },
    # ---------------- 注意与专注 ----------------
    {
        "id": "task_switching_cost",
        "name": "任务切换代价",
        "category": "attention",
        "summary": "频繁在任务间切换会产生数十秒到数分钟的切换成本，并留下注意残留；同类任务聚块（batching）可显著减少损耗。",
        "mechanism": "任务集重构（task-set reconfiguration）与目标屏蔽需要前额叶资源，切换后一段时间内仍受前一任务干扰。",
        "scheduling_effect": [
            "同一类型的碎片任务合并成 1–2 个「事务批处理块」（如回消息、填表、打印）",
            "两个深度块之间至少留 5–10min 缓冲，避免紧贴切换",
            "不同学科/项目尽量不在同一小时内交替",
        ],
        "evidence_strength": "strong",
        "citations": [
            _cite("Rubinstein JS, Meyer DE, Evans JE", "2001", "Executive control of cognitive processes in task switching", "Journal of Experimental Psychology: Human Perception and Performance 27(4):763-797"),
            _cite("Monsell S", "2003", "Task switching", "Trends in Cognitive Sciences 7(3):134-140"),
        ],
    },
    {
        "id": "ultradian_block",
        "name": "专注块长度与警觉性衰减",
        "category": "attention",
        "summary": "长时间连续高强度专注会导致警觉性下降（vigilance decrement）。90min 是常用的启发式上限，更稳妥的做法是 45–75min 一块并安排明确恢复。",
        "mechanism": "持续注意依赖的资源耗竭；长时程任务中错误率随时间上升。",
        "scheduling_effect": [
            "单个深度块默认 45–75min，上限 90min（用户档案 max_focus_min 可调）",
            "连续 2 个深度块后必须插入 ≥20min 的中等休息",
            "「90 分钟周期」仅作启发式，若用户反馈 60min 后效率下滑则按 60min 切分",
        ],
        "evidence_strength": "moderate",
        "citations": [
            _cite("Warm JS, Parasuraman R, Matthews G", "2008", "Vigilance requires hard mental work and is stressful", "Human Factors 50(3):433-441"),
            _cite("Ericsson KA, Krampe RT, Tesch-Roemer C", "1993", "The role of deliberate practice in the acquisition of expert performance", "Psychological Review 100(3):363-406"),
        ],
    },
    {
        "id": "micro_break",
        "name": "微休息恢复注意",
        "category": "attention",
        "summary": "短暂、真正的脱离任务（几秒到几分钟、不刷信息流）能防止注意资源持续下滑；关键是「完全脱离目标」。",
        "mechanism": "任务目标的去激活与再激活可缓解持续注意导致的绩效下降。",
        "scheduling_effect": [
            "每 45–50min 安排 5–10min 微休息（起身、看远处、喝水），不安排刷手机",
            "微休息块作为日历方块显式存在（可见、可勾选完成）",
        ],
        "evidence_strength": "moderate",
        "citations": [
            _cite("Ariga A, Lleras A", "2011", "Brief and rare mental 'breaks' keep you focused: deactivation and reactivation of task goals preempt vigilance decrements", "Cognition 118(1):82-89"),
        ],
    },
    {
        "id": "attention_restoration",
        "name": "自然环境的注意力恢复",
        "category": "recovery",
        "summary": "在自然环境中散步/休息可恢复定向注意，效果优于在室内刷手机或看屏幕。",
        "mechanism": "注意恢复理论（ART）：自然环境提供「柔性吸引」，让定向注意系统得以休息。",
        "scheduling_effect": [
            "长休息（≥20min）优先安排为户外散步/室外活动",
            "午后低谷安排 15–20min 户外步行块而不是再刷一轮内容",
        ],
        "evidence_strength": "moderate",
        "citations": [
            _cite("Berman MG, Jonides J, Kaplan S", "2008", "The cognitive benefits of interacting with nature", "Psychological Science 19(12):1207-1212"),
        ],
    },
    # ---------------- 恢复与运动 ----------------
    {
        "id": "exercise_aerobic",
        "name": "有氧运动提升执行功能与记忆",
        "category": "recovery",
        "summary": "中等强度有氧运动（20–40min）可改善执行功能与情绪；运动后短时窗口内进行学习，记忆收益更明显；长期有氧训练与海马体积增加相关。",
        "mechanism": "运动提升脑源性神经营养因子（BDNF）、脑血流与多巴胺/去甲肾上腺素水平，促进突触可塑性。",
        "scheduling_effect": [
            "每天固定 1 个 20–40min 运动块，优先放在午后低谷（替代继续硬撑）",
            "运动后 30–60min 安排需要记忆的学习块（利用运动后的短时窗口）",
            "运动块视为与学习等价的正式任务，不做「有空再说」",
        ],
        "evidence_strength": "moderate",
        "citations": [
            _cite("Hillman CH, Erickson KI, Kramer AF", "2008", "Be smart, exercise your heart: exercise effects on brain and cognition", "Nature Reviews Neuroscience 9(1):58-65"),
            _cite("Roig M et al.", "2013", "The effects of cardiovascular exercise on human memory: a review with meta-analysis", "Neuroscience & Biobehavioral Reviews 37(8):1645-1666"),
            _cite("Erickson KI et al.", "2011", "Exercise training increases size of hippocampus and improves memory", "PNAS 108(7):3017-3022"),
        ],
    },
    {
        "id": "nap_consolidation",
        "name": "小睡与巩固",
        "category": "recovery",
        "summary": "10–20min 小睡可快速提升警觉；60–90min 小睡含慢波/REM，有助记忆巩固但可能有睡眠惯性。",
        "mechanism": "短睡主要恢复警觉；较长睡眠阶段参与海马-皮层记忆重放。",
        "scheduling_effect": [
            "睡眠不足当天：安排 15–20min 小睡块（避开 15:00 之后，以免影响夜间入睡）",
            "学习后立刻安排 10min 闭眼休息，有利于巩固",
        ],
        "evidence_strength": "moderate",
        "citations": [
            _cite("Mednick S, Nakayama K, Stickgold R", "2003", "Sleep-dependent learning: a nap is as good as a night", "Nature Neuroscience 6(7):697-698"),
        ],
    },
    {
        "id": "stress_inverted_u",
        "name": "压力-表现的倒 U 曲线",
        "category": "recovery",
        "summary": "中等唤醒有利于记忆与专注，但慢性或强烈压力会损害前额叶工作记忆，表现为「越急越做不出」。",
        "mechanism": "高浓度儿茶酚胺与皮质醇过度激活会削弱前额叶网络功能。",
        "scheduling_effect": [
            "截止日前一天不排满，留出 1 个 30min 缓冲块用于收尾",
            "出现「连续 2 天未完成任务」时，第二天主动砍掉 1/3 任务量而不是加压",
        ],
        "evidence_strength": "moderate",
        "citations": [
            _cite("Arnsten AFT", "2009", "Stress signalling pathways that impair prefrontal cortex structure and function", "Nature Reviews Neuroscience 10(6):410-422"),
        ],
    },
    # ---------------- 动机与习惯 ----------------
    {
        "id": "implementation_intentions",
        "name": "实施意向（if-then 计划）",
        "category": "motivation",
        "summary": "把「什么时候、在哪、怎么做」写成 if-then 形式，能显著提升目标达成率（元分析 d≈0.65）。",
        "mechanism": "情境线索与目标行为建立自动联结，减少临场决策与意志力消耗。",
        "scheduling_effect": [
            "每个任务方块的 notes 写成「如果到 9:30 我就打开 X 做 Y」",
            "把新习惯绑定到已有稳定线索（如「吃完早饭就背 10 个单词」）",
            "规划时优先输出具体动作，不输出「好好学习」式模糊块",
        ],
        "evidence_strength": "strong",
        "citations": [
            _cite("Gollwitzer PM", "1999", "Implementation intentions: strong effects of simple plans", "American Psychologist 54(7):493-503"),
            _cite("Gollwitzer PM, Sheeran P", "2006", "Implementation intentions and goal achievement: a meta-analysis of effects and processes", "Advances in Experimental Social Psychology 38:69-119"),
        ],
    },
    {
        "id": "habit_cue_consistency",
        "name": "习惯的情境线索",
        "category": "motivation",
        "summary": "习惯由稳定的情境线索自动触发，而非意志力；平均约 66 天可形成自动化，且缺一天影响不大。",
        "mechanism": "重复在相同情境下执行 → 情境-反应联结增强，行为逐渐自动化。",
        "scheduling_effect": [
            "固定习惯（如背单词、运动）安排在每天同一时间、同一触发点之后",
            "习惯块不追求完美连续，中断一天后当天补一小块即可",
        ],
        "evidence_strength": "moderate",
        "citations": [
            _cite("Lally P et al.", "2010", "How are habits formed: modelling habit formation in the real world", "European Journal of Social Psychology 40(6):998-1009"),
            _cite("Wood W, Neal DT", "2007", "A new look at habits and the habit-goal interface", "Psychological Review 114(4):843-863"),
        ],
    },
    {
        "id": "goal_gradient",
        "name": "目标梯度与截止日期",
        "category": "motivation",
        "summary": "越接近目标/截止日期，动机越强；利用这一点可以给任务人为设置「小截止」，但也要防止把大任务堆到最后一刻。",
        "mechanism": "时间动机理论：动机 ≈ (期望×价值)/(1+冲动×延迟)，临近截止使延迟变小。",
        "scheduling_effect": [
            "大任务拆成 2–3 个小交付点（每 2–3 天一个），排成明确方块",
            "截止日前的方块标注「今日必须交付的最小产物」",
        ],
        "evidence_strength": "moderate",
        "citations": [
            _cite("Steel P, Koenig CJ", "2006", "Integrating theories of motivation", "Academy of Management Review 31(4):889-913"),
        ],
    },
    {
        "id": "procrastination_low_friction",
        "name": "拖延的情绪调节本质与低门槛启动",
        "category": "motivation",
        "summary": "拖延多源于对任务负面情绪（厌恶、焦虑）的回避；降低启动门槛（只做 2 分钟、先做最简单一步）比「下决心」有效。",
        "mechanism": "短期情绪修复优先于长期目标（present bias）；启动后任务厌恶感下降，进入状态的概率上升。",
        "scheduling_effect": [
            "容易拖延的任务：第一块只排 15–20min「启动仪式」",
            "把最难任务放在一天最靠前的位置，避免「等状态」",
            "连续拖延 ≥2 天的任务：拆到 10min 以下的最小步骤",
        ],
        "evidence_strength": "moderate",
        "citations": [
            _cite("Sirois F, Pychyl T", "2013", "Procrastination and the priority of short-term mood regulation", "Social and Personality Psychology Compass 7(2):115-127"),
            _cite("Steel P", "2007", "The nature of procrastination: a meta-analytic and theoretical review of quintessential self-regulatory failure", "Psychological Bulletin 133(1):65-94"),
        ],
    },
    {
        "id": "zeigarnik",
        "name": "蔡格尼克效应（未完成任务的记忆活跃）",
        "category": "motivation",
        "summary": "未完成任务在记忆中保持活跃，可用来跨天衔接（故意留一个明确的「下一步」）；但该效应的现代复现结果不稳，仅作辅助。",
        "mechanism": "未达成目标产生持续的目标激活；完成后该激活释放。",
        "scheduling_effect": [
            "每天最后一块结束时，在 notes 写下明天的第一步（1 句话）",
            "不要把任务停在「不知道下一步做什么」的状态",
        ],
        "evidence_strength": "emerging",
        "citations": [
            _cite("Zeigarnik B", "1927", "Das Behalten erledigter und unerledigter Handlungen", "Psychologische Forschung 9:1-85"),
        ],
    },
    # ---------------- 规划与执行偏差 ----------------
    {
        "id": "planning_fallacy_buffer",
        "name": "规划谬误与缓冲区",
        "category": "planning",
        "summary": "人系统性低估任务耗时（规划谬误）。规划应基于历史实际耗时，并预留 20–30% 缓冲。",
        "mechanism": "以「最佳情形」而非「参照类」估计；忽略意外与切换成本。",
        "scheduling_effect": [
            "总可用时间 × 0.7 作为可排任务量上限",
            "用近 28 天同类别实际耗时/预估耗时比值校准 estimate",
            "每天留出 1–2 个「缓冲块」，不排任务",
        ],
        "evidence_strength": "strong",
        "citations": [
            _cite("Buehler R, Griffin D, Ross M", "1994", "Exploring the planning fallacy: why people underestimate their task completion times", "Journal of Personality and Social Psychology 67(3):366-381"),
        ],
    },
    {
        "id": "flow_conditions",
        "name": "心流的前置条件",
        "category": "attention",
        "summary": "清晰目标 + 即时反馈 + 难度与技能匹配，是进入高投入状态的条件；任务描述越具体越容易进入。",
        "mechanism": "中等挑战水平伴随适度唤醒与注意聚焦，降低自我监控带来的干扰。",
        "scheduling_effect": [
            "每个深度块写明「完成标准」（如：做完 10 题并订正）",
            "难度过高的任务拆成「可完成的最小子任务」",
        ],
        "evidence_strength": "moderate",
        "citations": [
            _cite("Csikszentmihalyi M", "1990", "Flow: the psychology of optimal experience", "Harper & Row（专著）"),
        ],
    },
]

RULE_INDEX: dict[str, dict] = {r["id"]: r for r in RULES}


def all_rules() -> list[dict]:
    return RULES


def get_rule(rule_id: str) -> dict | None:
    return RULE_INDEX.get(rule_id)


def rules_compact_for_prompt(max_rules: int = 40) -> str:
    """把规则压缩成给 LLM 的紧凑文本，节省 token。"""
    lines = []
    for r in RULES[:max_rules]:
        effects = "；".join(r["scheduling_effect"][:3])
        lines.append(f"- [{r['id']}] {r['name']}（{STRENGTH_LABEL[r['evidence_strength']]}）：{effects}")
    return "\n".join(lines)


def rules_markdown() -> str:
    """生成人类可读的规则手册（/api/knowledge 与文档共用）。"""
    out = ["# 学习科学规则库", ""]
    for cat, label in CATEGORY_LABEL.items():
        rules = [r for r in RULES if r["category"] == cat]
        if not rules:
            continue
        out.append(f"## {label}")
        out.append("")
        for r in rules:
            out.append(f"### `{r['id']}` {r['name']}　<span>{STRENGTH_LABEL[r['evidence_strength']]}</span>")
            out.append("")
            out.append(r["summary"])
            out.append("")
            out.append(f"**机制**：{r['mechanism']}")
            out.append("")
            out.append("**排程影响**：")
            for e in r["scheduling_effect"]:
                out.append(f"- {e}")
            out.append("")
            out.append("**文献**：")
            for c in r["citations"]:
                out.append(f"- {c['authors']} ({c['year']}). {c['title']}. *{c['venue']}*")
            out.append("")
    return "\n".join(out)


# 默认能量曲线（0-23 点，1-5 分），基于「典型晨型偏中性」人群，实际以用户反馈校准
DEFAULT_ENERGY_CURVE = [
    1, 1, 1, 1, 1, 1, 2, 3,  # 00-07
    4, 5, 5, 5, 3, 2, 2, 3,  # 08-15
    4, 4, 3, 3, 4, 4, 3, 2,  # 16-23
]

DEFAULT_PROFILE = {
    "wake_time": "07:00",
    "sleep_time": "23:30",
    "chronotype": "neutral",
    "max_focus_min": 90,
    "preferred_block_min": 45,
    "break_min": 10,
    "lunch_start": "12:00",
    "lunch_end": "13:00",
    "dinner_start": "18:00",
    "dinner_end": "19:00",
    "energy_curve": DEFAULT_ENERGY_CURVE,
    "fixed_commitments": [],
    "preferences": [
        "晚上 22:30 之后不安排高认知负荷任务",
        "每天至少保留 1 个缓冲块",
    ],
    "goals": [],
    "notes": "",
}
