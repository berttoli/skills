#!/usr/bin/env bash
# install.sh: link the skills listed in skills.conf into each agent's skills folder.
#
# The repo stays the single source: every installed skill is a symlink back
# into this checkout, so `git pull` updates all agents at once. Run this
# script again after adding a skill to skills.conf.
#
# Targets (folder each agent reads):
#   claude  ~/.claude/skills   Claude Code (Cursor also reads it)
#   agents  ~/.agents/skills   Codex and Cursor
#   codex   ~/.codex/skills    older Codex location, only with --codex-legacy
#
# Usage:
#   ./install.sh                 show what would change (default, writes nothing)
#   ./install.sh --apply         create missing links; skip anything already there
#   ./install.sh --apply --replace
#                                also move conflicting folders/links into
#                                ~/.skills-backup/<time>/ and link in their place
#   ./install.sh --apply --prune also remove links into this repo that
#                                skills.conf no longer lists
#   ./install.sh --uninstall     remove every link that points into this repo
#
# Options:
#   --home DIR          act on DIR instead of $HOME (for testing)
#   --config FILE       skills list (default: skills.conf next to this script)
#   --local-config FILE machine-only extras, not committed
#                       (default: skills.local.conf next to this script)
#   --codex-legacy      also link "agents" skills into ~/.codex/skills
#
# skills.conf lines:   <name> [targets]
#   targets is "all" (= claude,agents) or a comma list such as "claude".
# skills.local.conf lines:   <name> <absolute path> [targets]
#   for skills that live in another checkout on this machine.
#
# The script never deletes a real folder. --replace moves things aside;
# --uninstall and --prune remove symlinks only.

set -euo pipefail

usage() { awk 'NR == 1 {next} /^#/ {sub(/^# ?/, ""); print; next} {exit}' "$0"; }

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HOME_DIR="${HOME:-}"
CONF="$REPO/skills.conf"
LOCAL_CONF="$REPO/skills.local.conf"
MODE=plan
REPLACE=0
PRUNE=0
CODEX_LEGACY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --apply) MODE=apply ;;
    --uninstall) MODE=uninstall ;;
    --replace) REPLACE=1 ;;
    --prune) PRUNE=1 ;;
    --codex-legacy) CODEX_LEGACY=1 ;;
    --home) HOME_DIR="${2:?--home needs a folder}"; shift ;;
    --config) CONF="${2:?--config needs a file}"; shift ;;
    --local-config) LOCAL_CONF="${2:?--local-config needs a file}"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "install.sh: unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

[ -n "$HOME_DIR" ] && [ -d "$HOME_DIR" ] || { echo "install.sh: home folder not found: '$HOME_DIR'" >&2; exit 2; }
HOME_DIR="$(cd "$HOME_DIR" && pwd -P)"
[ -f "$CONF" ] || { echo "install.sh: no skills list at $CONF" >&2; exit 2; }
if [ "$REPLACE" = 1 ] && [ "$MODE" != apply ]; then echo "install.sh: --replace needs --apply" >&2; exit 2; fi
if [ "$PRUNE" = 1 ] && [ "$MODE" != apply ]; then echo "install.sh: --prune needs --apply" >&2; exit 2; fi

SKILLS_ROOT="$REPO/skills"

STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$HOME_DIR/.skills-backup/$STAMP"
CHANGED=0
SKIPPED=0
PROBLEMS=0

say() { printf '%-9s %s\n' "$1" "$2"; }

target_dir() {
  case "$1" in
    claude) echo "$HOME_DIR/.claude/skills" ;;
    agents) echo "$HOME_DIR/.agents/skills" ;;
    codex) echo "$HOME_DIR/.codex/skills" ;;
    *) return 1 ;;
  esac
}

expand_targets() {
  local spec="${1:-all}" out="" t
  [ "$spec" = all ] && spec="claude,agents"
  for t in $(echo "$spec" | tr ',' ' '); do
    target_dir "$t" >/dev/null || { echo "BAD:$t"; return; }
    out="$out $t"
    if [ "$t" = agents ] && [ "$CODEX_LEGACY" = 1 ]; then out="$out codex"; fi
  done
  echo "$out"
}

