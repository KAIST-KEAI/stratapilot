import os
import logging
from stratapilot.prompts.friday_pt import prompt
import json
from stratapilot.utils import self_learning_print_logging, get_project_root_path, read_json, save_json

class SelfLearning:
    """
    Automates the creation and execution of self-paced learning courses for software topics.

    This class manages course generation, content extraction, and iterative learning cycles
    based on provided software and package information, leveraging configurable agents and tools.
    """

    def __init__(self, agent, learner_cls, tool_manager, config, text_extractor_cls=None):
        """
        Set up the SelfLearning framework with agent, learner, tool manager, and configuration.

        Args:
            agent (object): The execution agent responsible for running course lessons.
            learner_cls (type): Class that generates course structures and content.
            tool_manager (object): Utility for managing external tools needed during learning.
            config (dict): Settings controlling course paths, logging, and thresholds.
            text_extractor_cls (type, optional): Class for extracting text from demo files.
        """
        self.config = config
        self.agent = agent
        self.tool_manager = tool_manager
        # Instantiate learner with its prompt configuration
        self.learner = learner_cls(prompt['self_learning_prompt'], tool_manager)
        self.course = {}
        if text_extractor_cls:
            # Provide the agent context to the text extractor
            self.text_extractor = text_extractor_cls(agent)

    def _initialize_learning(self, software_name, package_name, demo_file_path):
        """
        Perform shared setup for learning methods: logging, directory setup, course loading, and demo extraction.

        Args:
            software_name (str): Identifier of the target software.
            package_name (str): Name of the specific package or module.
            demo_file_path (str): Path to an example file for content extraction.

        Returns:
            tuple:
                - prior_course_path (str): Filesystem path to the existing or new course JSON.
                - file_content (str or None): Extracted text from the demo file, if provided.
        """
        # Log the start of the learning session
        self_learning_print_logging(self.config)

        # Ensure the courses directory exists
        courses_dir = os.path.join(get_project_root_path(), 'courses')
        os.makedirs(courses_dir, exist_ok=True)

        # Define the course file path
        prior_course_path = os.path.join(
            courses_dir,
            f"{software_name}_{package_name}.json"
        )

        # Load existing course or initialize a new one
        if os.path.exists(prior_course_path):
            self.course = read_json(prior_course_path)
        else:
            save_json(prior_course_path, {})
            self.course = {}

        # Extract content from the demo file if provided
        file_content = None
        if demo_file_path:
            if not os.path.isabs(demo_file_path):
                demo_file_path = os.path.join(get_project_root_path(), demo_file_path)
            file_content = self.text_extract(demo_file_path)

        return prior_course_path, file_content

    def self_learning(self, software_name, package_name, demo_file_path):
        """
        Generate a new course and execute it once based on initial state and demo content.

        Args:
            software_name (str): Software to learn.
            package_name (str): Specific package or module within the software.
            demo_file_path (str): Example file path for extracting content.
        """
        prior_path, file_content = self._initialize_learning(
            software_name, package_name, demo_file_path
        )

        # Create a snapshot of the most recent lessons
        if len(self.course) > 50:
            prior_snapshot = json.dumps(dict(list(self.course.items())[-50:]), indent=4)
        else:
            prior_snapshot = json.dumps(self.course, indent=4)

        logging.info(f"Completed lessons so far:\n{prior_snapshot}")

        # Design and run the new course
        new_course = self.learner.design_course(
            software_name, package_name, demo_file_path, file_content, prior_snapshot
        )
        self.learn_course(new_course)
        save_json(prior_path, new_course)

    def continuous_learning(self, software_name, package_name, demo_file_path=None):
        """
        Continuously generate, update, and execute courses in a loop until externally stopped.

        Args:
            software_name (str): Software to learn.
            package_name (str): Package within the software.
            demo_file_path (str, optional): Example file for content extraction.
        """
        prior_path, file_content = self._initialize_learning(
            software_name, package_name, demo_file_path
        )

        # Repeat course design and execution indefinitely
        while True:
            if len(self.course) > 50:
                prior_snapshot = json.dumps(dict(list(self.course.items())[-50:]), indent=4)
            else:
                prior_snapshot = json.dumps(self.course, indent=4)

            logging.info(f"Completed lessons so far:\n{prior_snapshot}")

            new_course = self.learner.design_course(
                software_name, package_name, demo_file_path, file_content, prior_snapshot
            )
            self.course.update(new_course)
            self.learn_course(new_course)
            save_json(prior_path, new_course)

    def text_extract(self, demo_file_path):
        """
        Extract raw text content from a demo file using the configured extractor.

        Args:
            demo_file_path (str): File path to extract text from.

        Returns:
            str: Extracted file content.
        """
        return self.text_extractor.extract_file_content(demo_file_path)

    def course_design(self, software_name, package_name, demo_file_path, file_content=None):
        """
        Create a course outline and content based on provided parameters and optional demo content.

        Args:
            software_name (str): Name of the software topic.
            package_name (str): Relevant package or module name.
            demo_file_path (str): Path to the demo file.
            file_content (str, optional): Pre-extracted demo file content.

        Returns:
            dict: Generated course structure mapping lesson names to content.
        """
        return self.learner.design_course(
            software_name, package_name, demo_file_path, file_content
        )

    def learn_course(self, course):
        """
        Execute each lesson in the given course sequentially using the agent.

        Args:
            course (dict): Mapping of lesson identifiers to lesson content.
        """
        logging.info(f"Starting course with {len(course)} lessons.")
        for lesson_name, lesson_content in course.items():
            logging.info(f"Beginning lesson: {lesson_name}")
            logging.info(f"Lesson content: {lesson_content}")
            self.agent.run(lesson_content)
