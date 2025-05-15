# __import__('pysqlite3')
# import sys
# sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

from langchain.vectorstores import Chroma
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain_community.embeddings import OllamaEmbeddings
import argparse
import json
import sys
import os
import re
from dotenv import load_dotenv
load_dotenv(dotenv_path='.env', override=True)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_ORGANIZATION = os.getenv('OPENAI_ORGANIZATION')

EMBED_MODEL_TYPE = os.getenv('EMBED_MODEL_TYPE')
EMBED_MODEL_NAME = os.getenv('EMBED_MODEL_NAME')

class ToolManager:
    """
    Oversees storage, retrieval, and management of tool definitions in a repository.

    Each tool entry includes code, description, and metadata. ToolManager uses a vector
    database for similarity-based lookup and maintains JSON metadata alongside code
    and description files on disk.

    Attributes:
        generated_tools (dict): Mapping of tool names to their {'code', 'description'}.
        generated_tool_repo_dir (str): Root directory for tool metadata, code, and descriptions.
        vectordb_path (str): File path for the persistent vector database directory.
        vectordb (Chroma): In-memory client for similarity searches over tool descriptions.
    """

    def __init__(self, generated_tool_repo_dir: str):
        """
        Initialize ToolManager by loading existing tools and setting up persistence.

        Args:
            generated_tool_repo_dir (str): Directory containing generated_tools.json,
                                          tool_code/, and tool_description/ subfolders.
        Raises:
            AssertionError: If the vector database and JSON metadata have mismatched counts.
        """
        self.generated_tool_repo_dir = generated_tool_repo_dir
        # Load JSON metadata of existing tools
        tools_json = os.path.join(generated_tool_repo_dir, "generated_tools.json")
        with open(tools_json, "r") as f:
            self.generated_tools = json.load(f)

        # Ensure storage directories exist
        self.vectordb_path = os.path.join(generated_tool_repo_dir, "vectordb")
        os.makedirs(self.vectordb_path, exist_ok=True)
        os.makedirs(os.path.join(generated_tool_repo_dir, "tool_code"), exist_ok=True)
        os.makedirs(os.path.join(generated_tool_repo_dir, "tool_description"), exist_ok=True)

        # Choose embedding engine
        if EMBED_MODEL_TYPE == "OpenAI":
            embedder = OpenAIEmbeddings(
                openai_api_key=OPENAI_API_KEY,
                openai_organization=OPENAI_ORGANIZATION
            )
        else:
            embedder = OllamaEmbeddings(model=EMBED_MODEL_NAME)

        # Initialize or connect to vector database for description similarity
        self.vectordb = Chroma(
            collection_name="tool_vectordb",
            embedding_function=embedder,
            persist_directory=self.vectordb_path
        )

        # Validate that Chroma and JSON metadata are in sync
        count_db = self.vectordb._collection.count()
        count_json = len(self.generated_tools)
        assert count_db == count_json, (
            f"Vector DB ({count_db} entries) and metadata ({count_json} entries) are out of sync."
        )

    @property
    def programs(self) -> str:
        """
        Concatenate all stored tool code into one string.

        Returns:
            str: Each tool's source code separated by blank lines.
        """
        return "\n\n".join(entry["code"] for entry in self.generated_tools.values())

    @property
    def descriptions(self) -> dict:
        """
        Get a mapping of tool names to their descriptions.

        Returns:
            dict: {tool_name: description}
        """
        return {name: entry["description"] for name, entry in self.generated_tools.items()}

    @property
    def tool_names(self):
        """
        List all available tool identifiers.

        Returns:
            KeysView[str]: A view of all tool names.
        """
        return self.generated_tools.keys()

    def get_tool_code(self, tool_name: str) -> str:
        """
        Fetch source code for a given tool.

        Args:
            tool_name (str): Identifier of the tool.
        Returns:
            str: The tool's code.
        Raises:
            KeyError: If the tool is not present.
        """
        return self.generated_tools[tool_name]["code"]

    def add_new_tool(self, info: dict):
        """
        Register a new tool, updating JSON metadata, vector DB, and on-disk files.

        Args:
            info (dict): Contains 'task_name', 'code', and 'description' keys.
        """
        name = info['task_name']
        code = info['code']
        desc = info['description']

        # If tool exists, remove old entry from vector DB
        if name in self.generated_tools:
            self.vectordb._collection.delete(ids=[name])

        # Add description to vector DB for similarity search
        self.vectordb.add_texts(texts=[desc], ids=[name], metadatas=[{'name': name}])

        # Update in-memory and JSON metadata
        self.generated_tools[name] = {'code': code, 'description': desc}
        assert self.vectordb._collection.count() == len(self.generated_tools), \
            "Vector DB and metadata count mismatch after addition."

        # Save code and description files
        code_path = os.path.join(self.generated_tool_repo_dir, 'tool_code', f"{name}.py")
        with open(code_path, 'w') as f:
            f.write(code)
        desc_path = os.path.join(self.generated_tool_repo_dir, 'tool_description', f"{name}.txt")
        with open(desc_path, 'w') as f:
            f.write(desc)

        # Persist metadata JSON and vector DB
        json_path = os.path.join(self.generated_tool_repo_dir, 'generated_tools.json')
        with open(json_path, 'w') as f:
            json.dump(self.generated_tools, f, indent=4)
        self.vectordb.persist()

    def exist_tool(self, tool: str) -> bool:
        """
        Check if a tool is already registered.

        Args:
            tool (str): Tool identifier.
        Returns:
            bool: True if present, else False.
        """
        return tool in self.generated_tools

    def retrieve_tool_name(self, query: str, k: int = 10) -> list[str]:
        """
        Find top-k similar tools by description based on a text query.

        Args:
            query (str): Text to search descriptions.
            k (int): Maximum number of tools to return.
        Returns:
            list[str]: Sorted list of tool names by similarity.
        """
        total = self.vectordb._collection.count()
        k = min(total, k)
        if k == 0:
            return []

        results = self.vectordb.similarity_search_with_score(query, k=k)
        return [doc.metadata['name'] for doc, _ in results]

    def retrieve_tool_description(self, names: list[str]) -> list[str]:
        """
        Fetch descriptions for a list of tools.

        Args:
            names (list[str]): Tool identifiers.
        Returns:
            list[str]: Corresponding descriptions.
        """
        return [self.generated_tools[name]['description'] for name in names]

    def retrieve_tool_code(self, names: list[str]) -> list[str]:
        """
        Fetch source code snippets for a list of tools.

        Args:
            names (list[str]): Tool identifiers.
        Returns:
            list[str]: Corresponding code snippets.
        """
        return [self.generated_tools[name]['code'] for name in names]

    def delete_tool(self, tool: str):
        """
        Remove a tool from memory, storage, and vector DB.

        Args:
            tool (str): Identifier of the tool to delete.
        """
        if tool in self.generated_tools:
            self.vectordb._collection.delete(ids=[tool])

        # Update JSON metadata
        json_path = os.path.join(self.generated_tool_repo_dir, 'generated_tools.json')
        with open(json_path, 'r') as f:
            data = json.load(f)
        data.pop(tool, None)
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)

        # Remove on-disk files
        code_file = os.path.join(self.generated_tool_repo_dir, 'tool_code', f"{tool}.py")
        if os.path.exists(code_file): os.remove(code_file)
        desc_file = os.path.join(self.generated_tool_repo_dir, 'tool_description', f"{tool}.txt")
        if os.path.exists(desc_file): os.remove(desc_file)
