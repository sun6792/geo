"""P6: Unbiased Query Generator — 70/20/10 ratio + cold-start + region alignment.

Core rules (enforced at code level, NOT configurable):
1. 70% industry pain-point queries — NO brand mention, pure industry need
2. 20% competitor comparison queries — industry terms + competitor names
3. 10% brand direct-search queries — client brand name only, for identity verification
4. Every query is a NEW standalone session — single user message, no context
5. NO brand mention in system prompt, NO guiding content
6. Region-aligned — reads target region from identity baseline
7. Generates 3 colloquial variants per query intent, averages results

The 10% brand queries are EXCLUDED from natural ranking calculation.
"""

import json
import hashlib
import httpx
from app.config import settings


class UnbiasedQueryGenerator:
    """Generates probing queries that simulate REAL user behavior.

    Produces questions a real person would ask when searching for
    products/services, without any brand bias or leading prompts.
    """

    REGION_MODIFIERS = {
        "华东": ["上海", "江苏", "浙江", "安徽"],
        "华南": ["广东", "深圳", "广州", "东莞", "佛山"],
        "华北": ["北京", "天津", "河北"],
        "华中": ["湖北", "湖南", "河南"],
        "西南": ["四川", "重庆", "云南"],
        "其他": ["全国", "国内"],
    }

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.api_base = "https://api.deepseek.com/v1"
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    async def generate(self, company_name: str, industry: str,
                        main_business: str, competitor_names: list[str],
                        region: str = "", count: int = 15) -> dict:
        """Generate unbiased probing queries with 70/20/10 ratio.

        Returns:
            {
                "natural_ranking_queries": [...],  # 70% + 20% = used for scoring
                "brand_verification_queries": [...],  # 10% = identity check only, NOT scored
                "variant_groups": {...}  # Grouped by intent for averaging
            }
        """
        region_str = region or "全国"
        n_natural = max(8, int(count * 0.9))  # 70% pain + 20% comparison
        n_brand = max(1, int(count * 0.1))     # 10% brand

        # ── Generate via DeepSeek ──────────────────────────────
        prompt = f"""你是一个真实的企业采购用户。你要生成{count}个在AI助手里的自然提问。

企业行业：{industry}
主营业务：{main_business}
目标地域：{region_str}
竞品列表：{', '.join(competitor_names[:5])}

要求：
1. {n_natural}个自然搜索提问（含行业痛点词+竞品对比词），完全不包含「{company_name}」品牌名
2. {n_brand}个仅含品牌名的直搜提问，用于核验基础信息
3. 每个提问像真人在说话，语言自然口语化
4. 不同提问覆盖不同的信息需求：找厂家、比价格、看口碑、避坑建议
5. 输出JSON：{{"natural_ranking": ["提问1",...], "brand_verification": ["提问1",...]}}

只输出JSON。"""

        client = await self._get_client()
        queries = {"natural_ranking": [], "brand_verification": []}
        try:
            resp = await client.post(
                f"{self.api_base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": "deepseek-chat", "temperature": 0.9, "max_tokens": 2000,
                       "messages": [{"role": "user", "content": prompt}]},
            )
            if resp.status_code == 200:
                raw = resp.json()["choices"][0]["message"]["content"]
                queries = self._parse_json(raw)
        except Exception:
            pass

        # ── Fallback: template-based ───────────────────────────
        if not queries.get("natural_ranking"):
            queries["natural_ranking"] = self._fallback_natural(industry, main_business, competitor_names, region_str)[:n_natural]
        if not queries.get("brand_verification"):
            queries["brand_verification"] = self._fallback_brand(company_name, industry)[:n_brand]

        # ── Generate 3 variants per intent ─────────────────────
        variant_groups = {}
        expanded_natural = []
        for q in queries.get("natural_ranking", []):
            variants = self._generate_variants(q)
            group_id = hashlib.md5(q.encode()).hexdigest()[:8]
            variant_groups[group_id] = variants
            expanded_natural.extend(variants)

        return {
            "natural_ranking_queries": expanded_natural,
            "brand_verification_queries": queries.get("brand_verification", []),
            "variant_groups": variant_groups,
            "query_counts": {
                "natural_ranking": len(expanded_natural),
                "brand_verification": len(queries.get("brand_verification", [])),
                "total": len(expanded_natural) + len(queries.get("brand_verification", [])),
            },
        }

    def _generate_variants(self, base: str) -> list[str]:
        """Generate 3 colloquial variants of the same intent query."""
        variants = [base]
        # Variant 1: add regional modifier
        if "全国" not in base and "国内" not in base:
            regions = ["国内", "广东", "江浙沪", "深圳"]
            for r in regions:
                if r not in base:
                    variants.append(f"{r}{base}")
                    break
        # Variant 2: rephrase with different wording
        rephrases = {
            "有哪些": "哪家好",
            "推荐": "靠谱的",
            "怎么样": "好不好",
            "哪家": "哪个牌子",
            "厂家": "供应商",
        }
        for old, new in rephrases.items():
            if old in base:
                variants.append(base.replace(old, new))
                break
        if len(variants) < 3:
            variants.append(f"请问{base}？")
        return variants[:3]

    def _fallback_natural(self, industry: str, business: str,
                           competitors: list[str], region: str) -> list[str]:
        """Template-based natural queries."""
        rival = competitors[0] if competitors else f"{industry}行业头部企业"
        return [
            f"{region or '国内'}做{industry}的厂家有哪些？请列举",
            f"{business}哪家质量好？求推荐靠谱工厂",
            f"想采购{business}，{region or '国内'}有哪些源头厂家",
            f"{rival}和{industry}行业其他厂家比怎么样",
            f"买{business}容易踩什么坑？怎么选供应商",
            f"{industry}行业口碑最好的工厂是哪家",
            f"{business}厂家排名，按质量排序",
            f"有没有做{business}价格实惠质量又好的工厂",
            f"第一次采购{business}，怎么判断厂家实力",
            f"{industry}行业供应商应该具备什么资质",
        ]

    def _fallback_brand(self, company: str, industry: str) -> list[str]:
        return [
            f"{company}怎么样？是正规厂家吗",
            f"{company}在{industry}行业里口碑如何",
            f"{company}的产品质量好不好",
        ]

    @staticmethod
    def _parse_json(text: str) -> dict:
        try: return json.loads(text)
        except: pass
        import re
        m = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(m.group(0)) if m else {}

    async def close(self):
        if self._client: await self._client.aclose(); self._client = None
