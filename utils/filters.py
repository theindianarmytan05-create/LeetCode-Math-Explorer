from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


DIFFICULTY_ORDER = {
    "Hard": 0,
    "Medium": 1,
    "Easy": 2,
    "Unknown": 3,
}

MATH_TOPIC_NAME = "Math"

SCRAPER_CATEGORY_ORDER = [
    "Math Only",
    "Math + Array",
    "Math + Dynamic Programming",
    "Math + String",
    "Math + Hash Table",
    "Math + Number Theory",
    "Math + Greedy",
    "Math + Sorting",
    "Math + Combinatorics",
    "Math + Bit Manipulation",
    "Math + Enumeration",
    "Math + Geometry",
    "Math + Simulation",
    "Math + Binary Search",
    "Math + Counting",
    "Math + Game Theory",
    "Math + Prefix Sum",
    "Math + Recursion",
    "Math + Backtracking",
    "Math + Matrix",
    "Math + Heap (Priority Queue)",
    "Math + Stack",
    "Math + Two Pointers",
    "Math + Brainteaser",
    "Math + Memoization",
    "Math + Depth-First Search",
    "Math + Randomized",
    "Math + Tree",
    "Math + Bitmask",
    "Math + Sliding Window",
    "Math + Breadth-First Search",
    "Math + Segment Tree",
    "Math + Linked List",
    "Math + Union-Find",
    "Math + Divide and Conquer",
    "Math + Graph Theory",
    "Math + Probability and Statistics",
    "Math + Design",
    "Math + Binary Tree",
    "Math + Binary Indexed Tree",
    "Math + Ordered Set",
    "Math + Reservoir Sampling",
    "Math + Interactive",
    "Math + Monotonic Stack",
    "Math + Topological Sort",
    "Math + Binary Search Tree",
    "Math + Queue",
    "Math + Rejection Sampling",
    "Math + Sweep Line",
    "Math + Data Stream",
    "Math + Monotonic Queue",
    "Math + Quickselect",
    "Math + Shortest Path",
    "Math + String Matching",
]


def all_topics(questions: Iterable[Dict[str, Any]]) -> List[str]:
    topics = set()
    for question in questions:
        topics.update(question.get("topics") or [])
    return sorted(topics)


def math_category_labels(question: Dict[str, Any]) -> List[str]:
    other_topics = sorted(
        {
            topic
            for topic in question.get("topics") or []
            if topic.strip().lower() != MATH_TOPIC_NAME.lower()
        }
    )
    if not other_topics:
        return ["Math Only"]
    return [f"Math + {topic}" for topic in other_topics]


def build_math_categories(questions: Iterable[Dict[str, Any]]) -> List[Tuple[str, List[Dict[str, Any]]]]:
    categories: Dict[str, List[Dict[str, Any]]] = {}

    for question in questions:
        for label in math_category_labels(question):
            categories.setdefault(label, []).append(question)

    ordered_categories = [
        (label, categories[label])
        for label in SCRAPER_CATEGORY_ORDER
        if label in categories
    ]
    extra_categories = sorted(
        (label, questions)
        for label, questions in categories.items()
        if label not in SCRAPER_CATEGORY_ORDER
    )
    return ordered_categories + extra_categories


def question_matches_search(question: Dict[str, Any], search_text: str) -> bool:
    if not search_text.strip():
        return True

    haystack = " ".join(
        [
            str(question.get("question_id") or ""),
            str(question.get("title") or ""),
            str(question.get("title_slug") or ""),
            " ".join(question.get("topics") or []),
            " ".join(question.get("topic_slugs") or []),
        ]
    ).lower()

    tokens = [token.strip().lower() for token in search_text.split() if token.strip()]
    return all(token in haystack for token in tokens)


def acceptance_matches(
    question: Dict[str, Any],
    acceptance_mode: str,
    acceptance_range: Tuple[float, float],
    above_value: float,
    below_value: float,
) -> bool:
    rate = question.get("acceptance_rate")
    if rate is None:
        return acceptance_range[0] <= 0 and acceptance_range[1] >= 100

    if acceptance_mode == "Above":
        return rate >= above_value
    if acceptance_mode == "Below":
        return rate <= below_value
    return acceptance_range[0] <= rate <= acceptance_range[1]


