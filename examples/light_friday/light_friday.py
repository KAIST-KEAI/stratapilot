# This module is adapted from Open Interpreter: https://github.com/OpenInterpreter/open-interpreter

import os
import re
import dotenv
from rich.console import Console
from rich.markdown import Markdown
from oscopilot.utils import setup_config, setup_pre_run
from oscopilot.modules.base_module import BaseModule

# Load environment variables
dotenv.load_dotenv(dotenv_path='.env', override=True)
MODEL_NAME = os.getenv('MODEL_NAME')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_ORGANIZATION = os.getenv('OPENAI_ORGANIZATION')
BASE_URL = os.getenv('OPENAI_BASE_URL')

console = Console()

def rich_print(markdown_text: str):
    """Render Markdown-formatted text to the console using rich."""
    console.print(Markdown(markdown_text))

def send_chat_prompts(message: list, llm):
    """Send prompts to the LLM and return the response."""
    return llm.chat(message)

def extract_code(input_string: str):
    """
    Extract code block and its language identifier from a markdown-formatted string.
    Returns a tuple of (code_str, language).
    """
    pattern = r"```(\w+)?\s*(.*?)```"
    matches = re.findall(pattern, input_string, re.DOTALL)

    if not matches:
        return None, None

    language, code = matches[0]
    if not language:
        # Infer language heuristically
        if re.search(r"python|import\s+\w+", code.lower()):
            language = "Python"
        elif re.search(r"bash|echo", code.lower()):
            language = "Bash"

    return code.strip(), language

class LightFriday(BaseModule):
    """
    LightFriday is an autonomous code execution agent designed to complete arbitrary user-defined programming tasks.
    """

    def __init__(self, args):
        super().__init__()
        self.args = args

    def execute_tool(self, code: str, lang: str) -> str:
        """
        Executes a single step of code in the specified language environment and returns execution output or errors.
        """
        try:
            state = self.environment.step(lang, code)
        except Exception as e:
            return f"**Execution Error**: {str(e)}"

        result_output = ''
        if state.result and state.result.strip():
            result_output += f"**Execution Result**: {state.result.strip()}"
        if state.error and state.error.strip():
            result_output += f"\n**Execution Error**: {state.error.strip()}"

        return result_output.strip()

    def run(self, task: str):
        """
        Main execution loop that coordinates planning, prompting, code execution, and iterative feedback.
        """
        system_prompt = (
            "You are Light Friday, a world-class programmer that can complete any goal by executing code.\n"
            "Start with a plan. **Always recap the plan between each code block** to mitigate memory loss.\n"
            "Executed code will run on the user's machine with **full user consent**.\n"
            "You may install packages, access the internet, and use any tool necessary to succeed.\n"
            "Use small, incremental steps for stateful languages like Python or Bash.\n"
            "Wrap your code in triple backticks and label the language, e.g. ```python```.\n"
            "Supported languages: Python, Bash."
        )

        user_prompt = (
            f"User Environment Info:\n"
            f"- OS Version: {self.system_version}\n"
            f"- Task: {task}\n"
            f"- Working Directory: {self.environment.working_dir}"
        )

        message = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        while True:
            try:
                response = send_chat_prompts(message, self.llm)
                rich_print(response)
                message.append({"role": "system", "content": response})

                code, lang = extract_code(response)
                if code:
                    result = self.execute_tool(code, lang)
                    rich_print(result)
                else:
                    result = ''

                if result:
                    message.append({"role": "user", "content": f"Execution result:\n{result}"})
                else:
                    message.append({
                        "role": "user",
                        "content": (
                            "Please continue. If all tasks are complete, reply with 'Execution Complete'. "
                            "If you cannot proceed, reply with 'Execution Interrupted' and explain why, "
                            "along with possible alternatives."
                        )
                    })

                if 'Execution Complete' in response or 'Execution Interrupted' in response:
                    break

            except Exception as e:
                rich_print(f"**Runtime Error**: {str(e)}")
                break

if __name__ == "__main__":
    args = setup_config()
    if not args.query:
        args.query = "Plot AAPL and META's normalized stock prices"
    task = setup_pre_run(args)

    agent = LightFriday(args)
    agent.run(task)
