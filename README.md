# RepoPilot AI

RepoPilot AI is a Phase 1 command-line prototype that retrieves a GitHub issue and asks
a locally running Qwen2.5-Coder 7B model to turn it into a practical implementation
plan. LangGraph orchestrates the planning workflow, while Ollama performs inference on
this computer without hosted-model API charges.

## Phase 1 features

- Retrieves issues with PyGithub.
- Refuses pull-request numbers, even though GitHub exposes PRs through the issues API.
- Validates a missing GitHub token before making requests.
- Uses a compiled LangGraph `StateGraph` with an explicit planning node.
- Uses LangChain's `ChatOllama` integration for local inference.
- Defaults to `qwen2.5-coder:7b` and keeps optional LangSmith tracing disabled.
- Prints friendly, actionable errors without exposing secrets or stack traces.
- Includes isolated tests for GitHub retrieval and planner graph execution; tests make
  no GitHub, OpenAI, LangSmith, or Ollama network calls.

## Requirements

- Python 3.10 or newer
- Ollama with `qwen2.5-coder:7b` installed
- A GitHub personal access token with access to the repository you want to read
- No OpenAI API key is required

## Setup (Windows PowerShell)

```powershell
cd "$HOME\Desktop\projects\repopilot-ai"
ollama pull qwen2.5-coder:7b
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and replace only the GitHub token placeholder:

```dotenv
GITHUB_TOKEN=your_github_personal_access_token
OLLAMA_MODEL=qwen2.5-coder:7b
OLLAMA_BASE_URL=http://localhost:11434
LANGSMITH_TRACING=false
```

The `.env` file is ignored by Git. Never commit real credentials.

## Planning graph

```text
GitHub issue details
        |
        v
LangGraph START
        |
        v
draft_plan node --ChatOllama--> qwen2.5-coder:7b
        |
        v
LangGraph END
        |
        v
Markdown implementation plan
```

## Run

Make sure Ollama is running, then pass a repository in `owner/name` form and a GitHub
issue number:

```powershell
python run.py openai/openai-python 123
```

The command writes status information to stderr and the Markdown implementation plan
to stdout, so you can save only the plan if desired:

```powershell
python run.py owner/repository 123 > plan.md
```

For help:

```powershell
python run.py --help
```

## Test

```powershell
python -m pytest -q
python -m compileall -q run.py src tests
```

## Project structure

```text
repopilot-ai/
|-- .env.example
|-- .gitignore
|-- README.md
|-- requirements.txt
|-- run.py
|-- src/
|   `-- repopilot/
|       |-- __init__.py
|       |-- cli.py
|       |-- errors.py
|       |-- github_service.py
|       `-- planner.py
`-- tests/
    |-- conftest.py
    |-- test_github_service.py
    `-- test_planner.py
```

## Scope

This first phase plans from issue text and metadata only. It does not clone repositories,
inspect source code, edit files, open pull requests, or push to GitHub.
