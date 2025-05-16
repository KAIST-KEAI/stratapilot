import os
import json
import re
import sys
import argparse
from dotenv import load_dotenv

from langchain.vectorstores import Chroma
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain_community.embeddings import OllamaEmbeddings

load_dotenv(dotenv_path=".env", override=True)

API_KEY = os.getenv("OPENAI_API_KEY")
ORG_ID = os.getenv("OPENAI_ORGANIZATION")

MODEL_KIND = os.getenv("EMBED_MODEL_TYPE")
MODEL_ID = os.getenv("EMBED_MODEL_NAME")


class RegistryHandler:
    """
    Handles a searchable library of components. Each record includes source logic and
    explanatory context. Descriptions are indexed via a vector database for fast retrieval.
    """

    def __init__(self, storage_base: str):
        """
        Bootstraps the registry by loading stored data and setting up persistence layers.

        Args:
            storage_base (str): Root folder housing records and metadata.
        """
        self._storage_root = storage_base
        index_path = os.path.join(storage_base, "component_index.json")

        with open(index_path, "r") as f:
            self._records = json.load(f)

        self._vector_dir = os.path.join(storage_base, "index_vectors")
        os.makedirs(self._vector_dir, exist_ok=True)
        os.makedirs(os.path.join(storage_base, "impl"), exist_ok=True)
        os.makedirs(os.path.join(storage_base, "docs"), exist_ok=True)

        if MODEL_KIND == "OpenAI":
            embed = OpenAIEmbeddings(
                openai_api_key=API_KEY,
                openai_organization=ORG_ID
            )
        else:
            embed = OllamaEmbeddings(model=MODEL_ID)

        self._index = Chroma(
            collection_name="component_search",
            embedding_function=embed,
            persist_directory=self._vector_dir
        )

        assert self._index._collection.count() == len(self._records), \
            "Mismatch between stored JSON records and vector entries"

    @property
    def all_code(self) -> str:
        """Return all saved code blocks concatenated."""
        return "\n\n".join(entry["code"] for entry in self._records.values())

    @property
    def summaries(self) -> dict:
        """Expose component names and their documented roles."""
        return {name: rec["description"] for name, rec in self._records.items()}

    @property
    def keys(self):
        """Return all record identifiers."""
        return self._records.keys()

    def fetch_code(self, label: str) -> str:
        """Grab the source code for a named record."""
        return self._records[label]["code"]

    def register(self, metadata: dict):
        """
        Insert or replace a registry entry with provided details.

        Args:
            metadata (dict): Includes 'task_name', 'code', and 'description'.
        """
        ident = metadata["task_name"]
        code = metadata["code"]
        doc = metadata["description"]

        if ident in self._records:
            self._index._collection.delete(ids=[ident])

        self._index.add_texts(texts=[doc], ids=[ident], metadatas=[{"name": ident}])
        self._records[ident] = {"code": code, "description": doc}

        assert self._index._collection.count() == len(self._records), \
            "Post-update count discrepancy in index and memory store"

        with open(os.path.join(self._storage_root, "impl", f"{ident}.py"), "w") as f:
            f.write(code)

        with open(os.path.join(self._storage_root, "docs", f"{ident}.txt"), "w") as f:
            f.write(doc)

        with open(os.path.join(self._storage_root, "component_index.json"), "w") as f:
            json.dump(self._records, f, indent=4)

        self._index.persist()

    def is_known(self, label: str) -> bool:
        """Check if a named entry exists."""
        return label in self._records

    def query_names(self, clue: str, k: int = 10) -> list[str]:
        """
        Run a similarity search on descriptions using a natural language clue.

        Args:
            clue (str): Search prompt.
            k (int): Max result count.

        Returns:
            list[str]: Matched names.
        """
        count = self._index._collection.count()
        k = min(k, count)
        if k == 0:
            return []

        matches = self._index.similarity_search_with_score(clue, k=k)
        return [match.metadata["name"] for match, _ in matches]

    def get_docs(self, labels: list[str]) -> list[str]:
        """Return descriptions for multiple entries."""
        return [self._records[x]["description"] for x in labels]

    def get_sources(self, labels: list[str]) -> list[str]:
        """Return code for multiple entries."""
        return [self._records[x]["code"] for x in labels]

    def discard(self, label: str):
        """Fully remove a record from all storage locations."""
        if label in self._records:
            self._index._collection.delete(ids=[label])

        index_fp = os.path.join(self._storage_root, "component_index.json")
        with open(index_fp, "r") as f:
            data = json.load(f)
        data.pop(label, None)
        with open(index_fp, "w") as f:
            json.dump(data, f, indent=4)

        code_fp = os.path.join(self._storage_root, "impl", f"{label}.py")
        if os.path.exists(code_fp):
            os.remove(code_fp)

        doc_fp = os.path.join(self._storage_root, "docs", f"{label}.txt")
        if os.path.exists(doc_fp):
            os.remove(doc_fp)
