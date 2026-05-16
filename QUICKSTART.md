# Remediation Agent - Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### Prerequisites

- Python 3.8+
- Input file: `/addon/results/fp-triage-result.json` (from Agent 1)
- Git repository in `/harness/` or subdirectory

### Step 1: Run the Agent

```bash
cd /harness
python3 remediation_agent.py
```

**Expected Output:**
```
================================================================================
REMEDIATION AGENT - STARTING
================================================================================

✓ Loaded 11 issue(s)
✓ Total occurrences: 44
✓ Repository directory: /harness

================================================================================
Processing: 8FM3I2jdeuE9vWICYJrwGv
================================================================================
✓ Title: NoSQL Injection in allocations.js
✓ Type: SAST
✓ Severity: Critical
...
```

### Step 2: Validate Output

```bash
./validate_remediation_output.sh
```

**Expected Output:**
```
✓ All validation checks passed!
Output is ready for Agent 3 (PR Creator)
```

### Step 3: Inspect Results

```bash
# Count remediations
jq 'length' /addon/results/github-remediate.json
# Output: 9

# View summary
jq '.summary' /addon/results/remediation_metadata.json

# View first remediation
jq '.[0] | {issue_id, severity, title, branch_name}' /addon/results/github-remediate.json
```

### Step 4: Ready for Agent 3

The primary output file is now ready:
- **File**: `/addon/results/github-remediate.json`
- **Format**: Bare JSON array
- **Contains**: 9 remediations (1 per issue)
- **Each entry**: Complete PR details + file changes

---

## 📁 Output Files Overview

| File | Purpose | Consumer |
|------|---------|----------|
| `github-remediate.json` | **PRIMARY** - PR automation data | Agent 3 |
| `remediation_report.json` | Audit trail with all fixes | Human review |
| `remediation_metadata.json` | Statistics summary | Dashboards |
| `github_issues_created.json` | GitHub issues log | Tracking |

---

## 🔍 Common Commands

### View All Remediations

```bash
jq '.[] | {issue_id, severity, title, files: (.file_changes | length)}' /addon/results/github-remediate.json
```

### View Specific Remediation

```bash
# By index (0-based)
jq '.[0]' /addon/results/github-remediate.json

# By issue ID
jq '.[] | select(.issue_id == "8FM3I2jdeuE9vWICYJrwGv")' /addon/results/github-remediate.json
```

### View Fixes for a File

```bash
jq '.[] | select(.file_changes[].file_path == "app/routes/allocations.js") | {issue_id, severity, patches: .file_changes[0].patches}' /addon/results/github-remediate.json
```

### View PR Details

```bash
# PR title and labels
jq '.[0].pr_details | {title, labels}' /addon/results/github-remediate.json

# PR body (first 500 chars)
jq -r '.[0].pr_details.body' /addon/results/github-remediate.json | head -c 500
```

### View Statistics

```bash
# Summary by severity
jq '.summary.by_severity' /addon/results/remediation_metadata.json

# Summary by type
jq '.summary.by_type' /addon/results/remediation_metadata.json

# Total counts
jq '{remediations: .summary.total_remediations, files: .summary.total_file_changes}' /addon/results/remediation_metadata.json
```

---

## 🛠️ Testing with Sample Data

### Create Test Input

```bash
cat > /addon/results/fp-triage-result.json << 'EOF'
{
  "issues": [
    {
      "id": "test-001",
      "title": "SQL Injection in login.js",
      "issueType": "SAST",
      "severityCode": "Critical",
      "occurrences": [
        {
          "_raw": {
            "_rawId": "1",
            "_rawDetails": {
              "file_locations": ["app/routes/login.js:15"],
              "source_user_location": "app/routes/login.js:15"
            }
          },
          "details": {
            "title": "SQL Injection",
            "issueDescription": "User input used in SQL query without sanitization"
          }
        }
      ]
    }
  ]
}
EOF
```

### Run Agent

