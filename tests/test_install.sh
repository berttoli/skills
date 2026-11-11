#!/usr/bin/env bash
# Exercise the installer through its CLI, without touching the real home.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
WORK="$(mktemp -d "$REPO/tests/.test-install.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
TRIAL_HOME="$WORK/temporary home"
mkdir -p "$TRIAL_HOME"

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
install_skills() {
  bash "$REPO/install.sh" --home "$TRIAL_HOME" --local-config /dev/null "$@"
}

# Derive expected destinations from the public list, including target overrides.
links=()
sources=()
while read -r name targets rest || [ -n "${name:-}" ]; do
  case "${name:-}" in ''|'#'*) continue ;; esac
  targets="${targets:-all}"
  for target in claude agents; do
    case ",$targets," in
      *,all,*|*,"$target",*)
        links+=("$TRIAL_HOME/.$target/skills/$name")
        sources+=("$REPO/skills/$name")
        ;;
    esac
  done
done < "$REPO/skills.conf"
[ "${#links[@]}" -gt 0 ] || fail 'skills.conf has no default destinations'

# (a) Default mode must leave even an empty home entirely unchanged.
install_skills > "$WORK/plan.log"
[ -z "$(find "$TRIAL_HOME" -mindepth 1 -print)" ] || fail 'plan changed the home'
printf 'PASS: default run changes nothing\n'

# Keep unrelated objects in both destinations to test uninstall's ownership rule.
for target in claude agents; do
  dest="$TRIAL_HOME/.$target/skills"
  mkdir -p "$dest/keep-directory"
  printf 'keep directory\n' > "$dest/keep-directory/marker"
  printf 'keep file\n' > "$dest/keep-file"
  ln -s /dev/null "$dest/keep-link"
done

# (b) Apply must create each configured link to its actual skill directory.
install_skills --apply > "$WORK/apply.log"
for ((i = 0; i < ${#links[@]}; i++)); do
  [ -L "${links[i]}" ] || fail "missing link: ${links[i]##*/}"
  [ "$(readlink "${links[i]}")" = "${sources[i]}" ] || fail 'wrong link source'
  [ -f "${links[i]}/SKILL.md" ] || fail 'link does not resolve to a skill'
done
[ ! -e "$TRIAL_HOME/.codex" ] || fail 'apply created legacy Codex destination'
printf 'PASS: apply links skills to configured destinations\n'

# (c) A real folder at a configured destination must be reported and preserved.
conflict="${links[0]}"
rm "$conflict"
mkdir "$conflict"
printf 'keep conflict\n' > "$conflict/marker"
install_skills --apply > "$WORK/conflict.log"
conflict_target="${conflict#"$TRIAL_HOME/."}"
conflict_target="${conflict_target/\/skills\///}"
awk -v target="$conflict_target" '
  $1 == "conflict" && $2 == target && /left alone/ { found = 1 }
  END { exit !found }
' "$WORK/conflict.log" || fail 'conflict was not reported'
[ -d "$conflict" ] && [ ! -L "$conflict" ] || fail 'conflict folder was replaced'
[ "$(cat "$conflict/marker")" = 'keep conflict' ] || fail 'conflict contents changed'
for ((i = 1; i < ${#links[@]}; i++)); do
  [ -L "${links[i]}" ] || fail 'conflict disturbed another skill link'
  [ "$(readlink "${links[i]}")" = "${sources[i]}" ] || fail 'conflict changed another link'
done
printf 'PASS: real folder conflict is reported and left alone\n'

# (d) Uninstall removes owned links, preserving the conflict and unrelated objects.
install_skills --uninstall > "$WORK/uninstall.log"
for ((i = 1; i < ${#links[@]}; i++)); do
  [ ! -e "${links[i]}" ] && [ ! -L "${links[i]}" ] || fail 'uninstall left a skill link'
done
[ -d "$conflict" ] && [ ! -L "$conflict" ] || fail 'uninstall removed conflict folder'
[ "$(cat "$conflict/marker")" = 'keep conflict' ] || fail 'uninstall changed conflict contents'
for target in claude agents; do
  dest="$TRIAL_HOME/.$target/skills"
  [ -d "$dest/keep-directory" ] && [ ! -L "$dest/keep-directory" ] || fail 'uninstall removed real directory'
  [ "$(cat "$dest/keep-directory/marker")" = 'keep directory' ] || fail 'uninstall changed directory contents'
  [ -f "$dest/keep-file" ] && [ ! -L "$dest/keep-file" ] || fail 'uninstall removed real file'
  [ "$(cat "$dest/keep-file")" = 'keep file' ] || fail 'uninstall changed real file'
  [ -L "$dest/keep-link" ] || fail 'uninstall removed unrelated link'
  [ "$(readlink "$dest/keep-link")" = /dev/null ] || fail 'uninstall changed unrelated link'
done
printf 'PASS: uninstall removes only owned links\n'
