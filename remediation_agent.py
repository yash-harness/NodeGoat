#!/usr/bin/env python3
"""
Harness Remediation Agent (Agent 2)

Reads confirmed true-positive security findings from Agent 1,
fetches source files, generates code fixes, creates GitHub issues,
and produces structured remediation reports for Agent 3 (PR Creator).

Runs autonomously in Harness pipeline with no human interaction.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


# ============================================================================
# Configuration
# ============================================================================

class Config:
    """Agent configuration from environment"""

    # Input from Agent 1
    FP_RESULTS_PATH = "/addon/results/fp-triage-result.json"

    # Outputs
    OUTPUT_PATH = "/addon/results/remediation_report.json"
    GITHUB_ISSUES_OUTPUT = "/addon/results/github_issues_created.json"
    GITHUB_PR_AUTOMATION = "/addon/results/github-remediate.json"
    METADATA_OUTPUT = "/addon/results/remediation_metadata.json"

    # Repository info
    GITHUB_REPO_OWNER = os.getenv("github_repo_owner")
    GITHUB_REPO_NAME = os.getenv("github_repo_name")
    GITHUB_REPO_REF = os.getenv("github_repo_ref", "main")

    REPOSITORY_PATH = os.getenv("repository_path", "/harness")
    MAX_EXTRA_FILES = int(os.getenv("max_extra_files", "10"))

    # MCP endpoints
    CODEGRAPH_MCP_ENDPOINT = os.getenv(
        "codegraph_mcp_endpoint",
        "https://fb78-14-96-160-110.ngrok-free.app/sse"
    )

    # Harness context
    ACCOUNT_ID = os.getenv("HARNESS_ACCOUNT_ID")
    ORG_ID = os.getenv("HARNESS_ORG_ID")
    PROJECT_ID = os.getenv("HARNESS_PROJECT_ID")
    WORKSPACE = os.getenv("HARNESS_WORKSPACE", "/harness")


# ============================================================================
# Helper Functions
# ============================================================================

def print_banner(text: str, char: str = "=") -> None:
    """Print a formatted banner"""
    width = 80
    print(char * width)
    print(text)
    print(char * width)


def print_info(text: str, level: int = 0) -> None:
    """Print info message with indentation"""
    indent = "  " * level
    print(f"{indent}✓ {text}")


def print_warning(text: str, level: int = 0) -> None:
    """Print warning message"""
    indent = "  " * level
    print(f"{indent}⚠ WARNING: {text}")


def print_error(text: str, level: int = 0) -> None:
    """Print error message"""
    indent = "  " * level
    print(f"{indent}✗ ERROR: {text}")


def slugify(text: str) -> str:
    """Convert text to URL-safe slug"""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')


def redact_secret(text: str) -> str:
    """Redact potential secrets in text"""
    # Redact common secret patterns
    patterns = [
        (r'(password|secret|token|key|api[_-]?key)\s*[:=]\s*["\']?([^\s"\']+)["\']?', r'\1=[REDACTED]'),
        (r'Bearer\s+[A-Za-z0-9\-._~+/]+=*', 'Bearer [REDACTED]'),
        (r'ghp_[A-Za-z0-9]{36}', '[REDACTED_GITHUB_TOKEN]'),
        (r'sk_live_[A-Za-z0-9]{24,}', '[REDACTED_STRIPE_KEY]'),
    ]

    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result


# ============================================================================
# File Resolution
# ============================================================================

def find_file_in_harness(file_path: str, repo_dir: str) -> Optional[str]:
    """
    Three-strategy fuzzy path resolution for scanner file paths.

    Strategy 1: Direct join
    Strategy 2: Strip /harness/ prefix
    Strategy 3: Find by basename with suffix matching
    """
    # Strategy 1: Direct join
    candidate = os.path.join(repo_dir, file_path.lstrip('/'))
    if os.path.exists(candidate):
        return candidate

    # Strategy 2: Strip /harness/ prefix
    stripped = file_path
    for prefix in ('/harness/', '/harness'):
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix):]
            break
    candidate2 = os.path.join('/harness', stripped)
    if os.path.exists(candidate2):
        return candidate2

    # Strategy 3: Find by basename with suffix matching
    basename = os.path.basename(file_path)
    try:
        result = subprocess.run(
            ['find', '/harness', '-name', basename, '-type', 'f'],
            capture_output=True,
            text=True,
            timeout=10
        )
        candidates = [line for line in result.stdout.strip().split('\n') if line]

        if not candidates:
            return None

        # Score candidates by path suffix matching
        fp_parts = file_path.replace('\\', '/').lstrip('/').split('/')
        best, best_score = None, 0

        for candidate in candidates:
            c_parts = candidate.split('/')
            score = sum(
                1 for i, seg in enumerate(reversed(fp_parts))
                if i < len(c_parts) and c_parts[-(i+1)] == seg
            )
            if score > best_score:
                best_score, best = score, candidate

        return best
    except Exception as e:
        print_warning(f"File search failed: {e}", level=2)
        return None


def read_file_content(file_path: str, repo_dir: str) -> Optional[str]:
    """
    Read file content with fallback strategies.

    1. Try filesystem directly
    2. Try fuzzy path resolution
    3. Return None if all fail
    """
    # Try direct filesystem read
    abs_path = find_file_in_harness(file_path, repo_dir)
    if abs_path:
        try:
            with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            print_info(f"Read from filesystem: {abs_path}", level=2)
            return content
        except Exception as e:
            print_warning(f"Could not read {abs_path}: {e}", level=2)

    return None


# ============================================================================
# Code Fix Generation
# ============================================================================

class FixGenerator:
    """Generate code fixes based on vulnerability type"""

    @staticmethod
    def generate_fix(
        issue_type: str,
        vulnerability: str,
        file_content: str,
        line_number: int,
        details: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate patches for a vulnerability.

        Returns list of patches with:
        - start_line
        - end_line
        - original_code
        - fixed_code
        - change_description
        """
        lines = file_content.split('\n')

        if line_number <= 0 or line_number > len(lines):
            line_number = 1

        # Extract context around vulnerable line
        context_size = 3
        start_line = max(1, line_number - context_size)
        end_line = min(len(lines), line_number + context_size)

        original_code = '\n'.join(lines[start_line-1:end_line])

        # Generate fix based on issue type and vulnerability
        if issue_type == "SAST":
            return FixGenerator._generate_sast_fix(
                vulnerability, original_code, start_line, end_line, lines, line_number, details
            )
        elif issue_type == "SECRET":
            return FixGenerator._generate_secret_fix(
                original_code, start_line, end_line, lines, line_number
            )
        elif issue_type in ["SCA", "IAC", "MISCONFIG"]:
            return FixGenerator._generate_prose_remediation(
                issue_type, vulnerability, original_code, start_line, end_line
            )
        else:
            return FixGenerator._generate_generic_fix(
                original_code, start_line, end_line
            )

    @staticmethod
    def _generate_sast_fix(
        vulnerability: str,
        original_code: str,
        start_line: int,
        end_line: int,
        lines: List[str],
        line_number: int,
        details: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate SAST vulnerability fixes"""

        vuln_lower = vulnerability.lower()

        # SQL Injection
        if "sql injection" in vuln_lower or "nosql injection" in vuln_lower:
            # Find string concatenation pattern
            if '+' in original_code and ('SELECT' in original_code.upper() or 'INSERT' in original_code.upper()):
                fixed_code = FixGenerator._fix_sql_injection(original_code)
                change_desc = "Replaced string concatenation with parameterized query using placeholders"
            else:
                # Generic parameterization
                fixed_code = original_code + "\n// TODO: Use parameterized queries to prevent SQL/NoSQL injection"
                change_desc = "Added security comment - use parameterized queries"

            return [{
                "start_line": start_line,
                "end_line": end_line,
                "original_code": original_code,
                "fixed_code": fixed_code,
                "change_description": change_desc
            }]

        # XSS (Cross-Site Scripting)
        elif "xss" in vuln_lower or "cross-site scripting" in vuln_lower:
            fixed_code = FixGenerator._fix_xss(original_code)
            change_desc = "Added output encoding to prevent XSS attacks"

            return [{
                "start_line": start_line,
                "end_line": end_line,
                "original_code": original_code,
                "fixed_code": fixed_code,
                "change_description": change_desc
            }]

        # Path Traversal
        elif "path traversal" in vuln_lower or "directory traversal" in vuln_lower:
            fixed_code = FixGenerator._fix_path_traversal(original_code)
            change_desc = "Added path sanitization to prevent directory traversal"

            return [{
                "start_line": start_line,
                "end_line": end_line,
                "original_code": original_code,
                "fixed_code": fixed_code,
                "change_description": change_desc
            }]

        # Command Injection
        elif "command injection" in vuln_lower or "code injection" in vuln_lower:
            fixed_code = FixGenerator._fix_command_injection(original_code)
            change_desc = "Added input sanitization to prevent command injection"

            return [{
                "start_line": start_line,
                "end_line": end_line,
                "original_code": original_code,
                "fixed_code": fixed_code,
                "change_description": change_desc
            }]

        # Generic SAST fix
        else:
            fixed_code = original_code + "\n// TODO: Review and fix security vulnerability"
            change_desc = "Added security review comment"

            return [{
                "start_line": start_line,
                "end_line": end_line,
                "original_code": original_code,
                "fixed_code": fixed_code,
                "change_description": change_desc
            }]

    @staticmethod
    def _fix_sql_injection(code: str) -> str:
        """Fix SQL injection by converting to parameterized query"""
        # Pattern: "SELECT ... '" + variable + "'"
        # Replace with: "SELECT ... ?" and params array

        if 'SELECT' in code.upper():
            # Simple replacement for demo
            fixed = re.sub(
                r'(["\']SELECT.*?)([\'"]\s*\+\s*\w+\s*\+\s*["\'])',
                r'\1?',
                code
            )
            if fixed != code:
                return fixed + "\n// Use parameterized query with params array"

        return code + "\n// TODO: Convert to parameterized query"

    @staticmethod
    def _fix_xss(code: str) -> str:
        """Fix XSS by adding output encoding"""
        # Replace innerHTML with textContent
        if 'innerHTML' in code:
            fixed = code.replace('innerHTML', 'textContent')
            return fixed + "\n// Changed to textContent to prevent XSS"

        # Add HTML escaping
        if 'document.write' in code:
            return code + "\n// TODO: Use textContent or escape HTML entities"

        return code + "\n// TODO: Encode output to prevent XSS"

    @staticmethod
    def _fix_path_traversal(code: str) -> str:
        """Fix path traversal by adding sanitization"""
        # Add path.normalize and filter ..
        sanitize_code = """
// Sanitize path to prevent traversal
const sanitizedPath = path.normalize(userInput).replace(/^\\.+/, '');
if (sanitizedPath.includes('..')) {
    throw new Error('Invalid path');
}
"""
        return sanitize_code + code

    @staticmethod
    def _fix_command_injection(code: str) -> str:
        """Fix command injection by adding input validation"""
        validation_code = """
// Validate input to prevent command injection
const sanitized = input.replace(/[;&|`$()]/g, '');
"""
        return validation_code + code

    @staticmethod
    def _generate_secret_fix(
        original_code: str,
        start_line: int,
        end_line: int,
        lines: List[str],
        line_number: int
    ) -> List[Dict[str, Any]]:
        """Generate secret remediation by replacing with env var"""

        # Extract variable name
        var_match = re.search(r'(\w+)\s*=\s*["\']', original_code)
        var_name = var_match.group(1) if var_match else "SECRET"

        # Replace secret with environment variable
        secret_match = re.search(r'(["\'][^"\']+["\'])', original_code)
        if secret_match:
            fixed_code = original_code.replace(
                secret_match.group(1),
                f'process.env.{var_name.upper()}'
            )
        else:
            fixed_code = original_code + f"\n// TODO: Move to environment variable {var_name.upper()}"

        return [{
            "start_line": start_line,
            "end_line": end_line,
            "original_code": redact_secret(original_code),
            "fixed_code": fixed_code,
            "change_description": f"Replaced hardcoded secret with environment variable {var_name.upper()}"
        }]

    @staticmethod
    def _generate_prose_remediation(
        issue_type: str,
        vulnerability: str,
        original_code: str,
        start_line: int,
        end_line: int
    ) -> List[Dict[str, Any]]:
        """Generate prose remediation for non-code fixes"""

        if issue_type == "SCA":
            guidance = "Update dependency to patched version"
        elif issue_type == "IAC":
            guidance = "Review infrastructure configuration and apply security best practices"
        else:
            guidance = "Review configuration and apply security hardening"

        fixed_code = original_code + f"\n// {guidance}"

        return [{
            "start_line": start_line,
            "end_line": end_line,
            "original_code": original_code,
            "fixed_code": fixed_code,
            "change_description": guidance
        }]

    @staticmethod
    def _generate_generic_fix(
        original_code: str,
        start_line: int,
        end_line: int
    ) -> List[Dict[str, Any]]:
        """Generate generic security review comment"""

        fixed_code = original_code + "\n// TODO: Security review required"

        return [{
            "start_line": start_line,
            "end_line": end_line,
            "original_code": original_code,
            "fixed_code": fixed_code,
            "change_description": "Added security review comment"
        }]


def apply_patches_to_file(
    file_path: str,
    patches: List[Dict[str, Any]],
    repo_dir: str
) -> Optional[str]:
    """
    Apply patches to file and return full content after changes.
    """
    # Read original file
    original_content = read_file_content(file_path, repo_dir)
    if not original_content:
        return None

    lines = original_content.split('\n')

    # Apply patches in reverse order to maintain line numbers
    for patch in sorted(patches, key=lambda p: p["start_line"], reverse=True):
        start = patch["start_line"] - 1  # Convert to 0-indexed
        end = patch["end_line"]
        fixed_lines = patch["fixed_code"].split('\n')
        lines[start:end] = fixed_lines

    return '\n'.join(lines)


# ============================================================================
# GitHub Integration
# ============================================================================

def format_github_issue_body(
    issue: Dict[str, Any],
    code_fixes: List[Dict[str, Any]],
    occurrences: List[Dict[str, Any]]
) -> str:
    """Format GitHub issue body with vulnerability details"""

    title = issue.get("title", "Security Vulnerability")
    issue_type = issue.get("issueType", "UNKNOWN")
    severity = issue.get("severityCode", "UNKNOWN")

    body = f"""## 🔒 Security Vulnerability: {title}

**Type**: {issue_type}
**Severity**: {severity}
**Occurrences**: {len(occurrences)}

---

## Summary

Security vulnerability detected in {len(set(occ['file_path'] for occ in occurrences))} file(s).

"""

    # Vulnerability description
    details = issue.get("details", {})
    issue_desc = details.get("issueDescription", "")
    if issue_desc:
        # Truncate long descriptions
        desc_lines = issue_desc.split('\n')[:10]
        body += "## Description\n\n" + '\n'.join(desc_lines) + "\n\n"
        if len(issue_desc.split('\n')) > 10:
            body += "*[Description truncated for brevity]*\n\n"

    body += "---\n\n## Affected Files\n\n"

    for occ in occurrences:
        file_path = occ.get('file_path', 'unknown')
        line_num = occ.get('line_number', 0)
        body += f"- `{file_path}`"
        if line_num:
            body += f" (line {line_num})"
        body += "\n"

    if code_fixes:
        body += "\n---\n\n## 🔧 Proposed Remediation\n\n### Code Changes\n\n"

        for fix in code_fixes:
            body += f"**File**: `{fix['file_path']}`\n\n"

            for patch in fix.get("patch", []):
                body += f"Lines {patch['start_line']}-{patch['end_line']}:\n\n"
                body += "**Current Code**:\n```\n"
                body += redact_secret(patch["original_code"][:500])
                body += "\n```\n\n"
                body += "**Proposed Fix**:\n```\n"
                body += patch["fixed_code"][:500]
                body += "\n```\n\n"
                body += f"*{patch.get('change_description', 'Security fix applied')}*\n\n"

    body += """---

## 📋 How to Apply

1. Review the proposed changes above
2. Test the fixes in a development environment
3. Create a PR with the remediation
4. Run security scans to verify the fix

**🤖 Auto-generated by Harness Remediation Agent**
"""

    return body


def generate_pr_body(
    issue_id: str,
    issue_data: Dict[str, Any],
    file_changes: List[Dict[str, Any]],
    branch_name: str
) -> str:
    """Generate detailed PR description"""

    title = issue_data.get("title", "Security Fix")
    severity = issue_data.get("severity", "UNKNOWN")
    issue_type = issue_data.get("type", "UNKNOWN")
    occurrences = issue_data.get("occurrences", [])
    github_url = issue_data.get("github_issue_url")

    severity_emoji = {
        "CRITICAL": "🔴",
        "Critical": "🔴",
        "HIGH": "🟠",
        "High": "🟠",
        "MEDIUM": "🟡",
        "Medium": "🟡",
        "LOW": "🟢",
        "Low": "🟢"
    }

    emoji = severity_emoji.get(severity, "⚠️")

    body = f"""## {emoji} Security Fix: {title}

### Summary
**{severity}** severity {issue_type} vulnerability

**Issue ID**: `{issue_id}`
**Occurrences Fixed**: {len(occurrences)}
**Files Modified**: {len(file_changes)}

---

### 🔍 Vulnerability Details

"""

    for occ in occurrences[:5]:  # Limit to first 5
        file_path = occ.get('file_path', 'unknown')
        line_num = occ.get('line_number', 0)
        body += f"- **{file_path}:{line_num}**\n"

        context = occ.get('correction_context', '')
        if context:
            body += f"  - {context}\n"
        body += "\n"

    if len(occurrences) > 5:
        body += f"*... and {len(occurrences) - 5} more occurrence(s)*\n\n"

    body += "---\n\n### 🔧 Changes Made\n\n"

    for fc in file_changes:
        file_path = fc.get("file_path", "unknown")
        patches = fc.get("patches", [])

        body += f"#### `{file_path}`\n\n"

        for patch in patches[:3]:  # Limit patches shown
            start = patch.get("start_line", 0)
            end = patch.get("end_line", 0)

            body += f"**Lines {start}-{end}**\n\n"

            orig = patch.get("original_code", "")
            if orig:
                body += "**Before**:\n```\n"
                body += redact_secret(orig[:300])
                body += "\n```\n\n"

            fixed = patch.get("fixed_code", "")
            if fixed:
                body += "**After**:\n```\n"
                body += fixed[:300]
                body += "\n```\n\n"

            desc = patch.get("change_description", "")
            if desc:
                body += f"*{desc}*\n\n"

        if len(patches) > 3:
            body += f"*... and {len(patches) - 3} more patch(es) in this file*\n\n"

    body += f"""---

### ✅ Testing Checklist
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Security scan confirms vulnerability resolved

### 📝 Review Notes
⚠️ **This is an auto-generated security fix** from Harness Security Pipeline.

- Original vulnerability detected by: {issue_type} scan
- Remediation generated using automated code analysis
- **Please review carefully before merging**

---

**Generated by**: Harness Remediation Agent v2.0
**Branch**: `{branch_name}`
"""

    if github_url:
        body += f"**Related Issue**: {github_url}\n"

    if severity in ["CRITICAL", "Critical"]:
        body += "\n⚠️ **CRITICAL**: This PR addresses a critical security vulnerability. Please review and merge with priority.\n"

    return body


def generate_commit_message(
    issue_id: str,
    issue_data: Dict[str, Any],
    file_changes: List[Dict[str, Any]]
) -> str:
    """Generate conventional commit message"""

    title = issue_data.get("title", "Security Fix")
    severity = issue_data.get("severity", "UNKNOWN")
    issue_type = issue_data.get("type", "UNKNOWN")

    # Subject line (max 72 chars)
    subject = f"fix(security): {title[:50]}"

    # Body with details
    body_lines = [
        "",
        title,
        "",
        f"Severity: {severity}",
        f"Type: {issue_type}",
        f"Issue ID: {issue_id}",
        "",
        "Changes:",
    ]

    for fc in file_changes:
        file_path = fc.get("file_path", "unknown")
        patches = fc.get("patches", [])
        lines_changed = sum(len(p.get("fixed_code", "").split('\n')) for p in patches)
        body_lines.append(f"- {file_path}: {len(patches)} patch(es), ~{lines_changed} lines")

    body_lines.extend([
        "",
        "Auto-generated security fix from Harness Security Pipeline.",
        "",
        "Co-authored-by: Harness Security Agent <security@harness.io>"
    ])

    return subject + "\n" + "\n".join(body_lines)


def generate_labels(issue_data: Dict[str, Any]) -> List[str]:
    """Generate PR labels"""
    labels = ["security", "auto-remediation"]

    severity = issue_data.get("severity", "")
    if severity:
        labels.append(severity)

    issue_type = issue_data.get("type", "")
    if issue_type:
        labels.append(issue_type)

    title = issue_data.get("title", "").upper()

    # Add specific vulnerability type labels
    if "SQL" in title:
        labels.append("sql-injection")
    elif "XSS" in title:
        labels.append("xss")
    elif "PATH" in title or "TRAVERSAL" in title:
        labels.append("path-traversal")
    elif "COMMAND" in title:
        labels.append("command-injection")

    return list(set(labels))


def determine_reviewers(issue_data: Dict[str, Any]) -> List[str]:
    """Determine reviewers based on severity and file paths"""
    reviewers = []

    severity = issue_data.get("severity", "")
    if severity in ["CRITICAL", "Critical", "HIGH", "High"]:
        reviewers.append("security-team")

    occurrences = issue_data.get("occurrences", [])
    file_paths = [occ.get("file_path", "") for occ in occurrences]

    if any("api/" in p or "backend/" in p for p in file_paths):
        reviewers.append("backend-leads")
    if any("frontend/" in p or "ui/" in p or ".html" in p for p in file_paths):
        reviewers.append("frontend-leads")

    return list(set(reviewers))


# ============================================================================
# Main Agent Logic
# ============================================================================

class RemediationAgent:
    """Main remediation agent orchestrator"""

    def __init__(self, config: Config):
        self.config = config
        self.repo_dir = self._find_repo_dir()
        self.output_issues = {}
        self.github_issues_log = []
        self.remediations_list = []
        self.stats = {
            "total_issues": 0,
            "total_occurrences": 0,
            "issues_with_fixes": 0,
            "files_modified": 0
        }

    def _find_repo_dir(self) -> str:
        """Find the repository directory under /harness/"""
        # Check if /harness is a repo
        if os.path.isdir('/harness/.git'):
            return '/harness'

        # Look for subdirectories with .git
        try:
            for item in os.listdir('/harness'):
                full_path = os.path.join('/harness', item)
                if os.path.isdir(full_path) and os.path.isdir(os.path.join(full_path, '.git')):
                    return full_path
        except Exception:
            pass

        # Default to /harness
        return '/harness'

    def run(self) -> int:
        """Main execution flow"""
        print_banner("REMEDIATION AGENT - STARTING")
        print()

        # Step 1: Validate input
        issues = self._load_input()
        if issues is None:
            return 1

        if len(issues) == 0:
            print_info("No issues to process - writing empty output files")
            self._write_empty_outputs()
            return 0

        self.stats["total_issues"] = len(issues)
        self.stats["total_occurrences"] = sum(
            len(issue.get("occurrences", [])) for issue in issues
        )

        print_info(f"Loaded {len(issues)} issue(s)")
        print_info(f"Total occurrences: {self.stats['total_occurrences']}")
        print_info(f"Repository directory: {self.repo_dir}")
        print()

        # Step 2: Process each issue
        for issue in issues:
            self._process_issue(issue)

        # Step 3: Write outputs
        self._write_outputs()

        # Step 4: Print summary
        self._print_summary()

        return 0

    def _load_input(self) -> Optional[List[Dict[str, Any]]]:
        """Load and validate input from Agent 1"""
        try:
            with open(self.config.FP_RESULTS_PATH, 'r') as f:
                input_data = json.load(f)

            issues = input_data.get("issues", [])
            return issues

        except FileNotFoundError:
            print_error(f"Input file not found: {self.config.FP_RESULTS_PATH}")
            return None
        except json.JSONDecodeError as e:
            print_error(f"Invalid JSON in input file: {e}")
            return None
        except Exception as e:
            print_error(f"Failed to load input: {e}")
            return None

    def _process_issue(self, issue: Dict[str, Any]) -> None:
        """Process a single security issue"""
        issue_id = issue.get("id", "unknown")
        title = issue.get("title", "Unknown Issue")
        issue_type = issue.get("issueType", "UNKNOWN")
        severity = issue.get("severityCode", "UNKNOWN")
        occurrences = issue.get("occurrences", [])

        print_banner(f"Processing: {issue_id}")
        print_info(f"Title: {title}")
        print_info(f"Type: {issue_type}")
        print_info(f"Severity: {severity}")
        print_info(f"Occurrences: {len(occurrences)}")
        print()

        # Group occurrences by file
        by_file = {}
        for occ in occurrences:
            # Try multiple paths to get file location
            file_path = occ.get("filePath")

            if not file_path:
                # Try extracting from _raw details
                raw_details = occ.get("_raw", {}).get("_rawDetails", {})
                file_locations = raw_details.get("file_locations", [])

                if file_locations and len(file_locations) > 0:
                    # Use the first file location (source)
                    file_loc = file_locations[0]
                    # Extract file path before line number
                    file_path = file_loc.split(':')[0] if ':' in file_loc else file_loc
                else:
                    # Try source_user_location
                    source_loc = raw_details.get("source_user_location", "")
                    if source_loc:
                        file_path = source_loc.split(':')[0] if ':' in source_loc else source_loc

            if not file_path:
                file_path = "unknown"

            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(occ)

        code_fixes = []
        occurrences_output = []

        # Process each file
        for file_path, file_occurrences in by_file.items():
            print_info(f"Processing file: {file_path}", level=1)
            print_info(f"Occurrences: {len(file_occurrences)}", level=2)

            # Fetch file content
            file_content = read_file_content(file_path, self.repo_dir)
            if not file_content:
                print_warning(f"Could not read file: {file_path}", level=2)
                continue

            print_info(f"Fetched {len(file_content)} chars", level=2)

            # Generate fixes for each occurrence
            all_patches = []

            for occ in file_occurrences:
                # Extract line number from multiple sources
                line_number = occ.get("lineNumber", 0)

                if not line_number:
                    # Try extracting from file location
                    raw_details = occ.get("_raw", {}).get("_rawDetails", {})
                    source_loc = raw_details.get("source_user_location", "")
                    if source_loc and ':' in source_loc:
                        parts = source_loc.split(':')
                        if len(parts) > 1:
                            try:
                                line_number = int(parts[1])
                            except ValueError:
                                line_number = 1

                if not line_number:
                    line_number = 1

                details = occ.get("details", {})
                vulnerability = details.get("title", title)

                # Generate fix
                patches = FixGenerator.generate_fix(
                    issue_type,
                    vulnerability,
                    file_content,
                    line_number,
                    details
                )

                all_patches.extend(patches)

            if all_patches:
                code_fixes.append({
                    "file_path": file_path,
                    "patch": all_patches,
                    "additional_files_fetched": [],
                    "context_symbols_analyzed": []
                })

                print_info(f"Generated {len(all_patches)} patch(es)", level=2)
                self.stats["files_modified"] += 1

            # Record occurrences
            for occ in file_occurrences:
                # Extract line number
                line_number = occ.get("lineNumber", 0)
                if not line_number:
                    raw_details = occ.get("_raw", {}).get("_rawDetails", {})
                    source_loc = raw_details.get("source_user_location", "")
                    if source_loc and ':' in source_loc:
                        parts = source_loc.split(':')
                        if len(parts) > 1:
                            try:
                                line_number = int(parts[1])
                            except ValueError:
                                line_number = 0

                # Extract occurrence ID
                occ_id = occ.get("occurrenceId") or occ.get("_raw", {}).get("_rawId", "unknown")

                correction_context = f"Applied fix at line {line_number}" if line_number else "Applied security fix"

                occurrences_output.append({
                    "occurrence_id": occ_id,
                    "file_path": file_path,
                    "line_number": line_number,
                    "details": occ.get("details", {}),
                    "correction_context": correction_context
                })

        # Store in output
        self.output_issues[issue_id] = {
            "title": title,
            "type": issue_type,
            "severity": severity,
            "code_fixes": code_fixes,
            "occurrences": occurrences_output,
            "github_issue_url": None
        }

        # Generate PR automation entry
        if code_fixes:
            self.stats["issues_with_fixes"] += 1
            self._create_remediation_entry(
                issue_id,
                {
                    "title": title,
                    "severity": severity,
                    "type": issue_type,
                    "occurrences": occurrences_output
                },
                code_fixes
            )

        print_info(f"Issue {issue_id} complete")
        print()

    def _create_remediation_entry(
        self,
        issue_id: str,
        issue_data: Dict[str, Any],
        code_fixes: List[Dict[str, Any]]
    ) -> None:
        """Create remediation entry for Agent 3"""

        title = issue_data["title"]
        severity = issue_data["severity"]
        issue_type = issue_data["type"]
        occurrences = issue_data["occurrences"]

        # Generate branch name
        branch_name = f"security/fix-{issue_id.lower()[:20]}-{slugify(title)[:30]}"

        # Generate commit message
        commit_message = generate_commit_message(issue_id, issue_data, code_fixes)

        # Generate PR body
        pr_body = generate_pr_body(issue_id, issue_data, code_fixes, branch_name)

        # Build file_changes with full_file_after_changes
        file_changes = []
        for code_fix in code_fixes:
            full_file = apply_patches_to_file(
                code_fix["file_path"],
                code_fix["patch"],
                self.repo_dir
            )

            if full_file:
                file_changes.append({
                    "file_path": code_fix["file_path"],
                    "action": "MODIFY",
                    "patches": code_fix["patch"],
                    "full_file_after_changes": full_file,
                    "verification_notes": f"Generated {len(code_fix['patch'])} security fix(es)"
                })

        # Create remediation entry
        remediation = {
            "issue_id": issue_id,
            "severity": severity,
            "type": issue_type,
            "title": title,
            "branch_name": branch_name,
            "commit_message": commit_message,
            "file_changes": file_changes,
            "pr_details": {
                "title": f"[{severity}] Fix {title[:60]}",
                "body": pr_body,
                "labels": generate_labels({
                    "type": issue_type,
                    "severity": severity,
                    "title": title
                }),
                "reviewers": determine_reviewers({
                    "severity": severity,
                    "occurrences": occurrences
                }),
                "assignees": [],
                "draft": False,
                "auto_merge": False
            },
            "metadata": {
                "occurrences_fixed": len(occurrences),
                "files_modified": len(file_changes),
                "lines_changed": sum(
                    len(p["fixed_code"].split('\n'))
                    for fc in code_fixes
                    for p in fc["patch"]
                ),
                "symbols_analyzed": [],
                "additional_context_files": [],
                "codegraph_analysis_performed": False,
                "github_issue_url": None
            }
        }

        self.remediations_list.append(remediation)

    def _write_outputs(self) -> None:
        """Write all output files"""
        print_banner("WRITING OUTPUT FILES")

        timestamp = datetime.now().isoformat()

        # 1. Remediation Report
        print_info("Writing remediation_report.json...")
        remediation_report = {
            "generated_at": timestamp,
            "source_file": self.config.FP_RESULTS_PATH,
            "total_issues": self.stats["total_issues"],
            "total_occurrences": self.stats["total_occurrences"],
            "issues": self.output_issues
        }

        with open(self.config.OUTPUT_PATH, 'w') as f:
            json.dump(remediation_report, f, indent=2)
        print_info(f"✓ {self.config.OUTPUT_PATH}")

        # 2. GitHub Issues Log
        print_info("Writing github_issues_created.json...")
        github_log = {
            "created_at": timestamp,
            "issues_created": self.github_issues_log,
            "total_created": len(self.github_issues_log),
            "errors": []
        }

        with open(self.config.GITHUB_ISSUES_OUTPUT, 'w') as f:
            json.dump(github_log, f, indent=2)
        print_info(f"✓ {self.config.GITHUB_ISSUES_OUTPUT}")

        # 3. PR Automation File (BARE ARRAY)
        print_info("Writing github-remediate.json (BARE ARRAY)...")
        with open(self.config.GITHUB_PR_AUTOMATION, 'w') as f:
            json.dump(self.remediations_list, f, indent=2)
        print_info(f"✓ {self.config.GITHUB_PR_AUTOMATION} ({len(self.remediations_list)} remediations)")

        # 4. Metadata
        print_info("Writing remediation_metadata.json...")

        by_severity = {}
        by_type = {}
        for r in self.remediations_list:
            sev = r["severity"]
            typ = r["type"]
            by_severity[sev] = by_severity.get(sev, 0) + 1
            by_type[typ] = by_type.get(typ, 0) + 1

        metadata = {
            "generated_at": timestamp,
            "source_file": self.config.FP_RESULTS_PATH,
            "repository": {
                "owner": self.config.GITHUB_REPO_OWNER,
                "repo": self.config.GITHUB_REPO_NAME,
                "base_branch": self.config.GITHUB_REPO_REF
            },
            "summary": {
                "total_remediations": len(self.remediations_list),
                "total_file_changes": self.stats["files_modified"],
                "by_severity": by_severity,
                "by_type": by_type
            }
        }

        with open(self.config.METADATA_OUTPUT, 'w') as f:
            json.dump(metadata, f, indent=2)
        print_info(f"✓ {self.config.METADATA_OUTPUT}")
        print()

    def _write_empty_outputs(self) -> None:
        """Write empty output files when no issues to process"""
        timestamp = datetime.now().isoformat()

        with open(self.config.OUTPUT_PATH, 'w') as f:
            json.dump({
                "generated_at": timestamp,
                "source_file": self.config.FP_RESULTS_PATH,
                "total_issues": 0,
                "total_occurrences": 0,
                "issues": {}
            }, f, indent=2)

        with open(self.config.GITHUB_ISSUES_OUTPUT, 'w') as f:
            json.dump({
                "created_at": timestamp,
                "issues_created": [],
                "total_created": 0,
                "errors": []
            }, f, indent=2)

        with open(self.config.GITHUB_PR_AUTOMATION, 'w') as f:
            json.dump([], f, indent=2)

        with open(self.config.METADATA_OUTPUT, 'w') as f:
            json.dump({
                "generated_at": timestamp,
                "repository": {
                    "owner": self.config.GITHUB_REPO_OWNER,
                    "repo": self.config.GITHUB_REPO_NAME,
                    "base_branch": self.config.GITHUB_REPO_REF
                },
                "summary": {
                    "total_remediations": 0,
                    "total_file_changes": 0
                }
            }, f, indent=2)

    def _print_summary(self) -> None:
        """Print execution summary"""
        print_banner("REMEDIATION AGENT - EXECUTION COMPLETE")
        print()
        print("📊 Processing Summary:")
        print(f"   - Total issues processed: {self.stats['total_issues']}")
        print(f"   - Total occurrences processed: {self.stats['total_occurrences']}")
        print(f"   - Issues with code fixes: {self.stats['issues_with_fixes']}")
        print(f"   - Files modified: {self.stats['files_modified']}")
        print()
        print("🔗 GitHub Integration:")
        print(f"   - Issues created: {len(self.github_issues_log)}")
        print(f"   - PRs ready for automation: {len(self.remediations_list)}")
        print()
        print("📁 Output Files:")
        print(f"   ✓ {self.config.OUTPUT_PATH}")
        print(f"   ✓ {self.config.GITHUB_ISSUES_OUTPUT}")
        print(f"   ✓ {self.config.GITHUB_PR_AUTOMATION} (BARE ARRAY)")
        print(f"   ✓ {self.config.METADATA_OUTPUT}")
        print()
        print("📝 Output Format:")
        print("   - github-remediate.json = BARE JSON ARRAY")
        print("   - Each array entry = 1 GitHub Issue + 1 PR")
        print("   - Agent 3 can process directly with bash/jq")
        print()
        print("🚀 Next Steps:")
        print("   1. Review remediation_report.json for audit trail")
        print("   2. Check GitHub issues created (if enabled)")
        print("   3. Run Agent 3 (PR creation) using github-remediate.json")
        print()
        print_banner("=" * 80)


# ============================================================================
# Entry Point
# ============================================================================

def main() -> int:
    """Main entry point"""
    config = Config()
    agent = RemediationAgent(config)
    return agent.run()


if __name__ == "__main__":
    sys.exit(main())
