# Fork Sync Guide

## Quick Sync (No Conflicts Expected)

```powershell
.\scripts\sync-fork.ps1
# or
scripts\sync-fork.bat
```

## When Conflicts Occur

### Option A: GitHub Copilot CLI (Work - Recommended)

```powershell
.\scripts\sync-fork.ps1 -UseCopilot
# or
scripts\sync-fork.bat --copilot
```

Copilot CLI is a **full agentic CLI** (powered by Claude Sonnet 4.5) that can:
- Edit files directly to resolve conflicts
- Run git commands (add, rebase --continue, push)
- Plan and execute multi-step workflows
- Complete the entire resolution workflow autonomously

**What happens:**
```powershell
gh copilot -p "I have git merge conflicts in these files: config.py, main.py.
Please resolve by keeping BOTH upstream and my Ollama additions..."
```

Copilot CLI will then autonomously:
1. Read the conflicted files
2. Analyze the conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`)
3. Edit files to merge both sets of changes
4. Run `git add <files>`
5. Run `git rebase --continue`
6. Push the result

### Option B: Claude Code (Personal)

```powershell
.\scripts\sync-fork.ps1 -UseClaudeCode
# or
scripts\sync-fork.bat --claude
```

Launches Claude Code to resolve conflicts and complete the rebase. Works identically to Copilot CLI.

### Option C: VS Code + Copilot (Work - Manual)

```powershell
.\scripts\sync-fork.ps1 -UseVSCode
# or
scripts\sync-fork.bat --vscode
```

Opens VS Code with the conflicted files. Use:
- VS Code's built-in 3-way merge editor
- GitHub Copilot Chat for assistance

This option requires more manual intervention than the CLI options.

## Copilot CLI vs Claude Code

| Feature | Copilot CLI | Claude Code |
|---------|-------------|-------------|
| Powered by | Claude Sonnet 4.5 | Claude (various models) |
| Edit files | Yes | Yes |
| Run commands | Yes | Yes |
| Autonomous workflows | Yes | Yes |
| License | GitHub Copilot subscription | Anthropic subscription |
| Best for | Work environments | Personal projects |

**Both tools have equivalent capabilities** - the choice depends on which subscription you have access to.

## Manual Resolution

If already in a conflicted state or prefer manual control:

```bash
# 1. See conflicted files
git diff --name-only --diff-filter=U

# 2. Open each file, find conflict markers:
#    <<<<<<< HEAD
#    (upstream code - e.g., VertexAI additions)
#    =======
#    (your code - e.g., Ollama additions)
#    >>>>>>> your-commit

# 3. Edit to keep BOTH sets of changes, remove markers

# 4. Stage and continue
git add <resolved-files>
git rebase --continue

# 5. Push
git push origin ollama-local --force
```

## If Stuck

```bash
# Abort the rebase and return to previous state
git rebase --abort
```

## Prevention Tips

1. **Sync weekly** - Smaller conflicts are easier to resolve
2. **Keep changes minimal** - Only modify what's necessary for your feature
3. **Isolate new code** - New files don't conflict with upstream changes

## Files That Commonly Conflict

Your Ollama branch modifies:
- `libs/cli/deepagents_cli/config.py` - Provider detection, model creation, settings
- `libs/cli/deepagents_cli/main.py` - CLI argument help text

**Resolution pattern:** Always keep **both** - upstream's new features (like VertexAI) AND your Ollama additions. The providers are additive, not mutually exclusive.

## Installation Requirements

| Tool | Installation | Verify |
|------|-------------|--------|
| Copilot CLI | Included with GitHub Copilot | `gh copilot --version` |
| Claude Code | `npm install -g @anthropic-ai/claude-code` | `claude --version` |
| VS Code | GitHub Copilot extension | Check Extensions panel |

## Troubleshooting

### SSH passphrase timeout
If the script hangs waiting for SSH passphrase, run the push manually:
```bash
git push origin ollama-local --force
```

### Copilot CLI not found
```bash
# Ensure gh CLI is installed and authenticated
gh auth status

# Copilot should be available if you have a Copilot subscription
gh copilot --help
```

### Claude Code not found
```bash
npm install -g @anthropic-ai/claude-code
```
