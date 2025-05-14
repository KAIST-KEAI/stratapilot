import requests
from typing import List

# Parameters for managing search responses
_MAX_IMAGES = 10
_SAFE_REGION = "en-US"

class VisualSearchService:
    """
    A utility for retrieving visual content via Bing's image search interface.
    """
    def __init__(self, api_key: str) -> None:
        self._auth_headers = {
            "Ocp-Apim-Subscription-Key": api_key,
            "BingAPIs-Market": _SAFE_REGION
        }
        self._search_url = "https://api.bing.microsoft.com/v7.0/images/search"
        self._market_region = _SAFE_REGION

    def search_image(self, query_text: str, max_results: int = _MAX_IMAGES, retries: int = 3) -> List[dict]:
        """
        Query the Bing image index using provided keywords, and return visual snippet data.

        Args:
            query_text (str): Keywords describing the visual target.
            max_results (int): Maximum number of images to return.
            retries (int): Number of times to attempt the request on failure.

        Returns:
            List[dict]: Image metadata objects including title and preview URLs.
        """
        for _ in range(retries):
            try:
                response = requests.get(
                    self._search_url,
                    headers=self._auth_headers,
                    params={
                        "q": query_text,
                        "mkt": self._market_region,
                        "safeSearch": "moderate"
                    },
                    timeout=10
                )
            except Exception:
                continue

            if response.status_code == 200:
                payload = response.json()
                items = payload.get("value", [])
                previews = [
                    {
                        "imageTitle": entry.get("name", ""),
                        "imagePreviewUrl": entry.get("thumbnailUrl", ""),
                        "previewMetadata": entry.get("thumbnail", {})
                    }
                    for entry in items
                ]
                return previews[:max_results]
        raise RuntimeError("Bing image retrieval failed after multiple attempts.")
