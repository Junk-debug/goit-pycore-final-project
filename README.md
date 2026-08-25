# Personal Assistant

A personal assistant with a command-line interface: an address book and notes.

Final team project of the Python Programming: Foundations and Best Practices course.

## Requirements

- Python 3.10 or newer

## Installation

```bash
git clone <URL of this repository>
cd goit-pycore-final-project

python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -e .
```

Once installed, the `assistant` command is available from any directory:

```bash
assistant
```

Alternative way to run it, useful when the command is not on your `PATH`:

```bash
python -m personal_assistant
```

## Usage

The assistant runs in a loop: type a command, read the result, type `exit` to quit.
The `help` command prints the full list of available commands.

<!-- TODO: command reference table -->

## Data storage

Contacts and notes are stored in the user's home directory, under
`~/.personal_assistant/`. Data is preserved between runs.

## Development

Install the project together with the developer tools:

```bash
pip install -e ".[dev]"
```

Run the tests and the style checks:

```bash
pytest
ruff check .
ruff format .
mypy
```

### Running during development

The editable install means the `assistant` command already runs the sources in
this directory: edit a file and the next run picks it up, with no reinstall.
Reinstall only after changing `pyproject.toml`.

```bash
source .venv/bin/activate

assistant                                  # interactive session
assistant contact list                     # a single command
python -m personal_assistant               # same, without the console script
printf 'help\nexit\n' | assistant         # scripted, useful for a quick check
```

By default the assistant reads and writes `~/.personal_assistant/data.pkl`.
Point `PERSONAL_ASSISTANT_DATA` somewhere else to keep a development session
away from real data:

```bash
export PERSONAL_ASSISTANT_DATA=/tmp/assistant-dev.pkl
assistant
```

Delete that file to start from an empty state.

## Team

<!-- TODO: members and roles -->
