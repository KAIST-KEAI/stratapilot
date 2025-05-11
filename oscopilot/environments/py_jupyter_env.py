# This code is based on Open Interpreter. Original source: https://github.com/OpenInterpreter/open-interpreter

import ast
import os
import sys
import queue
import threading
import time
import logging

from jupyter_client import KernelManager
from stratapilot.environments.base_env import BaseEnv
from typing import Dict, Generator, Any


# turn off colors in "terminal"
# os.environ["ANSI_COLORS_DISABLED"] = "1"

class EnvState:
    def __init__(self, command: str):
        self.command: str = command
        self.result: str = ""
        self.error: str = ""

class PythonJupyterEnv(BaseEnv):
    """
    Environment for executing Python code in a Jupyter kernel.
    """
    file_extension = "py"
    name = "Python"
    aliases = ["py", "API"]

    def __init__(self):
        super().__init__()
        # Suppress specific IPKernel warnings
        logger = logging.getLogger('IPKernelApp')
        logger.addFilter(lambda rec: 'Parent appears to have exited' not in rec.getMessage())

        # Start the kernel
        python_exec = sys.executable
        self.km = KernelManager(
            kernel_name='python3',
            kernel_cmd=[python_exec, '-m', 'ipykernel_launcher', '-f', '{connection_file}']
        )
        self.km.start_kernel()
        self.kc = self.km.client()
        self.kc.start_channels()

        # Wait until the kernel is ready
        while not self.kc.is_alive():
            time.sleep(0.1)
        time.sleep(0.2)

        self.finish_flag = False
        self.msg_queue: queue.Queue[Dict[str, Any]] = queue.Queue()
        self.listener: threading.Thread = None

    def terminate(self):
        self.kc.stop_channels()
        self.km.shutdown_kernel()

    def step(self, code: str) -> Generator[Dict[str, Any], None, None]:
        """
        Execute a block of Python code and yield output messages.
        """
        self.finish_flag = False

        # Prepare code (e.g., insert active line markers)
        try:
            code_proc = self.preprocess_code(code)
        except Exception:
            code_proc = code

        # Listener thread to process IOPub messages
        def iopub_listener():
            while not self.finish_flag:
                try:
                    msg = self.kc.iopub_channel.get_msg(timeout=0.1)
                except queue.Empty:
                    continue

                msg_type = msg['header']['msg_type']
                content = msg['content']

                if msg_type == 'status' and content.get('execution_state') == 'idle':
                    self.finish_flag = True
                    break

                if msg_type == 'stream':
                    text = content.get('text', '')
                    self.msg_queue.put({'type': 'console', 'format': 'output', 'content': text})
                elif msg_type == 'error':
                    tb = '\n'.join(content.get('traceback', []))
                    self.msg_queue.put({'type': 'console', 'format': 'output', 'content': tb})
                elif msg_type in ('display_data', 'execute_result'):
                    data = content.get('data', {})
                    if img := data.get('image/png'):
                        self.msg_queue.put({'type': 'image', 'format': 'base64.png', 'content': img})
                    elif txt := data.get('text/plain'):
                        self.msg_queue.put({'type': 'console', 'format': 'output', 'content': txt})

        self.listener = threading.Thread(target=iopub_listener)
        self.listener.start()

        # Send execution request
        self.kc.execute(code_proc)

        # Yield messages from the queue
        while not self.finish_flag or not self.msg_queue.empty():
            try:
                yield self.msg_queue.get(timeout=0.1)
            except queue.Empty:
                continue

    def preprocess_code(self, code: str) -> str:
        """
        Optionally modify the code (e.g., add active line markers).
        """
        return code