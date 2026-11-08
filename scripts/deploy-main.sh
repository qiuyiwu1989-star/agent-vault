#!/usr/bin/env bash
# Run on the production host after fetching an approved main commit.
set -euo pipefail
cd /opt/agent-vault
expected="${1:?Pass the approved full main commit SHA}"
test "$(git rev-parse origin/main)" = "$expected"
test -z "$(git status --porcelain --untracked-files=no)"
git merge --ff-only origin/main
python3 -m compileall -q -x '(^|/)\._' src
sudo systemctl restart agent-vault.service
sudo systemctl is-active --quiet agent-vault.service
code=$(curl -ks --max-time 15 -o /dev/null -w '%{http_code}' --resolve qiuyiwu.com:443:127.0.0.1 https://qiuyiwu.com/vault/)
test "$code" = 200
git rev-parse HEAD | sudo tee /opt/agent-vault/DEPLOYED_COMMIT >/dev/null
