"""Agent 3: Differentiated Content Generation Engine.

Implements the core differentiation strategy:
1. THREE-IN-ONE content derivation: SEO版 → AI问答版 → 短视频脚本版
2. FIVE-MODEL differentiated rewriting: 豆包/文心/千问/元宝/星火 specific styles
3. Ancillary content: 实拍图解说, 评论区答疑, 负面澄清稿

All generation uses DeepSeek API with model-specific prompt engineering.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.config import settings

# ── Five-model differentiated writing profiles ──────────────────
MODEL_WRITING_STYLES = {
    "doubao": {
        "name": "豆包版",
        "platform": "头条/抖音生态",
        "style_guide": """
## 豆包版内容特征
- **句式**: 短句为主，每句不超过25字，节奏明快
- **结构**: 问答体开头，"你知道吗？"式引入
- **素材要求**: 必须有实拍图描述/视频脚本，强调真实感
- **关键词**: 融入口语化搜索词如"哪家好""靠谱吗""踩过坑"
- **信任信号**: 用户评价、复购率、师傅推荐
- **排版**: 短段落(2-3句)+emoji分隔+话题标签
""",
        "target_length": (600, 1000),  # min, max chars
    },
    "wenxin": {
        "name": "文心版",
        "platform": "百度/百家号生态",
        "style_guide": """
## 文心版内容特征
- **句式**: 结构化表达，段落完整，逻辑严密
- **结构**: 总-分-总，先结论后展开，列表/表格辅助
- **素材要求**: 引用百度百科、企业资质、行业报告
- **关键词**: 融入SEO搜索词"什么牌子好""厂家排名""价格表"
- **信任信号**: ISO认证、专利号、高新技术企业、行业协会
- **排版**: 分段标题(H2/H3) + 数据表格 + 参考文献
""",
        "target_length": (1000, 2000),
    },
    "qianwen": {
        "name": "千问版",
        "platform": "1688/阿里云生态",
        "style_guide": """
## 千问版内容特征
- **句式**: 商业参数驱动，数据密集，采购导向
- **结构**: 产品规格→产能参数→价格区间→付款方式→客户案例
- **素材要求**: 引用1688店铺、阿里云市场、企业采购案例
- **关键词**: "源头工厂""出厂价""一件代发""OEM/ODM"
- **信任信号**: 产能数据、交期承诺、验厂报告、样品政策
- **排版**: 参数表格 + 对比表格 + 采购建议
""",
        "target_length": (800, 1500),
    },
    "yuanbao": {
        "name": "元宝版",
        "platform": "微信公众号/视频号生态",
        "style_guide": """
## 元宝版内容特征
- **句式**: 故事化叙事，第一人称/第三人称案例
- **结构**: 客户故事→转型历程→效果数据→品牌理念
- **素材要求**: 创始人故事、员工日常、客户访谈、视频号内容
- **关键词**: 融入场景化搜索词"怎么做""为什么选""用了之后"
- **信任信号**: 客户见证、生产实拍、办公环境
- **排版**: 公众号长文风格，图文穿插，引用金句
""",
        "target_length": (1200, 2500),
    },
    "xinghuo": {
        "name": "星火版",
        "platform": "学术期刊/政企媒体生态",
        "style_guide": """