def topic_matches(question: Dict[str, Any], selected_topics: Sequence[str], topic_mode: str) -> bool:
    if not selected_topics:
        return True
    question_topics = set(question.get("topics") or [])
    selected = set(selected_topics)
    if topic_mode == "All selected topics":
        return selected.issubset(question_topics)
    return bool(question_topics & selected)


def progress_matches(
    question: Dict[str, Any],
    user_state: Dict[str, List[str]],
    progress_filter: str,
) -> bool:
    title_slug = question.get("title_slug")
    favorites = set(user_state.get("favorites") or [])
    solved = set(user_state.get("solved") or [])

    if progress_filter == "Favorites only":
        return title_slug in favorites
    if progress_filter in {"Solved only", "Finished only"}:
        return title_slug in solved
    if progress_filter in {"Unsolved only", "Not finished only"}:
        return title_slug not in solved
    return True


def premium_matches(question: Dict[str, Any], premium_filter: str) -> bool:
    is_premium = bool(question.get("premium"))
    if premium_filter == "Free only":
        return not is_premium
    if premium_filter == "Premium only":
        return is_premium
    return True


def filter_questions(
    questions: Iterable[Dict[str, Any]],
    difficulties: Sequence[str],
    acceptance_mode: str,
    acceptance_range: Tuple[float, float],
    above_value: float,
    below_value: float,
    selected_topics: Sequence[str],
    topic_mode: str,
    search_text: str,
    premium_filter: str,
    progress_filter: str,
    user_state: Dict[str, List[str]],
) -> List[Dict[str, Any]]:
    selected_difficulties = set(difficulties)
    filtered = []

    for question in questions:
        if selected_difficulties and question.get("difficulty") not in selected_difficulties:
            continue
        if not acceptance_matches(question, acceptance_mode, acceptance_range, above_value, below_value):
            continue
        if not topic_matches(question, selected_topics, topic_mode):
            continue
        if not question_matches_search(question, search_text):
            continue
        if not premium_matches(question, premium_filter):
            continue
        if not progress_matches(question, user_state, progress_filter):
            continue
        filtered.append(question)

    return filtered


def question_id_sort_key(question: Dict[str, Any]) -> Tuple[int, Any]:
    value = str(question.get("question_id") or "").strip()
    try:
        return 0, int(value)
    except ValueError:
        return 1, value


def sort_questions(
    questions: Iterable[Dict[str, Any]],
    sort_by: str,
    ascending: bool = True,
    difficulty_direction: str = "Hard -> Easy",
) -> List[Dict[str, Any]]:
    questions = list(questions)

    if sort_by == "Difficulty":
        if difficulty_direction == "Easy -> Hard":
            order = {"Easy": 0, "Medium": 1, "Hard": 2, "Unknown": 3}
        else:
            order = DIFFICULTY_ORDER
        return sorted(
            questions,
            key=lambda question: (
                order.get(question.get("difficulty"), 3),
                question_id_sort_key(question),
                question.get("title", ""),
            ),
        )

    if sort_by == "Acceptance rate":
        return sorted(
            questions,
            key=lambda question: (
                question.get("acceptance_rate") is None,
                question.get("acceptance_rate") if question.get("acceptance_rate") is not None else -1,
            ),
            reverse=not ascending,
        )

    if sort_by == "Title":
        return sorted(questions, key=lambda question: question.get("title", "").lower(), reverse=not ascending)

    if sort_by == "Question ID":
        return sorted(questions, key=question_id_sort_key, reverse=not ascending)

    return sorted(
        questions,
        key=lambda question: (
            DIFFICULTY_ORDER.get(question.get("difficulty"), 3),
            question_id_sort_key(question),
        ),
    )


def summarize_questions(questions: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    questions = list(questions)
    rates = [question["acceptance_rate"] for question in questions if question.get("acceptance_rate") is not None]
    return {
        "total": len(questions),
        "hard": sum(1 for question in questions if question.get("difficulty") == "Hard"),
        "medium": sum(1 for question in questions if question.get("difficulty") == "Medium"),
        "easy": sum(1 for question in questions if question.get("difficulty") == "Easy"),
        "average_acceptance": round(sum(rates) / len(rates), 2) if rates else None,
    }
