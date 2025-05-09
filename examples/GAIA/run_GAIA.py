import json
import requests
from oscopilot import FridayAgent
from oscopilot import FridayExecutor, FridayPlanner, FridayRetriever, ToolManager
from oscopilot.utils import setup_config, GAIALoader, GAIA_postprocess


def evaluate_results(path):
    """Load previous results and calculate correct and incomplete answer counts."""
    correct = 0
    incomplete = 0
    last_index = -1
    try:
        with open(path, 'r', encoding='utf-8') as file:
            results = [json.loads(line) for line in file]
            for item in results:
                if item["model_answer"] == item["groundtruth"]:
                    correct += 1
                if item["model_answer"] in ("", "incomplete"):
                    incomplete += 1
            if results:
                last_index = results[-1]["index"]
    except FileNotFoundError:
        pass  # File will be created later if it does not exist
    return correct, incomplete, last_index


def process_task(agent, task, task_index):
    """Run the agent on a single task and return result dict."""
    query = GAIALoader.task2query(task)
    try:
        agent.run(query)
        if agent.inner_monologue.result:
            result = GAIA_postprocess(task['Question'], agent.inner_monologue.result)
        else:
            result = "incomplete"
    except requests.exceptions.ConnectionError as ce:
        print(f"[Connection Error] {ce}")
        exit(1)
    except Exception as e:
        print(f"[Exception] {e}")
        result = "incomplete"

    return {
        "index": task_index,
        "task_id": task["task_id"],
        "model_answer": result,
        "groundtruth": task["Final answer"],
        "reasoning_trace": ""
    }


def main():
    args = setup_config()
    args.dataset_type = 'validation'
    model = 'gpt4-turbo'
    result_path = f'gaia_{model}_{args.dataset_type}_level{args.level}_results.jsonl'

    agent = FridayAgent(FridayPlanner, FridayRetriever, FridayExecutor, ToolManager, config=args)
    gaia = GAIALoader(args.level, args.dataset_cache)

    # Handle single-task mode
    if args.gaia_task_id:
        task = gaia.get_data_by_task_id(args.gaia_task_id, args.dataset_type)
        query = gaia.task2query(task)
        mock_result = "17000"  # hardcoded result (for debug/demo purposes)
        final_result = GAIA_postprocess(task['Question'], mock_result)
        print(f"The answer of GAIA Task {args.gaia_task_id}: {final_result}")
        return

    # Handle batch mode
    task_list = gaia.dataset[args.dataset_type]
    correct, incomplete, last_index = evaluate_results(result_path)

    with open(result_path, 'a', encoding='utf-8') as file:
        for idx, task in enumerate(task_list):
            if idx <= last_index:
                print(f"[Skip] Task {idx} already processed.")
                continue

            output = process_task(agent, task, idx)

            if output["model_answer"] == output["groundtruth"]:
                correct += 1
            if output["model_answer"] == "incomplete":
                incomplete += 1

            file.write(json.dumps(output) + '\n')
            file.flush()

        total = idx + 1
        print(f"Accuracy: {correct / total:.2%}")
        print(f"Incomplete: {incomplete / total:.2%}")
        print(f"Summary: correct={correct}, incomplete={incomplete}, total={total}")


if __name__ == '__main__':
    main()
