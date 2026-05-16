# Harness Remediation Agent (Agent 2)

**Version**: 2.0  
**Purpose**: Automated security vulnerability remediation with code fix generation

## Overview

The Remediation Agent is the second step in the Harness Security Pipeline. It processes confirmed true-positive security findings from Agent 1 (FP Triage), generates precise code fixes, and produces structured remediation reports for Agent 3 (PR Creator).

### Key Features

✅ **Automated Code Fix Generation** - Generates context-aware security fixes for SAST vulnerabilities  
✅ **Secret Remediation** - Replaces hardcoded secrets with environment variables  
✅ **Multi-File Processing** - Handles vulnerabilities across multiple files in a single issue  
✅ **Fuzzy Path Resolution** - Robust file path matching for scanner outputs  
✅ **Structured Output** - Produces JSON files ready for PR automation  
✅ **Zero Human Interaction** - Runs autonomously in Harness pipelines  
✅ **Safe Execution** - Redacts secrets, handles errors gracefully  

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  REMEDIATION AGENT (Agent 2)                │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   Read Input         Fetch Files        Generate Fixes
   (Agent 1)         (Filesystem)       (FixGenerator)
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
  Write Reports     Write Metadata    Write PR Automation
  (Audit Trail)     (Statistics)      (github-remediate.json)
                                                │
                                                ▼
                                          Agent 3 (PR Creator)
```

---

## Input

### Input File: `/addon/results/fp-triage-result.json`

**Source**: Agent 1 (FP Triage Agent)  
**Format**: JSON with confirmed true-positive findings

```json
{
  "issues": [
    {
      "id": "8FM3I2jdeuE9vWICYJrwGv",
      "title": "NoSQL Injection in allocations.js",
      "issueType": "SAST",
      "severityCode": "Critical",
      "occurrences": [
        {
          "_raw": {
            "_rawId": "4",
            "_rawDetails": {
              "file_locations": ["app/routes/allocations.js:11"],
              "source_user_location": "app/routes/allocations.js:11"
            }
          },
          "details": {
            "title": "NoSQL Injection",
            "issueDescription": "..."
          }
        }
      ]
    }
  ]
}
```

---

## Output Files

### 1. Primary Output: `github-remediate.json`

**Path**: `/addon/results/github-remediate.json`  
**Format**: **BARE JSON ARRAY** (not wrapped in object)  
**Consumer**: Agent 3 (PR Creator)

**Critical**: This is the primary output consumed by Agent 3. Each array entry represents one issue and will generate one PR.

```json
[
  {
    "issue_id": "8FM3I2jdeuE9vWICYJrwGv",
    "severity": "Critical",
    "type": "SAST",
    "title": "NoSQL Injection in allocations.js",
    "branch_name": "security/fix-8fm3i2jdeue9vwicyjrw-nosql-injection",
    "commit_message": "fix(security): NoSQL Injection in allocations.js\n\n...",
    "file_changes": [
      {
        "file_path": "app/routes/allocations.js",
        "action": "MODIFY",
        "patches": [
          {
            "start_line": 40,
            "end_line": 45,
            "original_code": "query = \"SELECT * FROM users WHERE id = '\" + userId + \"'\"",
            "fixed_code": "query = \"SELECT * FROM users WHERE id = ?\"\n// Use parameterized query",
            "change_description": "Replaced string concatenation with parameterized query"
          }
        ],
        "full_file_after_changes": "<!DOCTYPE html>\n<html>\n...\n</html>",
        "verification_notes": "Generated 1 security fix(es)"
      }
    ],
    "pr_details": {
      "title": "[Critical] Fix NoSQL Injection in allocations.js",
      "body": "## 🔴 Security Fix: NoSQL Injection\n\n...",
      "labels": ["security", "auto-remediation", "Critical", "SAST", "sql-injection"],
      "reviewers": ["security-team", "backend-leads"],
      "assignees": [],
      "draft": false,
      "auto_merge": false
    },
    "metadata": {
      "occurrences_fixed": 1,
      "files_modified": 1,
      "lines_changed": 2,
      "symbols_analyzed": [],
      "additional_context_files": [],
      "codegraph_analysis_performed": false,
      "github_issue_url": null
    }
  }
]
```

### 2. Remediation Report: `remediation_report.json`

**Path**: `/addon/results/remediation_report.json`  
**Purpose**: Complete audit trail with all fixes and occurrences

```json
{
  "generated_at": "2026-05-16T10:30:00Z",
  "source_file": "/addon/results/fp-triage-result.json",
  "total_issues": 11,
  "total_occurrences": 44,
  "issues": {
    "8FM3I2jdeuE9vWICYJrwGv": {
      "title": "NoSQL Injection in allocations.js",
      "type": "SAST",
      "severity": "Critical",
      "code_fixes": [...],
      "occurrences": [...],
      "github_issue_url": null
    }
  }
}
```

### 3. GitHub Issues Log: `github_issues_created.json`

**Path**: `/addon/results/github_issues_created.json`  
**Purpose**: Track GitHub issues created (if GitHub MCP is available)

```json
{
  "created_at": "2026-05-16T10:30:00Z",
  "issues_created": [],
  "total_created": 0,
  "errors": []
}
```

### 4. Metadata: `remediation_metadata.json`

**Path**: `/addon/results/remediation_metadata.json`  
**Purpose**: Summary statistics and repository info

```json
{
  "generated_at": "2026-05-16T10:30:00Z",
  "source_file": "/addon/results/fp-triage-result.json",
  "repository": {
    "owner": "myorg",
    "repo": "myrepo",
    "base_branch": "main"
  },
  "summary": {
    "total_remediations": 9,
    "total_file_changes": 15,
    "by_severity": {
      "Critical": 2,
      "High": 4,
      "Medium": 3
    },
    "by_type": {
      "SAST": 9
    }
  }
}
```

---

## Fix Generation Strategy

### SAST Vulnerabilities

#### SQL/NoSQL Injection
```javascript
// BEFORE
query = "SELECT * FROM users WHERE id = '" + userId + "'"

