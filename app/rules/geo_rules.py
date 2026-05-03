from datetime import datetime, timezone
from app.rules.base_rule import BaseRule
from app.rules.rule_registry import registry
from app.models import GEORuleResult


class AnswerFirstContentRule(BaseRule):
    """Rule 1: Answer-first content in first 200 words."""
    
    def evaluate(self, content_analyzer, schemas: list) -> GEORuleResult:
        first_200 = content_analyzer.get_first_n_words(200)
        word_count = len(first_200.split())
        
        # Check for definitional patterns in first 200 words
        patterns = self.config.get('patterns', [
            r'\b\w+\s+is\s+',
            r'\b\w+\s+refers to\s+',
            r'\b\w+\s+means\s+'
        ])
        
        matches = content_analyzer.find_patterns(patterns)
        has_definition = any(m['count'] > 0 for m in matches)
        
        # Score based on word count and presence of definitions
        if word_count >= 150 and has_definition:
            score = self.weight
            passed = True
            message = "Strong answer-first content with clear definitions"
        elif word_count >= 100:
            score = self.weight * 0.7
            passed = True
            message = "Good opening content, could use more definitional phrasing"
        elif word_count >= 50:
            score = self.weight * 0.4
            passed = False
            message = "Minimal opening content"
        else:
            score = 0
            passed = False
            message = "Insufficient opening content"
        
        return self.create_result(
            score=score,
            passed=passed,
            message=message,
            details={
                'word_count': word_count,
                'has_definition': has_definition,
                'first_200_words': first_200[:200] + '...' if len(first_200) > 200 else first_200
            }
        )


class QuotableChunksRule(BaseRule):
    """Rule 2: Quotable/extractable chunks (short paragraphs and lists)."""
    
    def evaluate(self, content_analyzer, schemas: list) -> GEORuleResult:
        paragraphs = content_analyzer.get_paragraphs()
        lists = content_analyzer.get_lists()
        avg_para_length = content_analyzer.get_average_paragraph_length()
        
        # Count short paragraphs (ideal for extraction)
        short_paras = sum(1 for p in paragraphs if len(p.split()) <= 50)
        list_count = len(lists)
        
        # Score based on quotable content
        quotable_score = 0
        if short_paras >= 5:
            quotable_score += 0.5
        elif short_paras >= 3:
            quotable_score += 0.3
        
        if list_count >= 2:
            quotable_score += 0.5
        elif list_count >= 1:
            quotable_score += 0.3
        
        score = self.weight * quotable_score
        passed = quotable_score >= 0.6
        
        if passed:
            message = f"Good quotable content: {short_paras} short paragraphs, {list_count} lists"
        else:
            message = f"Limited quotable content: {short_paras} short paragraphs, {list_count} lists"
        
        return self.create_result(
            score=score,
            passed=passed,
            message=message,
            details={
                'short_paragraphs': short_paras,
                'total_paragraphs': len(paragraphs),
                'lists': list_count,
                'avg_paragraph_length': round(avg_para_length, 1)
            }
        )


class DefinitionalPhrasingRule(BaseRule):
    """Rule 3: Definitional sentence patterns ("X is...")."""
    
    def evaluate(self, content_analyzer, schemas: list) -> GEORuleResult:
        patterns = self.config.get('patterns', [
            r'\b(\w+)\s+is\s+',
            r'\b(\w+)\s+refers to\s+',
            r'\b(\w+)\s+means\s+'
        ])
        
        matches = content_analyzer.find_patterns(patterns)
        total_matches = sum(m['count'] for m in matches)
        
        # Score based on number of definitional phrases
        if total_matches >= 5:
            score = self.weight
            passed = True
            message = f"Excellent definitional phrasing: {total_matches} instances"
        elif total_matches >= 3:
            score = self.weight * 0.7
            passed = True
            message = f"Good definitional phrasing: {total_matches} instances"
        elif total_matches >= 1:
            score = self.weight * 0.4
            passed = False
            message = f"Some definitional phrasing: {total_matches} instances"
        else:
            score = 0
            passed = False
            message = "No definitional phrasing found"
        
        return self.create_result(
            score=score,
            passed=passed,
            message=message,
            details={
                'total_matches': total_matches,
                'patterns_found': [m['pattern'] for m in matches if m['count'] > 0]
            }
        )


class SourcedStatisticsRule(BaseRule):
    """Rule 4: Numerical data and statistics."""
    
    def evaluate(self, content_analyzer, schemas: list) -> GEORuleResult:
        patterns = self.config.get('patterns', [
            r'\d+%',
            r'\d+\s+(percent|times|fold)',
            r'\$\d+'
        ])
        
        matches = content_analyzer.find_patterns(patterns)
        total_matches = sum(m['count'] for m in matches)
        
        # Score based on statistics presence
        if total_matches >= 5:
            score = self.weight
            passed = True
            message = f"Rich statistical content: {total_matches} data points"
        elif total_matches >= 3:
            score = self.weight * 0.7
            passed = True
            message = f"Good statistical content: {total_matches} data points"
        elif total_matches >= 1:
            score = self.weight * 0.4
            passed = False
            message = f"Limited statistical content: {total_matches} data points"
        else:
            score = 0
            passed = False
            message = "No statistics or numerical data found"
        
        return self.create_result(
            score=score,
            passed=passed,
            message=message,
            details={
                'total_statistics': total_matches,
                'sample_matches': [m['matches'][:3] for m in matches if m['count'] > 0]
            }
        )


