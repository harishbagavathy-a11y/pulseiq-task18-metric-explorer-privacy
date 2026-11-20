"""Test Suite: Zero Secrets in Repository Codebase
Verifies that no API keys, private credentials, or secrets are hardcoded in tracked files,
and that .gitignore strictly excludes .streamlit/secrets.toml.
"""

import os
import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Patterns that indicate accidentally hardcoded secrets
SUSPICIOUS_PATTERNS = [
    re.compile(r'(?i)(?:api_key|secret_key|private_key|password|auth_token)\s*=\s*["\'][A-Za-z0-9_\-]{16,}["\']'),
    re.compile(r'(?i)ghp_[A-Za-z0-9]{36}'),  # GitHub PAT
    re.compile(r'(?i)AKIA[0-9A-Z]{16}'),     # AWS Access Key
    re.compile(r'-----BEGIN\s+(?:RSA|OPENSSH|DSA|EC)?\s*PRIVATE KEY-----'),
]

# Files/folders to ignore during secret scanning
EXCLUDE_PATHS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".streamlit/secrets.toml",  # Local secret file (git-ignored)
    ".venv",
    "venv",
    "screenshots",
}


class TestNoSecretsInRepository(unittest.TestCase):
    def test_gitignore_contains_secrets_toml(self):
        """Verify .gitignore explicitly prevents committing .streamlit/secrets.toml."""
        gitignore_path = PROJECT_ROOT / ".gitignore"
        self.assertTrue(gitignore_path.exists(), ".gitignore must exist in project root")
        
        with open(gitignore_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn(".streamlit/secrets.toml", content, ".gitignore must ignore .streamlit/secrets.toml")
        self.assertIn("*.secret", content, ".gitignore must ignore *.secret files")
        self.assertIn("*.env", content, ".gitignore must ignore *.env files")

    def test_no_hardcoded_secrets_in_python_and_markdown(self):
        """Scans tracked Python, Markdown, and Config files for leaked secrets."""
        scanned_count = 0
        leaks_found = []

        for root, dirs, files in os.walk(PROJECT_ROOT):
            # Prune excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_PATHS]
            
            for file in files:
                rel_path = Path(root, file).relative_to(PROJECT_ROOT).as_posix()
                if any(rel_path.startswith(ex) for ex in EXCLUDE_PATHS):
                    continue
                
                # Only scan code and config
                if file.endswith((".py", ".md", ".json", ".yml", ".yaml", ".bat", ".sh", ".toml.example")):
                    scanned_count += 1
                    file_path = Path(root, file)
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                        for line_no, line in enumerate(lines, 1):
                            for pattern in SUSPICIOUS_PATTERNS:
                                if pattern.search(line):
                                    leaks_found.append(f"{rel_path}:{line_no} -> {line.strip()[:60]}")

        self.assertEqual(
            len(leaks_found), 0,
            f"Potential secrets found in repository:\n" + "\n".join(leaks_found)
        )
        self.assertGreater(scanned_count, 5, "Should scan at least 5 repository files")


if __name__ == "__main__":
    unittest.main()
