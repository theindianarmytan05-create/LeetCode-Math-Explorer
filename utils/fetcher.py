import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


try:
    from scraper import MATH_TOPIC_SLUG, build_filters
except Exception:
    MATH_TOPIC_SLUG = "math"

    def build_filters() -> Dict[str, Any]:
        return {
            "filterCombineType": "ALL",
            "topicFilter": {"topicSlugs": [MATH_TOPIC_SLUG], "operator": "IS"},
        }


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
QUESTIONS_PATH = DATA_DIR / "questions.json"
USER_STATE_PATH = DATA_DIR / "user_state.json"

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
LEETCODE_MATH_URL = "https://leetcode.com/problem-list/math/"
LEETCODE_PROBLEM_BASE = "https://leetcode.com/problems"

PAGE_SIZE = 100
REQUEST_PAUSE_SECONDS = 0.2


V2_QUERY = """
query problemsetQuestionListV2(
    $filters: QuestionFilterInput,
    $limit: Int,
    $searchKeyword: String,
    $skip: Int,
    $sortBy: QuestionSortByInput,
    $categorySlug: String
) {
    problemsetQuestionListV2(
        filters: $filters,
        limit: $limit,
        searchKeyword: $searchKeyword,
        skip: $skip,
        sortBy: $sortBy,
        categorySlug: $categorySlug
    ) {
        questions {
            acRate
            difficulty
            frontendQuestionId
            paidOnly
            title
            titleSlug
            topicTags {
                name
                slug
            }
        }
        totalLength
        hasMore
    }
}
"""


V2_ALIAS_QUERY = """
query problemsetQuestionListV2(
    $filters: QuestionFilterInput,
    $limit: Int,
    $searchKeyword: String,
    $skip: Int,
    $sortBy: QuestionSortByInput,
    $categorySlug: String
) {
    problemsetQuestionListV2(
        filters: $filters,
        limit: $limit,
        searchKeyword: $searchKeyword,
        skip: $skip,
        sortBy: $sortBy,
        categorySlug: $categorySlug
    ) {
        questions {
            acRate
            difficulty
            frontendQuestionId: questionFrontendId
            paidOnly: isPaidOnly
            title
            titleSlug
            topicTags {
                name
                slug
            }
        }
        totalLength
        hasMore
    }
}
"""


CLASSIC_QUERY = """
query problemsetQuestionList(
    $categorySlug: String,
    $limit: Int,
    $skip: Int,
    $filters: QuestionListFilterInput
) {
    problemsetQuestionList: questionList(
        categorySlug: $categorySlug,
        limit: $limit,
        skip: $skip,
        filters: $filters
    ) {
        total: totalNum
        questions: data {
            acRate
            difficulty
            frontendQuestionId: questionFrontendId
            paidOnly: isPaidOnly
            status
            title
            titleSlug
            topicTags {
                name
                slug
            }
        }
    }
}
"""


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, data: Any) -> None:
    ensure_data_dir()
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    temp_path.replace(path)


def load_cached_bundle() -> Optional[Dict[str, Any]]:
    bundle = read_json(QUESTIONS_PATH, None)
    if not isinstance(bundle, dict):
        return None
    questions = bundle.get("questions")
    if not isinstance(questions, list) or not questions:
        return None
    return bundle


def save_questions_bundle(questions: List[Dict[str, Any]], total_reported: Optional[int]) -> Dict[str, Any]:
    bundle = {
        "source": LEETCODE_MATH_URL,
        "fetched_at": now_iso(),
        "total_reported": total_reported,
        "count": len(questions),
        "questions": questions,
    }
    write_json(QUESTIONS_PATH, bundle)
    return bundle


def graphql_headers() -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://leetcode.com",
        "Referer": LEETCODE_MATH_URL,
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    }


