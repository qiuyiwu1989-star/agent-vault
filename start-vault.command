#!/bin/zsh
cd "$(dirname "$0")" || exit 1
export PYTHONPATH="$PWD/src"
python3 -m agent_vault.admin --root .vault/legacy-review --snapshot c160ef89c6663d65e768925b42d75a4a168947b60ca2d6b7553ff9fb505fad43 --site .vault/reader-site --with-reader
