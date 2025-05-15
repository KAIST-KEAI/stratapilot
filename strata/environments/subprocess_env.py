import os
import queue
import re
import subprocess
import threading
import time
import traceback
from stratapilot.environments.base_env import BaseEnv
from typing import Generator, Dict, Any

class OutputMessage:
    def __init__(self, type: str, format: str, content: Any):
        self.type = type
        self.format = format
        self.content = content

class SubprocessEnv(BaseEnv):
    """
    Environment for executing code in a persistent subprocess.
    """
    def __init__(self):
        self.start_cmd = []           # e.g. ['python3', '-u']
        self.process = None           # subprocess.Popen
        self.verbose = False
        self.output_queue: queue.Queue[OutputMessage] = queue.Queue()
        self.done = threading.Event()

    def detect_active_line(self, line: str) -> int:
        return -1                # Override to detect markers

    def detect_end_of_execution(self, line: str) -> bool:
        return False             # Override to detect end marker

    def line_postprocessor(self, line: str) -> str:
        return line              # Override to filter or transform

    def preprocess_code(self, code: str) -> str:
        return code              # Override to insert markers

    def terminate(self) -> None:
        if self.process:
            self.process.terminate()
            self.process.stdin.close()
            self.process.stdout.close()
            self.process.stderr.close()
            self.process = None

    def start_process(self) -> None:
        self.terminate()
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        self.process = subprocess.Popen(
            self.start_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
        )
        threading.Thread(target=self.handle_stream_output, args=(self.process.stdout, False), daemon=True).start()
        threading.Thread(target=self.handle_stream_output, args=(self.process.stderr, True), daemon=True).start()

    def step(self, code: str) -> Generator[Dict[str, Any], None, None]:
        retries = 0
        max_retries = 3

        try:
            code = self.preprocess_code(code)
            if not self.process:
                self.start_process()
        except Exception:
            yield {'type': 'console', 'format': 'output', 'content': traceback.format_exc()}
            return

        while retries <= max_retries:
            try:
                if self.verbose:
                    print(f"Running processed code:\n{code}")
                self.done.clear()
                self.process.stdin.write(code + '\n')
                self.process.stdin.flush()
                break
            except Exception:
                retries += 1
                if retries > max_retries:
                    yield {'type': 'console', 'format': 'output', 'content': 'Maximum retries reached.'}
                    return
                if self.verbose:
                    print(f"Retry {retries}/{max_retries}, restarting process.")
                self.start_process()

        while not self.done.is_set() or not self.output_queue.empty():
            try:
                msg = self.output_queue.get(timeout=0.3)
                yield {'type': msg.type, 'format': msg.format, 'content': msg.content}
            except queue.Empty:
                continue

    def handle_stream_output(self, stream, is_error: bool) -> None:
        for line in iter(stream.readline, ''):
            if self.verbose:
                print(f"Received: {line.strip()}")
            line = self.line_postprocessor(line)
            if line is None:
                continue
            if self.detect_active_line(line) >= 0:
                active = self.detect_active_line(line)
                self.output_queue.put(OutputMessage('console', 'active_line', active))
                cleaned = re.sub(r"##active_line\d+##", '', line)
                if cleaned:
                    self.output_queue.put(OutputMessage('console', 'output', cleaned))
            elif self.detect_end_of_execution(line):
                content = line.replace('##end_of_execution##', '').strip()
                if content:
                    self.output_queue.put(OutputMessage('console', 'output', content))
                self.done.set()
            elif is_error and 'KeyboardInterrupt' in line:
                self.output_queue.put(OutputMessage('console', 'output', 'KeyboardInterrupt'))
                self.done.set()
            else:
                self.output_queue.put(OutputMessage('console', 'output', line))

