import logging
import requests
import json

class LLAMA3:
    """
    A class for interacting with a local LLaMA3 chat API.

    This class provides a method to send chat messages to a LLaMA3 server and receive responses.
    """

    def __init__(self, server_url="http://localhost:11434/api/chat", model_name="llama3"):
        """
        Initialize the LLAMA3 instance with the server URL and model name.

        Args:
            server_url (str): The URL of the LLaMA3 API server.
            model_name (str): The name of the LLaMA3 model to use.
        """
        self.server_url = server_url
        self.model_name = model_name

    def chat(self, messages, temperature=0.0, stream=False):
        """
        Send a chat message to the LLaMA3 API.

        Args:
            messages (list): A list of dictionaries, each with 'role' and 'content' keys.
            temperature (float): Sampling temperature. Defaults to 0.0 for deterministic output.
            stream (bool): Whether to enable streaming output. Defaults to False.

        Returns:
            str: The content of the model's response, or an empty string on failure.
        """
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }

        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(self.server_url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            content = result.get("message", {}).get("content", "")
            logging.info(f"LLM response: {content}")
            return content
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to connect to LLaMA3 server: {e}")
        except (KeyError, json.JSONDecodeError) as e:
            logging.error(f"Invalid response format: {e}")
        return ""

if __name__ == "__main__":
    # Example usage
    llm = LLAMA3()
    test_messages = [
        {"role": "user", "content": "Why is the sky blue?"}
    ]
    print(llm.chat(messages=test_messages))
