# Vulture whitelist (false positives)
# Items that vulture marks as unused but are actually used

# TokenStats is used for type hints and session stats
from reviewbot.llm_client import TokenStats

# Dataclass fields are used internally
_ = TokenStats.prompt_tokens
_ = TokenStats.completion_tokens
_ = TokenStats.total_tokens
_ = TokenStats.requests_count
