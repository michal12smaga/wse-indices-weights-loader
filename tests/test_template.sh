#!/bin/bash
# Test script for Python project template
set -e

TEMPLATE_DIR="$(pwd)"
TEST_DIR="/tmp/setup-template-test-$$"

# Step 1: Copy template to temp dir
mkdir "$TEST_DIR"
cp -r "$TEMPLATE_DIR"/* "$TEST_DIR"
cd "$TEST_DIR"

# Step 2: Run Makefile targets
for target in help check-env init-git local-dev; do
    echo "\n--- Running: make $target ---"
    make $target || echo "Target $target failed"
done

# Step 3: Clean up
cd /tmp
rm -rf "$TEST_DIR"
echo "\nAll tests completed."
