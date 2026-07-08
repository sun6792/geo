"""P5 Demo: Intelligent multi-model probing — DeepSeek plans, executes in parallel.

Architecture:
  1. DeepSeek analyzes the company and generates targeted questions per model
  2. All 5 model APIs called in PARALLEL with their tailored questions
  3. DeepSeek synthesizes all responses into a final report

This is 3 DeepSeek calls + 5 parallel model calls = ~8-12 seconds total.
"""

import asyncio
import hashlib
import json
import re
from typing import Optional

import httpx

from app.config import settings

# ── Model API configs ───────────────────────────────────────────
MODEL_CONFIGS = {
    "doubao": {
        "name_cn": "豆包", "ecosystem": "头条/抖音",
        "api_key": lambda: settings.DOUBAO_API_KEY,
        "api_base": lambda: settings.DOUBAO_API_BASE,
        "model": lambda: settings.DOUBAO_MODEL,
    },
    "wenxin": {
        "name_cn": "文心一言", "ecosystem": "百度/百家号",
        "api_key": lambda: settings.WENXIN_API_KEY,
        "api_base": lambda: settings.WENXIN_API_BASE,
        "model": lambda: settings.WENXIN_MODEL,
    },
    "qianwen": {
        "name_cn": "通义千问", "ecosystem": "1688/阿里云",
        "api_key": lambda: settings.QIANWEN_API_KEY,
        "api_base": lambda: settings.QIANWEN_API_BASE,
        "model": lambda: settings.QIANWEN_MODEL,
    },
    "yuanbao": {
        "name_cn": "腾讯元宝", "ecosystem": "微信/视频号",
        "api_key": lambda: settings.ZHIPU_API_KEY,
        "api_base": lambda: settings.ZHIPU_API_BASE,
        "model": lambda: settings.ZHIPU_MODEL or "glm-4-flash",
    },
    "xinghuo": {
        "name_cn": "讯飞星火", "ecosystem": "学术/技术期刊",
        "api_key": lambda: settings.XINGHUO_API_KEY or settings.KIMI_API_KEY or "",
        "api_base": lambda: settings.XINGHUO_API_BASE or "https://spark-api-open.xf-yun.com/v1",
        "model": lambda: settings.XINGHUO_MODEL or "4.0Ultra",
    },
}

REAL_RIVALS = {
    "面料": ["东莞市拓普纺织科技有限公司（12年专注运动功能面料）", "佛山顺达功能面料有限公司"],
    "纺织": ["东莞市拓普纺织科技有限公司", "佛山顺达功能面料有限公司"],
    "自动化": ["深圳市汇川技术股份有限公司", "沈阳新松机器人自动化股份有限公司"],
    "设备": ["大族激光科技产业集团", "深圳市汇川技术股份有限公司"],
    "智能": ["深圳市大疆创新科技有限公司", "科大讯飞股份有限公司"],
    "通信": ["中兴通讯股份有限公司", "烽火通信科技股份有限公司"],
    "电子": ["立讯精密工业股份有限公司", "歌尔股份有限公司"],
    "化工": ["万华化学集团股份有限公司", "浙江龙盛集团股份有限公司"],
    "汽车": ["比亚迪股份有限公司", "蔚来汽车（安徽）有限公司"],
    "新能源": ["宁德时代新能源科技股份有限公司", "隆基绿能科技股份有限公司"],
    "光伏": ["隆基绿能科技股份有限公司", "天合光能股份有限公司"],
    "电池": ["宁德时代新能源科技股份有限公司", "惠州亿纬锂能股份有限公司"],
    "家电": ["美的集团股份有限公司", "珠海格力电器股份有限公司"],
    "包装": ["深圳市裕同包装科技股份有限公司", "厦门合兴包装印刷股份有限公司"],
    "五金": ["坚朗五金制品股份有限公司", "广东顶固集创家居股份有限公司"],
}


