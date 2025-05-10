import base64
import io
import os
import json
import time
from typing import Dict, List, Any, Optional, Generator, Union
from PIL import Image

from rich import print as rich_print
from rich.markdown import Markdown
from rich.rule import Rule

from dotenv import load_dotenv
import litellm
import tokentrim as tt

# Configure environment and logging
load_dotenv(dotenv_path='.env', override=True)
litellm.suppress_debug_info = True

# Configuration parameters
MODEL_NAME = os.getenv('MODEL_NAME')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_ORGANIZATION = os.getenv('OPENAI_ORGANIZATION')
BASE_URL = os.getenv('OPENAI_BASE_URL')

# Function schema for code execution
FUNCTION_SCHEMA = {
    "name": "execute",
    "description": "Executes code on the user's machine in the local environment and returns the output",
    "parameters": {
        "type": "object",
        "properties": {
            "language": {
                "type": "string",
                "description": "Programming language (required parameter for the `execute` function)",
                "enum": []  # Dynamically filled with supported languages
            },
            "code": {"type": "string", "description": "Code to execute (required)"}
        },
        "required": ["language", "code"]
    }
}

def parse_partial_json(s: str) -> Optional[Dict[str, Any]]:
    """
    Attempts to parse a JSON string that may be incomplete or malformed.
    Tries to fix common issues like missing closing brackets or quotes.
    
    Args:
        s: The JSON string to parse.
        
    Returns:
        Parsed JSON object or None if parsing fails.
    """
    try:
        # Try parsing as-is first
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        pass
    
    # Initialize parsing state
    new_s = ""
    stack = []
    is_inside_string = False
    escaped = False
    
    # Process each character to fix common issues
    for char in s:
        if is_inside_string:
            if char == '"' and not escaped:
                is_inside_string = False
            elif char == "\n" and not escaped:
                char = "\\n"  # Replace newline with escape sequence
            elif char == "\\":
                escaped = not escaped
            else:
                escaped = False
        else:
            if char == '"':
                is_inside_string = True
                escaped = False
            elif char == "{":
                stack.append("}")
            elif char == "[":
                stack.append("]")
            elif char == "}" or char == "]":
                if stack and stack[-1] == char:
                    stack.pop()
                else:
                    # Mismatched closing character
                    return None
        
        new_s += char
    
    # Close any remaining open structures
    if is_inside_string:
        new_s += '"'
    for closing_char in reversed(stack):
        new_s += closing_char
    
    try:
        return json.loads(new_s)
    except (json.JSONDecodeError, TypeError):
        return None

