from oscopilot import FridayAgent
from oscopilot import FridayExecutor, FridayPlanner, FridayRetriever, ToolManager
from oscopilot.utils import setup_config, SheetTaskLoader


def run_agent_on_task(agent, task, task_id=None):
    """
    Run the FridayAgent on a single task.

    Args:
        agent (FridayAgent): The agent instance responsible for task execution.
        task (dict): The task data to be processed.
        task_id (int, optional): Optional identifier for the task.
    """
    try:
        if task_id is not None:
            print(f"Running task ID: {task_id}")
        agent.run(task)
    except Exception as e:
        print(f"Error running task {task_id}: {e}")


def main():
    """
    Entry point for executing sheet tasks using the FridayAgent pipeline.
    Loads task(s) from a JSONL file and runs them based on the configuration.
    """
    try:
        args = setup_config()
        sheet_task_loader = SheetTaskLoader("examples/SheetCopilot/sheet_task.jsonl")
        agent = FridayAgent(FridayPlanner, FridayRetriever, FridayExecutor, ToolManager, config=args)
    except Exception as e:
        print(f"Initialization failed: {e}")
        return

    if args.sheet_task_id is not None:
        try:
            task = sheet_task_loader.get_data_by_task_id(args.sheet_task_id)
            run_agent_on_task(agent, task, args.sheet_task_id)
        except Exception as e:
            print(f"Failed to load or run task {args.sheet_task_id}: {e}")
    else:
        try:
            task_list = sheet_task_loader.load_sheet_task_dataset()
            for task_id, task in enumerate(task_list):
                args.sheet_task_id = task_id
                run_agent_on_task(agent, task, task_id)
        except Exception as e:
            print(f"Failed to load or execute task list: {e}")


if __name__ == "__main__":
    main()