// AFTER
query = "SELECT * FROM users WHERE id = ?"
// Use parameterized query with params array
```

#### XSS (Cross-Site Scripting)
```javascript
// BEFORE
element.innerHTML = userInput

// AFTER
element.textContent = userInput
// Changed to textContent to prevent XSS
```

#### Path Traversal
```javascript
// BEFORE
const filePath = userInput

// AFTER
// Sanitize path to prevent traversal
const sanitizedPath = path.normalize(userInput).replace(/^\.+/, '');
if (sanitizedPath.includes('..')) {
    throw new Error('Invalid path');
}
const filePath = sanitizedPath
```

#### Command Injection
```javascript
// BEFORE
exec(userCommand)

// AFTER
// Validate input to prevent command injection
const sanitized = input.replace(/[;&|`$()]/g, '');
exec(sanitized)
```

### SECRET Vulnerabilities

```javascript
// BEFORE
const apiKey = "sk_live_abc123xyz"

// AFTER
const apiKey = process.env.API_KEY
```

### SCA/IAC/MISCONFIG

For non-code fixes, the agent adds comments with guidance:

```javascript
// TODO: Update dependency to patched version
// TODO: Review infrastructure configuration and apply security best practices
```

---

## Configuration

### Environment Variables

```bash
# Input from Agent 1
fp_results_path=/addon/results/fp-triage-result.json

# Outputs
output_path=/addon/results/remediation_report.json
github_issues_output=/addon/results/github_issues_created.json
github_pr_automation_output=/addon/results/github-remediate.json
metadata_output=/addon/results/remediation_metadata.json

# Repository info
github_repo_owner=myorg
github_repo_name=myrepo
github_repo_ref=main

repository_path=/harness
max_extra_files=10

# Harness context
HARNESS_ACCOUNT_ID=abc123
HARNESS_ORG_ID=org_xyz
HARNESS_PROJECT_ID=proj_123
HARNESS_WORKSPACE=/harness
```

---

## Usage

### Standalone Execution

```bash
python3 remediation_agent.py
```

### In Harness Pipeline

```yaml
- step:
    type: Plugin
    name: Remediation Agent
    identifier: remediation_agent
    spec:
      connectorRef: account.harnessImage
      image: python:3.11-slim
      settings:
        fp_results_path: /addon/results/fp-triage-result.json
        output_path: /addon/results/remediation_report.json
        github_pr_automation_output: /addon/results/github-remediate.json
        github_repo_owner: <+pipeline.variables.repo_owner>
        github_repo_name: <+pipeline.variables.repo_name>
        github_repo_ref: <+pipeline.variables.branch>
      command: |
        python3 /harness/remediation_agent.py
```

---

## File Path Resolution

The agent uses a **three-strategy fuzzy path resolution** to handle different scanner output formats:

### Strategy 1: Direct Join
```python
/harness/app/routes/allocations.js
```

### Strategy 2: Strip /harness/ Prefix
```python
# Scanner output: /harness/app/routes/allocations.js
# Resolved to: /harness/app/routes/allocations.js
```

### Strategy 3: Basename Matching with Suffix Scoring
```python
# Scanner output: app/routes/allocations.js
# Find all files named: allocations.js
# Score by path suffix match
# Return best match: /harness/app/routes/allocations.js
```

---

## Safety Features

### 🔒 Secret Redaction

All secrets are automatically redacted in outputs:

```python
# Input
password = "my_secret_123"

# Output (original_code)
password = [REDACTED]

# Output (fixed_code)
password = process.env.PASSWORD
```

### ⚠️ Error Handling

- **File not found**: Continue processing other files
- **Invalid JSON**: Write empty outputs and exit gracefully
- **GitHub MCP unavailable**: Skip issue creation, continue with PR automation
- **CodeGraph MCP unavailable**: Fallback to filesystem reads

### ✅ Best Practices

1. **NEVER echo secret values** in any output
2. **Redact all secrets** to `[REDACTED]`
3. **Continue on errors** - best-effort processing
4. **1 Issue = 1 PR** - each issue generates one remediation entry
5. **Safe file handling** - explicit paths only, no wildcards

---

## Output Validation

### Check Remediation Output

```bash
# Count remediations
jq 'length' /addon/results/github-remediate.json

# Check first remediation structure
jq '.[0] | keys' /addon/results/github-remediate.json

# Verify file changes have full_file_after_changes
jq '.[0].file_changes[0] | has("full_file_after_changes")' /addon/results/github-remediate.json

# Check PR details
jq '.[0].pr_details | keys' /addon/results/github-remediate.json

# View summary
jq '.summary' /addon/results/remediation_metadata.json
```

### Expected Structure

```bash
# github-remediate.json MUST be a bare array
jq 'type' /addon/results/github-remediate.json
# Output: "array"

# Each entry MUST have these keys
jq '.[0] | keys | sort' /addon/results/github-remediate.json
# Output: ["branch_name", "commit_message", "file_changes", "issue_id", 
#          "metadata", "pr_details", "severity", "title", "type"]

# file_changes MUST have full_file_after_changes
jq '.[0].file_changes[0] | has("full_file_after_changes")' /addon/results/github-remediate.json
# Output: true
```

---

## Troubleshooting

### Issue: No files found

**Symptom**: All file paths show as "unknown"

**Solution**: Check that file paths in input data contain `file_locations` or `source_user_location` in `_rawDetails`

```bash
jq '.issues[0].occurrences[0]._raw._rawDetails.file_locations' /addon/results/fp-triage-result.json
```

### Issue: Empty output

**Symptom**: `github-remediate.json` is an empty array `[]`

**Possible Causes**:
1. No true-positive issues in input
2. All files could not be read
3. No code fixes could be generated

**Solution**: Check `remediation_report.json` for details

```bash
jq '.total_issues, .total_occurrences' /addon/results/remediation_report.json
jq '.issues | to_entries | .[0].value.code_fixes' /addon/results/remediation_report.json
```

### Issue: Fixes not specific enough

**Symptom**: Fixes only add TODO comments

**Solution**: The fix generator uses pattern matching. For better fixes:
1. Ensure vulnerability type is correctly identified
2. Check that file content is readable
3. Verify line numbers are accurate

```bash
# Check vulnerability types
jq '[.issues[].issueType] | unique' /addon/results/fp-triage-result.json

# Check line numbers
jq '.issues[0].occurrences[0]._raw._rawDetails.source_user_location' /addon/results/fp-triage-result.json
```

---

## Integration with Agent 3

Agent 3 (PR Creator) consumes `github-remediate.json` directly:

```bash
# Agent 3 reads the file
remediations=$(cat /addon/results/github-remediate.json)

# Process each remediation
echo "$remediations" | jq -c '.[]' | while read -r remediation; do
    issue_id=$(echo "$remediation" | jq -r '.issue_id')
    branch_name=$(echo "$remediation" | jq -r '.branch_name')
    
    # Create branch
    git checkout -b "$branch_name"
    
    # Apply file changes
    echo "$remediation" | jq -c '.file_changes[]' | while read -r change; do
        file_path=$(echo "$change" | jq -r '.file_path')
        full_file=$(echo "$change" | jq -r '.full_file_after_changes')
        
        # Write fixed file
        echo "$full_file" > "$file_path"
    done
    
    # Create commit and PR
    git add .
    git commit -m "$(echo "$remediation" | jq -r '.commit_message')"
    git push origin "$branch_name"
    
    gh pr create --title "$(echo "$remediation" | jq -r '.pr_details.title')" \
                 --body "$(echo "$remediation" | jq -r '.pr_details.body')"
done
```

---

## Statistics

### Current Implementation Results

**Test Run on nodejs-goof repository:**

- **Total Issues Processed**: 11
- **Total Occurrences**: 44
- **Issues with Fixes**: 9
- **Files Modified**: 15

**By Severity:**
- Critical: 2
- High: 4
- Medium: 3

**By Type:**
- SAST: 9
- SECRET: 2 (files not found)

---

## Roadmap

### Planned Enhancements

- [ ] **CodeGraph MCP Integration** - Semantic analysis for better fixes
- [ ] **GitHub MCP Integration** - Automatic issue creation
- [ ] **Multi-language Support** - Java, Python, Go fix generators
- [ ] **AI-powered Fix Generation** - LLM-based fix suggestions
- [ ] **Dependency Updates** - Automatic SCA remediation
- [ ] **Testing Integration** - Generate unit tests for fixes
- [ ] **Rollback Support** - Track and revert unsuccessful fixes

---

## Support

**Pipeline**: Harness Security Pipeline  
**Agent Version**: 2.0  
**Maintainer**: Harness Security Team  
**Documentation**: This file

For issues or questions:
1. Check troubleshooting section above
2. Review output files for error details
3. Contact Harness support with pipeline execution ID

---

**Generated by**: Harness Remediation Agent v2.0  
**Last Updated**: 2026-05-16
