# This code is based on Open Interpreter. Original source: https://github.com/OpenInterpreter/open-interpreter
from stratapilot.environments import BaseEnv
from stratapilot.environments import AppleScript
from stratapilot.environments import PythonJupyterEnv
from stratapilot.environments import Shell
from stratapilot.utils.schema import EnvState

import os
import subprocess
from typing import Any, Dict, List, Optional, Generator


class EnvState:
    def __init__(self, command: str):
        self.command: str = command
        self.result: str = ""
        self.error: str = ""
        self.pwd: str = ""
        self.ls: str = ""


class OutputChunk(Dict[str, Any]):
    """
    sample: console/output/active_line, content, recipient
    """
    pass


class Language:
    name: str = ""
    aliases: List[str] = []

    def step(self, code: str) -> EnvState:
        raise NotImplementedError

    def run(self, code: str) -> Generator[OutputChunk, None, None]:
        raise NotImplementedError

    def stop(self) -> None:
        pass

    def terminate(self) -> None:
        pass


class PythonJupyterEnv(Language):
    name = "Python"
    aliases = ["py"]

    def step(self, code: str) -> EnvState:
        state = EnvState(code)
        try:
            cp = subprocess.run(
                ["python3", "-c", code],
                capture_output=True, text=True
            )
            state.result = cp.stdout
            state.error = cp.stderr
        except Exception as e:
            state.error = str(e)
        return state

    def run(self, code: str):
        # simplification
        st = self.step(code)
        yield {"type": "console", "format": "output", "content": st.result}
        if st.error:
            yield {"type": "console", "format": "output", "content": st.error}


class Shell(Language):
    name = "Shell"
    aliases = ["sh", "bash"]

    def step(self, code: str) -> EnvState:
        state = EnvState(code)
        try:
            cp = subprocess.run(
                ["/bin/sh", "-c", code],
                capture_output=True, text=True
            )
            state.result = cp.stdout
            state.error = cp.stderr
        except Exception as e:
            state.error = str(e)
        return state

    def run(self, code: str):
        st = self.step(code)
        yield {"type": "console", "format": "output", "content": st.result}
        if st.error:
            yield {"type": "console", "format": "output", "content": st.error}


class AppleScript(Language):
    name = "AppleScript"
    aliases = ["osascript"]

    def step(self, code: str) -> EnvState:
        state = EnvState(code)
        try:
            cp = subprocess.run(
                ["osascript", "-e", code],
                capture_output=True, text=True
            )
            state.result = cp.stdout
            state.error = cp.stderr
        except Exception as e:
            state.error = str(e)
        return state

    def run(self, code: str):
        st = self.step(code)
        yield {"type": "console", "format": "output", "content": st.result}
        if st.error:
            yield {"type": "console", "format": "output", "content": st.error}


class Env:
    def __init__(self):
        self.languages: List[Language] = [PythonJupyterEnv(), Shell(), AppleScript()]
        self._active: Dict[str, Language] = {}
        self.working_dir: str = os.getcwd()

    def get_language(self, name: str) -> Optional[Language]:
        key = name.lower()
        for lang in self.languages:
            if lang.name.lower() == key or key in (a.lower() for a in lang.aliases):
                return lang
        return None

    def step(self, language: str, code: str, stream: bool = False, display: bool = False) -> Any:
        state = EnvState(command=code)
        lang = self.get_language(language)
        if not lang:
            raise ValueError(f"Unsupported language: {language}")

        if not stream:
            st = lang.step(code)
            state.result = st.result
            state.error = st.error
        else:
            for chunk in self._streaming_run(language, code, display):
                if chunk.get("format") == "active_line" or chunk.get("content") in ('', '\n'):
                    continue
                content = chunk["content"]
                if "Traceback" in content:
                    state.error += content
                else:
                    state.result += content
            if lang.name == "Python":
                lang.terminate()

        state.pwd = self.working_dir
        try:
            state.ls = subprocess.run(
                ["ls"], cwd=self.working_dir, capture_output=True, text=True
            ).stdout
        except:
            state.ls = ""

        return state

    def _streaming_run(self, language: str, code: str, display: bool = False):
        if language not in self._active:
            self._active[language] = self.get_language(language)
        lang = self._active[language]
        for chunk in lang.run(code):
            # 可在此解析 recipient
            if display and chunk.get("format") != "active_line":
                print(chunk.get("content", ""))
            yield chunk

    def stop(self):
        for lang in self._active.values():
            lang.stop()

    def terminate(self):
        for lang in self._active.values():
            lang.terminate()
        self._active.clear()

# example
if __name__ == "__main__":
    env = Env()
    st = env.step("Shell", "echo Hello from C++->Python refactor!", stream=False)
    print("Result:", st.result)