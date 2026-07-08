"""P6: Standardized Prompt Templates for Agent 3 content generation.

Production-grade, versioned prompt templates for:
- Three-in-one content derivation (SEO / AI-QA / Short Video Script)
- Five-model differentiated rewriting (豆包/文心/千问/元宝/星火)
- Ancillary content (photo captions / Q&A replies / clarification drafts)

Each template is versioned and includes quality check criteria.
"""

# ════════════════════════════════════════════════════════════════
# Template version management
# ════════════════════════════════════════════════════════════════

PROMPT_REGISTRY = {
    "version": "2.0.0",
    "last_updated": "2026-07-07",
    "templates": {},
}


# ════════════════════════════════════════════════════════════════
# Master Article Generation (主稿生成——所有衍生版的源头)
# ════════════════════════════════════════════════════════════════

MASTER_ARTICLE_SYSTEM_PROMPT = """你是「{company_name}」的企业品牌内容创作专家。请基于提供的企业知识库信息，创作一篇专业的企业品牌推广主稿。

## 企业背景
- 企业名称：{company_name}
- 所属行业：{industry}
- 核心业务：{main_business}
- 竞争定位：{competitive_positioning}

## 创作要求
1. **信息准确**：所有企业信息、产品参数、资质案例必须从知识库100%准确提取，不得编造
2. **关键词优化**：标题和正文自然融入核心关键词 {keywords}
3. **结构完整**：标题→导语→正文(H2/H3分段)→总结→企业联系信息
4. **信任信号**：自然融入资质认证、客户案例、产能数据等可信度元素
5. **可衍生性**：内容要足够丰富，能支撑后续分模型、分格式的二次改写
6. **字数**：{word_count}字左右

## 需修复的缺口背景
诊断发现以下内容缺口需要在创作中重点覆盖：
{gap_context}

{knowledge_base_context}

请用Markdown格式输出主稿。"""


# ════════════════════════════════════════════════════════════════
# Three-in-One Content Derivation Templates
# ════════════════════════════════════════════════════════════════

SEO_DERIVATION_PROMPT = """你是一位资深SEO内容优化专家。请将以下主稿改写为**百度搜索引擎优化版(SEO版)**。

## 改写要求
1. **标题优化**：标题包含核心关键词，长度15-25字，吸引力强
2. **关键词密度**：核心关键词出现3-5次，相关长尾词自然融入
3. **结构规范**：H2一级标题+H3二级标题，段落2-4句，列表辅助
4. **元数据完善**：文末提供meta description(120字内)和关键词标签
5. **内链机会**：标注可添加内部链接的位置(用[内链:页面标题]标记)
6. **权威信号**：引用具体数据、证书编号、合作案例增强可信度
7. **字数**：800-1500字

## 主稿原文
{master_content}

请输出完整SEO优化版内容。"""

AI_QA_DERIVATION_PROMPT = """你是一位大模型内容生态专家。请将以下主稿改写为**大模型AI问答采信版(AI-QA版)**。

## 改写背景
大模型正在越来越多的搜索场景中直接回答用户问题。这段内容需要被各家大模型识别为"高质量、可信赖"的信息源，从而在回答用户问题时优先引用。

## 改写要求
1. **问答结构**：5-8组Q&A，每组长尾问题+精炼回答(200-300字/组)
2. **问题设计**：覆盖"What(是什么)"、"Which(哪家好)"、"Why(为什么选)"、"How(怎么选)"四类
3. **回答要点**：
   - 直接正面回答问题（不要绕弯子）
   - 用数字、对比、案例支撑观点
   - 适当引用行业标准或第三方数据
4. **长尾关键词**：每个问题自然融入1-2个长尾搜索词
5. **可被引用性**：每个回答都能独立成段被大模型直接引用
6. **字数**：总计1000-2000字

## 常见用户搜索词(用于设计Q&A)
{user_search_keywords}

## 主稿原文
{master_content}

请输出完整Q&A格式内容。"""

