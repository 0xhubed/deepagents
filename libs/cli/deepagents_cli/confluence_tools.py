"""Confluence integration tools for the CLI agent."""

from __future__ import annotations

import logging
import re
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

from deepagents_cli.config import settings

logger = logging.getLogger(__name__)


def _confluence_request(
    method: str,
    path: str,
    *,
    verify_ssl: bool | None = None,
    **kwargs: Any,
) -> requests.Response:
    """Make an authenticated request to the Confluence REST API.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE).
        path: API path (e.g., "/rest/api/content").
        verify_ssl: Whether to verify SSL certificates.
        **kwargs: Passed to requests.request.

    Returns:
        The requests Response object.

    Raises:
        ValueError: If Confluence is not configured.
    """
    if not settings.has_confluence:
        msg = (
            "Confluence is not configured. Set CONFLUENCE_URL "
            "and credentials (CONFLUENCE_USERNAME/PASSWORD or "
            "JIRA_USERNAME/PASSWORD)."
        )
        raise ValueError(msg)

    if verify_ssl is None:
        verify_ssl = settings.confluence_verify_ssl

    base_url = settings.confluence_url.rstrip("/")  # type: ignore[union-attr]
    url = f"{base_url}{path}"

    auth = HTTPBasicAuth(
        settings.confluence_username,  # type: ignore[arg-type]
        settings.confluence_password,  # type: ignore[arg-type]
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


def _strip_html_tags(html: str) -> str:
    """Strip HTML tags to produce plain text.

    Args:
        html: HTML string to clean.

    Returns:
        Plain text with basic whitespace structure.
    """
    # Replace <br> and block-level tags with newlines
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(
        r"</(p|div|h[1-6]|li|tr)>", "\n", text, flags=re.IGNORECASE,
    )
    text = re.sub(
        r"<(p|div|h[1-6]|li|tr)[^>]*>", "", text, flags=re.IGNORECASE,
    )
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", "", text)
    # Collapse multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


_NOT_CONFIGURED_MSG = (
    "Confluence is not configured. Ask the user for their "
    "Confluence URL, username, and password, then call "
    "confluence_configure(url, username, password) before "
    "retrying."
)


def _err(msg: str) -> dict[str, Any]:
    """Build a standard error response dict.

    Returns:
        Dict with success=False and the error message.
    """
    return {"success": False, "error": msg}


def _resp_err(
    label: str, resp: requests.Response,
) -> dict[str, Any]:
    """Build error dict from a failed response.

    Returns:
        Dict with success=False and status/text details.
    """
    return _err(f"{label} ({resp.status_code}): {resp.text}")


def confluence_configure(
    url: str,
    username: str,
    password: str,
) -> dict[str, Any]:
    """Configure Confluence credentials for the current session.

    Call this when Confluence is not yet configured. Ask the user
    for their Confluence URL, username, and password first.

    Args:
        url: Confluence base URL (e.g., "https://confluence:8443")
        username: Confluence username
        password: Confluence password

    Returns:
        Dict with 'success' and confirmation message.
    """
    settings.confluence_url = url.rstrip("/")
    settings.confluence_username = username
    settings.confluence_password = password

    return {
        "success": True,
        "message": f"Confluence configured for {url}",
    }


def confluence_search(
    query: str,
    max_results: int = 10,
    space_key: str | None = None,
    verify_ssl: bool | None = None,
) -> dict[str, Any]:
    """Search Confluence pages using CQL.

    Args:
        query: CQL query or text search string
            (e.g., 'type=page AND text ~ "deployment"')
        max_results: Maximum results to return (default: 10)
        space_key: Optional space key to restrict search
        verify_ssl: Whether to verify SSL certificates

    Returns:
        Dict with 'success' and 'results', or 'error'.
    """
    # Build CQL query
    cql = query
    if space_key and "space" not in query.lower():
        cql = f'space = "{space_key}" AND ({query})'

    # If plain text (no CQL operators), wrap in text search
    cql_ops = (
        "=", "~", "AND", "OR", "NOT", "IN",
        "type", "space", "label",
    )
    if not any(op in query for op in cql_ops):
        cql = f'type = page AND text ~ "{query}"'
        if space_key:
            cql = f'space = "{space_key}" AND {cql}'

    params = {
        "cql": cql,
        "limit": str(max_results),
        "expand": "metadata.labels",
    }

    try:
        resp = _confluence_request(
            "GET", "/rest/api/content/search",
            params=params, verify_ssl=verify_ssl,
        )

        if not resp.ok:
            return _resp_err("Confluence search failed", resp)

        data = resp.json()
        results = []
        for item in data.get("results", []):
            labels = []
            metadata = item.get("metadata", {})
            lbl_results = metadata.get("labels", {}).get("results")
            if lbl_results:
                labels = [lbl.get("name") for lbl in lbl_results]

            space = item.get("space")
            results.append({
                "id": item.get("id"),
                "title": item.get("title"),
                "type": item.get("type"),
                "space_key": space.get("key") if space else None,
                "labels": labels,
                "url": item.get("_links", {}).get("webui"),
            })

        return {
            "success": True,
            "total": data.get("totalSize", 0),
            "results": results,
        }
    except ValueError:
        return _err(_NOT_CONFIGURED_MSG)
    except requests.exceptions.RequestException as e:
        return _err(f"Confluence request error: {e!s}")


def confluence_get_page(
    page_id: str | None = None,
    title: str | None = None,
    space_key: str | None = None,
    verify_ssl: bool | None = None,
) -> dict[str, Any]:
    """Get a Confluence page by ID or by title+space.

    Args:
        page_id: Page ID (preferred lookup method)
        title: Page title (requires space_key)
        space_key: Space key (required with title)
        verify_ssl: Whether to verify SSL certificates

    Returns:
        Dict with 'success' and page content, or 'error'.
    """
    expand = "body.storage,version,space"

    try:
        if page_id:
            resp = _confluence_request(
                "GET",
                f"/rest/api/content/{page_id}",
                params={"expand": expand},
                verify_ssl=verify_ssl,
            )
        elif title and space_key:
            resp = _confluence_request(
                "GET",
                "/rest/api/content",
                params={
                    "title": title,
                    "spaceKey": space_key,
                    "expand": expand,
                    "limit": "1",
                },
                verify_ssl=verify_ssl,
            )
        else:
            return _err(
                "Provide either page_id or both "
                "title and space_key.",
            )

        if not resp.ok:
            return _resp_err("Failed to get page", resp)

        data = resp.json()

        # If searched by title, extract from results array
        if not page_id:
            results = data.get("results", [])
            if not results:
                return _err(
                    f"No page found with title '{title}' "
                    f"in space '{space_key}'.",
                )
            data = results[0]

        # Extract body and convert to readable text
        body_storage = (
            data.get("body", {})
            .get("storage", {})
            .get("value", "")
        )
        body_text = _strip_html_tags(body_storage)

        space = data.get("space")
        return {
            "success": True,
            "id": data.get("id"),
            "title": data.get("title"),
            "space_key": space.get("key") if space else None,
            "version": data.get("version", {}).get("number"),
            "body_html": body_storage,
            "body_text": body_text,
            "url": data.get("_links", {}).get("webui"),
        }
    except ValueError:
        return _err(_NOT_CONFIGURED_MSG)
    except requests.exceptions.RequestException as e:
        return _err(f"Confluence request error: {e!s}")


def confluence_create_page(
    space_key: str,
    title: str,
    body: str,
    parent_id: str | None = None,
    verify_ssl: bool | None = None,
) -> dict[str, Any]:
    """Create a new Confluence page.

    Args:
        space_key: Space key (e.g., "DEV", "TEAM")
        title: Page title
        body: Content in Confluence storage format (HTML)
        parent_id: Optional parent page ID
        verify_ssl: Whether to verify SSL certificates

    Returns:
        Dict with 'success' and page details, or 'error'.
    """
    payload: dict[str, Any] = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {
            "storage": {
                "value": body,
                "representation": "storage",
            }
        },
    }

    if parent_id:
        payload["ancestors"] = [{"id": parent_id}]

    try:
        resp = _confluence_request(
            "POST",
            "/rest/api/content",
            json=payload,
            verify_ssl=verify_ssl,
        )

        if not resp.ok:
            return _resp_err("Failed to create page", resp)

        data = resp.json()
        return {
            "success": True,
            "id": data.get("id"),
            "title": data.get("title"),
            "url": data.get("_links", {}).get("webui"),
        }
    except ValueError:
        return _err(_NOT_CONFIGURED_MSG)
    except requests.exceptions.RequestException as e:
        return _err(f"Confluence request error: {e!s}")


