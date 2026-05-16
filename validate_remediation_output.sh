#!/bin/bash
#
# Validation Script for Remediation Agent Output
# Checks that all required output files exist and have correct structure
#

set -e

RESULTS_DIR="/addon/results"
PASSED=0
FAILED=0

echo "=============================================="
echo "Remediation Agent Output Validation"
echo "=============================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    PASSED=$((PASSED + 1))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    FAILED=$((FAILED + 1))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check 1: File existence
echo "1. Checking output files exist..."
echo ""

files=(
    "remediation_report.json"
    "github_issues_created.json"
    "github-remediate.json"
    "remediation_metadata.json"
)

for file in "${files[@]}"; do
    if [ -f "$RESULTS_DIR/$file" ]; then
        check_pass "File exists: $file"
    else
        check_fail "File missing: $file"
    fi
done

echo ""

# Check 2: JSON validity
echo "2. Checking JSON validity..."
echo ""

for file in "${files[@]}"; do
    if [ -f "$RESULTS_DIR/$file" ]; then
        if jq empty "$RESULTS_DIR/$file" 2>/dev/null; then
            check_pass "Valid JSON: $file"
        else
            check_fail "Invalid JSON: $file"
        fi
    fi
done

echo ""

# Check 3: github-remediate.json structure (CRITICAL)
echo "3. Checking github-remediate.json structure (PRIMARY OUTPUT)..."
echo ""

if [ -f "$RESULTS_DIR/github-remediate.json" ]; then
    # Must be an array
    type=$(jq -r 'type' "$RESULTS_DIR/github-remediate.json")
    if [ "$type" == "array" ]; then
        check_pass "github-remediate.json is a bare array"
    else
        check_fail "github-remediate.json is not an array (found: $type)"
    fi

    # Check array length
    length=$(jq 'length' "$RESULTS_DIR/github-remediate.json")
    if [ "$length" -gt 0 ]; then
        check_pass "Contains $length remediation(s)"

        # Check first entry structure
        required_keys=(
            "issue_id"
            "severity"
            "type"
            "title"
            "branch_name"
            "commit_message"
            "file_changes"
            "pr_details"
            "metadata"
        )

        for key in "${required_keys[@]}"; do
            has_key=$(jq ".[0] | has(\"$key\")" "$RESULTS_DIR/github-remediate.json")
            if [ "$has_key" == "true" ]; then
                check_pass "Has required key: $key"
            else
                check_fail "Missing required key: $key"
            fi
        done

        # Check file_changes structure
        file_changes_count=$(jq '.[0].file_changes | length' "$RESULTS_DIR/github-remediate.json")
        if [ "$file_changes_count" -gt 0 ]; then
            check_pass "First entry has $file_changes_count file change(s)"

            # Check file_changes has full_file_after_changes
            has_full_file=$(jq '.[0].file_changes[0] | has("full_file_after_changes")' "$RESULTS_DIR/github-remediate.json")
            if [ "$has_full_file" == "true" ]; then
                check_pass "File changes include full_file_after_changes"

                # Check it's not empty
                full_file_len=$(jq -r '.[0].file_changes[0].full_file_after_changes | length' "$RESULTS_DIR/github-remediate.json")
                if [ "$full_file_len" -gt 0 ]; then
                    check_pass "full_file_after_changes is not empty ($full_file_len chars)"
                else
                    check_fail "full_file_after_changes is empty"
                fi
            else
                check_fail "File changes missing full_file_after_changes"
            fi

            # Check patches structure
            patches_count=$(jq '.[0].file_changes[0].patches | length' "$RESULTS_DIR/github-remediate.json")
            if [ "$patches_count" -gt 0 ]; then
                check_pass "File changes include $patches_count patch(es)"
            else
                check_warn "File changes have no patches"
            fi
        else
            check_warn "First entry has no file changes"
        fi

        # Check pr_details structure
        pr_keys=(
            "title"
            "body"
            "labels"
            "reviewers"
        )

        for key in "${pr_keys[@]}"; do
            has_key=$(jq ".[0].pr_details | has(\"$key\")" "$RESULTS_DIR/github-remediate.json")
            if [ "$has_key" == "true" ]; then
                check_pass "PR details has: $key"
            else
                check_fail "PR details missing: $key"
            fi
        done

    else
        check_warn "github-remediate.json is empty (no remediations)"
    fi
fi

echo ""

# Check 4: Metadata summary
echo "4. Checking remediation_metadata.json..."
echo ""

if [ -f "$RESULTS_DIR/remediation_metadata.json" ]; then
    total=$(jq -r '.summary.total_remediations' "$RESULTS_DIR/remediation_metadata.json")
    files_modified=$(jq -r '.summary.total_file_changes' "$RESULTS_DIR/remediation_metadata.json")

    check_pass "Total remediations: $total"
    check_pass "Total file changes: $files_modified"

    # Print severity breakdown
    echo ""
    echo "   Severity Breakdown:"
    jq -r '.summary.by_severity | to_entries | .[] | "     \(.key): \(.value)"' "$RESULTS_DIR/remediation_metadata.json"

    echo ""
    echo "   Type Breakdown:"
    jq -r '.summary.by_type | to_entries | .[] | "     \(.key): \(.value)"' "$RESULTS_DIR/remediation_metadata.json"
fi

echo ""

# Check 5: Remediation report completeness
echo "5. Checking remediation_report.json completeness..."
echo ""

if [ -f "$RESULTS_DIR/remediation_report.json" ]; then
    total_issues=$(jq -r '.total_issues' "$RESULTS_DIR/remediation_report.json")
    total_occurrences=$(jq -r '.total_occurrences' "$RESULTS_DIR/remediation_report.json")
    issues_count=$(jq '.issues | length' "$RESULTS_DIR/remediation_report.json")

    check_pass "Total issues: $total_issues"
    check_pass "Total occurrences: $total_occurrences"
    check_pass "Issues in report: $issues_count"

    # Check timestamp
    generated_at=$(jq -r '.generated_at' "$RESULTS_DIR/remediation_report.json")
    if [ "$generated_at" != "null" ]; then
        check_pass "Generated at: $generated_at"
    else
        check_fail "Missing generated_at timestamp"
    fi
fi

echo ""

# Summary
echo "=============================================="
echo "Validation Summary"
echo "=============================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All validation checks passed!${NC}"
    echo ""
    echo "Output is ready for Agent 3 (PR Creator)"
    exit 0
else
    echo -e "${RED}✗ Validation failed with $FAILED error(s)${NC}"
    echo ""
    echo "Please review the output files and fix any issues before proceeding."
    exit 1
fi
