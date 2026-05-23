import json
import math
import re
from collections import Counter
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from utils.fetcher import (
    DATA_DIR,
    QUESTIONS_PATH,
    ensure_data_dir,
    get_questions,
    load_user_state,
    save_user_state,
    toggle_state_item,
)
from utils.filters import (
    all_topics,
    build_math_categories,
    filter_questions,
    sort_questions,
    summarize_questions,
)
from utils.ui_helpers import (
    difficulty_badge,
    format_acceptance,
    full_width_kwargs,
    inject_css,
    premium_badge,
    questions_to_dataframe,
    render_link_button,
    safe_container,
    state_chips,
    topic_chips,
)


APP_DIR = Path(__file__).resolve().parent
DIFFICULTIES = ["Hard", "Medium", "Easy"]


def rerun_app() -> None:
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def load_questions_for_app(force_refresh: bool = False):
    with st.spinner("Loading LeetCode math questions..."):
        questions, meta = get_questions(force_refresh=force_refresh)
    st.session_state["questions"] = questions
    st.session_state["questions_meta"] = meta
    return questions, meta


def init_state() -> None:
    ensure_data_dir()
    if "user_state" not in st.session_state:
        st.session_state["user_state"] = load_user_state()


def slugify_text(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "section"


def set_question_finished(title_slug: str, finished: bool) -> None:
    user_state = st.session_state.get("user_state", load_user_state())
    solved = set(user_state.get("solved") or [])
    if finished:
        solved.add(title_slug)
    else:
        solved.discard(title_slug)
    user_state["solved"] = sorted(solved)
    st.session_state["user_state"] = save_user_state(user_state)


def apply_finished_editor_changes(editor_key: str, row_slugs: list) -> None:
    editor_state = st.session_state.get(editor_key, {})
    edited_rows = editor_state.get("edited_rows", {}) if isinstance(editor_state, dict) else {}
    if not edited_rows:
        return

    user_state = st.session_state.get("user_state", load_user_state())
    solved = set(user_state.get("solved") or [])

    for row_index, changes in edited_rows.items():
        if "Finished" not in changes:
            continue
        try:
            title_slug = row_slugs[int(row_index)]
        except (IndexError, TypeError, ValueError):
            continue
        if changes["Finished"]:
            solved.add(title_slug)
        else:
            solved.discard(title_slug)

    user_state["solved"] = sorted(solved)
    st.session_state["user_state"] = save_user_state(user_state)


def render_data_status(meta: dict) -> None:
    fetched_at = meta.get("fetched_at") or "unknown"
    loaded_from = meta.get("loaded_from", "unknown")
    count = meta.get("count", 0)

    st.caption(f"Loaded {count} questions from {loaded_from}. Last fetch: {fetched_at}")
    if meta.get("warning"):
        st.warning(
            "LeetCode refresh failed, so the app is using the local cache.\n\n"
            f"{meta['warning']}"
        )

    with st.expander("Cache details", expanded=False):
        st.write(f"Data folder: `{DATA_DIR}`")
        st.write(f"Questions cache: `{QUESTIONS_PATH}`")
        st.write(f"Reported by LeetCode: `{meta.get('total_reported')}`")
        if meta.get("fetch_method"):
            st.write(f"Fetch method: `{meta.get('fetch_method')}`")


def render_metrics(questions: list, filtered_questions: list, user_state: dict) -> None:
    summary = summarize_questions(questions)
    filtered_summary = summarize_questions(filtered_questions)
    solved = set(user_state.get("solved") or [])
    question_slugs = {question.get("title_slug") for question in questions if question.get("title_slug")}
    filtered_slugs = {
        question.get("title_slug")
        for question in filtered_questions
        if question.get("title_slug")
    }
    finished_count = len(question_slugs & solved)
    left_count = max(len(question_slugs) - finished_count, 0)
    visible_left_count = len(filtered_slugs - solved)
    progress_percent = round((finished_count / len(question_slugs)) * 100, 1) if question_slugs else 0

    st.markdown(
        f"""
        <div class="progress-panel">
            <div class="progress-grid">
                <div class="progress-card">
                    <div class="progress-label">Left</div>
                    <div class="progress-value">{left_count}</div>
                </div>
                <div class="progress-card">
                    <div class="progress-label">Finished</div>
                    <div class="progress-value">{finished_count}</div>
                </div>
                <div class="progress-card">
                    <div class="progress-label">Visible Left</div>
                    <div class="progress-value">{visible_left_count}</div>
                </div>
                <div class="progress-card">
                    <div class="progress-label">Progress</div>
                    <div class="progress-value">{progress_percent}%</div>
                </div>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {progress_percent}%;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    columns = st.columns(5)
    columns[0].metric("Total questions", summary["total"])
    columns[1].metric("Hard", summary["hard"])
    columns[2].metric("Medium", summary["medium"])
    columns[3].metric("Easy", summary["easy"])
    avg_acceptance = summary["average_acceptance"]
    columns[4].metric("Avg acceptance", format_acceptance(avg_acceptance))

    st.caption(
        "Showing "
        f"{filtered_summary['total']} questions after filters "
        f"({filtered_summary['hard']} Hard, {filtered_summary['medium']} Medium, "
        f"{filtered_summary['easy']} Easy)."
    )


def render_question_actions(question: dict, user_state: dict, key_prefix: str) -> None:
    title_slug = question["title_slug"]
    favorites = set(user_state.get("favorites") or [])
    solved = set(user_state.get("solved") or [])

    action_columns = st.columns([1.2, 1.2, 1.2, 4])
    with action_columns[0]:
        render_link_button("Open", question["url"])
    with action_columns[1]:
        favorite_label = "Remove favorite" if title_slug in favorites else "Add favorite"
        if st.button(favorite_label, key=f"{key_prefix}_favorite", **full_width_kwargs(st.button)):
            st.session_state["user_state"] = toggle_state_item(user_state, "favorites", title_slug)
            rerun_app()
    with action_columns[2]:
        solved_label = "Mark not finished" if title_slug in solved else "Mark finished"
        if st.button(solved_label, key=f"{key_prefix}_solved", **full_width_kwargs(st.button)):
            st.session_state["user_state"] = toggle_state_item(user_state, "solved", title_slug)
            rerun_app()


def render_question_card(question: dict, index: int, user_state: dict) -> None:
    question_id = escape(question.get("question_id") or "?")
    title = escape(question.get("title") or "")
    url = question.get("url") or ""
    acceptance = format_acceptance(question.get("acceptance_rate"))
    difficulty = question.get("difficulty") or "Unknown"
    key_prefix = f"{question.get('title_slug')}_{index}"

    with safe_container(border=True):
        title_html = (
            f'<div class="question-title">{question_id}. '
            f'<a href="{url}" target="_blank">{title}</a></div>'
        )
        st.markdown(title_html, unsafe_allow_html=True)
        st.markdown(
            difficulty_badge(difficulty)
            + premium_badge(bool(question.get("premium")))
            + state_chips(question, user_state),
            unsafe_allow_html=True,
        )

        detail_columns = st.columns([1.2, 4])
        detail_columns[0].markdown(f"**Acceptance**  \n{acceptance}")
        detail_columns[1].markdown(topic_chips(question.get("topics") or [], limit=9), unsafe_allow_html=True)

        render_question_actions(question, user_state, key_prefix)

        with st.expander("Details", expanded=False):
            st.write(f"Slug: `{question.get('title_slug')}`")
            st.write(f"Direct URL: {url}")
            st.markdown(topic_chips(question.get("topics") or []), unsafe_allow_html=True)


def render_cards_tab(sorted_questions: list, user_state: dict) -> None:
    if not sorted_questions:
        st.info("No questions match the current filters.")
        return

    page_size = st.session_state.get("cards_per_page", 25)
    total_pages = max(1, math.ceil(len(sorted_questions) / page_size))
    if st.session_state.get("page_number", 1) > total_pages:
        st.session_state["page_number"] = 1

    top_columns = st.columns([1, 1, 4])
    with top_columns[0]:
        page_number = st.number_input(
            "Page",
            min_value=1,
            max_value=total_pages,
            value=st.session_state.get("page_number", 1),
            step=1,
            key="page_number",
        )
    with top_columns[1]:
        st.metric("Pages", total_pages)

    start = (page_number - 1) * page_size
    end = start + page_size
    page_questions = sorted_questions[start:end]
    st.caption(f"Showing questions {start + 1}-{min(end, len(sorted_questions))} of {len(sorted_questions)}.")

    for index, question in enumerate(page_questions, start=start + 1):
        render_question_card(question, index, user_state)


def render_table_tab(sorted_questions: list, user_state: dict) -> None:
    dataframe = questions_to_dataframe(sorted_questions, user_state)
    if dataframe.empty:
        st.info("No table rows match the current filters.")
        return

    column_config = None
    if hasattr(st, "column_config"):
        column_config = {
            "URL": st.column_config.LinkColumn("Question Link", display_text="Open"),
            "Acceptance %": st.column_config.NumberColumn("Acceptance %", format="%.2f"),
        }

    st.dataframe(
        dataframe,
        hide_index=True,
        column_config=column_config,
        **full_width_kwargs(st.dataframe),
    )

    csv_data = dataframe.to_csv(index=False).encode("utf-8")
    json_data = json.dumps(sorted_questions, indent=2, ensure_ascii=False).encode("utf-8")
    download_columns = st.columns(2)
    download_columns[0].download_button(
        "Download CSV",
        data=csv_data,
        file_name="leetcode_math_questions_filtered.csv",
        mime="text/csv",
        **full_width_kwargs(st.download_button),
    )
    download_columns[1].download_button(
        "Download JSON",
        data=json_data,
        file_name="leetcode_math_questions_filtered.json",
        mime="application/json",
        **full_width_kwargs(st.download_button),
    )


def render_category_questions_table(questions: list, user_state: dict, category_label: str) -> None:
    if not questions:
        st.info("No questions in this category.")
        return

    solved = set(user_state.get("solved") or [])
    rows = []
    row_slugs = []
    for question in questions:
        title_slug = question.get("title_slug")
        row_slugs.append(title_slug)
        rows.append(
            {
                "Finished": title_slug in solved,
                "Status": "Finished" if title_slug in solved else "Not finished",
                "ID": question.get("question_id") or "",
                "Title": question.get("title") or "",
                "Difficulty": question.get("difficulty") or "Unknown",
                "Acceptance %": question.get("acceptance_rate"),
                "Type": "Premium" if question.get("premium") else "Free",
                "URL": question.get("url") or "",
            }
        )

    dataframe = pd.DataFrame(rows)
    editor_key = f"finish_editor_{slugify_text(category_label)}"
    column_config = None
    if hasattr(st, "column_config"):
        column_config = {
            "Finished": st.column_config.CheckboxColumn(
                "Finished",
                help="Tick this when you finish the question.",
                default=False,
            ),
            "URL": st.column_config.LinkColumn("Open", display_text="Open"),
            "Acceptance %": st.column_config.NumberColumn("Acceptance %", format="%.2f"),
        }

    st.data_editor(
        dataframe,
        key=editor_key,
        hide_index=True,
        disabled=["Status", "ID", "Title", "Difficulty", "Acceptance %", "Type", "URL"],
        column_config=column_config,
        on_change=apply_finished_editor_changes,
        args=(editor_key, row_slugs),
        **full_width_kwargs(st.data_editor),
    )


def render_category_nav(categories: list, filtered_lookup: dict, filters_active: bool) -> None:
    links = []
    for label, all_questions in categories:
        row_count = len(filtered_lookup.get(label, [])) if filters_active else len(all_questions)
        if filters_active and row_count == 0:
            continue
        anchor = slugify_text(label)
        links.append(
            f'<a class="category-nav-chip" href="#{anchor}">{escape(label)} ({row_count})</a>'
        )

    if links:
        st.markdown(f'<div class="category-nav">{"".join(links)}</div>', unsafe_allow_html=True)


def render_category_heading(label: str, shown_count: int, total_count: int, filters_active: bool) -> None:
    anchor = slugify_text(label)
    if filters_active:
        count_text = f"{shown_count} shown / {total_count} total"
    else:
        count_text = str(total_count)
    st.markdown(
        f"""
        <div id="{anchor}" class="category-heading">
            <span class="category-heading-title">{escape(label)}</span>
            <span class="category-count">{escape(count_text)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_categories_tab(all_questions: list, filtered_sorted_questions: list, user_state: dict, filters_active: bool) -> None:
    if not all_questions:
        st.info("No categories match the current filters.")
        return

    all_categories = build_math_categories(all_questions)
    filtered_lookup = dict(build_math_categories(filtered_sorted_questions))
    render_category_nav(all_categories, filtered_lookup, filters_active)

    rendered_any_category = False
    for label, all_category_questions in all_categories:
        if filters_active:
            category_questions = filtered_lookup.get(label, [])
            if not category_questions:
                continue
        else:
            category_questions = sort_questions(all_category_questions, "Difficulty", difficulty_direction="Hard -> Easy")

        rendered_any_category = True
        render_category_heading(label, len(category_questions), len(all_category_questions), filters_active)
        render_category_questions_table(category_questions, user_state, label)
        st.divider()

    if not rendered_any_category:
        st.info("No category rows match the current filters.")


def render_analytics_tab(sorted_questions: list) -> None:
    if not sorted_questions:
        st.info("No analytics to show for the current filters.")
        return

    dataframe = questions_to_dataframe(sorted_questions, {"favorites": [], "solved": []})
    chart_columns = st.columns(2)

    with chart_columns[0]:
        difficulty_counts = (
            dataframe["Difficulty"]
            .value_counts()
            .reindex(["Hard", "Medium", "Easy", "Unknown"])
            .fillna(0)
            .astype(int)
        )
        st.subheader("Difficulty")
        st.bar_chart(difficulty_counts)

    with chart_columns[1]:
        rates = pd.to_numeric(dataframe["Acceptance %"], errors="coerce").dropna()
        st.subheader("Acceptance buckets")
        if rates.empty:
            st.info("No acceptance rates are available.")
        else:
            buckets = pd.cut(
                rates,
                bins=[0, 20, 40, 60, 80, 100],
                include_lowest=True,
                labels=["0-20", "20-40", "40-60", "60-80", "80-100"],
            )
            st.bar_chart(buckets.value_counts().sort_index())

    topic_counts = Counter()
    for question in sorted_questions:
        topic_counts.update(question.get("topics") or [])

    top_topics = pd.DataFrame(topic_counts.most_common(20), columns=["Topic", "Questions"])
    st.subheader("Top topics")
    st.dataframe(top_topics, hide_index=True, **full_width_kwargs(st.dataframe))


def sidebar_filters(questions: list, meta: dict) -> dict:
    with st.sidebar:
        st.header("Data")
        render_data_status(meta)

        st.header("Filters")
        difficulties = st.multiselect(
            "Difficulty",
            DIFFICULTIES,
            default=DIFFICULTIES,
        )

        acceptance_range = st.slider(
            "Acceptance range (%)",
            min_value=0.0,
            max_value=100.0,
            value=(0.0, 100.0),
            step=0.1,
        )
        acceptance_choice = st.selectbox(
            "Acceptance mode",
            ["Between selected range", "Above custom value", "Below custom value"],
        )
        above_value = acceptance_range[0]
        below_value = acceptance_range[1]
        acceptance_mode = "Between"
        if acceptance_choice == "Above custom value":
            acceptance_mode = "Above"
            above_value = st.number_input(
                "Minimum acceptance (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(acceptance_range[0]),
                step=0.1,
            )
        elif acceptance_choice == "Below custom value":
            acceptance_mode = "Below"
            below_value = st.number_input(
                "Maximum acceptance (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(acceptance_range[1]),
                step=0.1,
            )

        topics = all_topics(questions)
        selected_topics = st.multiselect("Topics", topics)
        topic_mode = st.radio("Topic match", ["Any selected topic", "All selected topics"])

        premium_filter = st.selectbox("Premium", ["All", "Free only", "Premium only"])
        progress_filter = st.selectbox(
            "Finish status",
            ["All", "Favorites only", "Finished only", "Not finished only"],
        )

        st.header("Sorting")
        sort_by = st.selectbox("Sort by", ["Difficulty", "Acceptance rate", "Title", "Question ID"])
        difficulty_direction = "Hard -> Easy"
        ascending = True
        if sort_by == "Difficulty":
            difficulty_direction = st.radio("Difficulty order", ["Hard -> Easy", "Easy -> Hard"])
        else:
            ascending = st.checkbox("Ascending", value=True)

        st.header("Display")
        st.select_slider("Cards per page", options=[10, 25, 50, 100], value=25, key="cards_per_page")

    return {
        "difficulties": difficulties,
        "acceptance_mode": acceptance_mode,
        "acceptance_range": acceptance_range,
        "above_value": above_value,
        "below_value": below_value,
        "selected_topics": selected_topics,
        "topic_mode": topic_mode,
        "premium_filter": premium_filter,
        "progress_filter": progress_filter,
        "sort_by": sort_by,
        "ascending": ascending,
        "difficulty_direction": difficulty_direction,
    }


def filters_are_active(filter_config: dict, search_text: str) -> bool:
    if search_text.strip():
        return True
    if set(filter_config["difficulties"]) != set(DIFFICULTIES):
        return True
    if filter_config["acceptance_mode"] != "Between":
        return True
    if tuple(filter_config["acceptance_range"]) != (0.0, 100.0):
        return True
    if filter_config["selected_topics"]:
        return True
    if filter_config["premium_filter"] != "All":
        return True
    if filter_config["progress_filter"] != "All":
        return True
    return False


def main() -> None:
    st.set_page_config(
        page_title="LeetCode Math Explorer",
        layout="wide",
    )
    init_state()
    inject_css()

    with st.sidebar:
        refresh = st.button("Refresh from LeetCode", **full_width_kwargs(st.button))

    try:
        if refresh or "questions" not in st.session_state:
            questions, meta = load_questions_for_app(force_refresh=refresh)
        else:
            questions = st.session_state["questions"]
            meta = st.session_state["questions_meta"]
    except RuntimeError as error:
        st.title("LeetCode Math Explorer")
        st.error("Could not load LeetCode math questions.")
        st.exception(error)
        st.stop()

    user_state = st.session_state["user_state"]

    st.title("LeetCode Math Explorer")
    search_text = st.text_input(
        "Search",
        placeholder="Search by title, question ID, topic, slug, or keyword",
    )

    filter_config = sidebar_filters(questions, meta)
    filtered_questions = filter_questions(
        questions=questions,
        difficulties=filter_config["difficulties"],
        acceptance_mode=filter_config["acceptance_mode"],
        acceptance_range=filter_config["acceptance_range"],
        above_value=filter_config["above_value"],
        below_value=filter_config["below_value"],
        selected_topics=filter_config["selected_topics"],
        topic_mode=filter_config["topic_mode"],
        search_text=search_text,
        premium_filter=filter_config["premium_filter"],
        progress_filter=filter_config["progress_filter"],
        user_state=user_state,
    )
    sorted_questions = sort_questions(
        filtered_questions,
        sort_by=filter_config["sort_by"],
        ascending=filter_config["ascending"],
        difficulty_direction=filter_config["difficulty_direction"],
    )

    filters_active = filters_are_active(filter_config, search_text)
    render_metrics(questions, sorted_questions, user_state)

    categories_tab, cards_tab, table_tab, analytics_tab = st.tabs(["Categories", "Cards", "Table", "Analytics"])
    with categories_tab:
        render_categories_tab(questions, sorted_questions, user_state, filters_active)
    with cards_tab:
        render_cards_tab(sorted_questions, user_state)
    with table_tab:
        render_table_tab(sorted_questions, user_state)
    with analytics_tab:
        render_analytics_tab(sorted_questions)


if __name__ == "__main__":
    main()
