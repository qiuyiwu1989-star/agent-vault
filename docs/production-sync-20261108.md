# Production synchronization — 2026-11-08

Current running source was captured from /opt/agent-vault. This branch reconciles production additions with the existing GitHub repository without removing repository-only files. No database, private notes, credentials or public content bodies are included. Historical backup files and macOS metadata are excluded.

Validation: 49 Python tests ran, 46 passed and 3 skipped. Production /vault/ returned HTTPS 200. This synchronization does not redeploy or overwrite production.

Production is not a Git checkout. Merge and deployment remain separate; inspect the PR before treating main as an exact production checkout.
