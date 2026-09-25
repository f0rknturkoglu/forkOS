#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${REPO_ROOT}/.vendor/career-ops"
PINNED_COMMIT="6326eb5d3804e8cb20d28acd5701a4e603a301f9"
PINNED_VERSION="1.34.0"
REPO_URL="https://github.com/career-ops-hq/career-ops.git"

echo "=== Setting up pinned career-ops engine (${PINNED_VERSION} @ ${PINNED_COMMIT:0:7}) ==="

if [ ! -d "${TARGET_DIR}/.git" ]; then
    echo "Cloning career-ops into ${TARGET_DIR}..."
    mkdir -p "$(dirname "${TARGET_DIR}")"
    git clone "${REPO_URL}" "${TARGET_DIR}"
fi

cd "${TARGET_DIR}"
echo "Checking out pinned commit ${PINNED_COMMIT}..."
git fetch origin "${PINNED_COMMIT}" --depth 1 2>/dev/null || git fetch origin --depth 1
git checkout -q "${PINNED_COMMIT}"

ACTUAL_COMMIT=$(git rev-parse HEAD)
if [ "${ACTUAL_COMMIT}" != "${PINNED_COMMIT}" ]; then
    echo "ERROR: Commit mismatch! Expected ${PINNED_COMMIT}, got ${ACTUAL_COMMIT}" >&2
    exit 1
fi

echo "Installing minimal Node.js runtime dependencies..."
npm install --ignore-scripts --no-audit

echo "Verifying package.json version..."
ACTUAL_VERSION=$(node -p "require('./package.json').version")
if [ "${ACTUAL_VERSION}" != "${PINNED_VERSION}" ]; then
    echo "ERROR: Version mismatch! Expected ${PINNED_VERSION}, got ${ACTUAL_VERSION}" >&2
    exit 1
fi

echo "=== career-ops setup complete: ${ACTUAL_VERSION} (${ACTUAL_COMMIT}) ==="
