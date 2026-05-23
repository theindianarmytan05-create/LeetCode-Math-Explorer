import inspect
from html import escape
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import streamlit as st


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 2rem;
        }
        h1 {
            color: #172554;
        }
        .progress-panel {
            border: 1px solid rgba(15, 23, 42, 0.12);
            border-radius: 0.65rem;
            padding: 0.85rem;
            margin: 0.75rem 0 1rem 0;
            background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 52%, #ecfeff 100%);
        }
        .progress-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(120px, 1fr));
            gap: 0.65rem;
        }
        .progress-card {
            border: 1px solid rgba(15, 23, 42, 0.1);
            border-radius: 0.55rem;
            padding: 0.75rem;
            background: rgba(255, 255, 255, 0.78);
        }
        .progress-label {
            color: #475569;
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
        }
        .progress-value {
            color: #0f172a;
            font-size: 1.7rem;
            font-weight: 800;
            line-height: 1.15;
        }
        .progress-bar {
            height: 0.55rem;
            margin-top: 0.85rem;
            overflow: hidden;
            border-radius: 999px;
            background: rgba(15, 23, 42, 0.12);
        }
        .progress-fill {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #2563eb, #0891b2);
        }
        .category-nav {
            position: sticky;
            top: 0;
            z-index: 20;
            display: flex;
            gap: 0.45rem;
            overflow-x: auto;
            padding: 0.55rem 0.15rem 0.7rem 0.15rem;
            margin: 0.3rem 0 0.9rem 0;
            background: rgba(255, 255, 255, 0.92);
            backdrop-filter: blur(8px);
            border-bottom: 1px solid rgba(15, 23, 42, 0.08);
        }
        .category-nav-chip {
            flex: 0 0 auto;
            display: inline-block;
            padding: 0.38rem 0.65rem;
            border-radius: 999px;
            color: #0f172a !important;
            background: #e0f2fe;
            border: 1px solid #bae6fd;
            font-size: 0.82rem;
            font-weight: 700;
            text-decoration: none !important;
        }
        .category-heading {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.55rem;
            scroll-margin-top: 5.25rem;
            margin-top: 1rem;
            margin-bottom: 0.65rem;
            padding: 0.75rem 0.9rem;
            border-radius: 0.65rem;
            color: #ffffff;
            background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 58%, #0891b2 100%);
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.16);
        }
        .category-heading-title {
            color: #ffffff;
            font-size: 1.22rem;
            font-weight: 850;
            line-height: 1.2;
        }
        .category-count {
            border-radius: 999px;
            padding: 0.22rem 0.58rem;
            background: rgba(255, 255, 255, 0.92);
            color: #0f172a;
            font-size: 0.8rem;
            font-weight: 800;
            white-space: nowrap;
        }
        .question-title {
            font-size: 1.03rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }
        .muted {
            color: #667085;
            font-size: 0.88rem;
        }
        .badge {
            display: inline-block;
            padding: 0.18rem 0.5rem;
            margin: 0.08rem 0.16rem 0.08rem 0;
            border-radius: 0.35rem;
            font-size: 0.78rem;
            font-weight: 700;
            line-height: 1.2;
            border: 1px solid rgba(0, 0, 0, 0.08);
        }
        .badge-hard {
            color: #991b1b;
            background: #fee2e2;
        }
        .badge-medium {
            color: #854d0e;
            background: #fef3c7;
        }
        .badge-easy {
            color: #166534;
            background: #dcfce7;
        }
        .badge-neutral {
            color: #344054;
            background: #f2f4f7;
        }
        .badge-premium {
            color: #7c2d12;
            background: #ffedd5;
        }
        .topic-chip {
            display: inline-block;
            padding: 0.16rem 0.42rem;
            margin: 0.08rem 0.12rem 0.08rem 0;
            border-radius: 0.32rem;
            font-size: 0.75rem;
            background: #eef2ff;
            color: #3730a3;
            border: 1px solid #c7d2fe;
        }
        .status-chip {
            display: inline-block;
            padding: 0.16rem 0.42rem;
            margin: 0.08rem 0.12rem 0.08rem 0;
            border-radius: 0.32rem;
            font-size: 0.75rem;
            background: #ecfeff;
            color: #155e75;
            border: 1px solid #a5f3fc;
        }
        .category-table-wrap {
            overflow-x: auto;
            margin: 0.35rem 0 1.2rem 0;
            border: 1px solid rgba(15, 23, 42, 0.1);
            border-radius: 0.55rem;
        }
        .category-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }
        .category-table th,
        .category-table td {
            border-bottom: 1px solid rgba(128, 128, 128, 0.24);
            padding: 0.48rem 0.55rem;
            text-align: left;
            vertical-align: top;
        }
        .category-table th {
            font-weight: 700;
            background: #f8fafc;
        }
        .category-table td.number-cell {
            white-space: nowrap;
            width: 5rem;
        }
        .category-table td.small-cell {
            white-space: nowrap;
            width: 7rem;
        }
        .finish-badge {
            display: inline-block;
            border-radius: 999px;
            padding: 0.18rem 0.48rem;
            font-size: 0.78rem;
            font-weight: 800;
        }
        .finish-done {
            background: #dcfce7;
            color: #166534;
        }
        .finish-left {
            background: #fee2e2;
            color: #991b1b;
        }
        @media (max-width: 900px) {
            .progress-grid {
                grid-template-columns: repeat(2, minmax(120px, 1fr));
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def safe_container(border: bool = False):
    try:
        return st.container(border=border)
    except TypeError:
        return st.container()


def format_acceptance(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}%"


def difficulty_badge(difficulty: str) -> str:
    css_class = {
        "Hard": "badge-hard",
        "Medium": "badge-medium",
        "Easy": "badge-easy",
    }.get(difficulty, "badge-neutral")
    return f'<span class="badge {css_class}">{escape(difficulty)}</span>'


def premium_badge(is_premium: bool) -> str:
    if is_premium:
        return '<span class="badge badge-premium">Premium</span>'
    return '<span class="badge badge-neutral">Free</span>'


def topic_chips(topics: Iterable[str], limit: Optional[int] = None) -> str:
    topics = list(topics or [])
    visible = topics[:limit] if limit else topics
    chips = "".join(f'<span class="topic-chip">{escape(str(topic))}</span>' for topic in visible)
    hidden_count = len(topics) - len(visible)
    if hidden_count > 0:
        chips += f'<span class="topic-chip">+{hidden_count} more</span>'
    return chips or '<span class="topic-chip">No topic tags</span>'


def state_chips(question: Dict[str, Any], user_state: Dict[str, List[str]]) -> str:
    title_slug = question.get("title_slug")
    chips = []
    if title_slug in set(user_state.get("favorites") or []):
        chips.append('<span class="status-chip">Favorite</span>')
    if title_slug in set(user_state.get("solved") or []):
        chips.append('<span class="status-chip">Finished</span>')
    return "".join(chips)


def questions_to_dataframe(questions: Iterable[Dict[str, Any]], user_state: Dict[str, List[str]]) -> pd.DataFrame:
    favorites = set(user_state.get("favorites") or [])
    solved = set(user_state.get("solved") or [])
    rows = []
    for question in questions:
        title_slug = question.get("title_slug")
        rows.append(
            {
                "ID": question.get("question_id") or "",
                "Title": question.get("title") or "",
                "Difficulty": question.get("difficulty") or "Unknown",
                "Acceptance %": question.get("acceptance_rate"),
                "Topics": ", ".join(question.get("topics") or []),
                "Premium": "Yes" if question.get("premium") else "No",
                "Favorite": "Yes" if title_slug in favorites else "No",
                "Finished": "Yes" if title_slug in solved else "No",
                "URL": question.get("url") or "",
            }
        )
    return pd.DataFrame(rows)


def render_link_button(label: str, url: str) -> None:
    if hasattr(st, "link_button"):
        st.link_button(label, url, **full_width_kwargs(st.link_button))
    else:
        st.markdown(f"[{label}]({url})")


def full_width_kwargs(streamlit_callable) -> Dict[str, Any]:
    try:
        if "width" in inspect.signature(streamlit_callable).parameters:
            return {"width": "stretch"}
    except (TypeError, ValueError):
        pass
    return {"use_container_width": True}
