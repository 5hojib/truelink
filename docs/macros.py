from __future__ import annotations

from datetime import datetime

import requests


def define_env(env) -> None:
    """
    This is the hook for defining variables, macros and filters for TrueLink documentation
    """

    @env.macro
    def github_releases(repo_name=None, token=None, limit=None):
        """
        Fetch GitHub releases and format them for changelog

        Args:
            repo_name (str): GitHub repository in format "owner/repo" (defaults to 5hojib/truelink)
            token (str, optional): GitHub token for private repos or higher rate limits
            limit (int, optional): Maximum number of releases to fetch

        Returns:
            str: Formatted markdown with releases
        """

        # Use default repo if not provided
        if repo_name is None:
            repo_name = "5hojib/truelink"

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "TrueLink-Docs",
        }

        if token:
            headers["Authorization"] = f"token {token}"

        url = f"https://api.github.com/repos/{repo_name}/releases"

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            releases = response.json()

            # Limit releases if specified
            if limit:
                releases = releases[:limit]

            changelog_content = "# Changelog\n\n"
            changelog_content += "All notable changes to this project will be documented in this file.\n\n"

            if not releases:
                changelog_content += "No releases found.\n"
                return changelog_content

            for release in releases:
                # Skip drafts
                if release.get("draft", False):
                    continue

                # Format release title
                title = release.get("name") or release.get(
                    "tag_name", "Unknown Release"
                )
                tag = release.get("tag_name", "")
                published_date = release.get("published_at", "")

                if published_date:
                    try:
                        date_obj = datetime.fromisoformat(published_date)
                        formatted_date = date_obj.strftime("%B %d, %Y")
                    except Exception:
                        formatted_date = published_date
                else:
                    formatted_date = "Unknown date"

                # Create release header
                changelog_content += f"## {title}\n\n"

                # Add metadata
                metadata_parts = []
                if formatted_date != "Unknown date":
                    metadata_parts.append(f"**Released:** {formatted_date}")
                if tag:
                    metadata_parts.append(f"**Tag:** `{tag}`")

                if metadata_parts:
                    changelog_content += " | ".join(metadata_parts) + "\n\n"

                # Add pre-release badge if applicable
                if release.get("prerelease", False):
                    changelog_content += '!!! warning "Pre-release"\n    This is a pre-release version.\n\n'

                # Add release body if it exists
                body = release.get("body", "").strip()
                if body:
                    # Process the body to make it look better
                    processed_body = process_release_body(body)
                    changelog_content += f"{processed_body}\n\n"
                else:
                    changelog_content += "No release notes provided.\n\n"

                # Add download link
                if release.get("html_url"):
                    changelog_content += (
                        f"[View on GitHub]({release['html_url']})\n\n"
                    )

                changelog_content += "---\n\n"

            return changelog_content

        except requests.exceptions.RequestException as e:
            error_msg = f"Error fetching releases from GitHub API: {e!s}"
            return f'# Changelog\n\n!!! error "API Error"\n    {error_msg}\n\nPlease check your internet connection or try again later.\n'
        except Exception as e:
            error_msg = f"Error processing releases: {e!s}"
            return f'# Changelog\n\n!!! error "Processing Error"\n    {error_msg}\n'


def process_release_body(body):
    """
    Process and clean up release body content
    """
    lines = body.split("\n")
    processed_lines = list(lines)
    return "\n".join(processed_lines)
