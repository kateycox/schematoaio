import httpx
from urllib.parse import urlparse
from typing import Optional
from app.models import LlmsTxtStatus


class LlmsTxtChecker:
    """Checks for the presence of llms.txt file on a domain."""
    
    def __init__(self, timeout: int = 10):
        """
        Initialize the llms.txt checker.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
    
    async def check_llms_txt(self, url: str) -> LlmsTxtStatus:
        """
        Check if llms.txt exists on the domain.
        
        Args:
            url: The URL to extract domain from and check
            
        Returns:
            LlmsTxtStatus object with status and content info
        """
        # Extract domain from URL
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        llms_txt_url = f"{domain}/llms.txt"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(llms_txt_url)
                
                # Check if response is 200 and has content
                if response.status_code == 200:
                    content = response.text.strip()
                    if content:
                        return LlmsTxtStatus(
                            status='Present',
                            url=llms_txt_url,
                            content_length=len(content)
                        )
                    else:
                        # 200 but empty
                        return LlmsTxtStatus(
                            status='Missing',
                            url=llms_txt_url,
                            content_length=0
                        )
                else:
                    # Non-200 status (404, etc.)
                    return LlmsTxtStatus(
                        status='Missing',
                        url=llms_txt_url,
                        content_length=None
                    )
                    
        except Exception as e:
            # Network error, timeout, or other exception
            return LlmsTxtStatus(
                status='Missing',
                url=llms_txt_url,
                content_length=None
            )


# Made with Bob