# The `name:` field inside the SKILL.md frontmatter (Cursor requires it to match the folder name).
frontmatter_name() {
  awk 'NR==1 && $0!="---" {exit} NR>1 && $0=="---" {exit}
       NR>1 && /^name:/ {sub(/^name:[ \t]*/, ""); gsub(/["\047]/, ""); print; exit}' "$1"
}

# Prints "name<TAB>source<TAB>targets" for every valid entry in both lists.
entries() {
  local name path targets rest
  while read -r name targets rest || [ -n "${name:-}" ]; do
    case "${name:-}" in ''|'#'*) continue ;; esac
    printf '%s\t%s\t%s\n' "$name" "$SKILLS_ROOT/$name" "${targets:-all}"
  done < "$CONF"
  [ -f "$LOCAL_CONF" ] || return 0
  while read -r name path targets rest || [ -n "${name:-}" ]; do
    case "${name:-}" in ''|'#'*) continue ;; esac
    printf '%s\t%s\t%s\n' "$name" "${path:-}" "${targets:-all}"
  done < "$LOCAL_CONF"
}

valid_entry() { # name source
  local name="$1" src="$2" fm
  if ! echo "$name" | grep -Eq '^[a-z0-9][a-z0-9-]*$'; then
    say problem "$name: not a valid skill name (lowercase letters, digits, hyphens)"; return 1
  fi
  case "$src" in /*) ;; *) say problem "$name: source must be an absolute path: '$src'"; return 1 ;; esac
  if [ ! -f "$src/SKILL.md" ]; then say problem "$name: no SKILL.md in $src"; return 1; fi
  fm="$(frontmatter_name "$src/SKILL.md")"
  if [ "$fm" != "$name" ]; then
    say problem "$name: SKILL.md says name '$fm'; it must match the folder name"; return 1
  fi
}

move_aside() { # dest target
  local dest="$1" t="$2"
  mkdir -p "$BACKUP/$t"
  mv "$dest" "$BACKUP/$t/"
  say moved "$dest -> $BACKUP/$t/"
}

link_one() { # name source target
  local name="$1" src="$2" t="$3" dir dest cur what
  dir="$(target_dir "$t")"
  dest="$dir/$name"
  if [ -L "$dest" ]; then
    cur="$(readlink "$dest")"
    if [ "$cur" = "$src" ]; then say ok "$t/$name"; return; fi
    what="link to $cur"
  elif [ -e "$dest" ]; then
    what="a real folder or file"
  else
    what=""
  fi

  if [ -n "$what" ]; then
    if [ "$MODE" = apply ] && [ "$REPLACE" = 1 ]; then
      move_aside "$dest" "$t"
    else
      say conflict "$t/$name is $what; left alone (use --apply --replace to back it up and link)"
      SKIPPED=$((SKIPPED + 1)); return
    fi
  fi

  if [ "$MODE" = apply ]; then
    mkdir -p "$dir"
    ln -s "$src" "$dest"
    say linked "$t/$name -> $src"
  else
    say would "link $t/$name -> $src"
  fi
  CHANGED=$((CHANGED + 1))
}

# Links in a target folder that point into this repo.
repo_links() { # target
  local dir f cur
  dir="$(target_dir "$1")"
  [ -d "$dir" ] || return 0
  for f in "$dir"/* "$dir"/.[!.]*; do
    [ -L "$f" ] || continue
    cur="$(readlink "$f")"
    case "$cur" in "$REPO"/*) printf '%s\t%s\n' "$f" "$cur" ;; esac
  done
}

WANTED=""
while IFS="$(printf '\t')" read -r name src targets; do
  if ! valid_entry "$name" "$src"; then PROBLEMS=$((PROBLEMS + 1)); continue; fi
  ts="$(expand_targets "$targets")"
  case "$ts" in *BAD:*) say problem "$name: unknown target in '$targets'"; PROBLEMS=$((PROBLEMS + 1)); continue ;; esac
  for t in $ts; do
    WANTED="$WANTED $t/$name "
    if [ "$MODE" = uninstall ]; then
      dest="$(target_dir "$t")/$name"
      # Only a link that points at this entry's own source; anything else is not ours.
      if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$src" ]; then
        rm "$dest"; say unlinked "$t/$name"; CHANGED=$((CHANGED + 1))
      fi
    else
      link_one "$name" "$src" "$t"
    fi
  done
done <<EOF
$(entries)
EOF

for t in claude agents codex; do
  while IFS="$(printf '\t')" read -r f cur; do
    [ -n "${f:-}" ] || continue
    name="$(basename "$f")"
    if [ "$MODE" = uninstall ]; then
      rm "$f"; say unlinked "$t/$name"; CHANGED=$((CHANGED + 1))
    else
      case "$WANTED" in *" $t/$name "*) continue ;; esac
      if [ "$PRUNE" = 1 ]; then
        rm "$f"; say pruned "$t/$name (not in skills.conf)"; CHANGED=$((CHANGED + 1))
      else
        say stale "$t/$name -> $cur is not in skills.conf (use --apply --prune to remove)"
      fi
    fi
  done <<EOF
$(repo_links "$t")
EOF
done

case "$MODE" in
  plan) echo "Plan only: $CHANGED change(s) to make, $SKIPPED conflict(s), $PROBLEMS problem(s). Rerun with --apply." ;;
  *) echo "Done: $CHANGED change(s), $SKIPPED conflict(s) left alone, $PROBLEMS problem(s)." ;;
esac
[ "$PROBLEMS" = 0 ]
