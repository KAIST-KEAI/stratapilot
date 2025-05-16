import os
import sys
import time
import json
import logging
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables (override mode)
load_dotenv(override=True)

# Environment config
ENGINE = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
API_KEY = os.getenv("OPENAI_API_KEY")
ORG_ID = os.getenv("OPENAI_ORGANIZATION")
ALT_URL = os.getenv("OPENAI_BASE_URL")
FALLBACK_ENDPOINT = os.getenv("MODEL_SERVER", "http://localhost:11434")

# Setup logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)


class LanguageGateway:
    """
    Generic LLM interaction interface. Acts as the base class for vendor-specific clients.
    """

    def __init__(self, model: str):
        self.model = model

    def interact(self, prompts: List[Dict[str, str]], temperature: float = 0.0, tag: str = "") -> str:
        """
        Executes a prompt cycle and returns the language model's output.
        """
        raise NotImplementedError("Concrete subclass required")


class OpenAIWrapper(LanguageGateway):
    """
    Wrapper for OpenAI’s chat-based models.
    Handles credentials and request configuration.
    """

    def __init__(self, token: str, model: str = ENGINE, org: Optional[str] = None):
        super().__init__(model)
        self.token = token
        self.org = org
        self._init_openai()

    def _init_openai(self):
        import openai
        openai.api_key = self.token
        if self.org:
            openai.organization = self.org
        if ALT_URL:
            openai.base_url = ALT_URL
        self._client = openai

    def interact(self, prompts: List[Dict[str, str]], temperature: float = 0.0, tag: str = "") -> str:
        try:
            reply = self._client.chat.completions.create(
                model=self.model,
                messages=prompts,
                temperature=temperature
            )
            output = reply.choices[0].message.content
            log.info(f"{tag}Result: {output[:200]}...")
            return output
        except Exception as err:
            log.error(f"[OpenAI] Failure: {err}")
            raise


class OllamaWrapper(LanguageGateway):
    """
    Client adapter for models hosted via Ollama API.
    """

    def __init__(self, model: str = ENGINE, endpoint: str = FALLBACK_ENDPOINT):
        super().__init__(model)
        self.api_url = f"{endpoint}/api/chat"

    def interact(self, prompts: List[Dict[str, str]], temperature: float = 0.0, tag: str = "") -> str:
        req = {
            "model": self.model,
            "messages": prompts,
            "temperature": temperature,
            "stream": False
        }

        try:
            response = requests.post(
                self.api_url,
                json=req,
                headers={"Content-Type": "application/json"},
                timeout=300
            )
            response.raise_for_status()
            text = response.json()["message"]["content"]
            log.info(f"{tag}Result: {text[:200]}...")
            return text
        except (requests.RequestException, KeyError, json.JSONDecodeError) as err:
            log.error(f"[Ollama] Failed to process response: {err}")
            raise


def get_llm() -> LanguageGateway:
    """
    Instantiate the appropriate LLM backend depending on available credentials.
    """
    if API_KEY:
        return OpenAIWrapper(token=API_KEY, model=ENGINE, org=ORG_ID)
    if FALLBACK_ENDPOINT:
        return OllamaWrapper(model=ENGINE, endpoint=FALLBACK_ENDPOINT)
    raise RuntimeError("Missing LLM configuration")


def boot():
    """
    Entry point for launching the language model interface.
    Runs a single prompt round and reports execution stats.
    """
    try:
        start = time.time()

        agent = get_llm()
        log.info(f"Connected to: {agent.__class__.__name__} | Model: {agent.model}")

        dialogue = [
            {
                "role": "system",
                "content": (
                    "You are an expert code assistant. Follow these principles:\n"
                    "1. Plan before coding and explain logic.\n"
                    "2. Write and execute scripts directly.\n"
                    "3. Use file I/O for data exchange.\n"
                    "4. Fetch resources as needed.\n"
                    "5. Format output using Markdown.\n"
                    "6. Solve in iterative steps.\n"
                    "# System APIs pre-imported:\n"
                    "computer.browser.search(query)\n"
                    "computer.files.edit(path, original, replacement)\n"
                    "computer.calendar.create_event(title, start, end, notes, location)\n"
                    "computer.calendar.get_events(start_date, end_date=None)\n"
                    "computer.calendar.delete_event(title, start_date)\n"
                    "computer.contacts.get_phone_number(name)\n"
                    "computer.contacts.get_email_address(name)\n"
                    "computer.mail.send(to, subject, body, attachments)\n"
                    "computer.mail.get(count, unread=True)\n"
                    "computer.mail.unread_count()\n"
                    "computer.sms.send(phone_number, message)\n"
                    "Do not import 'computer'. Use it directly.\n"
                    "Execute code using the built-in `execute(language, code)` function."
                )
            },
            {
                "role": "user",
                "content": "Plot normalized stock prices for AAPL and META"
            }
        ]

        log.info("Sending message to model...")
        reply = agent.interact(dialogue, temperature=0.2, tag="[Run]")

        print("\n=== Model Response ===")
        print(reply)

        elapsed = time.time() - start
        print(f"\nCharacters returned: {len(reply)}")
        print(f"Total time: {elapsed:.2f} seconds")

    except Exception as err:
        log.exception("Unhandled failure during model interaction")
        print(f"Fatal error: {err}")
        sys.exit(1)


if __name__ == "__main__":
    boot()
