"""P6: Content Quality Validator — compliance checks for generated content.

Validates:
- Sensitive word filtering (basic pattern matching)
- Content structure completeness
- Brand fact consistency (cross-reference with known facts)
- SEO quality scoring
"""

import re
from dataclasses import dataclass, field


# ════════════════════════════════════════════════════════════════
# Sensitive word patterns (basic implementation; production should use a library)
# ════════════════════════════════════════════════════════════════

SENSITIVE_PATTERNS = [
    (r"(最|第一|唯一|首家|独家|国家级|世界级)", "warning", "使用了绝对化表述，建议修改为客观描述"),
    (r"(点击|立即购买|限时|促销|折扣|优惠券)", "warning", "包含营销促销用语"),
    (r"(假|骗|欺诈|传销|非法)", "error", "包含风险词汇"),
    (r"(\d{11,})", "info", "检测到长数字串，请确认是否为手机号/身份证号"),
]

CONTACT_INFO_PATTERN = re.compile(
    r'(1[3-9]\d{9})|(\d{3,4}-\d{7,8})|([\w.-]+@[\w.-]+\.\w{2,})'
)


@dataclass
class ValidationResult:
    """Content validation result."""
    is_valid: bool
    errors: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)
    info: list[dict] = field(default_factory=list)
    quality_score: float = 0.0
    suggestions: list[str] = field(default_factory=list)


class ContentValidator:
    """Validates generated content quality and compliance."""

    def validate(self, content: str, check_contact_info: bool = True) -> ValidationResult:
        """Run full validation on content."""
        errors = []
        warnings = []
        info = []

        # 1. Sensitive word check
        for pattern, level, message in SENSITIVE_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                entry = {"pattern": pattern, "message": message, "matches": list(set(matches))[:5]}
                if level == "error":
                    errors.append(entry)
                elif level == "warning":
                    warnings.append(entry)
                else:
                    info.append(entry)

        # 2. Contact info check (if privacy is a concern)
        if check_contact_info:
            contacts = CONTACT_INFO_PATTERN.findall(content)
            if contacts:
                warnings.append({
                    "pattern": "contact_info",
                    "message": f"检测到{len(contacts)}处疑似联系方式",
                    "matches": [c[0] or c[1] or c[2] for c in contacts[:3]],
                })

        # 3. Structure completeness check
        struct_checks = self._check_structure(content)
        warnings.extend(struct_checks)

        # 4. Quality scoring
        quality = self._calculate_quality(content, errors, warnings)

        suggestions = []
        if not content:
            errors.append({"pattern": "empty", "message": "内容为空"})
        if len(content) < 300:
            warnings.append({"pattern": "too_short", "message": f"内容较短({len(content)}字)，建议扩展"})
        if len(content) > 10000:
            info.append({"pattern": "too_long", "message": f"内容较长({len(content)}字)，考虑拆分"})

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info,
            quality_score=quality,
            suggestions=suggestions,
        )

    def validate_fact_consistency(self, content: str, known_facts: dict) -> list[dict]:
        """Cross-reference content with known facts for consistency."""
        issues = []
        for field, expected_value in known_facts.items():
            if expected_value and isinstance(expected_value, str) and len(expected_value) > 2:
                # Check if expected value appears (or at least isn't contradicted)
                if field in ("company_name", "name") and expected_value[:3] not in content[:500]:
                    issues.append({
                        "field": field,
                        "expected": expected_value,
                        "issue": "企业名称可能未出现在内容开头",
                        "severity": "minor",
                    })
        return issues

    def calculate_seo_score(self, content: str, target_keywords: list[str]) -> float:
        """Calculate basic SEO quality score."""
        if not content or not target_keywords:
            return 0.0

        score = 50.0  # Base score

        # Title check (first line)
        first_line = content.split("\n")[0] if content else ""
        title_matches = sum(1 for kw in target_keywords if kw in first_line)
        score += title_matches * 10

        # Keyword density
        content_lower = content.lower()
        for kw in target_keywords:
            count = content_lower.count(kw.lower())
            if count >= 3:
                score += 5
            elif count >= 1:
                score += 2

        # Structure
        h2_count = len(re.findall(r'^##\s', content, re.MULTILINE))
        h3_count = len(re.findall(r'^###\s', content, re.MULTILINE))
        score += min(h2_count, 5) * 3 + min(h3_count, 8) * 1

        # Length
        content_len = len(content)
        if 800 <= content_len <= 2000:
            score += 10
        elif 500 <= content_len <= 3000:
            score += 5

        return min(100.0, score)

    def _check_structure(self, content: str) -> list[dict]:
        """Check content structure completeness."""
        warnings = []
        if not re.search(r'^#+\s', content):
            warnings.append({"pattern": "no_heading", "message": "缺少标题结构"})
        if len(re.findall(r'^#+\s', content, re.MULTILINE)) < 2 and len(content) > 500:
            warnings.append({"pattern": "few_headings", "message": "标题数量较少，建议增加分段标题"})
        if "\n\n" not in content and len(content) > 300:
            warnings.append({"pattern": "no_paragraphs", "message": "缺少段落分隔，阅读体验不佳"})
        return warnings

    def _calculate_quality(self, content: str, errors: list, warnings: list) -> float:
        """Calculate overall quality score."""
        score = 80.0
        score -= len(errors) * 20
        score -= len(warnings) * 5
        if not content:
            score = 0
        return max(0.0, min(100.0, score))
