import requests
from langchain.utilities import BingSearchAPIWrapper
from bs4 import BeautifulSoup
from typing import Tuple
from enum import Enum
from .web_loader import WebPageLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains.summarize import load_summarize_chain
from langchain import OpenAI

# Constants for controlling output behavior
_SNIPPET_BATCH = 3
_MAX_TEXT_UNIT = 500

class SmartWebSearchAgent:
    """
    Interface for executing Bing-powered queries, gathering and processing content from webpages.

    Responsibilities include performing safe queries, loading and segmenting HTML content,
    transforming chunks into vectors, and summarizing or attending to context.
    """

    def __init__(self):
        """
        Setup search utility, page content retrieval, segmentation engine, vectorizer, and summarizer.
        """
        self._engine = BingSearchAPIWrapper(search_kwargs={'mkt': 'en-us', 'safeSearch': 'moderate'})
        self._reader = WebPageLoader()
        self._segmenter = RecursiveCharacterTextSplitter(chunk_size=4500, chunk_overlap=0)
        self._encoder = OpenAIEmbeddings()
        self._summarizer = OpenAI(temperature=0)

    def query_web(self, prompt: str, count: int = 5, retries: int = 3):
        """
        Run a search request through Bing and fetch top URLs.

        Args:
            prompt (str): The phrase or term to search.
            count (int): Desired number of top links. Defaults to 5.
            retries (int): Times to retry on failure. Defaults to 3.

        Returns:
            list: Search result metadata.

        Raises:
            RuntimeError: If no results are fetched within retry attempts.
        """
        for _ in range(retries):
            try:
                hits = self._engine.results(prompt, count)
                if hits:
                    return hits
            except Exception:
                continue
        raise RuntimeError("Unable to connect to Bing and fetch results.")

    def fetch_site_content(self, link: str) -> str:
        """
        Download and parse content from a web address.

        Args:
            link (str): Target URL to extract textual data from.

        Returns:
            str: Flattened text content if successful; otherwise, an empty string.
        """
        payload = self._reader.load_data(link)
        doc_text = ""
        if payload.get("data") and payload["data"][0].get("content"):
            doc_text = payload["data"][0]["content"]
        return doc_text

    def generate_summary(self, full_text: str) -> str:
        """
        Produce a high-level synopsis of a web page’s contents.

        Args:
            full_text (str): Entire webpage data as string.

        Returns:
            str: Condensed version of the input.
        """
        if not full_text:
            return ""
        segments = self._segmenter.create_documents([full_text])
        reduction_pipeline = load_summarize_chain(self._summarizer, chain_type="map_reduce")
        abstract = reduction_pipeline.run(segments)
        return abstract

    def extract_relevant_passages(self, full_text: str, question: str) -> str:
        """
        Pull information most pertinent to the input query from a web document.

        Args:
            full_text (str): Raw data from a site.
            question (str): User-defined prompt to filter content relevance.

        Returns:
            str: Combined snippets matching the topic of interest.
        """
        if not full_text:
            return ""
        segments = self._segmenter.create_documents([full_text])
        vector_index = Chroma.from_documents(segments, self._encoder)
        top_matches = vector_index.similarity_search(question, k=3)
        focused_context = '...'.join([item.page_content for item in top_matches])
        return focused_context
