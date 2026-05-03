"""LLM service for generating AI-powered recommendations using Google Gemini."""
from typing import List
import random
from app.config import get_settings
from app.models import SchemaInventory, GEOScore, Issue

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class LLMService:
    """Service for generating recommendations using Google Gemini."""
    
    def __init__(self):
        """Initialize the LLM service with Google Gemini."""
        self.settings = get_settings()
        self.model = None
        
        if GEMINI_AVAILABLE and self.settings.gemini_api_key:
            try:
                genai.configure(api_key=self.settings.gemini_api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                print("✅ Google Gemini initialized successfully with gemini-1.5-flash")
            except Exception as e:
                print(f"⚠️ Failed to initialize Gemini: {e}")
                self.model = None
        else:
            print("⚠️ Gemini not available, using fallback recommendations")
    
    def generate_schema_improvements(
        self,
        inventory: SchemaInventory,
        url: str
    ) -> List[str]:
        """Generate improved JSON-LD schema markup or recommendations."""
        if not self.model:
            print("🔄 Using fallback for schema improvements (no model)")
            return self._fallback_schema_improvements(inventory)
        
        try:
            current_schemas = ', '.join([t.type_name for t in inventory.types_found if t.found]) if inventory.types_found else 'None'
            
            # Different prompt based on whether schema exists
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

            print(f"🤖 Calling Gemini for schema improvements (URL: {url[:50]}..., Schemas: {inventory.total_count})")
            response = self.model.generate_content(prompt)
            result = response.text.strip()
            print(f"✅ Gemini returned schema improvements ({len(result)} chars)")
            return [result]
        
        except Exception as e:
            print(f"⚠️ Gemini error in schema improvements: {e}")
            print("🔄 Using fallback for schema improvements")
            return self._fallback_schema_improvements(inventory)
    
    def generate_content_recommendations(
        self,
        geo_score: GEOScore,
        url: str
    ) -> List[str]:
        """Generate rule-based content optimization recommendations."""
        # Define recommendation options for each rule type
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
                'Add a FAQ section with 3-5 questions your audience commonly asks. Structure each as a clear question followed by a concise 2-3 sentence answer. This directly matches the extraction patterns AI search engines use.',
                'Create a Q&A section at the bottom of your page addressing common objections or questions. Use a clear question-then-answer format — this is the exact structure AI systems look for when extracting FAQ content.'
            ]
        }
        
        # Filter rules that scored below 50% (score < max_score * 0.5)
        low_scoring_rules = [
            r for r in geo_score.rules
            if r.score < (r.max_score * 0.5)
        ]
        
        # Sort by score (lowest first) to prioritize worst-performing rules
        low_scoring_rules.sort(key=lambda r: r.score)
        
        # Generate recommendations for up to 3 rules
        recommendations = []
        for rule in low_scoring_rules[:3]:
            # Check if we have recommendations for this rule
            if rule.rule_name in recommendation_map:
                # Randomly pick one of the two options
                options = recommendation_map[rule.rule_name]
                selected_recommendation = random.choice(options)
                recommendations.append(selected_recommendation)
        
        print(f"📋 Generated {len(recommendations)} rule-based content recommendations (from {len(low_scoring_rules)} low-scoring rules)")
        
        return recommendations
    
    def generate_issues(
        self,
        inventory: SchemaInventory,
        geo_score: GEOScore
    ) -> List[Issue]:
        """Generate critical issues found during analysis."""
        if not self.model:
            print("🔄 Using fallback for issues (no model)")
            return self._fallback_issues(inventory, geo_score)
        
        try:
            failed_rules = [r for r in geo_score.rules if not r.passed]
            prompt = f"""Identify 2-3 critical issues affecting this website's AI search readiness based on the failed GEO rules below.

Schema Count: {inventory.total_count}
Schema Types: {', '.join([t.type_name for t in inventory.types_found if t.found]) if inventory.types_found else 'None'}
GEO Score: {geo_score.total_score}/100

Failed GEO Rules:
{chr(10).join([f"- {r.rule_name}: {r.message}" for r in failed_rules])}

Generate SPECIFIC, ACTIONABLE issues based on these failed rules. Reference these research-backed statistics when relevant:
- Answer-first content is 33% more likely to be cited by AI systems
- Definitional phrasing is 2x more likely to be cited by AI systems
- Quotable chunks increase AI visibility by 30%
- Sourced statistics increase LLM visibility by 30-40%

Identify the most critical issues in this format:
SEVERITY: [critical/warning/info]
TITLE: [Short title]
DESCRIPTION: [One sentence description with specific actionable advice]

Separate each issue with "---"."""

            print(f"🤖 Calling Gemini for issues (Score: {geo_score.total_score}/100, Failed rules: {len(failed_rules)})")
            response = self.model.generate_content(prompt)
            issues_text = response.text.strip()
            print(f"✅ Gemini returned issues response ({len(issues_text)} chars)")
            
            issues = []
            issue_blocks = issues_text.split('---')
            
            for block in issue_blocks[:3]:
                lines = [l.strip() for l in block.strip().split('\n') if l.strip()]
                if len(lines) >= 3:
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
                            description=description
                        ))
            
            if issues:
                print(f"✅ Parsed {len(issues)} issues from Gemini response")
                return issues
            else:
                print("⚠️ No issues parsed from Gemini response, using fallback")
                return self._fallback_issues(inventory, geo_score)
        
        except Exception as e:
            print(f"⚠️ Gemini error in issues generation: {e}")
            print("🔄 Using fallback for issues")
            return self._fallback_issues(inventory, geo_score)
    
    def _fallback_schema_improvements(self, inventory: SchemaInventory) -> List[str]:
        """Fallback schema recommendations when LLM is unavailable."""
        # Return beginner-friendly explanation when no schema exists
        if inventory.total_count == 0:
            explanation = """No structured data was found on this page. Structured data (JSON-LD) helps AI search engines understand your content.

Here are the recommended schema types to add for this page:

1. **Organization Schema** - Helps AI understand your business identity
   - Add your company name, logo, and contact information

2. **WebSite Schema** - Defines your website's basic information
   - Include site name, URL, and search functionality if available

3. **Article or WebPage Schema** - Describes your content
   - Add headline, author, publication date, and description

To implement, add a <script type="application/ld+json"> tag in your page's <head> section with the appropriate schema markup."""
            return [explanation]
        else:
            # If schema exists, provide improvement suggestions
            suggestions = f"""Found {inventory.total_count} schema(s) on this page. Here are suggestions to enhance them:

1. **Add Missing Properties** - Enrich existing schemas with more detailed information
   - Include author credentials, publication dates, and images

2. **Implement Additional Schema Types** - Consider adding:
   - BreadcrumbList for navigation
   - FAQPage if you have Q&A content
   - HowTo for instructional content

3. **Validate Your Markup** - Use Google's Rich Results Test to ensure proper implementation
   - Fix any validation errors or warnings"""
            return [suggestions]
    
    def _fallback_content_recommendations(self, geo_score: GEOScore) -> List[str]:
        """Fallback content recommendations when LLM is unavailable."""
        recommendations = []
        failed_rules = [r for r in geo_score.rules if not r.passed]
        
        if len(failed_rules) > 3:
            recommendations.append("Improve content quality by addressing multiple GEO rule failures")
            recommendations.append("Add clear author information and credentials")
            recommendations.append("Include publication dates and last updated timestamps")
        elif len(failed_rules) > 0:
            for rule in failed_rules[:2]:
                recommendations.append(f"Fix: {rule.message}")
        else:
            recommendations.append("Maintain high content quality standards")
            recommendations.append("Regularly update content to keep it fresh")
        
        recommendations.append("Add more multimedia content (images, videos)")
        recommendations.append("Improve internal linking structure")
        
        return recommendations[:5]
    
    def _fallback_issues(self, inventory: SchemaInventory, geo_score: GEOScore) -> List[Issue]:
        """Fallback issues when LLM is unavailable."""
        issues = []
        
        if inventory.total_count == 0:
            issues.append(Issue(
                severity="critical",
                title="No Schema Markup Found",
                description="Page lacks structured data, making it harder for AI to understand content"
            ))
        
        if geo_score.total_score < 50:
            issues.append(Issue(
                severity="critical",
                title="Low GEO Score",
                description=f"Score of {geo_score.total_score}/100 indicates poor AI search readiness"
            ))
        elif geo_score.total_score < 70:
            issues.append(Issue(
                severity="warning",
                title="Moderate GEO Score",
                description=f"Score of {geo_score.total_score}/100 has room for improvement"
            ))
        
        failed_critical = [r for r in geo_score.rules if not r.passed and r.rule_name in ['has_title', 'has_meta_description']]
        if failed_critical:
            issues.append(Issue(
                severity="critical",
                title="Missing Critical Metadata",
                description="Page lacks essential title or meta description tags"
            ))
        
        return issues[:3]


# Made with Bob
