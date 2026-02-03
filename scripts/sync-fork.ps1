# Sync fork with upstream and handle conflicts
# Usage:
#   .\scripts\sync-fork.ps1                    # Normal sync
#   .\scripts\sync-fork.ps1 -UseClaudeCode     # Use Claude Code for conflicts
#   .\scripts\sync-fork.ps1 -UseCopilot        # Use Copilot CLI for conflicts
#   .\scripts\sync-fork.ps1 -UseVSCode         # Open VS Code for conflicts

param(
    [string]$Branch = "ollama-local",
    [switch]$UseClaudeCode,
    [switch]$UseCopilot,
    [switch]$UseVSCode
)

Set-Location $PSScriptRoot\..

function Assert-GitSuccess {
    param([string]$Message)
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: $Message" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n=== Syncing fork with upstream ===" -ForegroundColor Cyan

# Safety: abort if there are uncommitted changes (ignore this script itself)
$dirty = git status --porcelain | Where-Object { $_ -notmatch "scripts/sync-fork" -and $_ -notmatch "scripts/SYNC-GUIDE" }
if ($dirty) {
    Write-Host "ERROR: You have uncommitted changes. Commit or stash them first." -ForegroundColor Red
    Write-Host $dirty -ForegroundColor Gray
    Write-Host ""
    Write-Host "  git stash        # stash changes" -ForegroundColor Gray
    Write-Host "  git add . && git commit -m 'wip'   # commit changes" -ForegroundColor Gray
    exit 1
}

# 1. Fetch upstream
Write-Host "`n[1/5] Fetching upstream..." -ForegroundColor Yellow
git fetch upstream
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to fetch upstream. Is the remote configured?" -ForegroundColor Red
    Write-Host "Run: git remote add upstream https://github.com/langchain-ai/deepagents.git" -ForegroundColor Gray
    exit 1
}

# 2. Update master
Write-Host "`n[2/5] Updating master branch..." -ForegroundColor Yellow
git checkout master
Assert-GitSuccess "Failed to checkout master"

git reset --hard upstream/master
Assert-GitSuccess "Failed to reset master to upstream/master"

git push origin master --force
Assert-GitSuccess "Failed to push master"

Write-Host "Master updated successfully" -ForegroundColor Green

# 3. Switch to feature branch
Write-Host "`n[3/5] Switching to $Branch..." -ForegroundColor Yellow
git checkout $Branch
Assert-GitSuccess "Branch '$Branch' not found"

# 4. Attempt rebase
Write-Host "`n[4/5] Rebasing $Branch onto master..." -ForegroundColor Yellow
$rebaseOutput = git rebase master 2>&1
$rebaseExitCode = $LASTEXITCODE

if ($rebaseExitCode -ne 0) {
    Write-Host "`nCONFLICTS DETECTED!" -ForegroundColor Red
    Write-Host $rebaseOutput -ForegroundColor Gray

    # Get conflicted files
    $conflictFiles = git diff --name-only --diff-filter=U
    Write-Host "`nConflicted files:" -ForegroundColor Yellow
    $conflictFiles | ForEach-Object { Write-Host "  - $_" -ForegroundColor Gray }

    # Handle based on selected AI tool
    if ($UseClaudeCode) {
        Write-Host "`nLaunching Claude Code to resolve conflicts..." -ForegroundColor Cyan
        $filesStr = ($conflictFiles -join ", ")
        $prompt = "I have merge conflicts in: $filesStr. Help me resolve them by keeping both upstream changes AND my Ollama feature. After resolving, stage the files and run 'git rebase --continue'."

        claude --message $prompt

    } elseif ($UseCopilot) {
        Write-Host "`nLaunching Copilot CLI to resolve conflicts..." -ForegroundColor Cyan
        $filesStr = ($conflictFiles -join ", ")
        $prompt = "I have merge conflicts in: $filesStr. Help me resolve them by keeping both upstream changes AND my Ollama feature. After resolving, stage the files and run 'git rebase --continue'."

        copilot --message $prompt

    } elseif ($UseVSCode) {
        Write-Host "`nOpening VS Code with conflict files..." -ForegroundColor Cyan
        Write-Host "(Use VS Code's built-in merge editor + Copilot Chat for assistance)" -ForegroundColor Gray

        code . $conflictFiles

        Write-Host "`nAfter resolving in VS Code:" -ForegroundColor Yellow
        Write-Host "  git add $($conflictFiles -join ' ')" -ForegroundColor White
        Write-Host "  git rebase --continue" -ForegroundColor White
        Write-Host "  git push origin $Branch --force" -ForegroundColor White

    } else {
        Write-Host "`nOptions to resolve:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  AI-Assisted (choose one):" -ForegroundColor Cyan
        Write-Host "    .\scripts\sync-fork.ps1 -UseClaudeCode    # Claude Code CLI" -ForegroundColor White
        Write-Host "    .\scripts\sync-fork.ps1 -UseCopilot       # Copilot CLI" -ForegroundColor White
        Write-Host "    .\scripts\sync-fork.ps1 -UseVSCode        # VS Code merge editor" -ForegroundColor White
        Write-Host ""
        Write-Host "  Manual resolution:" -ForegroundColor Cyan
        Write-Host "    1. Edit files to resolve conflicts" -ForegroundColor Gray
        Write-Host "    2. git add <files>" -ForegroundColor White
        Write-Host "    3. git rebase --continue" -ForegroundColor White
        Write-Host "    4. git push origin $Branch --force" -ForegroundColor White
        Write-Host ""
        Write-Host "  Abort:" -ForegroundColor Cyan
        Write-Host "    git rebase --abort" -ForegroundColor White
    }

    # Check if rebase is still in progress
    $rebaseInProgress = (Test-Path ".git/rebase-merge") -or (Test-Path ".git/rebase-apply")
    if ($rebaseInProgress) {
        Write-Host "`nRebase still in progress - resolve conflicts and continue manually." -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "Rebase successful" -ForegroundColor Green

# 5. Push the rebased branch
Write-Host "`n[5/5] Pushing $Branch to origin..." -ForegroundColor Yellow
git push origin $Branch --force
Assert-GitSuccess "Failed to push $Branch"

Write-Host "`n=== Sync complete! ===" -ForegroundColor Green
Write-Host "Branch '$Branch' is now rebased on latest upstream master." -ForegroundColor Gray
