import json
import sys
import time
import urllib.error
import urllib.request
from collections import Counter


LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
REFERER_URL = "https://leetcode.com/problem-list/math/"
PAGE_SIZE = 100
MATH_TOPIC_SLUG = "math"


QUERY = """
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


def build_filters():
    return {
        "filterCombineType": "ALL",
        "statusFilter": {"questionStatuses": [], "operator": "IS"},
        "difficultyFilter": {"difficulties": [], "operator": "IS"},
        "languageFilter": {"languageSlugs": [], "operator": "IS"},
        "topicFilter": {"topicSlugs": [MATH_TOPIC_SLUG], "operator": "IS"},
        "acceptanceFilter": {},
        "frequencyFilter": {},
        "frontendIdFilter": {},
        "lastSubmittedFilter": {},
        "publishedFilter": {},
        "companyFilter": {"companySlugs": [], "operator": "IS"},
        "positionFilter": {"positionSlugs": [], "operator": "IS"},
        "contestPointFilter": {"contestPoints": [], "operator": "IS"},
        "premiumFilter": {"premiumStatus": [], "operator": "IS"},
    }


def fetch_page(skip, limit):
    payload = {
        "operationName": "problemsetQuestionListV2",
        "query": QUERY,
        "variables": {
            "categorySlug": "all-code-essentials",
            "skip": skip,
            "limit": limit,
            "searchKeyword": "",
            "sortBy": {"sortField": "CUSTOM", "sortOrder": "ASCENDING"},
            "filters": build_filters(),
        },
    }

    request = urllib.request.Request(
        LEETCODE_GRAPHQL_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Origin": "https://leetcode.com",
            "Referer": REFERER_URL,
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LeetCode returned HTTP {error.code}:\n{message}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not reach LeetCode: {error}") from error


def fetch_math_questions():
    questions = []
    total = None
    skip = 0

    while True:
        data = fetch_page(skip=skip, limit=PAGE_SIZE)

        if data.get("errors"):
            raise RuntimeError(json.dumps(data["errors"], indent=2))

        question_list = data.get("data", {}).get("problemsetQuestionListV2")
        if not question_list:
            raise RuntimeError("LeetCode response did not contain problemsetQuestionListV2.")

        page_questions = question_list.get("questions", [])
        total = question_list.get("totalLength", total)
        questions.extend(page_questions)

        if not question_list.get("hasMore") or not page_questions:
            return total, questions

        skip += len(page_questions)
        time.sleep(0.2)


def count_math_topic_combinations(questions):
    combo_count = Counter()
    math_only_count = 0

    for question in questions:
        tags = question.get("topicTags", [])
        has_math = any(tag.get("slug") == MATH_TOPIC_SLUG for tag in tags)

        if not has_math:
            continue

        other_topics = sorted(
            {
                tag.get("name", "").strip()
                for tag in tags
                if tag.get("slug") != MATH_TOPIC_SLUG and tag.get("name")
            }
        )

        if not other_topics:
            math_only_count += 1
            continue

        for topic in other_topics:
            combo_count[f"Math + {topic}"] += 1

    return combo_count, math_only_count


def main():
    try:
        expected_total, questions = fetch_math_questions()
        combo_count, math_only_count = count_math_topic_combinations(questions)
    except RuntimeError as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        sys.exit(1)

    print(f"\nTOTAL MATH QUESTIONS REPORTED BY LEETCODE : {expected_total}")
    print(f"TOTAL MATH QUESTIONS FETCHED              : {len(questions)}")
    print(f"MATH ONLY QUESTIONS                       : {math_only_count}")
    print("\nMATH + OTHER TOPICS DISTRIBUTION\n")

    for combo, count in sorted(combo_count.items(), key=lambda item: (-item[1], item[0])):
        print(f"{combo:<45} : {count}")


if __name__ == "__main__":
    main()
