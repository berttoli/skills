# Skills

Agent skills kept in one repo and linked into Claude Code, Codex and Cursor on every machine.

Each skill is a folder under `skills/` with a `SKILL.md`: frontmatter with `name` and `description`, then the instructions. An agent loads a skill when a task matches its description, or when you call it by name (for example `/grilling`).

## Skills

| Skill | What it does | Source |
|---|---|---|
| [codebase-design](skills/codebase-design/SKILL.md) | Vocabulary and principles for deep modules, interfaces and seams | [mattpocock/skills](https://github.com/mattpocock/skills), MIT |
| [diagnosing-bugs](skills/diagnosing-bugs/SKILL.md) | A loop for hard bugs: get a command that goes red on the bug before forming theories | mattpocock/skills, MIT |
| [grilling](skills/grilling/SKILL.md) | Questions a plan in numbered rounds, each with a recommended answer | mattpocock/skills, MIT |
| [tdd](skills/tdd/SKILL.md) | Red-green loop, one test at a time, at seams agreed up front | mattpocock/skills, MIT |
| [retro](skills/retro/SKILL.md) | Reviews recent Claude Code sessions for avoidable round trips and saves the lessons | This repo. Claude Code only |

Vendored skills keep their upstream `LICENSE` and a `.source` file with the upstream URL, commit and copy date.

## Install

Clone the repo, then:

```bash
./install.sh            # prints the plan, changes nothing
./install.sh --apply    # creates the links
```

`install.sh` links each skill listed in `skills.conf` into:

| Folder | Read by |
|---|---|
| `~/.claude/skills` | Claude Code, and Cursor |
| `~/.agents/skills` | Codex, and Cursor |

Every installed skill is a symlink back into this checkout, so `git pull` updates all agents at once. Run `./install.sh --apply` again after changing `skills.conf`.

If a folder with the same name already exists, the script leaves it alone and reports a conflict. `--apply --replace` moves it to `~/.skills-backup/<time>/` and links in its place. The script never deletes a real folder. `--uninstall` removes only the links it made. `--codex-legacy` also links into `~/.codex/skills`, the older Codex location. `./install.sh --help` lists every option.

Skills that live in another checkout on one machine go in `skills.local.conf` (see `skills.local.conf.example`). That file is gitignored, so machine paths stay out of the repo.

## Adding a skill

1. Create `skills/<name>/SKILL.md`. The `name` in its frontmatter must match the folder name, because Cursor rejects a mismatch and `install.sh` checks it.
2. Add `<name>` to `skills.conf`, with targets if it isn't for every agent (for example `retro claude`).
3. Run `./install.sh`, then `./install.sh --apply`.

For a vendored skill, copy the upstream `LICENSE` into its folder and add a `.source` file.

## This repo is public

Keep personal details out of every file and commit: email addresses, home paths, machine names, account names and the names of private projects. Commit with your GitHub noreply address. [AGENTS.md](AGENTS.md) has the checks.
