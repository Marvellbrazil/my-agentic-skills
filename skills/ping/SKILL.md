---
name: ping
description: Health-checks the agent session and reports a "pong" with measured tool round-trip latency, host facts, and clock skew. Use when the user types /ping, says "ping", "are you alive", "latency check", or wants to confirm the agent can reach the shell before a long task.
allowed-tools: Bash
---

# Ping

A connectivity and liveness probe for the agent session. Responds with `pong` and real measurements — never invented numbers.

## Contract

The first line of the reply is exactly:

```
pong
```

Nothing before it. No greeting, no preamble. After `pong`, report the measurements below. If any measurement fails, report the failure instead of a number — a fabricated latency is worse than an admitted failure.

## Procedure

### 1. Measure tool round-trip latency

Issue one Bash call that stamps a high-resolution timer, sleeps for a known interval, and stamps it again. The delta reveals the harness's own overhead once the sleep is subtracted.

```bash
python - <<'PY'
import time
t0 = time.perf_counter()
time.sleep(0.100)
t1 = time.perf_counter()
print(f"sleep_delta_ms={(t1 - t0) * 1000:.2f}")
print(f"overhead_ms={(t1 - t0 - 0.100) * 1000:.2f}")
PY
```

Run it three times in a single call and report the median, not a single sample. A single sample cannot distinguish real latency from a scheduler hiccup.

```bash
for i in 1 2 3; do
  python -c "
import time
t0 = time.perf_counter(); time.sleep(0.100); t1 = time.perf_counter()
print(f'sample=$i total_ms={(t1 - t0) * 1000:.2f}')
"
done
```

### 2. Measure process spawn latency

Measure how long it takes to start a fresh process, which is the floor for every future tool call in the session. Time a real child process rather than an in-shell no-op — command substitution forks a subshell, so this measures a genuine spawn.

```bash
python - <<'PY'
import subprocess, time, sys
t0 = time.perf_counter()
subprocess.run([sys.executable, "-c", "pass"], check=True)
t1 = time.perf_counter()
print(f"process_spawn_ms={(t1 - t0) * 1000:.2f}")
PY
```

For a shell-level equivalent, time a trivial external command rather than a builtin — `:` and `echo` are builtins and measure nothing:

```bash
start=$(date +%s%N); command -v true >/dev/null && true; end=$(date +%s%N)
echo "spawn_ns=$((end - start))"
```

On macOS, `date +%s%N` is unsupported and returns a literal `N`. Use the Python form above, or `perl -MTime::HiRes=time -e 'printf "%.0f\n", time*1000'`.

### 3. Report host and session facts

Collect these in one call so the report is a single round trip:

```bash
echo "cwd=$(pwd)"
echo "shell=${SHELL:-unknown}"
echo "user=${USER:-${USERNAME:-unknown}}"
echo "os=$(uname -s 2>/dev/null || echo windows)"
echo "arch=$(uname -m 2>/dev/null || echo unknown)"
echo "utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "epoch_ms=$(date +%s)000"
```

On Windows PowerShell use `$PWD`, `$env:USERNAME`, `[System.Environment]::OSVersion.VersionString`, and `[DateTime]::UtcNow.ToString('o')`.

### 4. Optionally measure network latency

Only when the user asked for connectivity rather than liveness, and only to a host they named or a neutral public endpoint. Three probes, report min/median/max.

```bash
for host in 1.1.1.1 8.8.8.8; do
  ping -c 3 -W 2 "$host" 2>/dev/null | tail -1 || echo "$host unreachable"
done
```

Windows uses `ping -n 3`. Treat a blocked ICMP reply as "unmeasurable", not as "down" — many networks drop ICMP while HTTP works fine.

Do not probe a host the user did not ask about. An unprompted outbound request from a `/ping` is a privacy surprise.

## Report Format

```
pong

Latency
  tool round-trip (median of 3)   142 ms
  sleep calibration overhead        1.8 ms
  shell spawn                       11 ms

Session
  working directory   E:\Projects\Clones\my-agentic-skills
  shell               PowerShell 7
  platform            win32 / x64
  utc                 2026-09-25T15:07:44Z

Verdict  responsive — no anomalies
```

Keep it to a single compact block. Omit the network section entirely when it was not requested rather than printing "N/A".

## Interpreting the Numbers

| Observation                                               | Likely Cause                                                                                              |
| --------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Round-trip under ~50 ms                                   | Local tool execution; harness overhead is negligible.                                                     |
| Round-trip 200-800 ms                                     | Network-attached shell, container boundary, or antivirus interception on Windows.                         |
| Round-trip over 2 s                                       | Cold process start, a loaded machine, or a sandboxed filesystem. Warn the user before starting long work. |
| First sample much slower than samples 2-3                 | Cold start. Report the median; do not report the outlier as the latency.                                  |
| Any measurement errors out                                | Report the raw error text. Do not estimate a plausible value.                                             |
| Clock skew between `utc` and the user's stated local time | The container clock is wrong; flag it, since timestamps in logs and commits will be wrong too.            |

## Failure Modes

- **Do not invent a latency number.** If the timer call fails, say it failed. A fabricated `pong, latency 12ms` is a lie that destroys trust in every later measurement.
- **Do not report a single sample as "the latency".** Report the median and label the sample count.
- **Do not treat a failed ICMP ping as an outage.** Report it as unmeasurable.
- **Do not run a long diagnostic.** `/ping` answers in one round trip. If the probe needs more than a few seconds, that is the finding.
- **Do not scan ports, resolve DNS for arbitrary domains, or contact third-party APIs.** Liveness only.
