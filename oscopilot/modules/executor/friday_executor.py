from strata.modules.base_module import BaseModule
from strata.tool_repository.manager.tool_manager import get_open_api_doc_path
import re
import json
import subprocess
from pathlib import Path
from strata.utils.utils import send_chat_prompts, api_exception_mechanism


class TaskHandler(BaseModule):
    """
    Handles dynamic tool generation, execution, evaluation, and persistence in a modular system.
    """

    def __init__(self, prompt_config, tool_registry, retry_limit=3):
        super().__init__()
        self.prompt_config = prompt_config
        self.tool_registry = tool_registry
        self.retry_limit = retry_limit
        self.api_doc_path = get_open_api_doc_path()
        with open(self.api_doc_path) as file:
            self.api_documentation = json.load(file)

    @api_exception_mechanism(max_retries=3)
    def compose_tool(self, name, description, kind, dependencies, references):
        ref_snippets = json.dumps(references)
        if kind == 'Python':
            sys_msg = self.prompt_config['PYTHON_SYS_GEN']
            user_msg = self.prompt_config['PYTHON_USER_GEN'].format(
                system_version=self.system_version,
                task_description=description,
                working_dir=self.environment.working_dir,
                task_name=name,
                pre_tasks_info=dependencies,
                relevant_code=ref_snippets
            )
        else:
            sys_msg = self.prompt_config['SHELL_SYS_GEN']
            user_msg = self.prompt_config['SHELL_USER_GEN'].format(
                system_version=self.system_version,
                task_description=description,
                working_dir=self.environment.working_dir,
                task_name=name,
                pre_tasks_info=dependencies,
                Type=kind
            )
        result = send_chat_prompts(sys_msg, user_msg, self.llm)
        executable = self._extract_code(result, kind)
        activation = self._extract_tagged_content(result, '<invoke>', '</invoke>')[0] if kind == 'Python' else ''
        return executable, activation

    def activate_tool(self, script, trigger, mode):
        if mode == 'Python':
            append_code = '\nprint("<return>")\nprint(result)\nprint("</return>")'
            script += f"\nresult={trigger}" + append_code

        print("<code_output>\n" + script + "\n</code_output>")
        outcome = self.environment.step(mode, script)
        print("<exec_state>\n" + str(outcome) + "\n</exec_state>")
        return outcome

    @api_exception_mechanism(max_retries=3)
    def assess_tool(self, script, summary, state, next_plan):
        plan_json = json.dumps(next_plan)
        sys_msg = self.prompt_config['JUDGE_SYS']
        user_msg = self.prompt_config['JUDGE_USER'].format(
            current_code=script,
            task=summary,
            code_output=state.result[:999] if len(state.result) > 1000 else state.result,
            current_working_dir=state.pwd,
            working_dir=self.environment.working_dir,
            files_and_folders=state.ls,
            next_action=plan_json,
            code_error=state.error,
        )
        reply = send_chat_prompts(sys_msg, user_msg, self.llm)
        parsed = self._parse_json(reply)
        return parsed['reasoning'], parsed['status'], parsed['score']

    @api_exception_mechanism(max_retries=3)
    def revise_tool(self, source_code, summary, kind, state, feedback, dependencies):
        key = 'PYTHON_SYS_FIX' if kind == 'Python' else 'SHELL_SYS_FIX'
        val = 'PYTHON_USER_FIX' if kind == 'Python' else 'SHELL_USER_FIX'
        sys_msg = self.prompt_config[key]
        user_msg = self.prompt_config[val].format(
            original_code=source_code,
            task=summary,
            error=state.error,
            code_output=state.result,
            current_working_dir=state.pwd,
            working_dir=self.environment.working_dir,
            files_and_folders=state.ls,
            critique=feedback,
            pre_tasks_info=dependencies
        )
        response = send_chat_prompts(sys_msg, user_msg, self.llm)
        revised = self._extract_python_code(response)
        activation = self._extract_tagged_content(response, '<invoke>', '</invoke>')[0]
        return revised, activation

    @api_exception_mechanism(max_retries=3)
    def inspect_tool(self, script, summary, state):
        sys_msg = self.prompt_config['ERR_SYS']
        user_msg = self.prompt_config['ERR_USER'].format(
            current_code=script,
            task=summary,
            code_error=state.error,
            current_working_dir=state.pwd,
            working_dir=self.environment.working_dir,
            files_and_folders=state.ls
        )
        outcome = send_chat_prompts(sys_msg, user_msg, self.llm)
        analysis = self._parse_json(outcome)
        return analysis['reasoning'], analysis['type']

    def catalog_tool(self, tool_name, content):
        if not self.tool_registry.exist_tool(tool_name):
            details = self._extract_summary(content)
            entry = self._compose_tool_entry(tool_name, content, details)
            self.tool_registry.add_new_tool(entry)
        else:
            print("Tool already present.")

    @api_exception_mechanism(max_retries=3)
    def request_api_tool(self, description, endpoint, context="No context provided."):
        sys_msg = self.prompt_config['API_SYS'].format(
            openapi_doc=json.dumps(self._filter_openapi(endpoint)),
            tool_sub_task=description,
            context=context
        )
        user_msg = self.prompt_config['API_USER']
        response = send_chat_prompts(sys_msg, user_msg, self.llm)
        return self._extract_python_code(response)

    def qa_tool(self, background, inquiry, prior_q=None):
        sys_msg = self.prompt_config['QA_SYS']
        user_msg = self.prompt_config['QA_USER'].format(
            context=background,
            question=inquiry,
            current_question=prior_q
        )
        return send_chat_prompts(sys_msg, user_msg, self.llm)

    def _extract_code(self, text, lang):
        marker = f"```{lang.lower()}"
        if marker in text:
            return text.split(marker)[1].split('```')[0].strip()
        elif '```' in text:
            return text.split('```')[1].split('```')[0].strip()
        raise NotImplementedError("Unsupported code format.")

    def _extract_python_code(self, text):
        return self._extract_code(text, 'python')

    def _parse_json(self, content):
        return json.loads(re.search(r'{.*}', content, re.DOTALL).group())

    def _extract_summary(self, snippet):
        match = re.search(r'"""\s*\n\s*(.*?)[\.\n]', snippet)
        if not match:
            raise NotImplementedError("Summary missing.")
        return match.group(1)

    def _compose_tool_entry(self, name, code, desc):
        return {
            "task_name": name,
            "code": code,
            "description": desc
        }

    def _extract_tagged_content(self, msg, start, end):
        return re.findall(f'{start}(.*?){end}', msg, re.DOTALL)

    def store_text(self, data, location):
        Path(location).parent.mkdir(parents=True, exist_ok=True)
        with open(location, 'w', encoding='utf-8') as f:
            sanitized = '\n'.join(line.strip() for line in data.strip().splitlines())
            f.write(sanitized)

    def extract_path(self, input_str):
        unix = r"/[^/\s]+(?:/[^/\s]*)*"
        windows = r"[a-zA-Z]:\\(?:[^\\/\s]+\\)*[^\\/\s]+"
        combined = f"({unix})|({windows})"
        found = re.findall(combined, input_str)
        paths = [i[0] or i[1] for i in found]
        return paths[0].strip('"\'') if paths else ''

    def _filter_openapi(self, route):
        if route not in self.api_documentation['paths']:
            return {"error": "Unknown endpoint."}

        minimal_doc = {
            "openapi": self.api_documentation['openapi'],
            "info": self.api_documentation['info'],
            "paths": {route: self.api_documentation['paths'][route]},
            "components": {"schemas": {}}
        }

        verb_data = self.api_documentation['paths'][route].get('get') or \
                    self.api_documentation['paths'][route].get('post', {})

        ref = verb_data.get('requestBody', {}).get('content', {}).get('application/json', {}).get('schema', {}).get('$ref')
        if not ref:
            allof = verb_data.get('requestBody', {}).get('content', {}).get('multipart/form-data', {}).get('schema', {}).get('allOf', [])
            if allof and '$ref' in allof[0]:
                ref = allof[0]['$ref']

        if ref:
            key = ref.split('/')[-1]
            minimal_doc['components']['schemas'][key] = self.api_documentation['components']['schemas'][key]

        return minimal_doc
