# Personal Assistant

A personal assistant with a command-line interface: an address book and notes.

Final team project of the Python Programming: Foundations and Best Practices
course.

## Requirements

- Python 3.10 or newer

## Installation

```bash
git clone https://github.com/Junk-debug/goit-pycore-final-project.git
cd goit-pycore-final-project

python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -e .
```

Once installed, the `assistant` command is available from any directory.

## Two ways to run it

Started without arguments, the assistant reads commands until you leave:

```
$ assistant
Personal assistant. Type 'help' to see the commands, 'exit' to leave.
assistant> contact add John --phone +48123456789
Added John; phones: +48123456789.
assistant> exit
Good bye!
```

Given arguments, it runs one command and exits, which is convenient in scripts:

```bash
assistant contact add John --phone +48123456789
```

Both forms accept exactly the same commands. If the `assistant` command is not
on your `PATH`, `python -m personal_assistant` does the same thing.

## Commands

Every command is written as `<entity> <action>`, with options for anything the
action does not require.

| Command | What it does |
|---------|--------------|
| `help` | List the available commands |
| `help <command>...` | Explain one command, for example `help contact add` |
| `contact add <name> [options]` | Create a contact |
| `contact show <name>` | Print one contact with all of its fields |
| `contact list [options]` | List and filter contacts |
| `contact edit <name> [options]` | Change fields of an existing contact |
| `contact delete <name>` | Remove a contact |
| `note add <text> [options]` | Write a note |
| `note show <id>` | Print one note in full |
| `note list [options]` | List notes, narrowed by the options |
| `note edit <id> [options]` | Change the text or the tags of a note |
| `note delete <id> [--force]` | Remove a note |
| `exit` | Leave the interactive session. Aliases: `quit`, `close` |
| `web` | Start the web interface (not implemented yet) |

### `contact add`

```
contact add <name> [--phone <phone>[,<phone>]] [--email <email>]
                   [--address <address>] [--birthday <DD.MM.YYYY>]
```

Only the name is required. Several phone numbers are separated by commas, and
spaces around the commas are ignored.

```bash
assistant contact add John
assistant contact add John --phone "+48123456789,+48999888777"
assistant contact add "Anna Kowalska" --birthday 12.05.1998 --address "Dluga 5, Gdansk"
```

Every value is checked as it is entered, and an invalid one is reported without
storing anything:

```
$ assistant contact add John --phone 123
'123' is not a valid phone number. Expected 9 to 15 digits, optionally starting with '+'.
```

| Field | Accepted |
|-------|----------|
| Name | Non-empty, at most 64 characters, unique in the book |
| Phone | An optional `+` followed by 9 to 15 digits; spaces, dashes, dots and brackets are ignored |
| Email | `name@domain.tld` |
| Address | Non-empty, at most 128 characters |
| Birthday | `DD.MM.YYYY`, a real date, not in the future, 1900 or later |

### `contact show`

```
contact show <name>
```

Prints one contact as a card, marking a field that is not set with a dash. The
name is matched without regard to case. `contact add` and `contact edit` print
the same card after they run, so the result of a change is always visible.

```bash
assistant contact show John
```

### `contact list`

```
contact list [--query <text>] [--birthday-in <days>] [--sort name|birthday]
```

Without options, lists every contact as a table. `--query` keeps contacts
whose name, any phone number, email or address contains the given text,
ignoring case. `--birthday-in` keeps contacts whose birthday falls within
that many days from today, and adds a "Greet on" column: the date the
birthday is next celebrated, moved to the following Monday when it would
otherwise land on a Saturday or Sunday. `--sort` orders the results by name
or by that same upcoming date, with contacts that have no birthday sorted
last.

```bash
assistant contact list
assistant contact list --query kowal
assistant contact list --birthday-in 7 --sort birthday
```

### `contact edit`

```
contact edit <name> [--name <new>] [--email <email>] [--address <address>]
                    [--birthday <DD.MM.YYYY>] [--add-phone <phone>[,<phone>]]
                    [--remove-phone <phone>[,<phone>]]
```

Only the fields you pass are touched. An empty value clears an optional field;
`--add-phone` and `--remove-phone` may be combined in one call to replace a
number atomically. At least one option is required — running `edit` with
nothing to change is reported rather than silently doing nothing.

```bash
assistant contact edit John --email new@example.com
assistant contact edit John --address ""
assistant contact edit John --remove-phone +48123456789 --add-phone +48111222333
assistant contact edit John --name "John Doe"
```

### `contact delete`

```
contact delete <name> [--force]
```

Asks for confirmation unless `--force` is given, or the input is not a
terminal — a piped or scripted run never deletes anything by default.

```bash
assistant contact delete John --force
```

### `note add`

```
note add <text> [--tag <tag>...]
```

Writes a note and reports the id the other commands address it by. Tags are
optional; repeat the option or separate the keywords with commas.

```bash
assistant note add "Buy milk and bread"
assistant note add "Read the pickle docs" --tag study --tag python
assistant note add "Read the pickle docs" --tag "study,python"
```

### `note list`

```
note list [--query <text>] [--tag <tag>] [--sort tag|created|updated]
```

Lists the notes as a table, showing the first 60 characters of each. Without
options it lists all of them; the options narrow the result and combine.
`--query` matches a part of the text, `--tag` keeps the notes carrying that
tag, and `--sort` orders them by their first tag or by time.

```bash
assistant note list
assistant note list --query pickle
assistant note list --tag python --sort updated
```

### `note show`, `note edit` and `note delete`

```
note show <id>
note edit <id> [--text <text>] [--add-tag <tag>...] [--remove-tag <tag>...]
note delete <id> [--force]
```

`note show` prints one note as a card, marking a note with no tags with a
dash. `note edit` changes what the options name and nothing else, so adding
and removing a tag in one call replaces it, and prints the same card after it
runs, so the result of a change is always visible. `note delete` asks for
confirmation unless `--force` is given, or the input is not a terminal — a
piped or scripted run never deletes anything by default.

```bash
assistant note show 3
assistant note edit 3 --text "Read the pickle and shelve docs"
assistant note edit 3 --add-tag urgent --remove-tag draft
assistant note delete 3 --force
```

| Field | Accepted |
|-------|----------|
| Text | Non-empty, at most 4096 characters |
| Tag | One keyword without spaces, at most 32 characters, stored in lower case |

## Where the data is kept

Contacts and notes are stored in your home directory, in
`~/.personal_assistant/data.pkl`. The file is written when the assistant exits
and read when it starts, so nothing is lost between runs. A file that cannot be
read is moved aside rather than deleted, and the assistant starts empty.

## Development

Install the project together with the developer tools:

```bash
pip install -e ".[dev]"
```

Run the checks:

```bash
pytest
ruff check .
ruff format .
mypy
```

The editable install means the `assistant` command already runs the sources in
this directory: edit a file and the next run picks it up. Reinstall only after
changing `pyproject.toml`.

Point `PERSONAL_ASSISTANT_DATA` somewhere else to keep a development session
away from real data:

```bash
export PERSONAL_ASSISTANT_DATA=/tmp/assistant-dev.pkl
```

Delete that file to start from an empty state.

## Team

<!-- TODO: members and roles -->
