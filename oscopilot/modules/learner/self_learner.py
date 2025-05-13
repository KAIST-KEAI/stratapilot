from strata.modules.base_module import BaseModule
from strata.utils.utils import send_chat_prompts
import logging


class SelfLearner(BaseModule):
    """
    A self-learning module that dynamically generates educational courses based on provided software information
    and file content. Inherits from BaseModule and uses LLM-based interaction to produce structured outputs.

    Attributes:
        prompt (dict): Contains system and user prompt templates.
        tool_manager (object): Interface for interacting with external tools.
        course (dict): Stores the generated course details.
    """
    def __init__(self, prompt, tool_manager):
        """
        Initialize SelfLearner with prompt templates and a tool manager.

        Args:
            prompt (dict): Dictionary containing system/user prompt templates.
            tool_manager (object): Tool manager for external integration.
        """
        super().__init__()
        self.prompt = prompt
        self.tool_manager = tool_manager
        self.course = {}

    def design_course(self, software_name, package_name, demo_file_path, file_content=None, prior_course=None):
        """
        Generate a course based on input parameters such as software and package details.

        Args:
            software_name (str): Target software for course content.
            package_name (str): Relevant package/module name.
            demo_file_path (str): Path to demo file used in the course.
            file_content (str, optional): Content of the demo file.
            prior_course (str, optional): Previously completed course to build upon.

        Returns:
            dict: A structured dictionary representing the designed course.

        Raises:
            ValueError: If response cannot be parsed into valid JSON.
        """
        try:
            sys_prompt = self.prompt['_SYSTEM_COURSE_DESIGN_PROMPT']
            user_prompt = self.prompt['_USER_COURSE_DESIGN_PROMPT'].format(
                system_version=self.system_version,
                software_name=software_name,
                package_name=package_name,
                file_content=file_content,
                demo_file_path=demo_file_path,
                prior_course=prior_course
            )

            response = send_chat_prompts(sys_prompt, user_prompt, self.llm)
            # logging.info(f"Received response: {response}")

            course = self.extract_json_from_string(response)
            if not isinstance(course, dict):
                raise ValueError("Failed to extract valid JSON course structure.")
            
            self.course = course
            return self.course

        except Exception as e:
            logging.error(f"Error while designing course: {e}")
            raise
