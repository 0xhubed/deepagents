---
name: jira
description: "Use this skill for any JIRA-related tasks: searching issues with JQL, viewing issue details, creating or updating tickets, adding comments, transitioning issue status, or working with JIRA issue keys (e.g., PROJ-123). Trigger on mentions of JIRA, ticket/issue management, sprint boards, backlogs, bug tracking, or patterns like PROJ-123."
license: MIT
compatibility: designed for deepagents-cli
---

# JIRA Integration

## Setup

JIRA credentials are usually pre-configured via environment variables. Always try using the tools directly first (e.g., `jira_search`). Do NOT ask the user for credentials upfront.

Only if a tool returns a "not configured" error, then ask the user for their JIRA URL, username, and password, and call `jira_configure(url, username, password)` to enable JIRA for the session.

## Available Tools

- **jira_configure(url, username, password)** — Configure JIRA credentials for the session
- **jira_search(jql)** — Search issues via JQL
- **jira_get_issue(issue_key)** — Get full issue details with comments
- **jira_create_issue(project_key, summary, ...)** — Create a new issue
- **jira_update_issue(issue_key, ...)** — Update issue fields
- **jira_add_comment(issue_key, body)** — Add a comment
- **jira_transition_issue(issue_key, transition_name)** — Change issue status

## JQL Quick Reference

```
# Issues assigned to current user
assignee = currentUser() AND resolution = Unresolved

# Open bugs in a project
project = PROJ AND issuetype = Bug AND status != Done

# Issues updated in last 7 days
project = PROJ AND updated >= -7d

# Issues by priority
project = PROJ AND priority = High AND status = "In Progress"

# Issues with specific labels
project = PROJ AND labels IN (backend, api)

# Full-text search
project = PROJ AND text ~ "login error"

# Sprint-based queries
sprint IN openSprints() AND assignee = currentUser()

# Issues created this week
project = PROJ AND created >= startOfWeek()

# Combining conditions
project = PROJ AND status IN ("To Do", "In Progress") AND assignee = "john.doe" ORDER BY priority DESC
```

## Common Workflows

### Triage new bugs
1. Search: `jira_search("project = PROJ AND issuetype = Bug AND status = 'Open' ORDER BY created DESC")`
2. Review each issue with `jira_get_issue`
3. Set priority and assign with `jira_update_issue`
4. Transition to "In Progress" with `jira_transition_issue`

### Create a feature ticket
1. `jira_create_issue(project_key="PROJ", summary="...", issue_type="Story", description="...", priority="Medium")`
2. Add acceptance criteria as a comment with `jira_add_comment`

### Status update
1. Search assigned issues: `jira_search("assignee = currentUser() AND sprint IN openSprints()")`
2. Get details on each with `jira_get_issue`
3. Summarize progress for standup

## Tips

- Issue keys follow the pattern `PROJECT-NUMBER` (e.g., PROJ-123, DEV-456)
- JQL supports `ORDER BY` for sorting (e.g., `ORDER BY priority DESC, created ASC`)
- Use `expand=changelog` in `jira_get_issue` to see status change history
- Transition names are workflow-specific — the tool auto-discovers available transitions
- For corporate SSL, set `REQUESTS_CA_BUNDLE` env var to your CA bundle path