```bash
python3 remediation_agent.py
```

### Verify Output

```bash
./validate_remediation_output.sh
```

---

## 🔄 Integration with Agent 3

Agent 3 (PR Creator) reads `github-remediate.json` and creates PRs.

**Example workflow:**

```bash
# Agent 2 (this agent) runs
python3 remediation_agent.py

# Agent 3 processes output
cat /addon/results/github-remediate.json | jq -c '.[]' | while read -r rem; do
    issue_id=$(echo "$rem" | jq -r '.issue_id')
    branch=$(echo "$rem" | jq -r '.branch_name')
    
    echo "Creating PR for $issue_id on branch $branch"
    
    # Create branch and apply fixes
    git checkout -b "$branch"
    
    # Process file changes
    echo "$rem" | jq -c '.file_changes[]' | while read -r change; do
        file=$(echo "$change" | jq -r '.file_path')
        content=$(echo "$change" | jq -r '.full_file_after_changes')
        echo "$content" > "$file"
    done
    
    # Commit and push
    git add .
    git commit -m "$(echo "$rem" | jq -r '.commit_message')"
    git push origin "$branch"
    
    # Create PR
    gh pr create \
        --title "$(echo "$rem" | jq -r '.pr_details.title')" \
        --body "$(echo "$rem" | jq -r '.pr_details.body')"
done
```

---

## 🐛 Troubleshooting

### No remediations generated

**Check input has issues:**
```bash
jq '.issues | length' /addon/results/fp-triage-result.json
```

**Check file paths are valid:**
```bash
jq '.issues[0].occurrences[0]._raw._rawDetails.file_locations' /addon/results/fp-triage-result.json
```

### Files not found

**Verify repository location:**
```bash
ls -la /harness/.git
```

**Check file exists:**
```bash
find /harness -name "allocations.js" -type f
```

### Invalid JSON output

**Validate input first:**
```bash
jq empty /addon/results/fp-triage-result.json
```

**Check for errors in agent output:**
```bash
python3 remediation_agent.py 2>&1 | grep -i error
```

---

## 📊 Example Run Output

```
================================================================================
REMEDIATION AGENT - EXECUTION COMPLETE
================================================================================

📊 Processing Summary:
   - Total issues processed: 11
   - Total occurrences processed: 44
   - Issues with code fixes: 9
   - Files modified: 15

🔗 GitHub Integration:
   - Issues created: 0
   - PRs ready for automation: 9

📁 Output Files:
   ✓ /addon/results/remediation_report.json
   ✓ /addon/results/github_issues_created.json
   ✓ /addon/results/github-remediate.json (BARE ARRAY)
   ✓ /addon/results/remediation_metadata.json

📝 Output Format:
   - github-remediate.json = BARE JSON ARRAY
   - Each array entry = 1 GitHub Issue + 1 PR
   - Agent 3 can process directly with bash/jq

🚀 Next Steps:
   1. Review remediation_report.json for audit trail
   2. Check GitHub issues created (if enabled)
   3. Run Agent 3 (PR creation) using github-remediate.json
```

---

## 🎯 Key Success Indicators

✅ **Output validation passes** - All 33 checks pass  
✅ **Bare array format** - `github-remediate.json` is array type  
✅ **File changes included** - Each entry has `full_file_after_changes`  
✅ **PR details complete** - Title, body, labels, reviewers present  
✅ **One issue = One PR** - Each array entry maps to one PR  

---

## 📚 Additional Resources

- **Full Documentation**: See `REMEDIATION_AGENT_README.md`
- **Validation Script**: Run `./validate_remediation_output.sh`
- **Agent Code**: See `remediation_agent.py`

---

**Need Help?**

1. Run validation: `./validate_remediation_output.sh`
2. Check logs: `python3 remediation_agent.py 2>&1 | less`
3. Inspect output: `jq . /addon/results/github-remediate.json | less`

---

**Last Updated**: 2026-05-16  
**Agent Version**: 2.0
