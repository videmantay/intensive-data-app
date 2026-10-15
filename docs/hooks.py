"""MkDocs hook: publish markdown files from the repo root as pages of the docs site.

Their relative links point at source files (`backend/app/...`, `README.md`), which aren't part
of the site, so they are rewritten to open the file in GitLab. Without a repo URL (a local
preview) the link text is kept and the link dropped.
"""

import os
import re
from pathlib import Path

from mkdocs.structure.files import File

ROOT = Path(__file__).resolve().parent.parent

# Repo-root file -> page path on the site.
PAGES = {"DEV.md": "dev.md"}

# [text](target) where target isn't a web link or an in-page anchor.
RELATIVE_LINK = re.compile(r"\[([^\]]+)\]\((?!https?://|mailto:|#)([^)\s]+)\)")


def on_files(files, config):
    repo = (config.repo_url or "").rstrip("/")
    branch = os.environ.get("CI_DEFAULT_BRANCH", "main")

    def to_repo(match: re.Match) -> str:
        text, target = match.groups()
        if not repo:
            return text
        kind = "tree" if target.endswith("/") else "blob"
        return f"[{text}]({repo}/-/{kind}/{branch}/{target})"

    for source, page in PAGES.items():
        markdown = (ROOT / source).read_text(encoding="utf-8")
        files.append(File.generated(config, page, content=RELATIVE_LINK.sub(to_repo, markdown)))
    return files
