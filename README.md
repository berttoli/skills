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
| [cli-for-agents](skills/cli-for-agents/SKILL.md) | Design and review CLIs for unattended agents, safe retries and useful output | [cursor/plugins](https://github.com/cursor/plugins/tree/246bc508c139c5e036dfafea8978d31a7433279f/cli-for-agent), MIT; adapted |
| [create-verification-skill](skills/create-verification-skill/SKILL.md) | Generate and exercise a project-local app verification skill for Codex, Claude Code, or both | [cursor/plugins](https://github.com/cursor/plugins/tree/246bc508c139c5e036dfafea8978d31a7433279f/pstack), MIT; adapted |
| [retro](skills/retro/SKILL.md) | Reviews recent Claude Code sessions for avoidable round trips and saves the lessons | This repo. Claude Code only |

Vendored skills keep their upstream `LICENSE` and a `.source` file with the upstream URL, commit and copy date.

`cli-for-agents` can be selected automatically for CLI design work. Invoke `create-verification-skill` explicitly (`$create-verification-skill` in Codex or `/create-verification-skill` in Claude Code). Its generated verification skills live with the application they describe; for both agents, it uses one source under `.agents/skills` with a relative link from `.claude/skills`.

## What belongs here

Keep reusable, agent-independent workflows in this repo. Keep skills that document a particular CLI beside that CLI and link them through `skills.local.conf`. Generated app verification skills, project design rules, and tool-managed skill bundles stay with their owning project or installer. This avoids two competing copies of the same instructions.

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
