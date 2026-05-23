# LogCraft Playground

LogCraft generates synthetic log streams from a YAML scenario file. Describe your
services as agents, configure rates and formats, and get a continuous stream of
realistic log records — web server access logs, database traces, error events — to
send anywhere.

> **New to LogCraft?** Read [GUIDE.md](GUIDE.md) first — it explains scenarios,
> agents, fields, latency distributions (including what p50/p99 means), phases,
> and incidents with worked examples.

This repository contains starter scenarios, a reusable agent library, and the source
of the CLI consumer. The CLI links against `logcraft_core` (closed source); the
scenario YAML, agent library, and CLI source in this repo are Apache 2.0.

**The free CLI includes everything.** The only feature gated to
[CodeRoast](https://coderoast.fr) is `seed:` (deterministic mode — same logs every
run). Without it, each run is uniquely randomized, which is the right default for
learning and testing.

## Key Paths

| Path | Purpose |
|---|---|
| `GUIDE.md` | Getting started — concepts, examples, and onboarding for new users. |
| `scenario/01_starter/` | Starter scenarios, ordered by increasing complexity. |
| `scenario/agents/` | Reusable agent definitions (nginx, postgres, redis, kafka, …). |
| `cli/` | Source for the LogCraft CLI consumer; links with `logcraft_core`. |
| `scenario_reference.md` | Complete DSL reference — every key, type, and default. |

## Build

Inside the full CodeRoast workspace, use `malf` from this package root:

```bash
malf build .
```

The build requires `logcraft_core/1.3.6`. Scenario YAML remains editable and inspectable without that dependency.
