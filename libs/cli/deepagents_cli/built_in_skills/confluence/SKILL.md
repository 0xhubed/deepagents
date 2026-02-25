---
name: confluence
description: "Use this skill for any Confluence-related tasks: searching wiki pages, reading page content, creating or updating documentation, or working with internal knowledge base content. Trigger on mentions of Confluence, wiki, internal docs, knowledge base, documentation pages, or team spaces."
license: MIT
compatibility: designed for deepagents-cli
---

# Confluence Integration

## Setup

Confluence credentials are usually pre-configured via environment variables. Always try using the tools directly first (e.g., `confluence_search`). Do NOT ask the user for credentials upfront.

Only if a tool returns a "not configured" error, then ask the user for their Confluence URL, username, and password, and call `confluence_configure(url, username, password)` to enable Confluence for the session.

## Available Tools

- **confluence_configure(url, username, password)** — Configure Confluence credentials for the session
- **confluence_search(query)** — Search pages via CQL or plain text
- **confluence_get_page(page_id or title+space_key)** — Get page content
- **confluence_create_page(space_key, title, body)** — Create a new page
- **confluence_update_page(page_id, title, body)** — Update existing page (auto-increments version)

## CQL Quick Reference

```
# Full-text search
type = page AND text ~ "deployment guide"

# Search in a specific space
space = "DEV" AND type = page AND text ~ "API docs"

# Pages with specific labels
type = page AND label = "architecture"

# Recently modified pages
type = page AND lastModified >= "2025-01-01"

# Pages by creator
type = page AND creator = "john.doe"

# Combining conditions
space = "TEAM" AND type = page AND label IN ("runbook", "ops") AND text ~ "database"
```

## Common Workflows

### Find documentation
1. Search: `confluence_search("deployment process", space_key="DEV")`
2. Read the page: `confluence_get_page(page_id="12345")`

### Create a new runbook
1. Create page with HTML body:
```python
confluence_create_page(
    space_key="OPS",
    title="Database Failover Runbook",
    body="<h2>Steps</h2><ol><li>Check primary status</li><li>Promote replica</li></ol>"
)
```

### Update existing documentation
1. Get current page: `confluence_get_page(title="API Reference", space_key="DEV")`
2. Modify and update: `confluence_update_page(page_id="12345", title="API Reference", body="<p>Updated content</p>")`

## Confluence Storage Format

Page bodies use Confluence storage format (XHTML-based):

```html
<h1>Heading 1</h1>
<h2>Heading 2</h2>
<p>Paragraph text with <strong>bold</strong> and <em>italic</em>.</p>
<ul><li>Bullet item</li></ul>
<ol><li>Numbered item</li></ol>
<table><tbody>
  <tr><th>Header</th><th>Header</th></tr>
  <tr><td>Cell</td><td>Cell</td></tr>
</tbody></table>
<ac:structured-macro ac:name="code"><ac:parameter ac:name="language">python</ac:parameter>
<ac:plain-text-body><![CDATA[print("hello")]]></ac:plain-text-body>
</ac:structured-macro>
```

## Tips

- Plain text queries are auto-wrapped in CQL: `confluence_search("deployment")` becomes `type = page AND text ~ "deployment"`
- Confluence credentials fall back to JIRA credentials if not set separately (common for shared LDAP)
- Page versions auto-increment — no need to track version numbers manually
- Use `parent_id` in `confluence_create_page` to nest pages under a parent
- For corporate SSL, set `REQUESTS_CA_BUNDLE` env var to your CA bundle path
