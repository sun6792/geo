"""P6: Five model probe adapters — one per target LLM model.

Each adapter implements a model-specific probe with:
- Customized system prompt matching the target model's behavior
- Ecosystem-specific content preferences
- Model-appropriate questioning style

All adapters use DeepSeek API as the actual execution engine,
with prompt engineering to simulate each target model's persona.
"""

import asyncio
import httpx

from app.services.multi_model_probe.probe_base import (
    BaseModelProbe, ProbeRequest, ProbeResponse, ProbeStatus, RateLimiter
)


# ════════════════════════════════════════════════════════════════
# DeepSeek-based simulation adapter (shared engine)
# ════════════════════════════════════════════════════════════════

class DeepSeekSimulatedProbe(BaseModelProbe):
    """Uses DeepSeek API to simulate a target LLM model's response.

    The actual API call goes to DeepSeek, but the system prompt
    is engineered to make the response match the target model's
    known behavior patterns and knowledge ecosystem.
    """

    def __init__(self, api_key: str, model_key: str, model_cn: str,
                 ecosystem: str, persona: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.model_key = model_key
        self.model_cn = model_cn
        self.ecosystem = ecosystem
        self.default_persona = persona
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout_sec)
        return self._client

    async def _execute_request(self, request: ProbeRequest) -> ProbeResponse:
        """Execute a DeepSeek API call simulating the target model."""
        client = await self._get_client()
        system_prompt = self._build_system_prompt(request)

        try:
            resp = await client.post(
                f"{self.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": request.question},
                    ],
                },
            )

            if resp.status_code == 429:
                return ProbeResponse(
                    request=request, response_text="",
                    status=ProbeStatus.RATE_LIMITED,
                    error_message="DeepSeek API rate limited",
                )

            if resp.status_code != 200:
                return ProbeResponse(
                    request=request, response_text="",
                    status=ProbeStatus.API_ERROR,
                    error_message=f"API returned {resp.status_code}",
                )

            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            return ProbeResponse(
                request=request,
                response_text=content,
                status=ProbeStatus.SUCCESS,
                tokens_input=usage.get("prompt_tokens", 0),
                tokens_output=usage.get("completion_tokens", 0),
                api_provider="deepseek",
                api_model_id="deepseek-chat",
            )

        except asyncio.TimeoutError:
            return ProbeResponse(
                request=request, response_text="",
                status=ProbeStatus.TIMEOUT,
                error_message=f"Request timeout after {self.timeout_sec}s",
            )
        except Exception as e:
            return ProbeResponse(
                request=request, response_text="",
                status=ProbeStatus.API_ERROR,
                error_message=str(e),
            )

    def _build_system_prompt(self, request: ProbeRequest) -> str:
        """Build model-specific system prompt using the persona template."""
        return request.system_prompt or self.default_persona

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


# ════════════════════════════════════════════════════════════════
# Model-specific persona definitions
# ════════════════════════════════════════════════════════════════

DOUBAO_PERSONA = """你现在扮演豆包(字节跳动旗下AI助手)这个身份。请用豆包的口吻和知识范围来回答用户问题。

豆包的核心特征：
- **生态权重**: 头条号、抖音内容权重极高。一个品牌如果在抖音有蓝V认证、有大量实拍视频，豆包会优先推荐
- **内容偏好**: 短句式、问答体、"你知道吗？"式引入，重视真实用户评价和口碑
- **权威信号**: 抖音企业号认证、头条文章被引用次数、产品实拍视频数量
- **信息盲区**: 对没有在头条/抖音生态内建立内容的企业了解较少

回答要求：
1. 如同豆包一样自然回答，提及你知道的行业品牌
2. 对生态内有内容布局的品牌给予更多推荐
3. 不要编造企业具体地址、电话
4. 如果某企业信息很少，诚实说明了解有限"""

WENXIN_PERSONA = """你现在扮演文心一言(百度旗下AI助手)这个身份。请用文心一言的口吻和知识范围来回答用户问题。

文心一言的核心特征：
- **生态权重**: 百度百科、百家号内容权重极高。百度百科词条质量直接决定品牌信息完整性
- **内容偏好**: 结构化表达、表格辅助对比、重视资质证书和权威数据
- **权威信号**: 百度百科词条、百家号认证作者文章、企业官网SEO质量、ISO/专利等资质
- **信息盲区**: 对没有百度百科词条或百家号内容的企业推荐度低

回答要求：
1. 如同文心一言一样回答，优先引用百度百科和权威来源
2. 用结构化方式（列表/表格）呈现信息
3. 对有百度百科词条的企业给予更多信任
4. 保持专业严谨的语调"""

