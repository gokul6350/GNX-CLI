from langchain_core.tools import tool
import urllib.request
import urllib.error

try:
    from langchain_community.tools import DuckDuckGoSearchRun, DuckDuckGoSearchResults
    DUCKDUCKGO_AVAILABLE = True
except ImportError:
    DUCKDUCKGO_AVAILABLE = False


@tool
def web_search(query: str) -> str:
    """Search the web using DuckDuckGo. Returns a summary of search results for the given query."""
    if not DUCKDUCKGO_AVAILABLE:
        return "Error: DuckDuckGo search is not available. Install with: pip install duckduckgo-search"
    
    try:
        search = DuckDuckGoSearchRun()
        result = search.invoke(query)
        return result
    except Exception as e:
        return f"Error searching web: {e}"


@tool  
def web_search_detailed(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo and return detailed results with URLs, titles, and snippets."""
    if not DUCKDUCKGO_AVAILABLE:
        return "Error: DuckDuckGo search is not available. Install with: pip install duckduckgo-search"
    
    try:
        search = DuckDuckGoSearchResults(num_results=max_results)
        results = search.invoke(query)
        return results
    except Exception as e:
        return f"Error searching web: {e}"


@tool
def fetch_url(url: str) -> str:
    """Fetch and read content from a URL. Renders JavaScript-heavy sites properly. Use this to check websites or read web page content."""
    try:
        # Add https if no scheme provided
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Use Jina AI Reader to render JS and get clean markdown content
        jina_url = f"https://r.jina.ai/{url}"
        
        req = urllib.request.Request(
            jina_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/plain'
            }
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode('utf-8', errors='ignore')
            
            # Truncate if too long
            if len(content) > 3000:
                content = content[:3000] + "\n\n... [truncated]"
            
            return f"URL: {url}\nStatus: OK\n\n{content}"
    except urllib.error.HTTPError as e:
        return f"HTTP Error {e.code}: {e.reason} for URL: {url}"
    except urllib.error.URLError as e:
        return f"URL Error: {e.reason} for URL: {url}"
    except Exception as e:
        return f"Error fetching URL: {e}"
