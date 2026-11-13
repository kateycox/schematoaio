"""LLM service that routes requests through the Zo /zo/ask API.

Supports per-request model selection and automatic fallback to other
configured tiers if the chosen model fails.
"""
from typing import List, Optional
import random
import httpx

from app.config import get_settings, MODEL_TIERS, DEFAULT_TIER, FALLBACK_ORDER
from app.models import SchemaInventory, GEOScore, Issue


ZO_ASK_URL = "https://api.zo.computer/zo/ask"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class LLMOutOfCredits(Exception):
    """Raised when every available model has refused for credit/quota reasons."""
    pass


def _looks_like_credit_error(status_code: Optional[int], body: str) -> bool:
    if status_code in (402, 429):
        return True
    needles = ("quota", "insufficient", "credit", "exhaust", "billing", "payment")
    lowered = body.lower()
    return any(n in lowered for n in needles)


class LLMService:
    """Generates schema improvements, content recs, and issues.

    Routes per-tier: Gemini tier hits Google's Gemini API directly;
    other tiers hit Zo /ask (which fans out to OpenRouter BYOK).
    """

    def __init__(self):
        self.settings = get_settings()
        self.zo_api_key = self.settings.zo_api_key
        self.gemini_api_key = self.settings.gemini_api_key

    def _call_gemini(self, prompt: str, model_id: str) -> tuple[Optional[str], bool]:
        """Returns (output, credits_exhausted)."""
        if not self.gemini_api_key:
            print("⚠️ GEMINI_API_KEY not configured; cannot call Gemini directly")
            return None, False
        try:
            with httpx.Client(timeout=90.0) as client:
                resp = client.post(
                    GEMINI_API_URL.format(model=model_id),
                    params={"key": self.gemini_api_key},
                    headers={"content-type": "application/json"},
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                )
                if resp.status_code >= 400:
                    body = resp.text or ""
                    print(f"⚠️ Gemini {resp.status_code}: {body[:200]}")
                    return None, _looks_like_credit_error(resp.status_code, body)
                data = resp.json()
                candidates = data.get("candidates") or []
                if not candidates:
                    print(f"⚠️ Gemini returned no candidates: {data}")
                    return None, False
                parts = candidates[0].get("content", {}).get("parts") or []
                text = "".join(p.get("text", "") for p in parts).strip()
                if text:
                    print(f"✅ Gemini ({model_id}) returned {len(text)} chars")
                    return text, False
                print("⚠️ Gemini returned empty text")
                return None, False
        except Exception as e:
            print(f"⚠️ Gemini call failed: {e}")
            return None, False

    def _call_zo_ask(self, prompt: str, model_id: str) -> tuple[Optional[str], bool]:
        """Returns (output, credits_exhausted)."""
        if not self.zo_api_key:
            print("⚠️ ZO_API_KEY not configured; cannot call Zo /ask")
            return None, False
        try:
            with httpx.Client(timeout=90.0) as client:
                resp = client.post(
                    ZO_ASK_URL,
                    headers={
                        "authorization": f"Bearer {self.zo_api_key}",
                        "content-type": "application/json",
                        "accept": "application/json",
                    },
                    json={"input": prompt, "model_name": model_id},
                )
                if resp.status_code >= 400:
                    body = resp.text or ""
                    print(f"⚠️ Zo /ask {resp.status_code}: {body[:200]}")
                    return None, _looks_like_credit_error(resp.status_code, body)
                data = resp.json()
                output = data.get("output")
                if isinstance(output, str) and output.strip():
                    print(f"✅ Zo /ask ({model_id}) returned {len(output)} chars")
                    return output, False
                print(f"⚠️ Zo /ask ({model_id}) returned empty output")
                return None, False
        except Exception as e:
            print(f"⚠️ Zo /ask ({model_id}) failed: {e}")
            return None, False

    def _call_zo(self, prompt: str, tier: str) -> Optional[str]:
        """Try the requested tier, then fall back through the rest.

        Raises LLMOutOfCredits when every attempted tier failed and at
        least one of those failures looked like a credit/quota error.
        """
        if tier not in MODEL_TIERS:
            tier = DEFAULT_TIER

        attempt_order = [tier] + [t for t in FALLBACK_ORDER if t != tier]

        any_credit_error = False
        for current in attempt_order:
            spec = MODEL_TIERS[current]
            model_id = spec["id"]
            provider = spec.get("provider", "zo")
            if not model_id:
                continue

            if provider == "gemini":
                output, credits_exhausted = self._call_gemini(prompt, model_id)
            else:
                output, credits_exhausted = self._call_zo_ask(prompt, model_id)

            if output:
                if current != tier:
                    print(f"⚠️ Tier '{tier}' failed; succeeded with '{current}'")
                return output

            if credits_exhausted:
                any_credit_error = True

        print("❌ All configured tiers failed")
        if any_credit_error:
            raise LLMOutOfCredits(
                "Yikes, looks like we're out of credits. Try choosing another LLM model, if that doesn't work come back again later."
            )
        return None

    def generate_schema_improvements(
        self,
        inventory: SchemaInventory,
        url: str,
        tier: str = DEFAULT_TIER,
    ) -> List[str]:
        current_schemas = (
            ", ".join([t.type_name for t in inventory.types_found if t.found])
            if inventory.types_found
            else "None"
        )

        if inventory.total_count == 0:
            prompt = f"""This webpage has NO structured data (JSON-LD schema markup).

URL: {url}

Provide a beginner-friendly explanation that:
1. Explains what structured data is and why it matters for AI search engines
2. Lists 2-3 specific schema types recommended for this page
3. Briefly explains what each schema type does
4. Keeps the tone helpful and educational, not technical

Format as plain text with clear sections. Do NOT include actual JSON-LD code."""
        else:
            prompt = f"""Generate improved JSON-LD schema markup for this website. Return ONLY valid JSON-LD code, not text descriptions.

URL: {url}
Current Schema Types: {current_schemas}
Total Schemas: {inventory.total_count}

Generate complete, valid JSON-LD markup that includes:
1. All existing schema types with enhanced properties
2. Additional recommended schema types (Article, Organization, WebSite, BreadcrumbList, etc.)
3. Proper @context and @type declarations
4. Rich properties like author, datePublished, description, image, etc.

Return ONLY the JSON-LD code wrapped in <script type="application/ld+json"> tags. Make it production-ready and valid according to schema.org standards."""

        result = self._call_zo(prompt, tier)
        if result:
            return [result]
        return self._fallback_schema_improvements(inventory)

    def generate_content_recommendations(
        self,
        geo_score: GEOScore,
        url: str,
        tier: str = DEFAULT_TIER,
        limit: Optional[int] = 3,
    ) -> List[str]:
        recommendation_map = {
            'answer_first_content': [
                'Lead with a direct answer in your first 200 words. Content that clearly summarizes answers upfront is 33% more likely to be cited by AI systems. Use patterns like [Topic] is... or [Topic] refers to... in your opening paragraph.',
                'Add a TL;DR or summary statement in your first paragraph. AI search engines extract from the top of the page first — content that answers the query upfront is 33% more likely to be cited.'
            ],
            'quotable_chunks': [
                'Break your content into short, extractable paragraphs (2-3 sentences each). Content structured into clear, quotable chunks can increase AI visibility by 30%. Add bullet point lists to summarize key takeaways.',
                'Add standalone sentences that can be quoted without context. AI systems extract individual passages, not full pages — concise, self-contained statements increase your visibility by 30%.'
            ],
            'definitional_phrasing': [
                'Use definitional sentence patterns like X is..., X refers to..., or X means... throughout your content. Cited sentences are nearly 2x as likely to use definitional phrasing rather than descriptive language.',
                'Replace descriptive language with definitions. Instead of saying AI helps businesses, say AI is a technology that enables businesses to... Definitional phrasing is 2x more likely to be cited by AI systems.'
            ],
            'sourced_statistics': [
                'Include specific numbers, percentages, and data points with sources. Adding sourced statistics increases LLM visibility by 30-40%. Example: Instead of saying growth is strong, say revenue grew 23% year-over-year (Source: Annual Report 2025).',
                'Add at least 2-3 concrete data points with attributions. Pages with sourced statistics see 30-40% higher AI visibility. Cite specific studies, reports, or datasets rather than making general claims.'
            ],
            'question_format_headings': [
                'Reformat your H2 and H3 headings as questions that match how users search. Instead of Our Services use What services do we offer? This aligns with how AI systems match content to queries.',
                'Turn at least half your subheadings into questions starting with Who, What, When, Where, Why, or How. AI search engines match user queries to headings — question format creates a direct match.'
            ],
            'content_freshness': [
                'Update your page with a recent dateModified timestamp. AI systems prefer fresh content. Add recent data points or update existing statistics to signal the content is current and maintained.',
                'Add a Last Updated date visible on the page and in your schema markup. AI systems deprioritize stale content — even small updates with a current timestamp signal freshness.'
            ],
            'faq_content_blocks': [
                'Give your FAQ its own page (for example /faq) and link to it from your navigation and footer. AI answer engines retrieve and cite individual pages, so a page that is only questions and answers, with FAQPage schema, matches question queries more cleanly than a block tucked under other content.',
                'Create a dedicated FAQ page with 5-10 questions your audience actually asks, each a visible question heading followed by a 2-3 sentence answer, and add matching FAQPage schema. Separate, focused pages help AI search; you do not need to cram everything onto one page.'
            ]
        }

        if limit is None:
            candidate_rules = [r for r in geo_score.rules if not r.passed or r.score < r.max_score]
        else:
            candidate_rules = [r for r in geo_score.rules if r.score < (r.max_score * 0.5)]

        candidate_rules.sort(key=lambda r: r.score)
        if limit is not None:
            candidate_rules = candidate_rules[:limit]

        recommendations = []
        for rule in candidate_rules:
            if rule.rule_name in recommendation_map:
                options = recommendation_map[rule.rule_name]
                recommendations.append(random.choice(options))

        return recommendations

    def generate_issues(
        self,
        inventory: SchemaInventory,
        geo_score: GEOScore,
        tier: str = DEFAULT_TIER,
    ) -> List[Issue]:
        failed_rules = [r for r in geo_score.rules if not r.passed]
        prompt = f"""Identify 2-3 critical issues affecting this website's AI search readiness based on the failed GEO rules below.

Schema Count: {inventory.total_count}
Schema Types: {', '.join([t.type_name for t in inventory.types_found if t.found]) if inventory.types_found else 'None'}
GEO Score: {geo_score.total_score}/100

Failed GEO Rules:
{chr(10).join([f"- {r.rule_name}: {r.message}" for r in failed_rules])}

Generate SPECIFIC, ACTIONABLE issues based on these failed rules. Do NOT recommend merging or consolidating content (FAQ, About, services) onto a single page: AI search engines retrieve and cite individual URLs, so dedicated pages for distinct topics help visibility. This tool scores one URL at a time, so content on other pages of the site is not counted here. Reference these research-backed statistics when relevant:
- Answer-first content is 33% more likely to be cited by AI systems
- Definitional phrasing is 2x more likely to be cited by AI systems
- Quotable chunks increase AI visibility by 30%
- Sourced statistics increase LLM visibility by 30-40%

Identify the most critical issues in this format:
SEVERITY: [critical/warning/info]
TITLE: [Short title]
DESCRIPTION: [One sentence description with specific actionable advice]

Separate each issue with "---"."""

        issues_text = self._call_zo(prompt, tier)
        if not issues_text:
            return self._fallback_issues(inventory, geo_score)

        issues = []
        for block in issues_text.split('---')[:3]:
            lines = [l.strip() for l in block.strip().split('\n') if l.strip()]
            if len(lines) < 3:
                continue
            severity = "warning"
            title = "Issue"
            description = ""
            for line in lines:
                if line.startswith('SEVERITY:'):
                    severity = line.split(':', 1)[1].strip().lower()
                elif line.startswith('TITLE:'):
                    title = line.split(':', 1)[1].strip()
                elif line.startswith('DESCRIPTION:'):
                    description = line.split(':', 1)[1].strip()
            if title and description:
                issues.append(Issue(
                    severity=severity if severity in ['critical', 'warning', 'info'] else 'warning',
                    title=title,
                    description=description,
                ))

        return issues if issues else self._fallback_issues(inventory, geo_score)

    def _fallback_schema_improvements(self, inventory: SchemaInventory) -> List[str]:
        if inventory.total_count == 0:
            return ["""No structured data was found on this page. Structured data (JSON-LD) helps AI search engines understand your content.

Here are the recommended schema types to add for this page:

1. **Organization Schema** - Helps AI understand your business identity
   - Add your company name, logo, and contact information

2. **WebSite Schema** - Defines your website's basic information
   - Include site name, URL, and search functionality if available

3. **Article or WebPage Schema** - Describes your content
   - Add headline, author, publication date, and description

To implement, add a <script type="application/ld+json"> tag in your page's <head> section with the appropriate schema markup."""]

        return [f"""Found {inventory.total_count} schema(s) on this page. Here are suggestions to enhance them:

1. **Add Missing Properties** - Enrich existing schemas with more detailed information
   - Include author credentials, publication dates, and images

2. **Implement Additional Schema Types** - Consider adding:
   - BreadcrumbList for navigation
   - FAQPage if you have Q&A content
   - HowTo for instructional content

3. **Validate Your Markup** - Use Google's Rich Results Test to ensure proper implementation
   - Fix any validation errors or warnings"""]

    def _fallback_issues(self, inventory: SchemaInventory, geo_score: GEOScore) -> List[Issue]:
        issues = []
        if inventory.total_count == 0:
            issues.append(Issue(
                severity="critical",
                title="No Schema Markup Found",
                description="Page lacks structured data, making it harder for AI to understand content",
            ))
        if geo_score.total_score < 50:
            issues.append(Issue(
                severity="critical",
                title="Low GEO Score",
                description=f"Score of {geo_score.total_score}/100 indicates poor AI search readiness",
            ))
        elif geo_score.total_score < 70:
            issues.append(Issue(
                severity="warning",
                title="Moderate GEO Score",
                description=f"Score of {geo_score.total_score}/100 has room for improvement",
            ))
        failed_critical = [
            r for r in geo_score.rules
            if not r.passed and r.rule_name in ['has_title', 'has_meta_description']
        ]
        if failed_critical:
            issues.append(Issue(
                severity="critical",
                title="Missing Critical Metadata",
                description="Page lacks essential title or meta description tags",
            ))
        return issues[:3]