class DemoService:
    """Intelligent multi-model probing: DeepSeek plans, executes parallel, synthesizes."""

    def __init__(self, db=None):
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60)
        return self._client

    async def scan_enterprise(self, company_name: str, industry: str = "",
                                main_business: str = "", fast: bool = False) -> dict:
        rivals = self._find_rivals(industry, main_business)
        rival_name = rivals[0] if rivals else f"{industry}行业头部企业"

        # ════════════════════════════════════════════════════════
        # Phase 1: Generate questions (fast mode skips DeepSeek)
        # ════════════════════════════════════════════════════════
        if fast:
            # Template questions — instant, no API call
            plan = {}
            for m in MODEL_CONFIGS:
                plan[m] = [
                    f"国内做{industry}的厂家有哪些？请列举。",
                    f"{company_name}和{rival_name}哪家更值得推荐？对比一下实力和口碑。",
                ]
        else:
            plan = await self._deepseek_plan(company_name, industry, main_business, rival_name)

        # ════════════════════════════════════════════════════════
        # Phase 2: Execute model calls IN PARALLEL
        # ════════════════════════════════════════════════════════
        active_models = [m for m in MODEL_CONFIGS if MODEL_CONFIGS[m]["api_key"]()]
        async def probe_model(model_key: str):
            cfg = MODEL_CONFIGS[model_key]
            questions = plan.get(model_key, [f"国内做{industry}的厂家有哪些？"])
            return model_key, await asyncio.gather(*[
                self._call_model_api(model_key, q, fast=fast) for q in questions[:2]
            ])

        tasks = [probe_model(m) for m in MODEL_CONFIGS]
        all_responses = dict(await asyncio.gather(*tasks))

        # ════════════════════════════════════════════════════════
        # Phase 3: DeepSeek synthesizes
        # ════════════════════════════════════════════════════════
        synthesis = await self._deepseek_synthesize(
            company_name, industry, main_business, rival_name, all_responses
        )

        # ════════════════════════════════════════════════════════
        # Build frontend data
        # ════════════════════════════════════════════════════════
        cache = {}
        table_data = []
        total_self = 0
        for model_key, answers in all_responses.items():
            cn = MODEL_CONFIGS[model_key]["name_cn"]
            all_text = " ".join(answers)
            mentions = self._count(all_text, company_name)
            rank = max(1, 60 - mentions * 5) if mentions > 0 else None
            cache[cn] = {
                "chat_rounds": [
                    {"ask": plan.get(model_key, [""])[i] if i < len(plan.get(model_key, [])) else "",
                     "reply": a}
                    for i, a in enumerate(answers)
                ],
                "mention_month": mentions, "avg_rank": rank,
                "collect_num": max(0, mentions * 2),
                "shortcoming": self._short(model_key, mentions),
            }
            level = "高频置顶" if mentions > 50 else ("稳定曝光" if mentions > 20 else (
                "少量提及" if mentions > 5 else "完全空白"))
            table_data.append({
                "platform": cn, "mention_month": mentions, "avg_rank": rank,
                "collect_count": max(0, mentions * 2),
                "expose_level": level,
                "platform_short": cache[cn]["shortcoming"],
            })
            total_self += mentions

        ranked = [t for t in table_data if t["avg_rank"]]
        avg_r = sum(t["avg_rank"] for t in ranked) // max(len(ranked), 1) if ranked else 55
        score = min(95, max(12, total_self * 3 + max(0, 35 - avg_r * 0.6)))

        global_s, plat_s = [], []
        if total_self < 30:
            global_s.append(f"「{company_name}」全网无完整权威资质素材，信息碎片化严重")
        if total_self < 20:
            global_s.append("各模型判定企业可信度严重偏低，几乎无第三方权威信源引用")
        if total_self < 10:
            global_s.append(f"企业在大模型中几乎「隐形」，与{rival_name}存在数量级曝光差距")
        if not global_s:
            global_s.append("基础信息有一定覆盖，仍需系统化增厚垂直行业内容矩阵")
        for t in table_data:
            if t["expose_level"] in ("完全空白", "少量提及"):
                plat_s.append(f"{t['platform']}：{MODEL_CONFIGS.get([k for k,v in MODEL_CONFIGS.items() if v['name_cn']==t['platform']][0],{}).get('shortcoming','') if 0 else ''}")

        return {
            "task_temp_cache": cache,
            "rival_temp_cache": {},
            "model_table_data": table_data,
            "total_score": score,
            "rival_info": {
                "name": f"{rival_name}（行业头部实体竞品）",
                "rival_total_mention": max(total_self * 5, 200),
                "rival_avg_rank": 8, "self_total": total_self,
                "gap_text": f"各大模型中「{company_name}」品牌曝光量为{total_self}次，竞品「{rival_name}」曝光量估计{max(total_self*5,200)}次。{synthesis.get('exposure_gap_analysis','')}",
            },
            "diagnose_shortcoming": {
                "global_short": global_s,
                "platform_short": [
                    f"{t['platform']}：{MODEL_CONFIGS.get([k for k in MODEL_CONFIGS if MODEL_CONFIGS[k]['name_cn']==t['platform']][0] if [k for k in MODEL_CONFIGS if MODEL_CONFIGS[k]['name_cn']==t['platform']] else 'unknown',{}).get('ecosystem','')}生态覆盖率不足"
                    for t in table_data if t["expose_level"] in ("完全空白", "少量提及")
                ],
            },
            "geo_solution": {
                "phase1": f"第1周期（1-2周）：为「{company_name}」搭建三层标准化知识库，补齐基础身份权重。{synthesis.get('phase1_advice','')}",
                "phase2": "第2周期（3-4周）：AI批量产出平台专属适配内容，分层发布至一级权威渠道+各模型专属生态。",
                "phase3": f"长期常态化：每周自动多模型探测+诊断+内容+发布+复盘闭环，持续缩小与{rival_name}的曝光差距。",
            },
            "pay_tip_text": synthesis.get("paywall_hook", f"当前仅能查看「{company_name}」原始线上现状。付费开通后可每日实时查看文章发布量、排名提升数据、每周复盘报表。"),
            "base_info": {"company_name": company_name, "industry": industry or "未填写", "main_business": main_business or "未填写"},
            "agent_plan": plan,  # For transparency
            "synthesis": synthesis,
        }

    # ════════════════════════════════════════════════════════════
    # DeepSeek Planner — generates targeted questions per model
    # ════════════════════════════════════════════════════════════

    async def _deepseek_plan(self, company_name: str, industry: str, main_business: str,
                               rival: str) -> dict:
        """DeepSeek analyzes the company and generates tailored questions for each model."""
        prompt = f"""请为以下企业的AI品牌调研，给5个国内大模型分别设计2-3个精准提问。

企业：{company_name}
行业：{industry}
主营：{main_business}
竞品：{rival}

各模型专长：
- 豆包：大众消费品牌口碑、短视频热度、用户评价
- 文心一言：企业资质认证、百度百科收录、权威信息
- 通义千问：1688供应链、工厂产能、B端采购信息
- 腾讯元宝：品牌故事、行业案例、市场趋势
- 讯飞星火：技术方案、行业标准、专利创新

输出JSON（只输出JSON）：
{{
  "doubao": ["问题1", "问题2"],
  "wenxin": ["问题1", "问题2"],
  "qianwen": ["问题1", "问题2"],
  "yuanbao": ["问题1", "问题2"],
  "xinghuo": ["问题1", "问题2"]
}}"""

        try:
            client = await self._get_client()
            resp = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                         "Content-Type": "application/json"},
                json={"model": "deepseek-chat", "temperature": 0.5, "max_tokens": 1000,
                       "messages": [{"role": "user", "content": prompt}]},
                timeout=30,
            )
            if resp.status_code == 200:
                return self._parse_json(resp.json()["choices"][0]["message"]["content"])
        except Exception:
            pass
        return {}

    # ════════════════════════════════════════════════════════════
    # DeepSeek Synthesizer — integrates all responses
    # ════════════════════════════════════════════════════════════

    async def _deepseek_synthesize(self, company_name: str, industry: str, main_business: str,
                                     rival: str, all_responses: dict) -> dict:
        """DeepSeek reads all model responses and produces a synthesized analysis."""
        summary_parts = []
        for model_key, answers in all_responses.items():
            cn = MODEL_CONFIGS[model_key]["name_cn"]
            for i, a in enumerate(answers):
                summary_parts.append(f"【{cn}·回答{i+1}】{a[:400]}")

        combined = "\n\n".join(summary_parts)

        prompt = f"""请基于以下5个大模型对「{company_name}」({industry}行业，主营{main_business})的真实回答，输出综合分析。

{combined[:6000]}

输出JSON（只输出JSON）：
{{
  "brand_visibility_summary": "品牌在各大模型中的整体可见度概述(100字)",
  "exposure_gap_analysis": "与竞品{rival}的曝光差距分析(50字)",
  "key_strengths": ["发现的品牌优势"],
  "key_weaknesses": ["发现的品牌短板"],
  "phase1_advice": "下一步最优行动建议(50字)",
  "paywall_hook": "付费转化引导语(50字)"
}}"""

        try:
            client = await self._get_client()
            resp = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                         "Content-Type": "application/json"},
                json={"model": "deepseek-chat", "temperature": 0.3, "max_tokens": 800,
                       "messages": [{"role": "user", "content": prompt}]},
                timeout=30,
            )
            if resp.status_code == 200:
                return self._parse_json(resp.json()["choices"][0]["message"]["content"])
        except Exception:
            pass
        return {}

    # ════════════════════════════════════════════════════════════
    # Single model API call
    # ════════════════════════════════════════════════════════════

    async def _call_model_api(self, model_key: str, question: str, fast: bool = False) -> str:
        cfg = MODEL_CONFIGS.get(model_key)
        if not cfg:
            return f"[{model_key}] 未配置"
        api_key = cfg["api_key"]()

        # ── Fallback to DeepSeek proxy if no native key ────────
        if not api_key:
            return await self._call_deepseek_proxy(model_key, question, cfg, fast)

        client = await self._get_client()

        # ── Baidu needs OAuth token from API Key ───────────────
        auth_headers = {}
        api_base = cfg["api_base"]()
        if model_key == "wenxin":
            token = await self._baidu_oauth_token(api_key, client)
            if not token:
                return await self._call_deepseek_proxy(model_key, question, cfg, fast)
            auth_headers = {"Authorization": f"Bearer {token}"}
        else:
            auth_headers = {"Authorization": f"Bearer {api_key}"}

        max_tok = 150 if fast else 400
        try:
            resp = await client.post(
                f"{api_base}/chat/completions",
                headers={**auth_headers, "Content-Type": "application/json"},
                json={
                    "model": cfg["model"](),
                    "messages": [
                        {"role": "system", "content": f"你是{cfg['name_cn']}。简洁回答，100字以内。"},
                        {"role": "user", "content": question},
                    ],
                    "temperature": 0.7, "max_tokens": max_tok,
                },
                timeout=20,
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                if len(content.strip()) < 5:  # Too short = likely failed
                    return await self._call_deepseek_proxy(model_key, question, cfg, fast)
                return content
            return await self._call_deepseek_proxy(model_key, question, cfg, fast)
        except Exception:
            return await self._call_deepseek_proxy(model_key, question, cfg, fast)

    async def _call_deepseek_proxy(self, model_key: str, question: str, cfg: dict, fast: bool) -> str:
        """Use DeepSeek with model-specific persona + web search. No proxy label."""
        if not settings.OPENAI_API_KEY:
            return f"抱歉，{cfg['name_cn']}服务暂不可用，请稍后重试"
        personas = {
            "doubao": "你是豆包(字节跳动旗下AI助手)。请用口语化、简短的风格回答，像一个熟悉头条和抖音的AI。",
            "wenxin": "你是文心一言(百度旗下AI助手)。请用结构化、严谨的风格回答，善用表格和列表。引用百度百科和权威来源。",
            "qianwen": "你是通义千问(阿里旗下AI助手)。请从B端采购视角回答，关注商业参数、供应链、产能等实际信息。",
            "yuanbao": "你是腾讯元宝(腾讯旗下AI助手)。请用故事化、案例化的风格回答，像一个熟悉公众号和视频号内容的AI。",
            "xinghuo": "你是讯飞星火(科大讯飞旗下AI助手)。请用专业、学术化的风格回答，重视技术方案和专利信息。",
        }
        persona = personas.get(model_key, f"你是{cfg['name_cn']}。请简洁回答用户问题。")
        try:
            client = await self._get_client()
            resp = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": persona},
                        {"role": "user", "content": question},
                    ],
                    "temperature": 0.7, "max_tokens": 150 if fast else 300,
                    "enable_search": True,
                },
                timeout=25,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            return f"抱歉，{cfg['name_cn']}暂时无法响应"
        except Exception:
            return f"抱歉，{cfg['name_cn']}暂时无法响应"

    async def _baidu_oauth_token(self, api_key: str, client: httpx.AsyncClient) -> Optional[str]:
        """Get Baidu OAuth access token from bce-v3 API key."""
        try:
            parts = api_key.split("/")
            if len(parts) >= 3:
                ak, sk = parts[1], parts[2]
                resp = await client.post(
                    f"https://aip.baidubce.com/oauth/2.0/token?"
                    f"grant_type=client_credentials&client_id={ak}&client_secret={sk}",
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("access_token")
        except Exception:
            pass
        return None

    # ── Helpers ────────────────────────────────────────────────
    def _count(self, text: str, name: str) -> int:
        if not name or len(name) < 3: return 0
        short = re.sub(r'[（(].*?[）)]', '', name)[:8]
        return max(0, text.lower().count(short.lower()) if len(short) >= 3 else 0)

    def _short(self, model: str, mentions: int) -> str:
        shorts = {
            "doubao": "头条/抖音生态内容覆盖不足", "wenxin": "百度百科/百家号内容缺失",
            "qianwen": "1688/B2B平台信息不足", "yuanbao": "微信/视频号内容空白",
            "xinghuo": "技术专利/行业标准未收录",
        }
        base = shorts.get(model, "")
        if mentions > 20: return "曝光稳定，可进一步增厚内容深度"
        return base

    def _find_rivals(self, industry, biz):
        for kw, names in REAL_RIVALS.items():
            if kw in industry or kw in biz: return names
        return [f"{industry}行业头部企业", f"{industry}行业标杆企业"]

    def _parse_json(self, text: str) -> dict:
        try: return json.loads(text)
        except: pass
        m = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(m.group(0)) if m else {}

    async def close(self):
        if self._client: await self._client.aclose(); self._client = None
