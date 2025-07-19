from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from mkdocs.config.defaults import MkDocsConfig


def define_env(env: MkDocsConfig) -> None:
    """
    This is the hook for defining variables, macros and filters for TrueLink documentation.
    """

    @env.macro
    def github_releases(
        repo_name: str | None = None,
        token: str | None = None,
        limit: int | None = None,
    ) -> str:
        """
        Fetch GitHub releases and format them for changelog.

        Args:
            repo_name (Optional[str]): GitHub repository in format "owner/repo" (defaults to 5hojib/truelink).
            token (Optional[str]): GitHub token for private repos or higher rate limits.
            limit (Optional[int]): Maximum number of releases to fetch.

        Returns:
            str: Formatted markdown with releases.
        """

        if repo_name is None:
            repo_name = "5hojib/truelink"

        headers: dict[str, str] = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "TrueLink-Docs",
        }

        if token:
            headers["Authorization"] = f"token {token}"

        url: str = f"https://api.github.com/repos/{repo_name}/releases"

        try:
            response: requests.Response = requests.get(
                url, headers=headers, timeout=10
            )
            response.raise_for_status()
            releases: list[dict] = response.json()

            if limit:
                releases = releases[:limit]

            changelog_content: str = "# Changelog\n\n"
            changelog_content += "All notable changes to this project will be documented in this file.\n\n"

            if not releases:
                changelog_content += "No releases found.\n"
                return changelog_content

            for release in releases:
                if release.get("draft", False):
                    continue

                title: str = release.get("name") or release.get(
                    "tag_name", "Unknown Release"
                )
                tag: str = release.get("tag_name", "")
                published_date: str = release.get("published_at", "")

                if published_date:
                    try:
                        date_obj: datetime = datetime.fromisoformat(published_date)
                        formatted_date: str = date_obj.strftime("%B %d, %Y")
                    except Exception:
                        formatted_date = published_date
                else:
                    formatted_date = "Unknown date"

                changelog_content += f"## {title}\n\n"

                metadata_parts: list[str] = []
                if formatted_date != "Unknown date":
                    metadata_parts.append(f"**Released:** {formatted_date}")
                if tag:
                    metadata_parts.append(f"**Tag:** `{tag}`")

                if metadata_parts:
                    changelog_content += " | ".join(metadata_parts) + "\n\n"

                if release.get("prerelease", False):
                    changelog_content += '!!! warning "Pre-release"\n    This is a pre-release version.\n\n'

                body: str = release.get("body", "").strip()
                if body:
                    processed_body: str = process_release_body(body)
                    changelog_content += f"{processed_body}\n\n"
                else:
                    changelog_content += "No release notes provided.\n\n"

                if release.get("html_url"):
                    changelog_content += (
                        f"[View on GitHub]({release['html_url']})\n\n"
                    )

                changelog_content += "---\n\n"

            return changelog_content

        except requests.exceptions.RequestException as e:
            error_msg: str = f"Error fetching releases from GitHub API: {e!s}"
            return (
                f"# Changelog\n\n"
                f'!!! error "API Error"\n    {error_msg}\n\n'
                f"Please check your internet connection or try again later.\n"
            )
        except Exception as e:
            error_msg: str = f"Error processing releases: {e!s}"
            return f'# Changelog\n\n!!! error "Processing Error"\n    {error_msg}\n'


def process_release_body(body: str) -> str:
    """
    Process and clean up release body content.

    Args:
        body (str): The body content of the release.

    Returns:
        str: The cleaned and processed release body.
    """
    lines: list[str] = body.split("\n")
    processed_lines: list[str] = list(lines)
    return "\n".join(processed_lines)
