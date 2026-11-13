from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse


class ContentAnalyzer:
    """Analyzes HTML content for GEO readiness signals."""
    
    def __init__(self, html: str, page_url: Optional[str] = None):
        """Initialize with HTML content and (optionally) the page's URL."""
        self.page_url = page_url
        self.soup = BeautifulSoup(html, 'lxml')
        self.text = self.soup.get_text(separator=' ', strip=True)
    
    def get_first_n_words(self, n: int = 200) -> str:
        """Get the first N words of the page content."""
        words = self.text.split()
        return ' '.join(words[:n])
    
    def get_headings(self, tags: List[str] = None) -> List[Dict[str, str]]:
        """
        Get all headings from the page.
        
        Args:
            tags: List of heading tags to extract (e.g., ['h2', 'h3'])
            
        Returns:
            List of dicts with 'tag' and 'text' keys
        """
        if tags is None:
            tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        
        headings = []
        for tag in tags:
            for heading in self.soup.find_all(tag):
                text = heading.get_text(strip=True)
                if text:
                    headings.append({'tag': tag, 'text': text})
        
        return headings
    
    def get_paragraphs(self) -> List[str]:
        """Get all paragraph texts from the page."""
        paragraphs = []
        for p in self.soup.find_all('p'):
            text = p.get_text(strip=True)
            if text:
                paragraphs.append(text)
        return paragraphs
    
    def get_lists(self) -> List[Dict[str, any]]:
        """Get all lists (ordered and unordered) from the page."""
        lists = []
        for list_tag in self.soup.find_all(['ul', 'ol']):
            items = [li.get_text(strip=True) for li in list_tag.find_all('li', recursive=False)]
            if items:
                lists.append({
                    'type': list_tag.name,
                    'items': items
                })
        return lists
    
    def find_patterns(self, patterns: List[str]) -> List[Dict[str, any]]:
        """
        Find regex patterns in the content.
        
        Args:
            patterns: List of regex patterns to search for
            
        Returns:
            List of dicts with 'pattern' and 'matches' keys
        """
        results = []
        for pattern in patterns:
            matches = re.findall(pattern, self.text, re.IGNORECASE)
            if matches:
                results.append({
                    'pattern': pattern,
                    'matches': matches,
                    'count': len(matches)
                })
        return results
    
    def get_date_modified(self, schemas: List[Dict] = None) -> Optional[datetime]:
        """
        Extract the last modified date from schema or meta tags.
        
        Args:
            schemas: List of JSON-LD schema objects
            
        Returns:
            datetime object or None
        """
        # Try schema first
        if schemas:
            for schema in schemas:
                for date_field in ['dateModified', 'datePublished', 'uploadDate']:
                    if date_field in schema:
                        try:
                            return datetime.fromisoformat(schema[date_field].replace('Z', '+00:00'))
                        except:
                            pass
        
        # Try meta tags
        meta_tags = [
            ('property', 'article:modified_time'),
            ('property', 'article:published_time'),
            ('name', 'last-modified'),
            ('name', 'date'),
        ]
        
        for attr, value in meta_tags:
            meta = self.soup.find('meta', {attr: value})
            if meta and meta.get('content'):
                try:
                    return datetime.fromisoformat(meta['content'].replace('Z', '+00:00'))
                except:
                    pass
        
        return None
    
    def find_dedicated_faq_page(self) -> Optional[str]:
        """Return the URL of a same-site FAQ page this page links to, if any.

        A dedicated FAQ page is the stronger setup for AI search: answer engines
        retrieve and cite individual URLs, so a page that is only Q&A (with its
        own title, headings and FAQPage schema) matches question queries more
        cleanly than a FAQ block appended to another page.
        """
        if not self.page_url:
            return None
        base = urlparse(self.page_url)
        current = base.path.rstrip('/') or '/'
        text_pattern = re.compile(r'^\s*(faqs?|frequently asked questions|questions)\s*$', re.I)
        for a in self.soup.find_all('a', href=True):
            href = a['href'].strip()
            if href.startswith(('mailto:', 'tel:', 'javascript:')):
                continue
            target = urlparse(urljoin(self.page_url, href))
            if target.netloc and target.netloc.lower().removeprefix('www.') != base.netloc.lower().removeprefix('www.'):
                continue
            path = target.path.rstrip('/') or '/'
            if path == current:
                continue
            last_segment = path.rsplit('/', 1)[-1].lower()
            if re.fullmatch(r'faqs?(\.html?)?|frequently-asked-questions', last_segment) or text_pattern.match(a.get_text(' ', strip=True)):
                return target._replace(fragment='', query='').geturl()
        return None

    def has_faq_structure(self) -> bool:
        """Check if the page has FAQ-style structure."""
        # Check for FAQ schema
        scripts = self.soup.find_all('script', type='application/ld+json')
        for script in scripts:
            if 'FAQPage' in script.string:
                return True
        
        # Check for common FAQ patterns in headings
        headings = self.get_headings(['h2', 'h3', 'h4'])
        question_words = ['what', 'how', 'why', 'when', 'where', 'who', 'which']
        
        question_count = 0
        for heading in headings:
            text_lower = heading['text'].lower()
            if any(text_lower.startswith(word) for word in question_words):
                question_count += 1
            if '?' in heading['text']:
                question_count += 1
        
        # If 3+ question-style headings, consider it FAQ-like
        return question_count >= 3
    
    def count_words(self) -> int:
        """Count total words in the content."""
        return len(self.text.split())
    
    def get_average_paragraph_length(self) -> float:
        """Get average paragraph length in words."""
        paragraphs = self.get_paragraphs()
        if not paragraphs:
            return 0.0
        
        total_words = sum(len(p.split()) for p in paragraphs)
        return total_words / len(paragraphs)