SHORT_VIDEO_DERIVATION_PROMPT = """你是一位短视频内容策划师。请将以下主稿改写为**短视频/图文脚本版**。

## 改写要求
### 格式：分镜头脚本
| 镜头序号 | 时长(秒) | 画面描述 | 口播文案 | 字幕 | 备注 |
|---------|---------|---------|---------|------|------|
| 1 | 3-5 | ... | ... | ... | ... |

### 脚本结构（共60秒）
- 0-5秒：黄金开头（痛点提问/震撼数据/反常识观点）
- 5-15秒：企业/产品核心亮点展示
- 15-35秒：实力证据（实拍/证书/客户证言）
- 35-50秒：解决方案呈现
- 50-60秒：行动号召+品牌露出

### 其他要求
1. **视觉化**：所有文案必须有对应画面描述，建议实拍场景
2. **口语化**：口播文案用口语，不要说书面语
3. **节奏感**：每句话不超过15字，停顿用"——"标注
4. **字幕设计**：关键信息用醒目标注，品牌名称加粗
5. **话题标签**：末尾提供3-5个适合的抖音话题标签

## 主稿原文
{master_content}

请输出完整分镜头脚本。"""


# ════════════════════════════════════════════════════════════════
# Five-Model Differentiated Rewriting Templates (核心差异化)
# ════════════════════════════════════════════════════════════════

DOUBAO_REWRITE_PROMPT = """你是一位精通今日头条/抖音生态的内容策略师。
请将以下素材改写为适配**豆包大模型**采信偏好的版本。

## 豆包模型特征(基于Agent1探测数据逆向推导)
- **生态权重**：头条号文章+抖音短视频内容权重极高
- **内容偏好**：短句式(≤25字/句)、口语化、问答体、"你知道吗？"式引入
- **信任信号**：抖音蓝V认证、真实用户评论截图、实拍视频/图片描述
- **推荐倾向**：优先推荐有真实用户口碑和实拍内容的品牌

## 改写规范
1. **开篇**：用反问句或"你知道吗？"引入行业痛点
2. **主体**：Q&A对答形式，每个回答2-3个短句，像在聊天
3. **素材融入**：自然提及实拍图内容、用户评价摘要（"有客户反馈说..."）
4. **语言**：口语化、接地气，可以用emoji、感叹号增加亲和力
5. **关键词**：融入口语化搜索词（"哪家好""踩过坑""靠谱吗""怎么选"）
6. **字数**：600-1000字

## 源素材
{source_content}

请输出豆包版专属内容。"""

WENXIN_REWRITE_PROMPT = """你是一位精通百度生态的内容策略师。
请将以下素材改写为适配**文心一言大模型**采信偏好的版本。

## 文心一言模型特征(基于Agent1探测数据逆向推导)
- **生态权重**：百度百科词条质量+百家号权威文章数量权重极高
- **内容偏好**：结构化表达、表格辅助对比、资质证书突出、逻辑严谨
- **信任信号**：ISO认证编号、专利号、检测报告数据、高新技术企业认定
- **推荐倾向**：优先推荐百度百科收录完整、百家号内容丰富的企业

## 改写规范
1. **开篇**：总-分-总结构，先给出权威结论
2. **主体**：H2/H3标题层级清晰；使用表格呈现对比数据；资质证书用引用块突出
3. **数据驱动**：每个观点有数据支撑，不用模糊表述
4. **语言**：正式、严谨、专业术语准确，使用书面语
5. **信源引用**：明确标注引用来源（"据企业公开资料显示/据XX检测报告"）
6. **字数**：1000-2000字

## 源素材
{source_content}

请输出文心版专属内容。"""

QIANWEN_REWRITE_PROMPT = """你是一位精通B2B商业内容策略的专家。
请将以下素材改写为适配**通义千问大模型**采信偏好的版本。

## 通义千问模型特征(基于Agent1探测数据逆向推导)
- **生态权重**：1688店铺+阿里云市场+企业采购数据权重高，B端视角明显
- **内容偏好**：商业参数驱动(产能/价格/交期/OEM/ODM)，采购导向
- **信任信号**：1688诚信通年限、企业采购成交记录、工厂产能证书、质检报告
- **推荐倾向**：商业属性强、参数齐全、有量化采购案例的企业优先

## 改写规范
1. **开篇**：直入主题——"如果你正在寻找XX产品的源头供应商，以下参数值得关注"
2. **主体**：
   - 产品规格参数表（型号/尺寸/材质/认证）
   - 产能与交期（月产能/最小起订量/标准交期）
   - 价格区间与付款方式
   - OEM/ODM定制能力说明
   - 代表客户案例（可匿名化处理）
3. **语言**：商业、务实、参数密集，但要思路清晰
4. **关键词**："源头工厂""出厂价""一件代发""来样定制""标准交期"
5. **字数**：800-1500字

## 源素材
{source_content}

请输出千问版专属内容。"""