def confluence_update_page(
    page_id: str,
    title: str,
    body: str,
    version_comment: str | None = None,
    verify_ssl: bool | None = None,
) -> dict[str, Any]:
    """Update an existing Confluence page.

    Auto-increments version number.

    Args:
        page_id: Page ID to update
        title: New page title
        body: New content in Confluence storage format (HTML)
        version_comment: Optional change description
        verify_ssl: Whether to verify SSL certificates

    Returns:
        Dict with 'success' and page details, or 'error'.
    """
    # First, get current version number
    try:
        get_resp = _confluence_request(
            "GET",
            f"/rest/api/content/{page_id}",
            params={"expand": "version"},
            verify_ssl=verify_ssl,
        )

        if not get_resp.ok:
            return _resp_err(
                "Failed to get page version", get_resp,
            )

        current_version = (
            get_resp.json()
            .get("version", {})
            .get("number", 0)
        )
    except ValueError:
        return _err(_NOT_CONFIGURED_MSG)
    except requests.exceptions.RequestException as e:
        return _err(f"Confluence request error: {e!s}")

    # Build update payload
    version_payload: dict[str, Any] = {
        "number": current_version + 1,
    }
    if version_comment:
        version_payload["message"] = version_comment

    payload: dict[str, Any] = {
        "type": "page",
        "title": title,
        "body": {
            "storage": {
                "value": body,
                "representation": "storage",
            }
        },
        "version": version_payload,
    }

    try:
        resp = _confluence_request(
            "PUT",
            f"/rest/api/content/{page_id}",
            json=payload,
            verify_ssl=verify_ssl,
        )

        if not resp.ok:
            return _resp_err("Failed to update page", resp)

        data = resp.json()
        return {
            "success": True,
            "id": data.get("id"),
            "title": data.get("title"),
            "version": data.get("version", {}).get("number"),
            "url": data.get("_links", {}).get("webui"),
        }
    except ValueError:
        return _err(_NOT_CONFIGURED_MSG)
    except requests.exceptions.RequestException as e:
        return _err(f"Confluence request error: {e!s}")
