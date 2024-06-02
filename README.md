# Prefect Code Assistant

An AI-powered assistant that helps you write and test Prefect flows and tasks using a sandboxed Docker environment. Chat with the assistant, and it will leverage custom tools to research Prefect concepts, write Python functions, and run them safely in a Docker container.

## Requirements

- Python 3.x
- Docker

## Installation

1. Clone the repository:

```bash
git clone https://github.com/zzstoatzz/prefect-code-assistant.git
cd prefect-code-assistant
```

2. Install the required Python dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

Run the Prefect Code Assistant:

```bash
python main.py
```

Start chatting with the AI assistant. It will use the available tools to help you write and test Prefect code.

## Notes

- The assistant uses the `research_prefect` tool to provide accurate information about Prefect concepts and syntax.
- Custom Python functions are stored in the `scratchpad` directory and can be reused across sessions.
- The Docker container provides a sandboxed environment to run Python files safely.

Feel free to explore and extend the capabilities of the Prefect Code Assistant to suit your needs!