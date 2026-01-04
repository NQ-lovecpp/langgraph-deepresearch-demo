"""Search provider implementations for different backends."""

from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SearchResult:
    """Unified search result format."""
    title: str
    url: str
    content: str
    score: Optional[float] = None


class SearchProvider(ABC):
    """Abstract base class for search providers."""

    @abstractmethod
    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Execute a search query and return results."""
        pass


class ExaSearchProvider(SearchProvider):
    """Exa search provider implementation."""

    def __init__(self, api_key: str):
        from exa_py import Exa
        self.client = Exa(api_key=api_key)

    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Execute a search using Exa API."""
        try:
            # Use search_and_contents to get full content
            response = self.client.search_and_contents(
                query=query,
                num_results=num_results,
                text=True,  # Get full text content
                highlights=True,  # Get highlighted snippets
            )
            
            results = []
            for result in response.results:
                # Combine highlights or use text
                content = ""
                if hasattr(result, 'highlights') and result.highlights:
                    content = " ".join(result.highlights)
                elif hasattr(result, 'text') and result.text:
                    content = result.text[:2000]  # Limit content length
                
                results.append(SearchResult(
                    title=result.title or "",
                    url=result.url,
                    content=content,
                    score=result.score if hasattr(result, 'score') else None,
                ))
            
            return results
        except Exception as e:
            print(f"Exa search error: {e}")
            return []


def format_exa_results_for_llm(results: List[SearchResult], query_id: int) -> tuple[str, List[Dict[str, Any]]]:
    """Format Exa search results for LLM consumption.
    
    Returns:
        Tuple of (formatted_text, sources_list)
    """
    if not results:
        return "No search results found.", []
    
    formatted_parts = []
    sources = []
    
    for idx, result in enumerate(results):
        # Create a short URL for citation
        short_url = f"https://exa.ai/search/id/{query_id}-{idx}"
        
        # Format the result for LLM
        formatted_parts.append(f"""
### Source {idx + 1}: {result.title}
URL: {short_url}

{result.content}
""")
        
        # Track source for citation
        sources.append({
            "label": result.title.split(".")[0] if result.title else f"Source {idx + 1}",
            "short_url": short_url,
            "value": result.url,
        })
    
    formatted_text = "\n---\n".join(formatted_parts)
    return formatted_text, sources


def get_search_provider(provider_type: str, api_key: str) -> Optional[SearchProvider]:
    """Factory function to create search provider instances."""
    if provider_type in ("openrouter", "local"):
        if not api_key:
            raise ValueError("Exa API key is required for OpenRouter and local providers")
        return ExaSearchProvider(api_key=api_key)
    elif provider_type == "google":
        # Google uses its own search mechanism in the model
        return None
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")

