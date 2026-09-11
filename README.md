# ctx-handoff

> **Built by [The Foundry](https://github.com/solstice035/the-foundry)**, an autonomous build pipeline I run. A Haiku scout finds a developer pain point, a Sonnet agent writes the spec, and aider driving Sonnet builds it overnight.
>
> This repo was produced end to end by that pipeline. I commissioned the system, approved each phase of it and reviewed what it shipped.

> Capture development context from git repos into portable handoff documents for AI coding assistants.

## Why ctx-handoff?

When working with AI coding assistants, you often face these challenges:

- **Rate limits**: Hit API limits mid-session and need to switch tools
- **Tool switching**: Want to try different AI assistants (Claude, GPT, Gemini) on the same problem
- **Context window limits**: Need to manage what context fits in the AI's attention span
- **Pair programming handoffs**: Sharing context with teammates or your future self
- **Session continuity**: Resuming work after a break without losing context

**ctx-handoff** solves these by creating portable, token-budgeted snapshots of your development context that you can paste into any AI tool.

## Installation

```bash
# Using pipx (recommended)
pipx install ctx-handoff

# Using pip
pip install ctx-handoff

# From source (development)
git clone https://github.com/solstice035/ctx-handoff.git
cd ctx-handoff
pip install -e ".[dev]"
```

## Quick Start

```bash
cd your-project        # Navigate to any git repo
ctx snap               # Create a context snapshot
ctx copy               # Copy to clipboard, paste into AI chat
```

## Commands

### `ctx snap` — Create a snapshot

Captures git branch, recent commits, staged/unstaged changes, recently modified file contents, and TODO/FIXME items.

```bash
ctx snap                              # Basic snapshot
ctx snap --tag "before-refactor"      # Tag for reference
ctx snap --budget 8000                # Custom token budget (default: 4000)
ctx snap --output context.md          # Save to specific file
ctx snap --json                       # JSON output only
ctx snap --markdown                   # Markdown output only
```

### `ctx show [ID]` — Display a snapshot

```bash
ctx show                # Show latest snapshot
ctx show a1b2c3d4       # Show specific snapshot by ID
```

### `ctx copy [ID]` — Copy to clipboard

```bash
ctx copy                # Copy latest snapshot markdown
ctx copy a1b2c3d4       # Copy specific snapshot
```

Platform support: macOS (pbcopy), Linux (xclip/xsel), Windows (clip).

### `ctx list` — List all snapshots

```bash
ctx list
```

Shows ID, timestamp, repo name, branch, tag, and token count.

### `ctx resume [ID]` — Generate AI-optimized resume prompt

```bash
ctx resume --tool claude    # Claude-optimized prompt
ctx resume --tool gpt       # GPT-optimized prompt
ctx resume --tool gemini    # Gemini-optimized prompt
```

## Token Budgeting

Tokens are estimated at ~4 characters per token. The default budget is 4,000 tokens. Content is prioritized:

1. Git state (branch, commits) — always included
2. Diffs (staged, then unstaged) — included if budget allows
3. File contents (most recently modified first) — truncated to fit

```bash
ctx snap --budget 2000     # Small budget for quick questions
ctx snap --budget 10000    # Large budget for comprehensive context
```

## .ctxignore

Create a `.ctxignore` file in your repo to exclude sensitive files:

```
.env
*.key
*.pem
*.log
node_modules/
```

## Storage

Snapshots are saved locally:

```
~/.ctx-handoff/
├── index.json
└── snapshots/
    └── my-project/
        ├── 20240115_103000_a1b2c3d4.json
        └── 20240115_143000_e5f6g7h8.json
```

## Example Output

```markdown
# Context Handoff: my-project

## Session Info
- Branch: feature/new-api
- Last commit: a1b2c3d4 - Add user authentication
- Timestamp: 2024-01-15T10:30:00
- Token count: 3847

## Recent Commits
- a1b2c3d4 Add user authentication — John Doe
- e5f6g7h8 Fix database migration — Jane Smith

## Working State
### Staged Changes
M src/auth.py

### Unstaged Changes
M src/db.py

## Key Files
### src/auth.py
...

## TODOs & FIXMEs
- TODO (src/auth.py:42): implement password hashing
- FIXME (src/db.py:15): handle connection timeout
```

## Development

```bash
pip install -e ".[dev]"
pytest                     # Run tests
black src/ tests/          # Format code
mypy src/ctx_handoff       # Type checking
```

## License

MIT
