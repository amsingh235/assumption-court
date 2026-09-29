# START HERE

1. Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY` + `GEMINI_MODEL` (from Google AI Studio).
2. Open this folder in a terminal and run: `claude`
3. Say: **Read BUILD.md fully, then build.**
4. If interrupted, say: **Read BUILD.md and PROGRESS.md, resume.**

Files:
- `BUILD.md`: the one-go build order (what the agent follows)
- `CLAUDE.md`: auto-loads BUILD.md in Claude Code
- `AGENTS.md`: the same spec, for Antigravity / other IDE agents
- `MASTER-reference.md`: the human-facing master plan (principles, LinkedIn plan)
- `PROGRESS.md`: the status log the agent updates

Tips: use "accept edits" mode and pre-allow python, pytest, pip, npm, git and curl in `/permissions`. Don't skip all permissions. Watch `/cost` or `/status`.