class QuestionFormatHeadingsRule(BaseRule):
    """Rule 5: Question-format H2/H3 headings."""
    
    def evaluate(self, content_analyzer, schemas: list) -> GEORuleResult:
        headings = content_analyzer.get_headings(['h2', 'h3'])
        question_words = self.config.get('question_words', 
            ['who', 'what', 'when', 'where', 'why', 'how', 'which'])
        
        question_headings = []
        for heading in headings:
            text_lower = heading['text'].lower()
            if any(text_lower.startswith(word) for word in question_words) or '?' in heading['text']:
                question_headings.append(heading['text'])
        
        count = len(question_headings)
        total_headings = len(headings)
        
        # Score based on question headings
        if count >= 5:
            score = self.weight
            passed = True
            message = f"Excellent question-format headings: {count}/{total_headings}"
        elif count >= 3:
            score = self.weight * 0.7
            passed = True
            message = f"Good question-format headings: {count}/{total_headings}"
        elif count >= 1:
            score = self.weight * 0.4
            passed = False
            message = f"Some question-format headings: {count}/{total_headings}"
        else:
            score = 0
            passed = False
            message = "No question-format headings found"
        
        return self.create_result(
            score=score,
            passed=passed,
            message=message,
            details={
                'question_headings': count,
                'total_headings': total_headings,
                'examples': question_headings[:3]
            }
        )


class ContentFreshnessRule(BaseRule):
    """Rule 6: Recent content modification."""
    
    def evaluate(self, content_analyzer, schemas: list) -> GEORuleResult:
        date_modified = content_analyzer.get_date_modified(schemas)
        thresholds = self.config.get('thresholds', {
            'full_points': 180,
            'partial_points': 365
        })
        
        if date_modified is None:
            return self.create_result(
                score=0,
                passed=False,
                message="No modification date found",
                details={'date_modified': None}
            )
        
        # Calculate days since modification
        now = datetime.now(timezone.utc)
        if date_modified.tzinfo is None:
            date_modified = date_modified.replace(tzinfo=timezone.utc)
        
        days_old = (now - date_modified).days
        
        # Score based on freshness
        if days_old <= thresholds['full_points']:
            score = self.weight
            passed = True
            message = f"Very fresh content: {days_old} days old"
        elif days_old <= thresholds['partial_points']:
            score = self.weight * 0.6
            passed = True
            message = f"Reasonably fresh content: {days_old} days old"
        else:
            score = self.weight * 0.2
            passed = False
            message = f"Stale content: {days_old} days old"
        
        return self.create_result(
            score=score,
            passed=passed,
            message=message,
            details={
                'date_modified': date_modified.isoformat(),
                'days_old': days_old
            }
        )


class FAQContentBlocksRule(BaseRule):
    """Rule 7: FAQ-style Q&A content."""
    
    def evaluate(self, content_analyzer, schemas: list) -> GEORuleResult:
        has_faq = content_analyzer.has_faq_structure()
        
        # Check for FAQ schema
        has_faq_schema = any(
            schema.get('@type') == 'FAQPage' 
            for schema in schemas
        )
        
        if has_faq_schema:
            score = self.weight
            passed = True
            message = "FAQ schema present with structured Q&A content"
        elif has_faq:
            score = self.weight * 0.7
            passed = True
            message = "FAQ-style content detected (no schema)"
        else:
            score = 0
            passed = False
            message = "No FAQ content found"
        
        return self.create_result(
            score=score,
            passed=passed,
            message=message,
            details={
                'has_faq_structure': has_faq,
                'has_faq_schema': has_faq_schema
            }
        )


def register_all_rules(config: dict) -> None:
    """
    Register all GEO rules with the global registry.
    
    Args:
        config: GEO rules configuration from YAML
    """
    rules_config = config.get('geo_rules', {})
    
    # Clear existing rules
    registry.clear()
    
    # Register each rule
    rule_classes = [
        ('answer_first_content', AnswerFirstContentRule),
        ('quotable_chunks', QuotableChunksRule),
        ('definitional_phrasing', DefinitionalPhrasingRule),
        ('sourced_statistics', SourcedStatisticsRule),
        ('question_format_headings', QuestionFormatHeadingsRule),
        ('content_freshness', ContentFreshnessRule),
        ('faq_content_blocks', FAQContentBlocksRule),
    ]
    
    for rule_name, rule_class in rule_classes:
        rule_config = rules_config.get(rule_name, {})
        rule = rule_class(
            name=rule_name,
            weight=rule_config.get('weight', 14.29),
            description=rule_config.get('description', ''),
            config=rule_config
        )
        registry.register(rule)

# Made with Bob
