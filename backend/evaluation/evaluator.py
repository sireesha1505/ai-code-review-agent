from graph.review_graph import review_graph
from evaluation.dataset import EVALUATION_DATASET


async def evaluate_case(case):
    initial_state = {
        "files": case["files"],
        "retrieved_context": "",
        "bug_review": None,
        "security_review": None,
        "performance_review": None,
        "maintainability_review": None,
        "testing_review": None,
        "final_review": None,
    }

    result = await review_graph.ainvoke(initial_state)

    final_review = result["final_review"]

    actual_categories = {
        issue.category.value
        for issue in final_review.issues
    }

    required_categories = set(
        case["expected"]["required_categories"]
    )

    allowed_categories = set(
        case["expected"]["allowed_categories"]
    )

    # Required category was detected
    true_positives = required_categories & actual_categories

    # Required category was not detected
    false_negatives = required_categories - actual_categories

    # AI reported a category that is not allowed
    false_positives = actual_categories - allowed_categories

    tp = len(true_positives)
    fp = len(false_positives)
    fn = len(false_negatives)

    precision = (
        tp / (tp + fp)
        if (tp + fp) > 0
        else 0
    )

    recall = (
        tp / (tp + fn)
        if (tp + fn) > 0
        else 0
    )

    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0
    )

    return {
        "name": case["name"],
        "required": required_categories,
        "allowed": allowed_categories,
        "actual": actual_categories,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }
