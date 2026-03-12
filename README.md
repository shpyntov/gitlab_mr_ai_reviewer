# GitLab MR AI Reviewer

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-containerized-blue.svg)](https://www.docker.com/)

**Automated AI-powered code review for GitLab Merge Requests.**

A production-ready Python service that integrates with GitLab CI to analyze merge request changes using Large Language Models (LLMs). Provides intelligent feedback on bugs, security issues, performance problems, and code quality.

## Features

- 🤖 **LLM-Powered Analysis** - Uses advanced language models to understand code context and provide meaningful feedback
- 📝 **Two Review Modes**
  - **Line Mode**: Posts inline comments on specific lines in the diff
  - **Summary Mode**: Provides a single comprehensive review summary
- 🔧 **GitLab CI Integration** - Runs automatically in merge request pipelines
- ⚙️ **Configurable** - Customize review behavior via `.reviewbot.yml`
- 🐳 **Containerized** - Docker-ready for easy deployment
- 🛡️ **Smart Deduplication** - Avoids posting duplicate comments
- 🔄 **Retry Logic** - Handles API failures gracefully

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   GitLab CI     │────▶│   ReviewBot      │────▶│   LLM Service   │
│   (MR Pipeline) │     │   (Docker)       │     │   (OpenAI API)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │                        │
         │                       ▼                        │
         │              ┌──────────────────┐              │
         │              │   GitLab API     │◀─────────────┘
         │              │   (Fetch MR)     │
         │              └──────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌──────────────────┐
│   MR Comments   │◀────│   Review Engine  │
│   (Inline/Sum)  │     │   (Analysis)     │
└─────────────────┘     └──────────────────┘
```

## Quick Start

### 1. Build the Docker Image

```bash
docker build -t reviewbot:latest .
```

### 2. Run Locally for Testing

```bash
docker run \
  -e API_KEY=your_llm_api_key \
  -e GITLAB_TOKEN=your_gitlab_token \
  -e CI_PROJECT_ID=12345 \
  -e CI_MERGE_REQUEST_IID=67 \
  -e REVIEW_MODE=line \
  reviewbot:latest
```

### 3. Integrate with GitLab CI

Copy `.gitlab-ci.yml.example` to `.gitlab-ci.yml` in your project:

```yaml
ai_code_review:
  image: reviewbot:latest
  stage: test
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  script:
    - python -m reviewbot.main
  allow_failure: true
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `API_KEY` | Yes | LLM API key |
| `GITLAB_TOKEN` | Yes | GitLab personal access token (api scope) |
| `CI_PROJECT_ID` | Yes | GitLab project ID |
| `CI_MERGE_REQUEST_IID` | Yes | Merge request IID |
| `CI_API_V4_URL` | No | GitLab API URL (default: `https://gitlab.com/api/v4`) |
| `REVIEW_MODE` | No | Review mode: `line` or `summary` (default: `line`) |
| `REVIEW_LANGUAGE` | No | Language for review comments (default: `en`). Examples: `en`, `ru`, `zh`, `es` |

### Repository Configuration (.reviewbot.yml)

Create a `.reviewbot.yml` file in your repository root to customize behavior:

```yaml
review:
  # Maximum comments per MR
  max_comments: 10

  # Language for review comments (e.g., 'en', 'ru', 'zh', 'es')
  language: en

  # Languages to review
  languages:
    - python
    - go
    - javascript
    - typescript

  # Paths to ignore
  ignore_paths:
    - migrations/
    - docs/
    - vendor/

ai:
  # Model temperature (0.0-1.0)
  temperature: 0.3

  # Max response tokens
  max_tokens: 2000

  # Model name
  model: zai-org/GLM-4.6
```

## Review Modes

### Line Mode (Default)

Posts inline comments on specific lines:

```
⚠️ Issue:
Possible None dereference when accessing user.id

💡 Suggestion:
Add null check before accessing the property
```

### Summary Mode

Posts a single comprehensive review:

```markdown
## AI Code Review Summary

### Potential Issues
- Possible null pointer in user service
- Missing input validation in API endpoint

### Improvements
- Consider using dependency injection
- Add unit tests for edge cases

### Positive Notes
- Good error handling in database layer
- Clean separation of concerns
```

## Supported Languages

- Python
- Go
- JavaScript / TypeScript
- Java
- C / C++
- Rust

## Getting GitLab Token

1. Go to **User Settings** → **Access Tokens**
2. Create a new token with `api` scope
3. Copy the token and set as `GITLAB_TOKEN` environment variable

## Local Development

### Prerequisites

- Python 3.11+
- Docker (optional)

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export API_KEY=your_key
export GITLAB_TOKEN=your_token
export CI_PROJECT_ID=12345
export CI_MERGE_REQUEST_IID=67

# Run the reviewer
python -m reviewbot.main
```

### Testing with Docker Compose

```bash
# Create .env file
cat > .env << EOF
API_KEY=your_key
GITLAB_TOKEN=your_token
CI_PROJECT_ID=12345
CI_MERGE_REQUEST_IID=67
REVIEW_MODE=line
EOF

# Run with docker-compose
docker-compose up reviewbot
```

## Project Structure

```
gitlab_mr_ai_reviwer/
├── reviewbot/
│   ├── __init__.py          # Package initialization
│   ├── main.py              # Entry point
│   ├── config_loader.py     # Configuration management
│   ├── diff_parser.py       # Diff parsing logic
│   ├── gitlab_client.py     # GitLab API client
│   ├── llm_client.py        # LLM API client
│   └── review_engine.py     # Main review orchestration
├── config/
│   └── default_config.yml   # Default configuration
├── prompts/
│   ├── line_review_prompt.md    # Line review prompt
│   └── summary_review_prompt.md # Summary review prompt
├── .reviewbot.yml.example   # Example repo config
├── .gitlab-ci.yml.example   # Example CI config
├── Dockerfile               # Container definition
├── docker-compose.yml       # Local testing
├── requirements.txt         # Python dependencies
├── README.md                # This file
└── LICENSE                  # MIT License
```

## Logging

The bot uses structured logging:

```
[INFO] Fetching MR changes
[INFO] Found 5 changed files
[INFO] Sending diff to LLM for app/service.py
[INFO] Posting comment to app/service.py:42
[INFO] Review completed successfully
```

## Error Handling

- **API Retries**: Automatic retry with exponential backoff for GitLab and LLM APIs
- **Rate Limiting**: Respects GitLab rate limits with proper wait times
- **JSON Validation**: Validates LLM responses and handles parsing errors
- **Duplicate Detection**: Prevents posting duplicate comments

## Security Considerations

- API keys are passed via environment variables only
- No sensitive data is logged
- GitLab tokens should have minimal required scope (`api`)
- Consider using CI/CD variables for secrets in GitLab

## Troubleshooting

### "Missing required environment variables"

Ensure all required environment variables are set:
```bash
export API_KEY=xxx
export GITLAB_TOKEN=xxx
export CI_PROJECT_ID=xxx
export CI_MERGE_REQUEST_IID=xxx
```

### "API_KEY is required"

The LLM API key must be set. Check the [LLM client integration](reviewbot/llm_client.py) for the expected format.

### No comments posted

Check:
1. Files match configured languages
2. Paths are not in ignore list
3. Max comments limit not reached
4. Comments are not duplicates

### Rate limiting

The bot implements automatic retry with backoff. If you hit rate limits frequently, consider:
- Increasing retry delay in configuration
- Reducing review frequency
- Using a dedicated GitLab token

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Merge Request.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests (if applicable)
5. Submit a Merge Request