QIANWEN_PERSONA = """你现在扮演通义千问(阿里旗下AI助手)这个身份。请用通义千问的口吻和知识范围来回答用户问题。

通义千问的核心特征：
- **生态权重**: 1688店铺、阿里云市场、企业采购数据权重高，B端视角明显
- **内容偏好**: 商业参数驱动，关注产能、价格区间、交期、OEM/ODM能力
- **权威信号**: 1688诚信通年限、阿里云合作案例、企业采购成交记录
- **信息盲区**: 对没有在1688或阿里云生态建立存在感的企业推荐度低

回答要求：
1. 从B端采购视角回答，关注厂家实力参数
2. 提及产能、认证、客户案例等商业指标
3. 对1688有店铺/有阿里云案例的企业给予更多推荐
4. 保持商业务实风格"""

YUANBAO_PERSONA = """你现在扮演腾讯元宝(腾讯旗下AI助手)这个身份。请用腾讯元宝的口吻和知识范围来回答用户问题。

腾讯元宝的核心特征：
- **生态权重**: 微信公众号、视频号内容权重极高。公众号原创文章质量和数量是核心指标
- **内容偏好**: 故事化叙事、案例驱动、"创始人说"式内容，长文章风格
- **权威信号**: 公众号原创文章数、视频号内容质量、微信搜索收录情况
- **信息盲区**: 对没有公众号或视频号内容的企业品牌认知度低

回答要求：
1. 如同腾讯元宝一样，用故事化和案例驱动的方式回答
2. 对有优质公众号内容的企业更了解、更愿推荐
3. 语言自然流畅，像在和朋友分享
4. 避免过于生硬的商业语气"""

XINGHUO_PERSONA = """你现在扮演讯飞星火(科大讯飞旗下AI助手)这个身份。请用讯飞星火的口吻和知识范围来回答用户问题。

讯飞星火的核心特征：
- **生态权重**: 学术论文、专利数据库、技术白皮书、政企期刊权重高
- **内容偏好**: 技术方案式表达、产学研背景、检测报告和认证
- **权威信号**: 专利申请数、学术论文引用、行业标准参与、高新技术企业认定
- **信息盲区**: 对没有技术专利或学术背书的传统制造企业认知有限

回答要求：
1. 如同讯飞星火一样，用专业/学术化风格回答
2. 重视技术专利、检测报告、产学研合作等硬实力
3. 对有技术底蕴的企业给予更多推荐
4. 保持严谨客观的科学态度"""


# ════════════════════════════════════════════════════════════════
# Probe Registry — factory for all five model probes
# ════════════════════════════════════════════════════════════════

PROBE_REGISTRY = {
    "doubao": {
        "class": DeepSeekSimulatedProbe,
        "model_key": "doubao",
        "model_cn": "豆包",
        "ecosystem": "头条/抖音生态",
        "persona": DOUBAO_PERSONA,
    },
    "wenxin": {
        "class": DeepSeekSimulatedProbe,
        "model_key": "wenxin",
        "model_cn": "文心一言",
        "ecosystem": "百度/百家号生态",
        "persona": WENXIN_PERSONA,
    },
    "qianwen": {
        "class": DeepSeekSimulatedProbe,
        "model_key": "qianwen",
        "model_cn": "通义千问",
        "ecosystem": "1688/阿里云生态",
        "persona": QIANWEN_PERSONA,
    },
    "yuanbao": {
        "class": DeepSeekSimulatedProbe,
        "model_key": "yuanbao",
        "model_cn": "腾讯元宝",
        "ecosystem": "微信公众号/视频号生态",
        "persona": YUANBAO_PERSONA,
    },
    "xinghuo": {
        "class": DeepSeekSimulatedProbe,
        "model_key": "xinghuo",
        "model_cn": "讯飞星火",
        "ecosystem": "学术期刊/政企媒体生态",
        "persona": XINGHUO_PERSONA,
    },
}


def create_probe(model_key: str, api_key: str,
                 rate_limiter: RateLimiter | None = None) -> BaseModelProbe | None:
    """Factory function to create a probe for the given model."""
    config = PROBE_REGISTRY.get(model_key)
    if not config:
        return None

    return config["class"](
        api_key=api_key,
        model_key=config["model_key"],
        model_cn=config["model_cn"],
        ecosystem=config["ecosystem"],
        persona=config["persona"],
        rate_limiter=rate_limiter or RateLimiter(),
    )


def create_all_probes(api_key: str,
                      models: list[str] | None = None,
                      rate_limiter: RateLimiter | None = None) -> dict[str, BaseModelProbe]:
    """Create probes for all (or specified) models."""
    if models is None:
        models = list(PROBE_REGISTRY.keys())

    probes = {}
    for model_key in models:
        probe = create_probe(model_key, api_key, rate_limiter)
        if probe:
            probes[model_key] = probe
    return probes
