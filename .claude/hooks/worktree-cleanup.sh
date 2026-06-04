#!/bin/bash
# Worktree Cleanup
# Remove worktrees stale do evo-nexus (criadas por agents via isolation:worktree).
# Uso manual: bash .claude/hooks/worktree-cleanup.sh
# Uso via Makefile: make worktree-clean
#
# Regra: remove worktrees cujo branch name começa com "worktree-agent-"
# (padrão gerado pelo Claude Code/openclaude para sub-agents isolados).
# Worktrees customizadas (ex: feature branches) são preservadas.

set -uo pipefail

REPO="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
WORKTREES_DIR="$REPO/.claude/worktrees"
DRY_RUN="${DRY_RUN:-0}"

removed=0
failed=0
current_wt=""

echo "[worktree-cleanup] repo: $REPO"
echo "[worktree-cleanup] dry_run: $DRY_RUN"

# 1. Remove worktrees registradas com branch "worktree-agent-*"
while IFS= read -r line; do
  if [[ "$line" == worktree\ * ]]; then
    current_wt="${line#worktree }"
  elif [[ "$line" == branch\ refs/heads/worktree-agent-* ]]; then
    if [[ -n "$current_wt" && "$current_wt" != "$REPO" ]]; then
      if [[ "$DRY_RUN" == "1" ]]; then
        echo "[dry-run] would remove: $current_wt"
      else
        if git -C "$REPO" worktree remove --force "$current_wt" 2>/dev/null; then
          echo "[removed] $current_wt"
          removed=$((removed + 1))
        else
          echo "[failed]  $current_wt"
          failed=$((failed + 1))
        fi
      fi
    fi
  fi
done < <(git -C "$REPO" worktree list --porcelain 2>/dev/null)

# 2. Prune referências soltas no git db
git -C "$REPO" worktree prune 2>/dev/null || true

# 3. Remove diretórios órfãos (sem registro no git)
if [[ -d "$WORKTREES_DIR" ]]; then
  registered=$(git -C "$REPO" worktree list --porcelain 2>/dev/null \
    | grep "^worktree $WORKTREES_DIR" | awk '{print $2}')
  for dir in "$WORKTREES_DIR"/*/; do
    [[ -d "$dir" ]] || continue
    dir="${dir%/}"
    if ! echo "$registered" | grep -qF "$dir"; then
      if [[ "$DRY_RUN" == "1" ]]; then
        echo "[dry-run] would remove orphan dir: $dir"
      else
        rm -rf "$dir"
        echo "[removed orphan] $dir"
        removed=$((removed + 1))
      fi
    fi
  done
fi

echo "[worktree-cleanup] done — removed: $removed, failed: $failed"
