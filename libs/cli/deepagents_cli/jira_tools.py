"""JIRA integration tools for the CLI agent."""

from __future__ import annotations

import logging
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

from deepagents_cli.config import settings

logger = logging.getLogger(__name__)

# Module-level cache for detected API version
_api_version: str | None = None


def _jira_request(
    method: str,
    path: str,
    *,
    verify_ssl: bool | None = None,
    **kwargs: Any,
) -> requests.Response:
    """Make an authenticated request to the JIRA REST API.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE).
        path: API path (e.g., "/rest/api/2/issue/PROJ-1").
        verify_ssl: Whether to verify SSL certificates.
        **kwargs: Passed to requests.request.

    Returns:
        The requests Response object.

    Raises:
        ValueError: If JIRA is not configured.
    """
    if not settings.has_jira:
        msg = (
            "JIRA is not configured. "
            "Set JIRA_URL, JIRA_USERNAME, and JIRA_PASSWORD."
        )
        raise ValueError(msg)

    if verify_ssl is None:
        verify_ssl = settings.jira_verify_ssl

    base_url = settings.jira_url.rstrip("/")  # type: ignore[union-attr]
    url = f"{base_url}{path}"

    auth = HTTPBasicAuth(
        settings.jira_username,  # type: ignore[arg-type]
        settings.jira_password,  # type: ignore[arg-type]
    )

    headers = kwargs.pop("headers", {})
    headers.setdefault("Content-Type", "application/json")
    headers.setdefault("Accept", "application/json")

    return requests.request(
        method,
        url,
        auth=auth,
        headers=headers,
        verify=verify_ssl,
        timeout=30,
        **kwargs,
    )


def _detect_api_version(verify_ssl: bool | None = None) -> str:
    """Auto-detect JIRA API version on first call.

    Tries /rest/api/2/serverInfo to confirm v2 is available.
    Falls back to v2 regardless (v2 endpoints work on v3 servers).

    Returns:
        The API version string (e.g., "2").
    """
    global _api_version  # noqa: PLW0603
    if _api_version is not None:
        return _api_version

    try:
        resp = _jira_request(
            "GET", "/rest/api/2/serverInfo",
            verify_ssl=verify_ssl,
        )
        if resp.ok:
            data = resp.json()
            ver = data.get("versionNumbers", [])
            logger.debug("JIRA server version: %s", ver)
    except Exception:
        logger.debug(
            "Could not detect JIRA API version, defaulting to v2",
            exc_info=True,
        )

    _api_version = "2"
    return _api_version


def _get_nested(
    d: dict[str, Any],
    key: str,
    nested_key: str,
) -> str | None:
    """Safely get a nested value from a dict.

    Returns:
        d[key][nested_key] if d[key] is truthy, else None.
    """
    val = d.get(key)
    if val:
        return val.get(nested_key)  # type: ignore[union-attr]
    return None


_NOT_CONFIGURED_MSG = (
    "JIRA is not configured. Ask the user for their JIRA URL, "
    "username, and password, then call jira_configure(url, "
    "username, password) before retrying."
)


def _err(msg: str) -> dict[str, Any]:
    """Build a standard error response dict.

    Returns:
        Dict with success=False and the error message.
    """
    return {"success": False, "error": msg}


def _resp_err(label: str, resp: requests.Response) -> dict[str, Any]:
    """Build error dict from a failed response.

    Returns:
        Dict with success=False and status/text details.
    """
    return _err(f"{label} ({resp.status_code}): {resp.text}")


def jira_configure(
    url: str,
    username: str,
    password: str,
) -> dict[str, Any]:
    """Configure JIRA credentials for the current session.

    Call this when JIRA is not yet configured. Ask the user
    for their JIRA URL, username, and password first.

    Args:
        url: JIRA base URL (e.g., "https://jira.example.com")
        username: JIRA username
        password: JIRA password

    Returns:
        Dict with 'success' and confirmation message.
    """
    settings.jira_url = url.rstrip("/")
    settings.jira_username = username
    settings.jira_password = password

    # Reset API version cache so it re-detects
    global _api_version  # noqa: PLW0603
    _api_version = None

    return {
        "success": True,
        "message": f"JIRA configured for {url}",
    }


