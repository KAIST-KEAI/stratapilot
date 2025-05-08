import openai
import logging
import os
import time
import requests
import json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables with override option
load_dotenv(override=True)

# Configuration parameters
MODEL_NAME = os.getenv('MODEL_NAME', 'gpt-3.5-turbo')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_ORGANIZATION = os.getenv('OPENAI_ORGANIZATION')
BASE_URL = os.getenv('OPENAI_BASE_URL')
MODEL_SERVER = os.getenv('MODEL_SERVER', 'http://localhost:11434')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LLMClient:
    """
    Abstract base class for Large Language Model (LLM) clients.
    Defines a standard interface for interacting with different LLM providers.
    """
    def __init__(self, model_name: str):
        self.model_name = model_name
        
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.0, 
             prefix: str = "") -> str:
        """
        Sends a chat message to the LLM and returns the response.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys.
            temperature: Controls the randomness of the model's output.
            prefix: Prefix to add to log messages.
            
        Returns:
            The model's response as a string.
        """
        raise NotImplementedError("Subclasses must implement this method")

class OpenAIClient(LLMClient):
    """
    Client for interacting with OpenAI's language models.
    Handles authentication and chat completions using the OpenAI API.
    """
    def __init__(self, api_key: str, model_name: str = MODEL_NAME, 
                 organization: Optional[str] = None):
        super().__init__(model_name)
        self.api_key = api_key
        self.organization = organization
        self._configure_openai()
        
    def _configure_openai(self) -> None:
        """Configures the OpenAI client with API credentials and settings."""
        openai.api_key = self.api_key
        if self.organization:
            openai.organization = self.organization
        if BASE_URL:
            openai.base_url = BASE_URL
            
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.0, 
             prefix: str = "") -> str:
        """
        Sends a chat request to the OpenAI model and processes the response.
        
        Args:
            messages: List of messages in OpenAI format.
            temperature: Randomness parameter (0.0 to 2.0).
            prefix: Log message prefix.
            
        Returns:
            The generated response text.
        """
        try:
            response = openai.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature
            )
            content = response.choices[0].message.content
            logger.info(f"{prefix}Response: {content[:200]}...")  # Truncate long responses
            return content
        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            raise

class OllamaClient(LLMClient):
    """
    Client for interacting with Ollama-based language models.
    Handles HTTP requests to a local or remote Ollama server.
    """
    def __init__(self, model_name: str = MODEL_NAME, server_url: str = MODEL_SERVER):
        super().__init__(model_name)
        self.server_url = server_url
        self.chat_url = f"{server_url}/api/chat"
        
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.0, 
             prefix: str = "") -> str:
        """
        Sends a chat request to the Ollama model and processes the response.
        
        Args:
            messages: List of messages in Ollama format.
            temperature: Randomness parameter.
            prefix: Log message prefix.
            
        Returns:
            The generated response text.
        """
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }
        
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(self.chat_url, json=payload, headers=headers, timeout=300)
            response.raise_for_status()  # Raise exception for HTTP errors
            content = response.json()["message"]["content"]
            logger.info(f"{prefix}Response: {content[:200]}...")  # Truncate long responses
            return content
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API call failed: {str(e)}")
            raise
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse Ollama response: {str(e)}")
            raise

def create_llm_client() -> LLMClient:
    """
    Creates an appropriate LLM client based on environment configuration.
    Prefers OpenAI if API key is set, otherwise falls back to Ollama.
    
    Returns:
        An initialized LLM client instance.
    """
    if OPENAI_API_KEY:
        return OpenAIClient(api_key=OPENAI_API_KEY, model_name=MODEL_NAME, 
                           organization=OPENAI_ORGANIZATION)
    elif MODEL_SERVER:
        return OllamaClient(model_name=MODEL_NAME, server_url=MODEL_SERVER)
    else:
        raise ValueError("No API configuration found. Set OPENAI_API_KEY or MODEL_SERVER.")

def main():
    """
    Main entry point for the script.
    Demonstrates usage of the LLM client to generate a response for a given task.
    """
    try:
        start_time = time.time()
        
        # Initialize LLM client
        llm_client = create_llm_client()
        logger.info(f"LLM client initialized: {llm_client.__class__.__name__}, Model: {llm_client.model_name}")
        
        # Prepare conversation messages
        messages = [
            {
                'role': 'system',
                'content': 'You are Open Interpreter, a world-class programmer capable of completing any task by executing code.\n'
                           'Follow these guidelines:\n'
                           '1. Always start with a plan and recap it between code blocks.\n'
                           '2. Execute code on the user\'s machine with full permission.\n'
                           '3. Use txt or json files to exchange data between programming languages.\n'
                           '4. You can access the internet and install new packages.\n'
                           '5. Write messages to the user in Markdown format.\n'
                           '6. Break down tasks into small, iterative steps.\n\n'
                           '# COMPUTER API\n'
                           'A `computer` module is already imported with these functions:\n'
                           '```python\n'
                           'computer.browser.search(query)  # Returns Google search results\n'
                           'computer.files.edit(path, original, replacement)  # Edits a file\n'
                           'computer.calendar.create_event(title, start, end, notes, location)  # Creates a calendar event\n'
                           'computer.calendar.get_events(start_date, end_date=None)  # Gets calendar events\n'
                           'computer.calendar.delete_event(title, start_date)  # Deletes a calendar event\n'
                           'computer.contacts.get_phone_number(name)  # Gets a phone number\n'
                           'computer.contacts.get_email_address(name)  # Gets an email address\n'
                           'computer.mail.send(to, subject, body, attachments)  # Sends an email\n'
                           'computer.mail.get(count, unread=True)  # Gets emails\n'
                           'computer.mail.unread_count()  # Counts unread emails\n'
                           'computer.sms.send(phone_number, message)  # Sends a text message\n'
                           '```\n'
                           'Do not import the computer module; it is already available.\n\n'
                           'User Info:\n'
                           'Name: hanchengcheng\n'
                           'CWD: /Users/hanchengcheng/Documents/official_space/open-interpreter\n'
                           'SHELL: /bin/bash\n'
                           'OS: Darwin\n'
                           'Use only the provided `execute(language, code)` function.'
            },
            {
                'role': 'user',
                'content': "Plot AAPL and META's normalized stock prices"
            }
        ]
        
        # Send request to LLM
        logger.info("Sending request to LLM...")
        response = llm_client.chat(messages, temperature=0.2, prefix="[Main]")
        
        # Process and display response
        print("\n===== LLM Response =====")
        print(response)
        
        # Log execution statistics
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"\nResponse length: {len(response)} characters")
        print(f"Execution time: {execution_time:.2f} seconds")
        
    except Exception as e:
        logger.exception("An error occurred during execution")
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()