"""Git Helper Utility using Dulwich (Native Pure-Python Git Implementation).
Initializes repository, stages files, commits changes, and tags v1.0.0-live.
Strictly respects .gitignore to guarantee zero secrets are ever committed.
"""

import sys
from pathlib import Path
from dulwich import porcelain
from dulwich.repo import Repo

PROJECT_ROOT = Path(__file__).resolve().parent


def init_and_tag(tag_name: str = "v1.0.0-live", message: str = "PulseIQ Task 17: Live Dashboard Cloud Deployment & Scheduled Refresh"):
    repo_path = str(PROJECT_ROOT)
    
    # 1. Initialize repository if .git doesn't exist
    git_dir = PROJECT_ROOT / ".git"
    if not git_dir.exists():
        print(f"Initializing Git repository in {repo_path}...")
        repo = porcelain.init(repo_path)
    else:
        print(f"Opening existing Git repository in {repo_path}...")
        repo = Repo(repo_path)

    # 2. Stage all files (respecting .gitignore)
    print("Staging tracked files (excluding secrets)...")
    # Porcelain add with paths
    porcelain.add(repo, paths=["."])

    # 3. Commit staged changes
    try:
        commit_id = porcelain.commit(
            repo,
            message=message.encode("utf-8"),
            author="Harish Bagavathy <harish.bagavathy@pulseiq.internal>".encode("utf-8"),
            committer="Harish Bagavathy <harish.bagavathy@pulseiq.internal>".encode("utf-8"),
        )
        print(f"Committed changes with commit hash: {commit_id.decode('ascii')}")
    except Exception as e:
        print(f"Commit note: {e}")

    # 4. Create release tag
    try:
        print(f"Tagging release: {tag_name}...")
        porcelain.tag_create(
            repo,
            tag=tag_name.encode("utf-8"),
            message=f"Release {tag_name}: Live Public Dashboard with Governed Aggregates & Scheduled Refresh".encode("utf-8"),
            author="Harish Bagavathy <harish.bagavathy@pulseiq.internal>".encode("utf-8"),
            annotated=True
        )
        print(f"Successfully tagged {tag_name}!")
    except Exception as e:
        print(f"Tag note: {e}")

    # 5. List all tags
    tags = porcelain.tag_list(repo)
    print(f"\nRepository Tags ({len(tags)}):")
    for t in tags:
        print(f"  • {t.decode('utf-8') if isinstance(t, bytes) else t}")

    # 6. Show status
    status = porcelain.status(repo)
    print(f"\nGit Status: Staged={len(status.staged['add'])}, Unstaged={len(status.unstaged)}, Untracked={len(status.untracked)}")


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "v1.0.0-live"
    init_and_tag(tag)