def jira_search(
    jql: str,
    max_results: int = 20,
    fields: list[str] | None = None,
    verify_ssl: bool | None = None,
) -> dict[str, Any]:
    """Search JIRA issues using JQL (JIRA Query Language).

    Args:
        jql: JQL query string
            (e.g., 'project = PROJ AND status = "In Progress"')
        max_results: Maximum results to return (default: 20)
        fields: Fields to include (default: key, summary,
            status, assignee, priority, created, updated)
        verify_ssl: Whether to verify SSL certificates

    Returns:
        Dict with 'success' and 'issues', or 'error' on failure.
    """
    _detect_api_version(verify_ssl=verify_ssl)

    if fields is None:
        fields = [
            "key", "summary", "status", "assignee",
            "priority", "created", "updated",
        ]

    payload = {
        "jql": jql,
        "maxResults": max_results,
        "fields": fields,
    }

    try:
        resp = _jira_request(
            "POST", "/rest/api/2/search",
            json=payload, verify_ssl=verify_ssl,
        )

        if not resp.ok:
            return _resp_err("JIRA search failed", resp)

        data = resp.json()
        issues = []
        for issue in data.get("issues", []):
            f = issue.get("fields", {})
            assignee = _get_nested(f, "assignee", "displayName")
            issues.append({
                "key": issue.get("key"),
                "summary": f.get("summary"),
                "status": _get_nested(f, "status", "name"),
                "assignee": assignee,
                "priority": _get_nested(f, "priority", "name"),
                "created": f.get("created"),
                "updated": f.get("updated"),
            })

        return {
            "success": True,
            "total": data.get("total", 0),
            "issues": issues,
        }
    except ValueError:
        return _err(_NOT_CONFIGURED_MSG)
    except requests.exceptions.RequestException as e:
        return _err(f"JIRA request error: {e!s}")


def jira_get_issue(
    issue_key: str,
    expand: str | None = None,
    verify_ssl: bool | None = None,
) -> dict[str, Any]:
    """Get full details of a JIRA issue.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
        expand: Fields to expand
            (e.g., "changelog,renderedFields")
        verify_ssl: Whether to verify SSL certificates

    Returns:
        Dict with 'success' and issue details, or 'error'.
    """
    _detect_api_version(verify_ssl=verify_ssl)

    params: dict[str, str] = {}
    if expand:
        params["expand"] = expand

    try:
        resp = _jira_request(
            "GET",
            f"/rest/api/2/issue/{issue_key}",
            params=params,
            verify_ssl=verify_ssl,
        )

        if not resp.ok:
            return _resp_err("Failed to get issue", resp)

        data = resp.json()
        f = data.get("fields", {})

        # Extract comments
        comment_data = f.get("comment", {})
        comments = [
            {
                "author": c.get("author", {}).get("displayName"),
                "body": c.get("body"),
                "created": c.get("created"),
            }
            for c in comment_data.get("comments", [])
        ]

        return {
            "success": True,
            "key": data.get("key"),
            "summary": f.get("summary"),
            "description": f.get("description"),
            "status": _get_nested(f, "status", "name"),
            "assignee": _get_nested(f, "assignee", "displayName"),
            "reporter": _get_nested(f, "reporter", "displayName"),
            "priority": _get_nested(f, "priority", "name"),
            "issue_type": _get_nested(f, "issuetype", "name"),
            "labels": f.get("labels", []),
            "created": f.get("created"),
            "updated": f.get("updated"),
            "comments": comments,
        }
    except ValueError:
        return _err(_NOT_CONFIGURED_MSG)
    except requests.exceptions.RequestException as e:
        return _err(f"JIRA request error: {e!s}")


def jira_create_issue(
    project_key: str,
    summary: str,
    issue_type: str = "Task",
    description: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    labels: list[str] | None = None,
    custom_fields: dict[str, Any] | None = None,
    verify_ssl: bool | None = None,
) -> dict[str, Any]:
    """Create a new JIRA issue.

    Args:
        project_key: Project key (e.g., "PROJ")
        summary: Issue summary/title
        issue_type: Issue type name (default: "Task")
        description: Issue description
        priority: Priority name (e.g., "High", "Medium")
        assignee: Assignee username
        labels: List of label strings
        custom_fields: Custom field IDs to values
        verify_ssl: Whether to verify SSL certificates

    Returns:
        Dict with 'success' and issue key, or 'error'.
    """
    _detect_api_version(verify_ssl=verify_ssl)

    fields: dict[str, Any] = {
        "project": {"key": project_key},
        "summary": summary,
        "issuetype": {"name": issue_type},
    }

    if description is not None:
        fields["description"] = description
    if priority is not None:
        fields["priority"] = {"name": priority}
    if assignee is not None:
        fields["assignee"] = {"name": assignee}
    if labels is not None:
        fields["labels"] = labels
    if custom_fields:
        fields.update(custom_fields)

    try:
        resp = _jira_request(
            "POST",
            "/rest/api/2/issue",
            json={"fields": fields},
            verify_ssl=verify_ssl,
        )

        if not resp.ok:
            return _resp_err("Failed to create issue", resp)

        data = resp.json()
        return {
            "success": True,
            "key": data.get("key"),
            "id": data.get("id"),
            "self": data.get("self"),
        }
    except ValueError:
        return _err(_NOT_CONFIGURED_MSG)
    except requests.exceptions.RequestException as e:
        return _err(f"JIRA request error: {e!s}")


