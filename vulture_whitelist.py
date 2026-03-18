# Vulture whitelist (false positives)
# Items that vulture marks as unused but are actually used

# TokenStats is used for type hints and session stats
from reviewbot.llm_client import TokenStats

# Dataclass fields are used internally
TokenStats.prompt_tokens
TokenStats.completion_tokens
TokenStats.total_tokens
TokenStats.requests_count
