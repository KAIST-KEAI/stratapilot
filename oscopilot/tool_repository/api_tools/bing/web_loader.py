import hashlib
import logging
import re
import requests
import pdfplumber
from io import BytesIO

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise ImportError(
        'HTMLParser requires additional packages. Install with: `pip install --upgrade "embedchain[dataloaders]"`'
    ) from None


def sanitize_text(raw_text: str) -> str:
    """
    Apply multi-step cleansing to textual content.
    """
    # Flatten newlines and reduce spacing
    cleaned = raw_text.replace("\n", " ")
    cleaned = re.sub(r"\s+", " ", cleaned.strip())
    cleaned = cleaned.replace("\\", "")
    cleaned = cleaned.replace("#", " ")
    cleaned = re.sub(r"([^\w\s])\1*", r"\1", cleaned)
    return cleaned


class WebScrapeAgent:
    """
    Retrieves and sanitizes data from HTML or PDF documents at a given URL.
    """
    _http = requests.Session()

    def fetch_content(self, target_url: str) -> dict:
        """
        Acquire content from a target web page or document.

        Returns:
            dict: Structured content and metadata
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 "
                          "(KHTML like Gecko) Chrome/52.0.2743.116 Safari/537.36"
        }

        document = {}
        parsed_text = ""

        try:
            reply = self._http.get(target_url, headers=headers, timeout=30)
            reply.raise_for_status()
            raw_bytes = reply.content
            content_type = reply.headers.get("Content-Type", "")

            if "html" in content_type:
                parsed_text = self._parse_html(raw_bytes, target_url)

            elif "pdf" in content_type:
                with pdfplumber.open(BytesIO(reply.content)) as doc:
                    parsed_text = "\n".join([
                        page.extract_text() for page in doc.pages if page.extract_text()
                    ])

            checksum = hashlib.sha256((parsed_text + target_url).encode()).hexdigest()
            document = {
                "doc_id": checksum,
                "data": [
                    {
                        "content": parsed_text,
                        "meta_data": {"url": target_url}
                    }
                ]
            }
        except Exception:
            document = {
                "data": [
                    {
                        "content": "",
                        "meta_data": ""
                    }
                ]
            }

        return document

    def _parse_html(self, html_bytes: bytes, ref_url: str) -> str:
        soup = BeautifulSoup(html_bytes, "html.parser")
        original_chars = len(soup.get_text())

        # Filter out noisy layout elements
        drop_tags = [
            "nav", "aside", "form", "header", "noscript", "svg",
            "canvas", "footer", "script", "style"
        ]
        for tag in soup(drop_tags):
            tag.decompose()

        unwanted_ids = ["sidebar", "main-navigation", "menu-main-menu"]
        for node_id in unwanted_ids:
            for tag in soup.find_all(id=node_id):
                tag.decompose()

        bad_classes = [
            "elementor-location-header", "navbar-header", "nav",
            "header-sidebar-wrapper", "blog-sidebar-wrapper", "related-posts"
        ]
        for cls in bad_classes:
            for tag in soup.find_all(class_=cls):
                tag.decompose()

        text = soup.get_text()
        final_text = sanitize_text(text)

        new_len = len(final_text)
        if original_chars:
            logging.info(
                f"[{ref_url}] Trimmed from {original_chars} to {new_len} chars "
                f"({original_chars - new_len} removed, {round((1 - new_len/original_chars) * 100, 2)}% saved)"
            )

        return final_text

    @classmethod
    def shutdown(cls):
        cls._http.close()
