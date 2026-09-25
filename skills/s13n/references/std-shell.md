# Shell and Scripting Standards

Shell is the only language in a repository that fails at runtime with no compiler to stop it: a missing quote, an unchecked `cd`, or a swallowed exit status ships silently and destroys data in production. This module covers the conventions that make scripts deterministic — declaring the target interpreter, arming failure detection while knowing where it goes blind, keeping data intact through expansions, and giving the caller a meaningful exit code. The recurring production failures are `rm -rf "$dir/"` where `dir` is empty, a `cd` that failed so the cleanup deletes the wrong tree, and a pipeline whose first stage failed while the script exited 0.

## Contents

- [When This Applies](#when-this-applies)
- [Choosing and Declaring the Shell](#choosing-and-declaring-the-shell)
- [Failure Semantics: `set -euo pipefail` and Its Sharp Edges](#failure-semantics-set--euo-pipefail-and-its-sharp-edges)
- [Quoting, Expansion, and Data Flow](#quoting-expansion-and-data-flow)
- [Process Hygiene: Traps, Temp Files, and Dependencies](#process-hygiene-traps-temp-files-and-dependencies)
- [Interfaces: Arguments, Exit Codes, Configuration, and Secrets](#interfaces-arguments-exit-codes-configuration-and-secrets)
- [Common Mistakes](#common-mistakes)
- [Checklist](#checklist)
- [References](#references)

## When This Applies

- The repository contains any `.sh`, `.bash`, `.bats`, `.zsh`, or extensionless file with a `#!` line, plus `Makefile` recipes, `Dockerfile` `RUN` lines, and CI `run:` steps — all of these are shell.
- Scripts exist under `scripts/`, `bin/`, `hack/`, `tools/`, `ci/`, or `.github/scripts/`, or a `package.json` `scripts` entry contains more than one `&&`.
- A shebang is inconsistent across files (`#!/bin/sh` in one, `#!/usr/bin/env bash` in another) or absent where the file is executed directly.
- `set -e`, `set -u`, `set -o pipefail`, or `shopt` appears in some scripts but not others.
- ShellCheck or shfmt is absent from the repo, is not run in CI, or is configured only through inline `# shellcheck disable=` comments with no committed config.
- A script is called by automation (CI, cron, systemd, a container entrypoint, a git hook) where a non-zero exit code is the only signal available.
- A script contains embedded credentials, a connection string, a token, or a `curl` with an inline secret.
- A script has grown past the point where its logic should live in a real language, or it parses structured data (JSON, YAML, XML) with `sed`, `awk`, or `grep`.
- Scripts must run on more than one platform family (Linux GNU, macOS/BSD, WSL, Git Bash, Alpine busybox).

## Choosing and Declaring the Shell

The `#!` line is a kernel convention, not a POSIX one — POSIX.1-2024 states that if the first line of a file of shell commands starts with `#!`, **the results are unspecified**. The interpreter is chosen by the kernel reading the path after `#!`, so the line is a contract you must make explicit and keep consistent across the repository.

| Shebang                                | Interpreter actually resolved                                                                             | When to use                                                                | Cost                                                                           |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `#!/bin/sh`                            | Whatever the distro links: `dash` on Debian/Ubuntu, `bash` in POSIX mode on RHEL, `busybox ash` on Alpine | Only when the script is genuinely POSIX and must run in minimal containers | No arrays, no `[[ ]]`, no `local` (SC3043), no `pipefail` before dash 5.13     |
| `#!/usr/bin/env bash`                  | First `bash` on `PATH`                                                                                    | Default for anything using arrays, `[[ ]]`, `mapfile`, `BASH_REMATCH`      | Requires bash on `PATH`; `PATH` is caller-controlled                           |
| `#!/usr/bin/env -S bash -euo pipefail` | `bash` with the options pre-armed                                                                         | Scripts that must never run without `-euo pipefail`                        | `-S` needs coreutils 8.30+ / FreeBSD / macOS `env`; unavailable on older Linux |
| `#!/bin/bash`                          | Absolute path                                                                                             | Only where `PATH` is untrusted (systemd units, root cron)                  | Breaks on NixOS and BSD where bash is `/usr/local/bin/bash`                    |
| `#!/usr/bin/env zsh`                   | First `zsh` on `PATH`                                                                                     | Never as a repository default                                              | `zsh` is not a Bourne shell for arrays, `read`, `$path`, or word splitting     |

Rules that follow from the table:

- **One repository, one dialect per script class.** Do not mix `sh` and `bash` scripts that share libraries: `source` semantics, `local`, `[[ ]]`, and array syntax differ, and ShellCheck reports the mismatch as SC3010/SC3054/SC3043. Declare the dialect in the config so the linter agrees with the shebang.
- **Never put more than one argument after the interpreter path without `env -S`.** `#!/usr/bin/env bash -e` passes `bash -e` as a single argument string and fails with `bad interpreter`. `env -S` splits it.
- **A CRLF line ending breaks the shebang.** The kernel hands the interpreter path to `execve` including the trailing `\r`, so Linux and macOS report `bad interpreter: No such file or directory` while the script still runs when invoked as `bash script.sh`. Commit `.gitattributes` with `*.sh text eol=lf` and let the normalizer strip CR.
- **Format with `shfmt`, not by hand.** `shfmt -i 2 -ci -bn` is the Google shell style; `shfmt -ln posix -d .` fails CI on any deviation. Dialect is selectable per file: `-ln`/`--language-dialect` accepts `bash`, `posix`, `mksh`, `bats`, `zsh`, and `.sh` implies `posix` unless a valid shebang overrides it. Committing the same values to `.editorconfig` (`indent_style`, `indent_size`, `language_dialect`, `simplify`, `binary_next_line`, `case_indent`, `space_redirects`, `ignore`) keeps editors and CI in agreement without extra flags.

## Failure Semantics: `set -euo pipefail` and Its Sharp Edges

`set -euo pipefail` is the baseline for every script that touches the filesystem, the network, or a database. It is not a safety net you can stop thinking about: `errexit` is suspended in a specific, documented set of contexts, and `pipefail` changes the exit status of the whole pipeline. Know the blind spots or the options give false confidence.

```bash
#!/usr/bin/env bash
set -euo pipefail

IFS=$'\n\t'
```

`pipefail` is now standardized: Austin Group defect 789 added it to POSIX.1-2024, and `dash` 5.13 implements it. ShellCheck still flags `set -o pipefail` in a `#!/bin/sh` script as SC3040 ("In POSIX sh, set option _name_ is undefined") because the option is not in the earlier POSIX versions ShellCheck targets — declare `shell=bash` in `.shellcheckrc` or switch the shebang rather than suppressing the code.

Where `errexit` does **not** fire — every one of these is a silent-failure path:

| Context                               | Example                                                                                | What actually happens                                                                                  |
| ------------------------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Command is a condition                | `if f; then` — and `errexit` is disabled for the _entire body of `f`_                  | A `false` inside `f` no longer aborts; the function runs to completion and returns its last status     |
| `!` negation                          | `! false`                                                                              | Always succeeds; `set -e` never triggers on a negated command                                          |
| `&&` / `\|\|` except the last command | `false && true`                                                                        | Safe by design — but `true && false` still exits                                                       |
| `while`/`until`/`if` condition        | `while false; do :; done`                                                              | The condition's status is consumed, never fatal                                                        |
| Arithmetic returning 0                | `(( i++ ))` when `i` is 0                                                              | The command's status is 1, so `set -e` exits. Use `(( i++ )) \|\| true` or `i=$(( i + 1 ))`            |
| Assignment builtins                   | `local v=$(false)`, `export v=$(false)`, `declare`, `readonly`                         | The builtin's own status (0) masks the substitution's failure. SC2155. Split: `local v; v=$(false)`    |
| Command substitution in a variable    | `x=$(false)` — a _plain_ assignment does propagate, but `x=$(false; echo hi)` does not | Bash clears `errexit` inside the subshell; enable `shopt -s inherit_errexit` (bash 4.4+) to inherit it |
| Background job                        | `false &`                                                                              | The parent never observes it; `wait $!` returns the status, but only if you check it                   |
| `cd` in a subshell                    | `( cd /missing && rm -rf * )`                                                          | The subshell dies, the parent continues — the classic wrong-directory delete                           |

Two more behaviors that bite during normalization:

- **`set -u` is not uniform.** Bash exempts the special parameters `@` and `*` and array expansions subscripted with `@`/`*`; before bash 4.4 an empty array still raised "unbound variable" under `-u`, which is why macOS's bash 3.2 breaks scripts that run fine on Linux. `dash` exits 2 on an unbound variable, bash exits 1 in a script and 127 when driven by `bash -c`. Do not rely on the code — validate the variable explicitly with `${VAR:?message}`.
- **`pipefail` turns `SIGPIPE` into a failure.** `seq 1 100000 | head -1` exits 141 with `pipefail` set because `head` closed the pipe. Either accept 141 as success (`|| [ $? -eq 141 ]`) or avoid the pattern.

`trap 'cleanup' EXIT` runs on normal exit, on `exit N`, and on `set -e` termination; `$?` inside the handler is the status that caused the exit, because POSIX requires the EXIT trap's environment to be identical to the moment before the trap fired. Capture it first, then clean up, then re-exit with the captured status — otherwise `rm -rf` succeeds and the script reports 0 for a failure. `trap ... ERR` is a bash extension, not POSIX, and does not fire inside functions unless `set -E` is also set.

## Quoting, Expansion, and Data Flow

Every unquoted expansion is subject to word splitting and globbing, and the two are indistinguishable in the source: `$files` where `files` is empty passes _zero_ arguments to `rm`, which is why `rm -rf $dir/` deletes the current directory. The audit rule is mechanical: every `$` expansion is either inside double quotes, inside `"${...}"`, or is a deliberate `$*`/array-splat with a stated reason.

```bash
printf '%s\n' "$@"
files=("$@")
for f in "${files[@]}"; do
  printf '%s\n' "${f}"
done
```

- **`"$@"` forwards arguments; `$*` and `"$*"` do not.** `"$@"` preserves each argument as a separate word; `"$*"` joins them with the first character of `IFS`; unquoted `$@` re-splits and globs every argument. In `set -- "a b" "c"`, `"$*"` prints `a b c` as one word and `"$@"` prints two.
- **Arrays are bash/ksh/zsh only.** `dash` has none — `a=(1 2)` is a syntax error. `${#arr[@]}` is the length; `${arr[@]}` under `set -u` errors on bash < 4.4 if the array is empty; `"${arr[@]}"` never splits elements, `"${arr[*]}"` joins them.
- **`read` needs `-r` and usually `IFS=`.** Without `-r`, a backslash is consumed as an escape and `a\b` becomes `ab` (SC2162). Without `IFS=`, leading and trailing whitespace is stripped. A `while read` loop silently drops a final line that has no trailing newline unless you write `while IFS= read -r line || [ -n "$line" ]`. A `read` inside a pipeline runs in a subshell and its variable disappears; use `shopt -s lastpipe` (bash, job control off) or a process substitution: `while ... done < <(cmd)`.
- **`printf` over `echo`.** `echo` flag handling is undefined in POSIX (SC3037): `echo -n` and `echo -e` are not portable, `echo` with no arguments prints a newline, and `printf '%s\n'` with zero arguments prints one empty line — guard with `if [ "$#" -gt 0 ]`. Use `printf '%s\n' "$x"` for data and `printf '%s\n' "$x" >&2` for errors.
- **Never parse `ls`.** Filenames may contain spaces, newlines, glob characters, and leading dashes; `ls` output is not a machine format. Use `for f in ./*; do` with a `[ -e "$f" ] || continue` guard, or glob with `nullglob`/`failglob` set explicitly.
- **NUL-delimit file lists.** `find ... -print0 | xargs -0 cmd` and `find ... -exec cmd {} +` are both correct; `-print0` and `xargs -0` were added to POSIX in Issue 8, so they are now portable to conformant systems. `xargs` runs the command once with no arguments on empty input under GNU and skips it under BSD, so pass `-r` (GNU) or ensure the input is non-empty. `read -d ''` reads NUL-delimited records in bash.
- **Never `eval` untrusted input**, and treat `eval` as a code smell everywhere else: it re-parses the string, so quoting is applied twice, globs re-expand, and a filename containing `;` becomes a command. `eval "$(ssh-agent -s)"` is the accepted narrow exception because the producer is trusted and the format is fixed.
- **`IFS` is global state.** Save and restore it around any change (`old=$IFS; IFS=,; ...; IFS=$old`) rather than leaving a modified separator for the rest of the script.

## Process Hygiene: Traps, Temp Files, and Dependencies

Cleanup must run on the failure path, and it must not delete anything it did not create. The pattern below is the only one that survives `set -e`, `exit N`, and an interrupt, and it is idempotent:

```bash
#!/usr/bin/env bash
set -euo pipefail

workdir=$(mktemp -d "${TMPDIR:-/tmp}/app.XXXXXX")
cleaned=0
cleanup() {
  rc=$?
  [ "$cleaned" -eq 1 ] && return 0
  cleaned=1
  rm -rf -- "$workdir"
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
```

- **`mktemp` is not one tool.** GNU `mktemp` requires at least three consecutive `X`s in the last component; BSD/OpenBSD require at least six and reject fewer with "insufficient number of Xs in template". Use six or more, and prefer the template form `mktemp -d "${TMPDIR:-/tmp}/name.XXXXXX"` over `-t`, whose argument handling differs between GNU and BSD. Never hand-roll a temp name from `$$` or `date` — it is predictable and racy.
- **`trap ... EXIT` is POSIX; `trap ... ERR` is not.** Trapping `SIGKILL` or `SIGSTOP` produces undefined results — the shell cannot catch them, so no trap will run on `kill -9`. `trap - EXIT` resets the handler.
- **Check dependencies before use, and check the right way.** `command -v name >/dev/null 2>&1` is POSIX and returns 1 when absent; `which` is not POSIX, is a separate binary, and returns 0 in some builds even when the command is missing.

```bash
for cmd in jq curl openssl; do
  command -v "$cmd" >/dev/null 2>&1 || { printf 'missing dependency: %s\n' "$cmd" >&2; exit 127; }
done
```

The same guard in other ecosystems, so a mixed-tooling repo reads consistently:

| Language        | Existence check                                                        | Temp dir                                         | Fatal error with context                     |
| --------------- | ---------------------------------------------------------------------- | ------------------------------------------------ | -------------------------------------------- |
| Bash            | `command -v jq >/dev/null 2>&1`                                        | `mktemp -d`                                      | `printf '%s\n' "msg" >&2; exit 1`            |
| Python          | `shutil.which("jq")`                                                   | `tempfile.TemporaryDirectory()`                  | `raise SystemExit("msg")` / `sys.exit(2)`    |
| Node/TypeScript | `spawnSync("jq", ["--version"]).status === 0`                          | `fs.mkdtempSync(path.join(os.tmpdir(), "app-"))` | `console.error("msg"); process.exitCode = 1` |
| Go              | `exec.LookPath("jq")`                                                  | `os.MkdirTemp("", "app-*")`                      | `fmt.Fprintln(os.Stderr, "msg"); os.Exit(1)` |
| Rust            | `which::which("jq")` or `Command::new("jq").arg("--version").status()` | `tempfile::tempdir()`                            | `eprintln!("msg"); std::process::exit(1)`    |
| PHP             | `shell_exec('command -v jq')` / `exec()` exit code                     | `sys_get_temp_dir()` + `tempnam()`               | `fwrite(STDERR, "msg\n"); exit(1);`          |

- **Write output files atomically.** Create in the same directory, then `mv` — `mv` is a rename within a filesystem and is atomic, so a reader never sees a half-written file. A redirect straight onto the target truncates it first.
- **Make scripts idempotent.** `install -d` instead of `mkdir`, `ln -sfn` instead of `ln -s`, `mkdir -p`, and "already exists" treated as success. An idempotent script is safe to re-run after a partial failure, which is the only recovery path in CI.

## Interfaces: Arguments, Exit Codes, Configuration, and Secrets

A script's contract is its arguments, its stdout/stderr split, and its exit code. Automation depends on all three.

- **Parse options with `getopts`, and reset `OPTIND=1` before every parse.** `OPTIND` is a global that persists across function calls, so a function that parses options works once and silently stops working on the second call unless it resets `OPTIND`. A leading `:` in the optstring enables silent mode: a missing argument yields `:` with `OPTARG` set to the option character, an unknown option yields `?` with `OPTARG` set to the character.

```bash
usage() { printf 'usage: %s [-v] [-o OUT] [-h]\n' "${0##*/}" >&2; }

verbose=0; out=
while getopts ':vo:h' opt; do
  case "$opt" in
    v) verbose=1 ;;
    o) out=$OPTARG ;;
    h) usage; exit 0 ;;
    :) printf 'error: -%s requires an argument\n' "$OPTARG" >&2; usage; exit 2 ;;
    \?) printf 'error: unknown option -%s\n' "$OPTARG" >&2; usage; exit 2 ;;
  esac
done
shift $((OPTIND - 1))
```

- **Exit codes are an API.** Reserve 0 for success, 2 for usage errors (matching `getopt` and the `EX_USAGE`/`EX_CONFIG` values 64/78 from `sysexits.h`), and use distinct non-zero codes for distinct failure classes so callers can branch. The shell itself already claims 126 (found but not executable / `ENOEXEC`), 127 (not found), 128 (unrecoverable read error), and 128+N for death by signal N — do not reuse those. Never exit 0 after a partial failure, and never `exit $?` after a `trap` that already changed `$?`.
- **Errors go to stderr; data goes to stdout.** A script whose diagnostics land on stdout cannot be used in a pipeline, and `$(cmd)` will capture its error text as data. Log with a consistent prefix and level on stderr, keep human output uncolored unless `[ -t 2 ]`, and honor `NO_COLOR`/`TERM=dumb`.
- **Validate environment variables with defaults and hard failures at the top of the script**, before any side effect:

```bash
: "${DATABASE_URL:?DATABASE_URL must be set}"
: "${PORT:=8080}"
: "${LOG_LEVEL:=info}"
```

`${VAR:?msg}` aborts with a non-zero status (bash 1, dash 2) — the exact code is not portable, so do not branch on it. `${VAR:-default}` supplies a fallback without assigning; `${VAR:=default}` assigns. `${VAR:?}` treats empty and unset identically, which is what you want for required settings.

- **Read configuration from files or the environment, never hardcoded paths.** `$HOME`, `$XDG_CONFIG_HOME`, `$TMPDIR`, and the script's own directory differ per host and per container. Locate the script's directory with `script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)` — note `${BASH_SOURCE[0]}` is bash-only and `$0` is not the script name when the file is sourced. Never write `PATH=/usr/local/bin:$PATH` into a script without quoting, and never assume `/tmp` is writable: honor `TMPDIR`.
- **Secrets never live in a script, a default, or a command line.** `set -x` prints every expanded command to stderr, so a token exported in a traced script lands in the CI log; command-line arguments are visible in `ps` to every user on the host. Read secrets from the environment or a file with restrictive permissions, unset them after use (`unset API_TOKEN`), and keep `set -x` out of any script that handles them.
- **Cross-platform utilities diverge, so probe rather than assume.** GNU and BSD differ on `sed -i` (BSD requires a suffix as a separate argument, `sed -i '' -e ...`, which GNU `sed` instead parses as the script file — so `-i` is not portable at all; write to a temp file and `mv`, or use `sed -i.bak` and delete the backup), `stat` (`-c` vs `-f`), `date -r` (GNU: reference file; BSD: seconds since epoch), `readlink -f` (absent on older macOS, which ships `realpath` instead), `grep -P` (GNU-only), `xargs -r` (GNU-only), `mktemp -t` argument handling, and `sha256sum` vs `shasum -a 256`. Detect the platform once (`case "$(uname -s)" in Linux*) ... ;; Darwin*) ... ;; esac`) and set variables, rather than branching at each call site. On Windows, WSL and Git Bash provide a POSIX layer but not the kernel: `CRLF` endings, `PATH` translation, and file-mode bits all behave differently, so scripts intended for Windows callers should be invoked explicitly through `bash script.sh` rather than relied on via the shebang.
- **Keep scripts small; move real logic into a proper language.** A shell script is the right tool for process orchestration — sequencing commands, wiring pipes, setting up an environment. It is the wrong tool for JSON/YAML parsing, date arithmetic, retry/backoff state machines, concurrency, or anything over roughly 150 lines with branching business rules. Delegate: call out to a checked-in program in [std-python.md](std-python.md), [std-go.md](std-go.md), [std-rust.md](std-rust.md), [std-js.md](std-js.md), [std-ts.md](std-ts.md), [std-php.md](std-php.md), or [std-java.md](std-java.md), and let the shell script do nothing but invoke it with validated arguments. This also removes `jq`/`awk`/`sed` as hidden runtime dependencies.

## Common Mistakes

| Mistake                                                    | Why It Breaks                                                                                            | Correct Approach                                                                                                                                                                |
| ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `rm -rf "$dir/"` where `dir` may be empty                  | Unquoted or empty expansions collapse to nothing or to `/`, deleting the wrong tree                      | Validate first: `[ -n "$dir" ] && [ -d "$dir" ] \|\| exit 1`, then `rm -rf -- "$dir"`; prefer `mktemp -d` and delete only what you created                                      |
| `cd "$dir"` then operate on relative paths                 | A failed `cd` leaves the shell in the original directory, so cleanup runs against the wrong tree; SC2164 | `cd -- "$dir" \|\| exit 1`, or `( cd "$dir" && cmd )` in a subshell so failure cannot leak                                                                                      |
| `local v=$(cmd)` / `export v=$(cmd)`                       | The builtin's status 0 masks the substitution's failure, so `set -e` never fires; SC2155                 | `local v; v=$(cmd)` on two lines                                                                                                                                                |
| `set -e` inside a function used as an `if` condition       | `errexit` is disabled for the entire function body, so intermediate failures are ignored; SC2310         | Check status explicitly inside the function, or call it as a plain command and let `set -e` act                                                                                 |
| `x=$(cmd1; cmd2)` with `set -e`                            | Bash clears `errexit` in the substitution subshell, so only the last command's status is seen; SC2311    | `shopt -s inherit_errexit` (bash 4.4+) or `x=$(cmd1) \|\| exit 1`                                                                                                               |
| `for f in $(ls)` or `cmd $(ls)`                            | Filenames with spaces, globs, or newlines split into multiple words and expand as patterns               | `for f in ./*; do [ -e "$f" ] \|\| continue; ...` or `find ... -print0 \| xargs -0`                                                                                             |
| `read line` without `-r`                                   | Backslashes are consumed as escapes, so Windows paths and regexes are silently corrupted; SC2162         | `while IFS= read -r line \|\| [ -n "$line" ]; do ... done`                                                                                                                      |
| `set -o pipefail` in a `#!/bin/sh` script                  | `dash` before 5.13 rejects it with `Illegal option -o pipefail`, aborting the script at line 1           | Declare `#!/usr/bin/env bash`, or guard with `(set -o pipefail 2>/dev/null) && set -o pipefail`                                                                                 |
| `echo "$var"` for arbitrary data                           | `echo` flag handling is undefined in POSIX (SC3037); `-n`/`-e` data is interpreted as flags              | `printf '%s\n' "$var"`, and `printf '%s\n' "$var" >&2` for errors                                                                                                               |
| `trap 'rm -rf "$workdir"' EXIT` without capturing `$?`     | The `rm` succeeds, the trap returns 0, and the script reports success for a failed run                   | Capture `rc=$?` first, clean up, then `exit "$rc"`; make the handler idempotent                                                                                                 |
| `mktemp /tmp/name`                                         | Fewer than three `X`s (GNU) or six (BSD) is rejected; `-t` argument semantics differ between them        | `mktemp -d "${TMPDIR:-/tmp}/app.XXXXXX"`                                                                                                                                        |
| `eval "$user_input"` or `eval "$(cmd)"` for untrusted data | The string is re-parsed, so quoting, globs, and `;` become executable                                    | Pass data as arguments or through a file; reserve `eval` for fixed formats from trusted producers                                                                               |
| Secrets in a script, a default value, or `set -x` output   | `set -x` writes every expanded command to stderr, so tokens reach CI logs and `ps` exposes arguments     | Read from the environment or a mode-600 file, `unset` after use, keep `set -x` away from credential paths                                                                       |
| `git`-ignored `*.sh` files with no lint config             | Each contributor's editor and linter disagree, so divergence reappears after normalization               | Commit `.shellcheckrc` (`shell=bash`, `source-path=SCRIPTDIR`, `external-sources=true`, explicit `disable=` list) and run `shellcheck --severity=warning` plus `shfmt -d` in CI |

## Checklist

1. Enumerate every shell-executable file (shebang, `.sh`/`.bash`/`.bats`/`.zsh`, `Makefile`, Dockerfile `RUN`, CI `run:`) and record its declared dialect.
2. Verify every shebang names a real interpreter for the target platform; replace `#!/bin/bash` with `#!/usr/bin/env bash` unless the caller controls `PATH`, and confirm no shebang passes multiple arguments without `env -S`.
3. Add or verify `.gitattributes` with `*.sh text eol=lf`, and confirm no committed script contains a CRLF shebang.
4. Confirm every script that performs side effects begins with `set -euo pipefail` and, where applicable, `shopt -s inherit_errexit`.
5. Search for the `errexit` blind spots and fix each: `local`/`export`/`declare`/`readonly` with a substitution (SC2155), functions called in conditions (SC2310), `(( ))` arithmetic whose result is 0, `cd` without a failure check (SC2164).
6. Verify every `$` expansion is double-quoted or explicitly justified; flag `$*`, unquoted `$@`, and unquoted array splats (SC2086, SC2046, SC2068).
7. Confirm no script parses `ls`, and that file lists use `find -print0 | xargs -0` or `find -exec {} +` with the empty-input case handled.
8. Verify each `read` uses `-r` and an explicit `IFS`, and that read loops handle a missing trailing newline and do not rely on a pipeline subshell (SC2162).
9. Confirm every script that creates state has an idempotent `trap ... EXIT` cleanup that captures `$?`, guards against double-cleanup, and removes only paths it created; check for `trap ... ERR` where POSIX-only portability is required.
10. Confirm temporary files come from `mktemp` with a six-or-more-`X` template under `${TMPDIR:-/tmp}`, and that output files are written via a same-directory temp plus `mv`.
11. Verify every external command is guarded by `command -v` (or an equivalent per-language lookup) and that missing dependencies exit with a distinct non-zero code and a message on stderr.
12. Audit exit codes: 0 only on full success, 2 for usage errors, no reuse of 126/127/128, and no `exit $?` after a trap has run.
13. Confirm `getopts` parsing resets `OPTIND=1`, uses a leading `:` optstring, and that `--help` prints usage to stdout with exit 0 while errors print usage to stderr with exit 2.
14. Verify required environment variables are validated with `${VAR:?message}` at the top of the script and optional ones have explicit defaults via `${VAR:-default}`; confirm no absolute host path is hardcoded.
15. Grep every script for credentials, tokens, connection strings, and `set -x` near secrets; confirm no secret is committed, defaulted, or passed on a command line.
16. Identify scripts that exceed the "orchestration only" threshold or parse structured data, and move that logic into a checked-in program in another language.
17. Commit a `.shellcheckrc` with `shell`, `source-path=SCRIPTDIR`, `external-sources=true`, and an explicit `disable=` list, and wire `shellcheck --severity=warning` and `shfmt -d` into CI as a required check.

## References

- [POSIX.1-2024 Shell Command Language](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html) — quoting rules, parameter expansion, `set`, pipeline exit status with `pipefail`, and the statement that a `#!` first line has unspecified results
- [Austin Group Defect 789: Add `set -o pipefail`](https://austingroupbugs.net/view.php?id=789) — the accepted resolution, including the four-row exit-status table for `pipefail` × `!`
- [POSIX.1-2024 `sh`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html) — exit statuses 126 (`ENOEXEC`), 127 (not found), 128 (unrecoverable read error)
- [POSIX.1-2024 `trap`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/trap.html) — `EXIT`/`0` equivalence, symbolic signal names, and why trapping `SIGKILL`/`SIGSTOP` is undefined
- [POSIX.1-2024 `find`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/find.html) and [`xargs`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/xargs.html) — `-print0` and `-0` are now standardized
- [ShellCheck `shellcheck.1.md`](https://github.com/koalaman/shellcheck/blob/master/shellcheck.1.md) — `.shellcheckrc` keys (`shell`, `source-path`, `external-sources`, `enable`, `disable`), `.editorconfig` `shellcheck.*` mapping, `--severity` values, and ShellCheck's own exit codes 0–4
- [ShellCheck SC3040](https://www.shellcheck.net/wiki/SC3040) — why `set -o pipefail` is flagged in `sh`, and the POSIX-safe alternatives
- [ShellCheck SC2155](https://www.shellcheck.net/wiki/SC2155), [SC2162](https://www.shellcheck.net/wiki/SC2162), [SC2164](https://www.shellcheck.net/wiki/SC2164), [SC2310](https://www.shellcheck.net/wiki/SC2310) — masking, `read -r`, unchecked `cd`, and `set -e` suppression
- [GNU Bash Reference Manual](https://www.gnu.org/software/bash/manual/bash.html) — `-u` exemptions for `@`/`*` and `@`/`*`-subscripted arrays, `inherit_errexit`, `BASH_REMATCH` scope
- [Bash FAQ 105](https://mywiki.wooledge.org/BashFAQ/105) and [BashFAQ 001](https://mywiki.wooledge.org/BashFAQ/001) — why `set -e` is unreliable, and how to read files line by line
- [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html) — the style `shfmt -i 2 -ci -bn` reproduces, plus its rules on which shell to use and when to switch languages
- [shfmt manual](https://github.com/mvdan/sh/blob/master/cmd/shfmt/shfmt.1.scd) — `-ln`/`--language-dialect` values, printer flags, and the EditorConfig keys that mirror them
- [GNU coreutils `env` invocation](https://www.gnu.org/software/coreutils/manual/html_node/env-invocation.html) and [coreutils NEWS 8.30](https://github.com/coreutils/coreutils/blob/master/NEWS) — `-S`/`--split-string` for multi-argument shebangs
- [GNU `mktemp(1)`](https://man7.org/linux/man-pages/man1/mktemp.1.html) and [OpenBSD `mktemp(1)`](https://man.openbsd.org/mktemp.1) — the three-`X` versus six-`X` template divergence
- [FreeBSD `sysexits.h`](https://github.com/freebsd/freebsd-src/blob/main/include/sysexits.h) — `EX_USAGE` 64 through `EX_CONFIG` 78 for scripts with a real exit-code contract
- [POSIX.1-2024 `make`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/make.html) — worked example of `set -o pipefail` and `$${...}` escaping inside a recipe
