import httpx
from typing import Tuple


class FetchError(Exception):
    """Custom exception for URL fetching errors."""
    pass


async def fetch_url(url: str, timeout: int = 15) -> Tuple[str, int]:
    """
    Fetch HTML content from a URL.
    
    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (html_content, status_code)
        
    Raises:
        FetchError: If fetching fails
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0"
    }
    
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.text, response.status_code
            
    except httpx.TimeoutException:
        raise FetchError(f"Request timeout after {timeout} seconds")
        
    except httpx.HTTPStatusError as e:
        raise FetchError(f"HTTP {e.response.status_code}: {e.response.reason_phrase}")
        
    except httpx.RequestError as e:
        raise FetchError(f"Request failed: {str(e)}")
        
    except Exception as e:
        raise FetchError(f"Unexpected error: {str(e)}")

# Made with Bob
