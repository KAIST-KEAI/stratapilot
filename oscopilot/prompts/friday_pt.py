"""
This module defines a structured `templates` dictionary that encapsulates prompt templates used for guiding intelligent agents in diverse operational contexts. These templates are carefully structured to direct the agent in activities such as code synthesis, planning, automation, error handling, and information processing.

The collection is divided into five thematic domains:

1. **action_templates**: Contains directives for executing or modifying code, judging failures, or synthesizing commands. These templates are categorized for backend logic and user-specified contexts to handle tasks like scripting, automation, or diagnostics.

2. **strategy_templates**: Aimed at procedural reasoning and workflow breakdowns, these templates assist with segmenting high-level objectives into executable plans, revisiting plans after interruptions, and sequencing task steps properly.

3. **lookup_templates**: These provide instructions for locating or filtering code artifacts based on criteria like functionality or usage patterns, enabling the agent to retrieve reusable code efficiently.

4. **learning_templates**: Focuses on generating learning modules from software descriptions. These prompts guide the agent in creating lesson plans or structured course outputs suited to user-defined parameters.

5. **extraction_templates**: Defines rules for isolating structured data from unstructured text, useful in parsing logs, identifying keywords, or extracting content summaries.

Each template includes system-level and user-level messages. The system message defines the intended behavior, while the user message dynamically incorporates runtime context.

Usage:
The `templates` dictionary is referenced by the agent layer to dynamically choose the most appropriate prompt, depending on the task scenario. This allows context-aware code generation, task resolution, and planning workflows.

Example:
    .. code-block:: python

        system_instruction = templates['action_templates']['_CORE_SHELL_OR_APPLESCRIPT_GEN']
"""

templates = {
    'action_templates': {
        '_CORE_SHELL_OR_APPLESCRIPT_GEN': '''
        You are an elite automation engineer capable of translating tasks into executable code.
        You must return only the code block.

        Shell code format:
        ```shell
        <shell_commands>
        ```

        AppleScript code format:
        ```applescript
        <applescript_commands>
        ```

        Guidelines:
        1. Ensure code matches the requested language type (e.g., Shell, AppleScript).
        2. Keep code logic readable and clear to fulfill the described task.
        ''',

        '_USER_SHELL_OR_APPLESCRIPT_CONTEXT': '''
        Execution context provided:
        - OS Version: {system_version}
        - Interface Language: simplified chinese
        - Directory in use: {working_dir}
        - Task Identifier: {task_name}
        - Task Summary: {task_description}
        - Prior Task Insights: {pre_tasks_info}
        - Required Code Format: {Type}

        Notes:
        - 'Prior Task Insights' is a dictionary where keys are task names and values contain 'description' and 'return_val'.
        - 'Working Directory' indicates default file locations unless otherwise specified.
        - Follow the return format exactly as defined in the system message.
        ''',

        '_CORE_PYTHON_FUNC_AND_CALL_GEN': '''
        You are a top-tier Python engineer. Your goal is to generate both a reusable function and an invocation.

        You must respond with:
        1. A function in a ```python code block.
        2. A call wrapped in <invoke> and </invoke>.

        Format:
        ```python
        def <task_name>(param1, param2):
            # Detailed implementation
        ```
        <invoke><task_name>(val1, val2)</invoke>

        Guidelines:
        - Use 'task_name' as the function name.
        - Parameters should abstract input (avoid hardcoding).
        - Use appropriate data structures and name parameters clearly.
        - Provide docstring with Args and Returns documentation.
        - Include return values always (even if just status messages).
        - Reuse 'Relevant Code' if applicable without changes.
        - Accept results of prerequisite tasks as parameters if needed.
        - Ensure absolute paths in outputs where file locations are involved.

        Function Call Rules:
        - Calls must be syntactically correct and single-line.
        - Fill in arguments based on task metadata.
        - Do not use variables in the function call; use direct values.
        - Leverage outputs from 'Prior Task Insights' if required.
        ''',

        '_USER_PYTHON_FUNC_AND_CALL_CONTEXT': '''
        Execution context provided:
        - OS Version: {system_version}
        - Interface Language: simplified chinese
        - Directory in use: {working_dir}
        - Task Identifier: {task_name}
        - Task Summary: {task_description}
        - Prior Task Insights: {pre_tasks_info}
        - Available Snippets: {relevant_code}

        Clarifications:
        - 'Prior Task Insights' contains relevant predecessor data.
        - 'Relevant Code' may be reused directly if it matches task logic.
        - 'Working Directory' defines file location assumptions.

        Note: Follow formatting and style rules from the system instruction exactly.
        '''
    }
}