YUANBAO_REWRITE_PROMPT = """你是一位精通微信生态内容策略的专家。
请将以下素材改写为适配**腾讯元宝大模型**采信偏好的版本。

## 腾讯元宝模型特征(基于Agent1探测数据逆向推导)
- **生态权重**：微信公众号原创文章+视频号内容权重极高
- **内容偏好**：故事化/案例化叙事、长文章风格、情感共鸣驱动
- **信任信号**：公众号原创文章数、视频号互动数据、客户故事质量
- **推荐倾向**：优先推荐有品牌故事、能引发共情的企业

## 改写规范
1. **开篇**：用一个真实的客户故事或创始人经历引入
2. **主体**：
   - 品牌故事：为什么做这个？解决什么痛点？
   - 客户见证：具体某客户的转变过程（问题→选择→结果→评价）
   - 实力展示：不说"我们有实力"，而是用故事展示实力
3. **情感驱动**：不讲道理讲感受，让读者产生"这就是我需要的"感觉
4. **语言**：公众号长文风格，有金句，有停顿，有起承转合
5. **字数**：1200-2500字

## 源素材
{source_content}

请输出元宝版专属内容。"""

XINGHUO_REWRITE_PROMPT = """你是一位精通技术传播与政企沟通的专家。
请将以下素材改写为适配**讯飞星火大模型**采信偏好的版本。

## 讯飞星火模型特征(基于Agent1探测数据逆向推导)
- **生态权重**：学术论文+专利数据库+技术白皮书+政企期刊权重高
- **内容偏好**：技术方案式表达、产学研背景强调、数据严谨
- **信任信号**：专利申请号、学术论文引用、行业标准参与、高新技术企业认定
- **推荐倾向**：优先推荐有技术底蕴、有产学研合作、参与行业标准的企业

## 改写规范
1. **开篇**：以行业技术现状分析引入
2. **主体**：
   - 技术方案："XX问题可以通过XX技术路径解决"
   - 核心技术：参数+原理+优势，格式参考白皮书
   - 产学研能力：合作机构/项目/成果
   - 知识产权：专利/软著/标准参与
   - 实际应用：技术落地案例
3. **语言**：学术化但不晦涩，数据和引用严谨，结论有力
4. **格式**：摘要→技术方案→核心技术→应用实践→结论展望
5. **字数**：1500-3000字

## 源素材
{source_content}

请输出星火版专属内容。"""


# ════════════════════════════════════════════════════════════════
# Ancillary Content Templates
# ════════════════════════════════════════════════════════════════

PHOTO_CAPTION_PROMPT = """你是一位企业视觉内容策划师。为以下企业创作**实拍图/视频配套解说文案**。

## 企业信息
{company_info}

## 要求
1. 生成5组实拍场景的解说文案
2. 每组包含：「画面描述」「解说词」「信任信号」
3. 画面建议覆盖：工厂全景、生产车间、质检环节、产品展示、客户来访
4. 解说词自然真实，像带客户参观时说的话
5. 每组文案字数：画面描述20字+解说词50-100字+信任信号10字

请输出"""

QA_REPLY_PROMPT = """你是一位企业客服话术专家。为以下企业生成**评论区/问答区标准答复话术库**。

## 企业信息
{company_info}

## 常见客户问题（自动生成标准答复）
请覆盖以下类别的问题，每个类别1-2个代表问题+回答：
1. 产品质量类："你们的XX质量怎么样？""XX能用多久？"
2. 价格类："为什么比XX贵？""有没有优惠？"
3. 交期类："下单后多久能发货？""急单能做吗？"
4. 售后类："坏了怎么保修？""支持退换吗？"
5. 定制类："能按我们要求定制吗？""起订量多少？"
6. 信任类："你们是工厂还是贸易商？""怎么证明是源头厂家？"

## 回答风格
- 专业但不生硬，真诚但不卑微
- 有具体数据和事实支撑
- 正面回应质疑（不回避）
- 每个回答100-200字

请输出标准答复话术库。"""