def post_graphql(query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "query": query,
        "variables": variables,
    }
    request = urllib.request.Request(
        LEETCODE_GRAPHQL_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=graphql_headers(),
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LeetCode returned HTTP {error.code}: {message}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not reach LeetCode: {error}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError("LeetCode returned a response that was not valid JSON.") from error


def v2_variables(skip: int, limit: int) -> Dict[str, Any]:
    return {
        "categorySlug": "all-code-essentials",
        "skip": skip,
        "limit": limit,
        "searchKeyword": "",
        "sortBy": {"sortField": "CUSTOM", "sortOrder": "ASCENDING"},
        "filters": build_filters(),
    }


def classic_variables(skip: int, limit: int) -> Dict[str, Any]:
    return {
        "categorySlug": "",
        "skip": skip,
        "limit": limit,
        "filters": {"tags": [MATH_TOPIC_SLUG]},
    }


def fetch_with_v2(query: str) -> Tuple[Optional[int], List[Dict[str, Any]]]:
    questions: List[Dict[str, Any]] = []
    total_reported: Optional[int] = None
    skip = 0

    while True:
        data = post_graphql(query, v2_variables(skip=skip, limit=PAGE_SIZE))
        errors = data.get("errors")
        if errors:
            raise RuntimeError(json.dumps(errors, indent=2))

        question_list = data.get("data", {}).get("problemsetQuestionListV2")
        if not isinstance(question_list, dict):
            raise RuntimeError("LeetCode response did not include problemsetQuestionListV2.")

        page_questions = question_list.get("questions") or []
        total_reported = question_list.get("totalLength", total_reported)
        questions.extend(page_questions)

        has_more = bool(question_list.get("hasMore"))
        if not has_more or not page_questions:
            return total_reported, questions

        skip += len(page_questions)
        time.sleep(REQUEST_PAUSE_SECONDS)


def fetch_with_classic_query() -> Tuple[Optional[int], List[Dict[str, Any]]]:
    questions: List[Dict[str, Any]] = []
    total_reported: Optional[int] = None
    skip = 0

    while True:
        data = post_graphql(CLASSIC_QUERY, classic_variables(skip=skip, limit=PAGE_SIZE))
        errors = data.get("errors")
        if errors:
            raise RuntimeError(json.dumps(errors, indent=2))

        question_list = data.get("data", {}).get("problemsetQuestionList")
        if not isinstance(question_list, dict):
            raise RuntimeError("LeetCode response did not include problemsetQuestionList.")

        page_questions = question_list.get("questions") or []
        total_reported = question_list.get("total", total_reported)
        questions.extend(page_questions)

        skip += len(page_questions)
        if not page_questions or (total_reported is not None and skip >= int(total_reported)):
            return total_reported, questions

        time.sleep(REQUEST_PAUSE_SECONDS)


def parse_acceptance_rate(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return round(float(str(value).replace("%", "").strip()), 2)
    except (TypeError, ValueError):
        return None


def normalize_topics(topic_tags: Iterable[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    topics = []
    slugs = []
    for tag in topic_tags or []:
        name = str(tag.get("name") or "").strip()
        slug = str(tag.get("slug") or "").strip()
        if name and name not in topics:
            topics.append(name)
        if slug and slug not in slugs:
            slugs.append(slug)
    return sorted(topics), sorted(slugs)


def normalize_question(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    title = str(raw.get("title") or "").strip()
    title_slug = str(raw.get("titleSlug") or "").strip()
    if not title or not title_slug:
        return None

    topics, topic_slugs = normalize_topics(raw.get("topicTags") or [])
    question_id = (
        raw.get("frontendQuestionId")
        or raw.get("questionFrontendId")
        or raw.get("questionId")
        or ""
    )

    return {
        "question_id": str(question_id).strip(),
        "title": title,
        "title_slug": title_slug,
        "difficulty": str(raw.get("difficulty") or "Unknown").strip() or "Unknown",
        "acceptance_rate": parse_acceptance_rate(raw.get("acRate")),
        "url": f"{LEETCODE_PROBLEM_BASE}/{title_slug}/",
        "topics": topics,
        "topic_slugs": topic_slugs,
        "premium": bool(raw.get("paidOnly") or raw.get("isPaidOnly")),
    }


def normalize_and_dedupe(raw_questions: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: Dict[str, Dict[str, Any]] = {}
    for raw in raw_questions:
        normalized = normalize_question(raw)
        if not normalized:
            continue
        key = normalized["title_slug"] or normalized["question_id"] or normalized["title"]
        deduped[key] = normalized
    return list(deduped.values())


def fetch_all_math_questions() -> Tuple[Optional[int], List[Dict[str, Any]], str]:
    attempts = [
        ("LeetCode problem-list v2", lambda: fetch_with_v2(V2_QUERY)),
        ("LeetCode problem-list v2 aliases", lambda: fetch_with_v2(V2_ALIAS_QUERY)),
        ("LeetCode classic questionList", fetch_with_classic_query),
    ]
    errors = []

    for label, fetcher in attempts:
        try:
            total_reported, raw_questions = fetcher()
            questions = normalize_and_dedupe(raw_questions)
            if questions:
                return total_reported, questions, label
            errors.append(f"{label}: returned no questions")
        except RuntimeError as error:
            errors.append(f"{label}: {error}")

    raise RuntimeError("Could not fetch math questions.\n\n" + "\n\n".join(errors))


def get_questions(force_refresh: bool = False) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    cached_bundle = load_cached_bundle()
    if cached_bundle and not force_refresh:
        meta = {
            "loaded_from": "cache",
            "fetched_at": cached_bundle.get("fetched_at"),
            "total_reported": cached_bundle.get("total_reported"),
            "count": cached_bundle.get("count", len(cached_bundle["questions"])),
            "path": str(QUESTIONS_PATH),
            "warning": None,
        }
        return cached_bundle["questions"], meta

    try:
        total_reported, questions, fetch_method = fetch_all_math_questions()
        bundle = save_questions_bundle(questions, total_reported)
        meta = {
            "loaded_from": "network",
            "fetch_method": fetch_method,
            "fetched_at": bundle["fetched_at"],
            "total_reported": total_reported,
            "count": len(questions),
            "path": str(QUESTIONS_PATH),
            "warning": None,
        }
        return questions, meta
    except RuntimeError as error:
        if cached_bundle:
            meta = {
                "loaded_from": "cache",
                "fetched_at": cached_bundle.get("fetched_at"),
                "total_reported": cached_bundle.get("total_reported"),
                "count": cached_bundle.get("count", len(cached_bundle["questions"])),
                "path": str(QUESTIONS_PATH),
                "warning": str(error),
            }
            return cached_bundle["questions"], meta
        raise


def load_user_state() -> Dict[str, List[str]]:
    state = read_json(USER_STATE_PATH, {})
    if not isinstance(state, dict):
        state = {}
    return {
        "favorites": sorted(set(state.get("favorites") or [])),
        "solved": sorted(set(state.get("solved") or [])),
    }


def save_user_state(state: Dict[str, Iterable[str]]) -> Dict[str, List[str]]:
    normalized = {
        "favorites": sorted(set(state.get("favorites") or [])),
        "solved": sorted(set(state.get("solved") or [])),
    }
    write_json(USER_STATE_PATH, normalized)
    return normalized


def toggle_state_item(state: Dict[str, List[str]], collection: str, title_slug: str) -> Dict[str, List[str]]:
    values = set(state.get(collection) or [])
    if title_slug in values:
        values.remove(title_slug)
    else:
        values.add(title_slug)
    state[collection] = sorted(values)
    return save_user_state(state)
