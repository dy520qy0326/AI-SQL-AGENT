from app.ai.client import AIClient, AIServiceError
from app.ai.prompts import (
    COMMENT_COMPLETION_SYSTEM,
    COMMENT_COMPLETION_USER,
    NL_QUERY_SYSTEM,
    PROJECT_SUMMARY_SYSTEM,
    PROJECT_SUMMARY_USER,
    RELATION_COMPLETION_SYSTEM,
    RELATION_COMPLETION_USER,
    TABLE_DESCRIPTION_SYSTEM,
    TABLE_DESCRIPTION_USER,
)
from app.ai.cache import clear_all_cache, get_cached, set_cache
from app.ai.service import (
    complete_comments,
    complete_relations,
    generate_project_summary,
    generate_table_descriptions,
)

__all__ = [
    "AIClient",
    "AIServiceError",
    "RELATION_COMPLETION_SYSTEM",
    "RELATION_COMPLETION_USER",
    "COMMENT_COMPLETION_SYSTEM",
    "COMMENT_COMPLETION_USER",
    "TABLE_DESCRIPTION_SYSTEM",
    "TABLE_DESCRIPTION_USER",
    "PROJECT_SUMMARY_SYSTEM",
    "PROJECT_SUMMARY_USER",
    "NL_QUERY_SYSTEM",
    "get_cached",
    "set_cache",
    "clear_all_cache",
    "complete_relations",
    "complete_comments",
    "generate_table_descriptions",
    "generate_project_summary",
]