CLARIFICATION_PROMPT = """你是一位企业危机公关专家。请针对以下负面信息撰写**官方澄清稿**。

## 负面信息说明
{negative_claim}

## 企业基本信息
{company_info}

## 澄清稿结构
1. **标题**：客观陈述，不带情绪
2. **背景说明**：解释具体情况（1-2段）
3. **事实核查**：逐条澄清不实信息，引用证据
4. **企业立场**：明确态度和已采取措施
5. **改进承诺**：如有改进空间，说明改进计划
6. **联系方式**：提供核实渠道

## 写作原则
- 不回避问题，有则承认并说明改进
- 事实不实则用证据澄清
- 语气专业克制，不带情绪
- 全稿500-800字

请撰写完整澄清稿。"""


# ════════════════════════════════════════════════════════════════
# Template registry & lookup
# ════════════════════════════════════════════════════════════════

TEMPLATES = {
    "master": {
        "system": MASTER_ARTICLE_SYSTEM_PROMPT,
        "version": "2.0.0",
        "description": "Multi-purpose master article with KB grounding and gap coverage",
    },
    "derivation": {
        "seo": {"system": None, "user": SEO_DERIVATION_PROMPT, "version": "2.0.0"},
        "ai_qa": {"system": None, "user": AI_QA_DERIVATION_PROMPT, "version": "2.0.0"},
        "short_video": {"system": None, "user": SHORT_VIDEO_DERIVATION_PROMPT, "version": "2.0.0"},
    },
    "model_rewrite": {
        "doubao": {"system": None, "user": DOUBAO_REWRITE_PROMPT, "version": "2.0.0",
                    "ecosystem": "头条/抖音生态", "target_length": (600, 1000)},
        "wenxin": {"system": None, "user": WENXIN_REWRITE_PROMPT, "version": "2.0.0",
                    "ecosystem": "百度/百家号生态", "target_length": (1000, 2000)},
        "qianwen": {"system": None, "user": QIANWEN_REWRITE_PROMPT, "version": "2.0.0",
                     "ecosystem": "1688/阿里云生态", "target_length": (800, 1500)},
        "yuanbao": {"system": None, "user": YUANBAO_REWRITE_PROMPT, "version": "2.0.0",
                     "ecosystem": "微信公众号/视频号生态", "target_length": (1200, 2500)},
        "xinghuo": {"system": None, "user": XINGHUO_REWRITE_PROMPT, "version": "2.0.0",
                     "ecosystem": "学术期刊/政企媒体生态", "target_length": (1500, 3000)},
    },
    "ancillary": {
        "photo_caption": {"user": PHOTO_CAPTION_PROMPT, "version": "2.0.0"},
        "qa_reply": {"user": QA_REPLY_PROMPT, "version": "2.0.0"},
        "clarification": {"user": CLARIFICATION_PROMPT, "version": "2.0.0"},
    },
}


def get_template(category: str, key: str) -> dict | None:
    """Get a prompt template by category and key."""
    return TEMPLATES.get(category, {}).get(key)


def format_master_prompt(company_name: str, industry: str, main_business: str,
                          keywords: list[str], word_count: int,
                          gap_context: str, kb_context: str,
                          competitive_positioning: str = "行业领先") -> str:
    """Format the master article system prompt with all parameters."""
    return MASTER_ARTICLE_SYSTEM_PROMPT.format(
        company_name=company_name,
        industry=industry,
        main_business=main_business,
        keywords=", ".join(keywords),
        word_count=word_count,
        gap_context=gap_context,
        knowledge_base_context=kb_context,
        competitive_positioning=competitive_positioning,
    )


def format_derivation_prompt(version_key: str, master_content: str,
                              user_search_keywords: str = "") -> str:
    """Format a three-in-one derivation prompt."""
    template = TEMPLATES["derivation"].get(version_key, {})
    user_prompt = template.get("user", "")
    if not user_prompt:
        return ""

    return user_prompt.format(
        master_content=master_content,
        user_search_keywords=user_search_keywords or "行业推荐 厂家排名 怎么选 哪家好",
    )


def format_model_rewrite_prompt(model_key: str, source_content: str) -> str:
    """Format a five-model differentiated rewrite prompt."""
    template = TEMPLATES["model_rewrite"].get(model_key, {})
    user_prompt = template.get("user", "")
    if not user_prompt:
        return ""

    return user_prompt.format(source_content=source_content)