def jira_update_issue(
    issue_key: str,
    summary: str | None = None,
    description: str | None = None,
    assignee: str | None = None,
    labels: list[str] | None = None,
    priority: str | None = None,
    custom_fields: dict[str, Any] | None = None,
    verify_ssl: bool | None = None,
) -> dict[str, Any]:
    """Update fields on an existing JIRA issue.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
        summary: New summary/title
        description: New description
        assignee: New assignee username
        labels: New labels list (replaces existing)
        priority: New priority name
        custom_fields: Custom field IDs to values
        verify_ssl: Whether to verify SSL certificates

    Returns:
        Dict with 'success' boolean, or 'error' on failure.
    """
    _detect_api_version(verify_ssl=verify_ssl)

    fields: dict[str, Any] = {}
    if summary is not None:
        fields["summary"] = summary
    if description is not None:
        fields["description"] = description
    if assignee is not None:
        fields["assignee"] = {"name": assignee}
    if labels is not None:
        fields["labels"] = labels
    if priority is not None:
        fields["priority"] = {"name": priority}
    if custom_fields:
        fields.update(custom_fields)

    if not fields:
        return _err("No fields to update.")

    try:
        resp = _jira_request(
            "PUT",
            f"/rest/api/2/issue/{issue_key}",
            json={"fields": fields},
            verify_ssl=verify_ssl,
        )

        if not resp.ok:
            return _resp_err("Failed to update issue", resp)
    except ValueError:
        return _err(_NOT_CONFIGURED_MSG)
    except requests.exceptions.RequestException as e:
        return _err(f"JIRA request error: {e!s}")
    else:
        return {"success": True, "key": issue_key}


def jira_add_comment(
    issue_key: str,
    body: str,
    verify_ssl: bool | None = None,
) -> dict[str, Any]:
    """Add a comment to a JIRA issue.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
        body: Comment body text
        verify_ssl: Whether to verify SSL certificates

    Returns:
        Dict with 'success' and comment details, or 'error'.
    """
    _detect_api_version(verify_ssl=verify_ssl)

    try:
        resp = _jira_request(
            "POST",
            f"/rest/api/2/issue/{issue_key}/comment",
            json={"body": body},
            verify_ssl=verify_ssl,
        )

        if not resp.ok:
            return _resp_err("Failed to add comment", resp)

        data = resp.json()
        return {
            "success": True,
            "id": data.get("id"),
            "author": data.get("author", {}).get("displayName"),
            "body": data.get("body"),
            "created": data.get("created"),
        }
    except ValueError:
        return _err(_NOT_CONFIGURED_MSG)
    except requests.exceptions.RequestException as e:
        return _err(f"JIRA request error: {e!s}")


def jira_transition_issue(
    issue_key: str,
    transition_name: str,
    verify_ssl: bool | None = None,
) -> dict[str, Any]:
    """Transition a JIRA issue to a new status.

    Fetches available transitions, matches by name
    (case-insensitive), and executes.

    Args:
        issue_key: Issue key (e.g., "PROJ-123")
        transition_name: Target transition name
            (e.g., "In Progress", "Done", "To Do")
        verify_ssl: Whether to verify SSL certificates

    Returns:
        Dict with 'success' boolean, or 'error' on failure.
    """
    _detect_api_version(verify_ssl=verify_ssl)

    try:
        # Get available transitions
        resp = _jira_request(
            "GET",
            f"/rest/api/2/issue/{issue_key}/transitions",
            verify_ssl=verify_ssl,
        )

        if not resp.ok:
            return _resp_err("Failed to get transitions", resp)

        data = resp.json()
        transitions = data.get("transitions", [])

        # Find matching transition (case-insensitive)
        target = transition_name.lower()
        matched = None
        for t in transitions:
            if t.get("name", "").lower() == target:
                matched = t
                break

        if not matched:
            available = [t.get("name") for t in transitions]
            return _err(
                f"Transition '{transition_name}' not found. "
                f"Available: {available}",
            )

        # Execute transition
        resp = _jira_request(
            "POST",
            f"/rest/api/2/issue/{issue_key}/transitions",
            json={"transition": {"id": matched["id"]}},
            verify_ssl=verify_ssl,
        )

        if not resp.ok:
            return _resp_err("Failed to transition", resp)

        return {
            "success": True,
            "key": issue_key,
            "transition": matched.get("name"),
            "to_status": matched.get("to", {}).get("name"),
        }
    except ValueError:
        return _err(_NOT_CONFIGURED_MSG)
    except requests.exceptions.RequestException as e:
        return _err(f"JIRA request error: {e!s}")
