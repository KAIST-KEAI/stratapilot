from oscopilot import FridayAgent, ToolManager
from oscopilot import FridayExecutor, FridayPlanner, FridayRetriever
from oscopilot.utils import setup_config, setup_pre_run


def main():
    try:
        # Load configuration from CLI or default setup
        args = setup_config()

        # Provide a default task description if none is specified
        if not args.query:
            args.query = (
                "Replace the word 'cup' with 'cups' in all text files under my home directory"
            )

        # Preprocess the task into the required internal structure
        task = setup_pre_run(args)

        # Initialize the FridayAgent with its planning, retrieval, execution modules
        agent = FridayAgent(
            planner_cls=FridayPlanner,
            retriever_cls=FridayRetriever,
            executor_cls=FridayExecutor,
            tool_manager_cls=ToolManager,
            config=args
        )

        # Run the task
        agent.run(task=task)

    except Exception as e:
        print(f"[ERROR] Failed to execute FridayAgent pipeline: {e}")


if __name__ == "__main__":
    main()
