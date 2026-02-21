# ctx-handoff

> Capture development context from git repos into portable handoff documents for AI coding assistants.

## Why ctx-handoff?

When working with AI coding assistants, you often face these challenges:

- **Rate limits**: Hit API limits mid-session and need to switch tools
- **Tool switching**: Want to try different AI assistants (Claude, GPT, Gemini) on the same problem
- **Context window limits**: Need to manage what context fits in the AI's attention span
- **Pair programming handoffs**: Sharing context with teammates or your future self
- **Session continuity**: Resuming work after a break without losing context

**ctx-handoff** solves these by creating portable, token-budgeted snapshots of your development context that you can easily share with any AI tool or teammate.

## Features

- 📸 **Smart snapshots**: Captures git state, diffs, file contents, and TODOs
- 🎯 **Token budgeting**: Automatically fits context within configurable token limits
- 📋 **Clipboard ready**: One command to copy context for pasting into AI chats
- 🎨 **Rich formatting**: Beautiful terminal output with syntax highlighting
- 💾 **Persistent storage**: Saves snapshots locally for later retrieval
- 🏷️ **Tagging**: Organize snapshots with custom tags
- 🔧 **Tool-optimized**: Generate resume prompts optimized for Claude, GPT, or Gemini
- 🙈 **Ignore patterns**: `.ctxignore` file support for excluding sensitive files

## Installation

### Using pipx (recommended)