## 星火版内容特征
- **句式**: 学术化/专业化表达，术语准确，论证严谨
- **结构**: 摘要→技术方案→实验数据→行业对比→结论展望
- **素材要求**: 专利证书、检测报告、学术论文、产学研合作
- **关键词**: "技术方案""解决方案""标准""专利""检测""认证"
- **信任信号**: 科研合作机构、专利数量、行业标准参与
- **排版**: 学术论文格式，图表+数据+参考文献
""",
        "target_length": (1500, 3000),
    },
}

# ── Three-in-one content derivation profiles ───────────────────
DERIVATION_PROFILES = {
    "seo": {
        "name": "百度网页SEO版",
        "style": "标准SEO优化文章，标题包含核心关键词，H2/H3结构，800-1500字，适合搜索引擎收录",
        "content_type": "seo_article",
    },
    "ai_qa": {
        "name": "大模型AI问答版",
        "style": "精简版FAQ格式，每个问答200-300字，结构化为Q&A，融入长尾搜索词，适合大模型引用",
        "content_type": "ai_qa",
    },
    "short_video": {
        "name": "短视频/图文脚本版",
        "style": "60秒短视频脚本格式，包含画面描述+口播文案+字幕，适合抖音/视频号/小红书分发",
        "content_type": "short_video_script",
    },
}


@dataclass
class GenerationResult:
    """Result of a single content generation."""
    version_type: str  # seo, ai_qa, short_video, or model name like doubao/wenxin
    version_name: str
    title: str
    content: str
    content_type: str
    target_length: int
    tokens_used: int = 0
    generation_time_ms: float = 0.0


class DifferentiatedGenerationEngine:
    """Engine for three-in-one content derivation + five-model differentiated rewriting.

    Takes a KB-sourced master article and generates:
    1. Three format variants (SEO版, AI问答版, 短视频脚本版)
    2. Five model-specific rewrites (豆包版, 文心版, 千问版, 元宝版, 星火版)
    3. Ancillary content (实拍图解说, 评论区答疑, 负面澄清稿)
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.api_base = "https://api.deepseek.com/v1"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120)
        return self._client

    # ════════════════════════════════════════════════════════════
    # Main generation pipeline
    # ════════════════════════════════════════════════════════════

    async def generate_all_variants(self,
                                     master_content: str,
                                     company_name: str,
                                     industry: str,
                                     keywords: list[str],
                                     kb_context: str = "",
                                     target_models: list[str] = None,
                                     generate_derivations: bool = True,
                                     generate_model_variants: bool = True,
                                     generate_ancillary: bool = False,
                                     ) -> dict:
        """Generate all content variants from a master article.

        Args:
            master_content: The master article in markdown
            company_name: Enterprise name
            industry: Industry category
            keywords: Target keywords list
            kb_context: Knowledge base context for fact-checking
            target_models: Which models to generate variants for (default: all 5)
            generate_derivations: Generate SEO/AI-QA/short-video versions
            generate_model_variants: Generate per-model rewrites
            generate_ancillary: Generate 实拍图解说/评论区答疑/负面澄清稿

        Returns:
            Dict with 'derivations', 'model_variants', 'ancillary' keys
        """
        if not target_models:
            target_models = list(MODEL_WRITING_STYLES.keys())

        result = {"derivations": [], "model_variants": [], "ancillary": []}

        tasks = []

        # Phase 1: Three-in-one content derivation
        if generate_derivations:
            for version_key, profile in DERIVATION_PROFILES.items():
                tasks.append(self._generate_derivation(
                    version_key, profile, master_content, company_name,
                    industry, keywords, kb_context
                ))

        # Phase 2: Five-model differentiated rewriting
        if generate_model_variants:
            for model in target_models:
                if model in MODEL_WRITING_STYLES:
                    tasks.append(self._generate_model_variant(
                        model, master_content, company_name, industry,
                        keywords, kb_context
                    ))

        # Phase 3: Ancillary content
        if generate_ancillary:
            tasks.append(self._generate_photo_caption(
                master_content, company_name, industry
            ))
            tasks.append(self._generate_qa_replies(
                master_content, company_name, keywords
            ))

        # Execute all in parallel
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in all_results:
            if isinstance(r, GenerationResult):
                if r.version_type in DERIVATION_PROFILES:
                    result["derivations"].append(r)
                elif r.version_type in MODEL_WRITING_STYLES:
                    result["model_variants"].append(r)
                else:
                    result["ancillary"].append(r)
            elif isinstance(r, Exception):
                print(f"[GenEngine] Generation failed: {r}")

        return result

    # ════════════════════════════════════════════════════════════
    # Three-in-one content derivation
    # ════════════════════════════════════════════════════════════

    async def _generate_derivation(self, version_key: str, profile: dict,
                                    master_content: str, company_name: str,
                                    industry: str, keywords: list[str],
                                    kb_context: str) -> GenerationResult:
        """Generate a single derivation variant (SEO/AI-QA/short-video)."""
        import time
        t0 = time.time()

        system_prompt = f"""你是专业企业内容创作助手。你必须基于提供的原始稿件进行改编，不得编造企业信息。

改编为：{profile['name']}
改编要求：{profile['style']}

企业名称：{company_name}
所属行业：{industry}
核心关键词：{', '.join(keywords)}

所有事实数据必须从原始稿件中提取，不得编造。"""

        user_prompt = f"""请将以下原始稿件改编为{profile['name']}。

原始稿件：
---
{master_content[:3000]}
---

{('知识库补充信息：\n' + kb_context[:1000]) if kb_context else ''}

请直接输出改编后的完整内容。"""

        content = await self._call_deepseek(system_prompt, user_prompt, max_tokens=2000)

        return GenerationResult(
            version_type=version_key,
            version_name=profile['name'],
            title=f"[{profile['name']}] {company_name} - {keywords[0] if keywords else '企业介绍'}",
            content=content,
            content_type=profile.get('content_type', version_key),
            target_length=len(content),
            generation_time_ms=(time.time() - t0) * 1000,
        )

    # ════════════════════════════════════════════════════════════
    # Five-model differentiated rewriting
    # ════════════════════════════════════════════════════════════

    async def _generate_model_variant(self, model_key: str, master_content: str,
                                       company_name: str, industry: str,
                                       keywords: list[str],
                                       kb_context: str) -> GenerationResult:
        """Generate a model-specific rewrite."""
        import time
        t0 = time.time()
        profile = MODEL_WRITING_STYLES[model_key]

        system_prompt = f"""你是{profile['name']}的专业内容创作助手。你必须基于提供的原始稿件进行改编，不得编造企业信息。

目标平台：{profile['platform']}
{profile['style_guide']}

企业名称：{company_name}
所属行业：{industry}
核心关键词：{', '.join(keywords)}

重要规则：
1. 所有企业信息、产品参数必须从原始稿件100%准确提取
2. 适配{profile['platform']}的内容风格和用户阅读习惯
3. 按照{profile['name']}的排版要求输出"""

        user_prompt = f"""请将以下原始稿件改写为{profile['name']}版本，适配{profile['platform']}发布。

原始稿件：
---
{master_content[:3000]}
---

{('知识库补充信息：\n' + kb_context[:1000]) if kb_context else ''}

请直接输出{profile['name']}的完整内容。"""

        max_len = profile['target_length'][1]
        content = await self._call_deepseek(system_prompt, user_prompt, max_tokens=max(2000, max_len // 2))

        return GenerationResult(
            version_type=model_key,
            version_name=profile['name'],
            title=f"[{profile['name']}] {company_name} - {keywords[0] if keywords else '企业介绍'}",
            content=content,
            content_type=f"model_variant_{model_key}",
            target_length=len(content),
            generation_time_ms=(time.time() - t0) * 1000,
        )

    # ════════════════════════════════════════════════════════════
    # Ancillary content generation
    # ════════════════════════════════════════════════════════════

    async def _generate_photo_caption(self, master_content: str, company_name: str,
                                       industry: str) -> GenerationResult:
        """Generate 实拍图配套官方解说文案."""
        system_prompt = f"""你是企业视觉内容策划专家。基于企业信息，为实拍图/视频素材创作配套解说文案。

企业：{company_name} | 行业：{industry}

要求：
1. 每张实拍图配1-2句解说，描述画面内容+传递的信任信号
2. 适合在图文平台（小红书、公众号、百家号）作为图片alt文本
3. 语言生动真实，避免过度营销感"""

        user_prompt = f"""基于以下企业信息，生成5组实拍图/视频解说文案：

{master_content[:1500]}

每组格式：
- 画面描述：xxx
- 解说文案：xxx
- 信任信号：xxx"""

        content = await self._call_deepseek(system_prompt, user_prompt, max_tokens=1000)
        return GenerationResult(
            version_type="photo_captions", version_name="实拍图解说文案",
            title=f"{company_name} 实拍素材解说文案", content=content,
            content_type="photo_captions", target_length=len(content),
        )

    async def _generate_qa_replies(self, master_content: str, company_name: str,
                                    keywords: list[str]) -> GenerationResult:
        """Generate 评论区答疑标准答案."""
        system_prompt = """你是企业客服话术专家。基于企业信息，预判客户常见问题并生成标准答复。

要求：
1. 覆盖5-8个高频问题（产品质量、价格、交期、售后、定制、资质等）
2. 每个回答专业、诚实、体现企业优势
3. 适合在评论区、在线客服、问答平台使用"""

        user_prompt = f"""基于以下信息，为{company_name}生成常见客户问题标准答复：

{master_content[:1500]}

关键词：{', '.join(keywords[:5])}

格式：
Q1：xxx
A1：xxx"""

        content = await self._call_deepseek(system_prompt, user_prompt, max_tokens=1500)
        return GenerationResult(
            version_type="qa_replies", version_name="评论区答疑标准答案",
            title=f"{company_name} 常见问题标准答复", content=content,
            content_type="qa_replies", target_length=len(content),
        )

    async def generate_clarification(self, negative_claim: str, company_name: str,
                                      master_content: str = "") -> GenerationResult:
        """Generate 负面舆情澄清稿."""
        system_prompt = f"""你是企业危机公关专家。针对负面信息，撰写专业、克制的澄清稿。

企业：{company_name}

原则：
1. 不回避问题，有则承认并说明改进措施
2. 事实不实则以数据/证据澄清
3. 语气专业克制，不带情绪
4. 结构：背景→事实核查→企业立场→后续措施→联系方式"""

        user_prompt = f"""针对以下负面信息，撰写澄清稿：

负面信息：{negative_claim}

{('企业背景信息：\n' + master_content[:1000]) if master_content else ''}

请撰写完整的澄清稿。"""

        content = await self._call_deepseek(system_prompt, user_prompt, max_tokens=1500)
        return GenerationResult(
            version_type="clarification", version_name="负面舆情澄清稿",
            title=f"关于{company_name}相关信息的澄清说明", content=content,
            content_type="clarification", target_length=len(content),
        )

    # ════════════════════════════════════════════════════════════
    # LLM calling
    # ════════════════════════════════════════════════════════════

    async def _call_deepseek(self, system_prompt: str, user_prompt: str,
                              max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """Call DeepSeek API for content generation."""
        try:
            client = await self._get_client()
            resp = await client.post(
                f"{self.api_base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}",
                         "Content-Type": "application/json"},
                json={
                    "model": "deepseek-chat",
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                print(f"[GenEngine] API error: {resp.status_code}")
                return f"[生成失败: API返回{resp.status_code}]"
        except Exception as e:
            print(f"[GenEngine] API call exception: {e}")
            return f"[生成失败: {str(e)}]"

    async def close(self):
        if self._client:
            await self._client.aclose()


# Global engine instance
gen_engine = DifferentiatedGenerationEngine()