def merge_deltas(original: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merges a delta dictionary into the original dictionary recursively.
    Used for reconstructing streaming responses from language models.
    
    Args:
        original: The original dictionary to update.
        delta: The delta dictionary with updates.
        
    Returns:
        The updated original dictionary.
    """
    for key, value in dict(delta).items():
        if value is not None:
            if isinstance(value, str):
                original[key] = (original.get(key) or "") + (value or "")
            else:
                value = dict(value)
                if key not in original:
                    original[key] = value
                else:
                    merge_deltas(original[key], value)
    return original

def run_function_calling_llm(llm: Any, request_params: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
    """
    Executes a function-calling LLM request and processes the response stream.
    
    Args:
        llm: The LLM client instance.
        request_params: Parameters for the LLM request.
        
    Yields:
        Processed response chunks in LMC format.
    """
    accumulated_deltas = {}
    language = None
    code = ""
    
    for chunk in llm.completions(**request_params):
        if "choices" not in chunk or len(chunk["choices"]) == 0:
            continue
            
        delta = chunk["choices"][0]["delta"]
        accumulated_deltas = merge_deltas(accumulated_deltas, delta)
        
        if "content" in delta and delta["content"]:
            yield {"type": "message", "content": delta["content"]}
            
        if (accumulated_deltas.get("function_call") and 
            "arguments" in accumulated_deltas["function_call"] and 
            accumulated_deltas["function_call"]["arguments"]):
            
            if ("name" in accumulated_deltas["function_call"] and 
                accumulated_deltas["function_call"]["name"] == "execute"):
                
                arguments = accumulated_deltas["function_call"]["arguments"]
                arguments = parse_partial_json(arguments)
                
                if arguments:
                    if (language is None and 
                        "language" in arguments and 
                        "code" in arguments and 
                        arguments["language"]):
                        language = arguments["language"]
                        
                    if language is not None and "code" in arguments:
                        code_delta = arguments["code"][len(code):]
                        code = arguments["code"]
                        if code_delta:
                            yield {
                                "type": "code",
                                "format": language,
                                "content": code_delta
                            }
                else:
                    if llm.interpreter.verbose:
                        print("Arguments not a valid dictionary.")
                        
            # Handle common hallucinations
            elif "name" in accumulated_deltas["function_call"] and (
                accumulated_deltas["function_call"]["name"] == "python" or 
                accumulated_deltas["function_call"]["name"] == "functions"):
                
                if llm.interpreter.verbose:
                    print("Received direct python call")
                    
                if language is None:
                    language = "python"
                    
                if language is not None:
                    code_delta = accumulated_deltas["function_call"]["arguments"][len(code):]
                    code = accumulated_deltas["function_call"]["arguments"]
                    if code_delta:
                        yield {
                            "type": "code",
                            "format": language,
                            "content": code_delta
                        }
            else:
                if "name" in accumulated_deltas["function_call"]:
                    yield {
                        "type": "code",
                        "format": "python",
                        "content": accumulated_deltas["function_call"]["name"]
                    }
                    return

def run_text_llm(llm: Any, params: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
    """
    Executes a text-based LLM request and processes the response stream.
    
    Args:
        llm: The LLM client instance.
        params: Parameters for the LLM request.
        
    Yields:
        Processed response chunks in LMC format.
    """
    try:
        # Add code execution instructions to the system message
        params["messages"][0]["content"] += (
            "\nTo execute code on the user's machine, write a markdown code block. "
            "Specify the language after the ```. You will receive the output. "
            "Use any programming language."
        )
    except Exception as e:
        print('params["messages"][0]', params["messages"][0])
        raise
        
    inside_code_block = False
    accumulated_block = ""
    language = None
    
    for chunk in llm.completions(**params):
        if llm.interpreter.verbose:
            print("Chunk in text-based LLM", chunk)
            
        if "choices" not in chunk or len(chunk["choices"]) == 0:
            continue
            
        content = chunk["choices"][0]["delta"].get("content", "")
        if content is None:
            continue
            
        accumulated_block += content
        
        if accumulated_block.endswith("`"):
            # Might be part of a markdown code block delimiter
            continue
            
        # Check if entering a code block
        if "```" in accumulated_block and not inside_code_block:
            inside_code_block = True
            accumulated_block = accumulated_block.split("```")[1]
            
        # Check if exiting a code block
        if inside_code_block and "```" in accumulated_block:
            return
            
        # Process code block content
        if inside_code_block:
            if language is None and "\n" in accumulated_block:
                language = accumulated_block.split("\n")[0]
                
                # Default to python if language not specified
                if language == "":
                    if not llm.interpreter.os:
                        language = "python"
                    else:
                        language = "text"
                else:
                    # Clean up language name from hallucinated characters
                    language = "".join(char for char in language if char.isalpha())
                    
            if language:
                yield {
                    "type": "code",
                    "format": language,
                    "content": content.replace(language, "")
                }
                
        # Process non-code content
        if not inside_code_block:
            yield {"type": "message", "content": content}

def display_markdown_message(message: str) -> None:
    """
    Displays a markdown-formatted message using rich formatting.
    Handles multi-line strings and ensures proper rendering of markdown elements.
    
    Args:
        message: The markdown-formatted message to display.
    """
    for line in message.split("\n"):
        line = line.strip()
        if line == "":
            print("")
        elif line == "---":
            rich_print(Rule(style="white"))
        else:
            try:
                rich_print(Markdown(line))
            except UnicodeEncodeError as e:
                print("Error displaying line:", line)
                
    if "\n" not in message and message.startswith(">"):
        # Add spacing for blockquotes
        print("")

def convert_to_openai_messages(
    messages: List[Dict[str, Any]],
    function_calling: bool = True,
    vision: bool = False,
    shrink_images: bool = True,
    code_output_sender: str = "assistant"
) -> List[Dict[str, Any]]:
    """
    Converts messages from LMC format to OpenAI-compatible format.
    Handles different message types including text, code, console output, images, and files.
    
    Args:
        messages: List of messages in LMC format.
        function_calling: Whether function calling is enabled.
        vision: Whether vision capabilities are enabled.
        shrink_images: Whether to shrink images to reduce size.
        code_output_sender: Sender role for code outputs.
        
    Returns:
        List of messages in OpenAI-compatible format.
    """
    new_messages = []
    
    for message in messages:
        # Skip messages not intended for the assistant
        if "recipient" in message and message["recipient"] != "assistant":
            continue
            
        new_message = {}
        
        if message["type"] == "message":
            new_message["role"] = message["role"]
            new_message["content"] = message["content"]
            
        elif message["type"] == "code":
            new_message["role"] = "assistant"
            if function_calling:
                new_message["function_call"] = {
                    "name": "execute",
                    "arguments": json.dumps({
                        "language": message["format"],
                        "code": message["content"]
                    }),
                    "parsed_arguments": {
                        "language": message["format"],
                        "code": message["content"]
                    }
                }
                # Ensure required content field exists
                new_message["content"] = ""
            else:
                new_message["content"] = f"```${message['format']}\n${message['content']}\n```"
                
        elif message["type"] == "console" and message["format"] == "output":
            if function_calling:
                new_message["role"] = "function"
                new_message["name"] = "execute"
                new_message["content"] = message["content"].strip() or "No output"
            else:
                if code_output_sender == "user":
                    if message["content"].strip() == "":
                        content = "The code executed on my machine produced no output. What's next?"
                    else:
                        content = (
                            f"Code output: {message['content']}\n\n"
                            "What does this output mean or what should I do next?"
                        )
                    new_message["role"] = "user"
                    new_message["content"] = content
                elif code_output_sender == "assistant":
                    if "@@@SEND_MESSAGE_AS_USER@@@" in message["content"]:
                        new_message["role"] = "user"
                        new_message["content"] = message["content"].replace(
                            "@@@SEND_MESSAGE_AS_USER@@@", ""
                        )
                    else:
                        new_message["role"] = "assistant"
                        new_message["content"] = f"\n```output\n{message['content']}\n```"
                        
        elif message["type"] == "image":
            if not vision:
                continue
                
            if "base64" in message["format"]:
                # Extract image extension
                extension = message["format"].split(".")[-1] if "." in message["format"] else "png"
                content = f"data:image/{extension};base64,{message['content']}"
                
                if shrink_images:
                    try:
                        # Decode and resize image if needed
                        img_data = base64.b64decode(message["content"])
                        img = Image.open(io.BytesIO(img_data))
                        
                        if img.width > 1024:
                            new_height = int(img.height * 1024 / img.width)
                            img = img.resize((1024, new_height))
                            
                        buffered = io.BytesIO()
                        img.save(buffered, format=extension)
                        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                        content = f"data:image/{extension};base64,{img_str}"
                    except Exception as e:
                        # Non-blocking error handling
                        pass
                        
            elif message["format"] == "path":
                # Convert image path to base64
                image_path = message["content"]
                file_extension = image_path.split(".")[-1]
                
                with open(image_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                    
                content = f"data:image/{file_extension};base64,{encoded_string}"
            else:
                if "format" not in message:
                    raise Exception("Image format not specified.")
                else:
                    raise Exception(f"Unsupported image format: {message['format']}")
                    
            # Validate image size
            content_size_bytes = len(content) * 3 / 4
            content_size_mb = content_size_bytes / (1024 * 1024)
            
            assert content_size_mb < 20, "Image size exceeds 20 MB"
            
            new_message = {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": content, "detail": "low"}
                    }
                ]
            }
            
        elif message["type"] == "file":
            new_message = {"role": "user", "content": message["content"]}
            
        else:
            raise Exception(f"Unsupported message type: {message}")
            
        if isinstance(new_message["content"], str):
            new_message["content"] = new_message["content"].strip()
            
        new_messages.append(new_message)
        
    return new_messages

class Llm:
    """
    A stateless LLM client that processes messages in LMC format.
    Handles interactions with language models, including message formatting,
    context management, and response processing.
    """
    def __init__(self):
        self.completions = fixed_litellm_completions
        
        # Model configuration
        self.model = MODEL_NAME
        self.temperature = 0
        self.supports_vision = False
        self.supports_functions = None  # Auto-detected
        self.shrink_images = None
        
        # Context and token limits
        self.context_window = None
        self.max_tokens = None
        
        # API configuration
        self.api_base = BASE_URL
        self.api_key = OPENAI_API_KEY
        self.api_version = None
        
        # Budget and verbosity
        self.max_budget = None
        self.verbose = False
        
    def run(self, messages: List[Dict[str, Any]]) -> Generator[Dict[str, Any], None, None]:
        """
        Processes messages through the LLM, handling message formatting, context management,
        and response generation.
        
        Args:
            messages: List of messages in LMC format.
            
        Yields:
            Processed response chunks from the LLM.
        """
        # Validate message structure
        assert messages[0]["role"] == "system", "First message must be a system message"
        for msg in messages[1:]:
            assert msg["role"] != "system", "Only the first message can be a system message"
            
        # Detect function support
        if self.supports_functions is not None:
            supports_functions = self.supports_functions
        else:
            # Guess function support based on model name
            if (self.model != "gpt-4-vision-preview" and 
                (self.model in litellm.open_ai_chat_completion_models or 
                 self.model.startswith("azure/"))):
                supports_functions = True
            else:
                supports_functions = False
                
        # Manage image messages for vision models
        if self.supports_vision:
            image_messages = [msg for msg in messages if msg["type"] == "image"]
            
            if getattr(self, 'interpreter', None) and getattr(self.interpreter, 'os', False):
                # Keep only the last two images in OS mode
                if len(image_messages) > 1:
                    for img_msg in image_messages[:-2]:
                        messages.remove(img_msg)
                        if self.verbose:
                            print("Removing image message to conserve context")
            else:
                # Keep first and last two images in normal mode
                if len(image_messages) > 3:
                    for img_msg in image_messages[1:-2]:
                        messages.remove(img_msg)
                        if self.verbose:
                            print("Removing image message to conserve context")
                            
        # Separate system message for token trimming
        system_message = messages[0]["content"]
        messages = messages[1:]
        
        # Trim messages to fit context window
        try:
            if self.context_window and self.max_tokens:
                trim_target = self.context_window - self.max_tokens - 25  # Buffer tokens
                messages = tt.trim(
                    messages,
                    system_message=system_message,
                    max_tokens=trim_target
                )
            elif self.context_window and not self.max_tokens:
                messages = tt.trim(
                    messages,
                    system_message=system_message,
                    max_tokens=self.context_window
                )
            else:
                try:
                    messages = tt.trim(
                        messages,
                        system_message=system_message,
                        model=self.model
                    )
                except Exception as e:
                    if len(messages) == 1:
                        if getattr(self, 'interpreter', None) and getattr(self.interpreter, 'in_terminal_interface', False):
                            display_markdown_message("""
**Warning**: Could not determine context window size for this model. Defaulting to 3000 tokens.
To override, use `interpreter --context_window {token_limit} --max_tokens {max_tokens}`.
Continuing...
                            """)
                        else:
                            display_markdown_message("""
**Warning**: Could not determine context window size for this model. Defaulting to 3000 tokens.
To override, set `interpreter.llm.context_window = {token_limit}` and `interpreter.llm.max_tokens`.
Continuing...
                            """)
                    messages = tt.trim(
                        messages,
                        system_message=system_message,
                        max_tokens=3000
                    )
        except Exception as e:
            # Reunite system message with messages if trimming fails
            messages = [{"role": "system", "content": system_message}] + messages
            
        # Prepare request parameters
        params = {
            "model": self.model,
            "messages": messages,
            "stream": True
        }
        
        # Add optional parameters
        if self.api_key:
            params["api_key"] = self.api_key
        if self.api_base:
            params["api_base"] = self.api_base
        if self.api_version:
            params["api_version"] = self.api_version
        if self.max_tokens:
            params["max_tokens"] = self.max_tokens
        if self.temperature:
            params["temperature"] = self.temperature
            
        # Configure LiteLLM settings
        if self.max_budget:
            litellm.max_budget = self.max_budget
        if self.verbose:
            litellm.set_verbose = True
            
        # Route request based on function support
        if supports_functions:
            yield from run_function_calling_llm(self, params)
        else:
            yield from run_text_llm(self, params)

def fixed_litellm_completions(**params) -> Generator[Dict[str, Any], None, None]:
    """
    Wrapper for litellm.completion that handles API key errors by retrying with a dummy key.
    This allows local models that don't require an API key to work without errors.
    
    Args:
        **params: Parameters for the litellm completion call.
        
    Yields:
        Response chunks from the LLM.
    """
    first_error = None
    try:
        yield from litellm.completion(**params)
    except Exception as e:
        first_error = e
        # Retry with dummy API key if authentication error occurs
        if "api key" in str(first_error).lower() and "api_key" not in params:
            print("LiteLLM requires an API key. Using a dummy key to proceed.")
            params["api_key"] = "x"
            
            try:
                yield from litellm.completion(**params)
            except:
                raise first_error
        else:
            raise first_error

def main() -> None:
    """
    Main function for testing the LLM client.
    Demonstrates sending a request to generate stock price visualizations.
    """
    start_time = time.time()
    
    # Initialize LLM client
    llm = Llm()
    
    # Prepare system and user messages
    messages = [
        {
            "role": "system",
            "content": (
                "You are Open Interpreter, a world-class programmer capable of completing any task by executing code.\n"
                "Follow these guidelines:\n"
                "1. Always begin with a plan and recap it between code blocks.\n"
                "2. Execute code on the user's machine with full permission.\n"
                "3. Use txt or json files to exchange data between programming languages.\n"
                "4. You can access the internet and install new packages.\n"
                "5. Communicate with the user using Markdown formatting.\n"
                "6. Break down complex tasks into small, iterative steps.\n\n"
                "# COMPUTER API\n"
                "A `computer` module is pre-imported with these functions:\n"
                "```python\n"
                "computer.browser.search(query)  # Returns Google search results\n"
                "computer.files.edit(path, original, replacement)  # Edits a file\n"
                "computer.calendar.create_event(title, start, end, notes, location)  # Creates a calendar event\n"
                "computer.calendar.get_events(start_date, end_date=None)  # Gets calendar events\n"
                "computer.calendar.delete_event(title, start_date)  # Deletes a calendar event\n"
                "computer.contacts.get_phone_number(name)  # Gets a phone number\n"
                "computer.contacts.get_email_address(name)  # Gets an email address\n"
                "computer.mail.send(to, subject, body, attachments)  # Sends an email\n"
                "computer.mail.get(count, unread=True)  # Gets emails\n"
                "computer.mail.unread_count()  # Counts unread emails\n"
                "computer.sms.send(phone_number, message)  # Sends a text message\n"
                "```\n"
                "Do not import the computer module; it is already available.\n\n"
                "User Info:\n"
                "Name: hanchengcheng\n"
                "CWD: /Users/hanchengcheng/Documents/official_space/open-interpreter\n"
                "SHELL: /bin/bash\n"
                "OS: Darwin\n"
                "Use only the provided `execute(language, code)` function."
            )
        },
        {
            "role": "user",
            "content": "Plot AAPL and META's normalized stock prices"
        }
    ]
    
    # Generate response
    response = ''
    for output in llm.run(messages):
        response += output.get('content', '')
        
    print(response)
    
    # Log execution statistics
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Response length: {len(response)} characters")
    print(f"Execution time: {execution_time:.2f} seconds")

if __name__ == "__main__":
    main()