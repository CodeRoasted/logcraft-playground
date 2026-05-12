# LogCraft — Concepts Guide

New to LogCraft? This is the place to start. The [scenario reference](scenario_reference.md)
is a complete API listing — come back to it once you understand the pieces. This guide
explains what everything *means*.

---

## What is LogCraft?

LogCraft generates synthetic log streams. You write a small YAML file that describes your
system — which services you have, how busy they are, what their logs look like — and
LogCraft produces a continuous stream of realistic log records.

The logs look like real application output:

```
{"timestamp":"2026-01-15T10:23:45Z","level":"info","service":"api-gateway","message":"GET /api/orders -> 200","status_code":"200","latency_ms":23,"bytes_sent":1842}
{"timestamp":"2026-01-15T10:23:45Z","level":"error","service":"api-gateway","message":"GET /api/users -> 500","status_code":"500","latency_ms":2341,"bytes_sent":0}
127.0.0.1 - - [15/Jan/2026:10:23:46 +0000] "POST /api/checkout HTTP/1.1" 201 512
Jan 15 10:23:47 payments-prod payment-service[4821]: transaction_id=txn-98342 result=approved amount=49.99
```

**Why would I use this?**

- **Test your log pipeline before production** — Does your Elasticsearch mapping handle all your fields? Does your Splunk alert fire when error rates spike? Find out with synthetic data, not a real outage.
- **Generate sample data** — Demos, tutorials, documentation screenshots, benchmark test beds.
- **Practice log analysis** — Want to study with Drain, a SIEM, or a log anomaly detector? Generate controlled scenarios where you know exactly what happened and when.
- **Benchmark your ingestion** — Push 50,000 records/s through your pipeline and see what breaks.
- **Test your alerting rules** — Write an incident that spikes error rates at minute 5, then verify your alert fires within 30 seconds.

---

## Your first scenario

The starter scenarios in `scenario/01_starter/` are designed to be read in order.
Start with the simplest:

```bash
logcraft scenario/01_starter/01_hello_world.yaml
```

Open the file alongside this guide. Each starter introduces one new concept. Read the
YAML, run it, watch the output, then move to the next one.

---

## What is a scenario?

A scenario is a YAML file that fully describes one simulation run. It specifies:

- **How long** to run (or run forever until you stop it)
- **Which services** to simulate — called *agents*
- **Where to send** the logs — called *outputs*

```yaml
scenario:
  name: my-api
  duration: 2m              # Stop after 2 minutes (0 = run forever)

  agents:
    - name: web-server
      rate: 100/s           # 100 log records per second

  outputs:
    - type: console
      format: json          # Print JSON to stdout
```

Every scenario starts with `scenario:`. Everything else is nested under it.

---

## Agents

An **agent** is a simulated service — a web server, a database, a cache, a background
worker. Each agent runs independently and generates log records at its own rate.

```yaml
agents:
  - name: api-gateway
    type: web_server        # Free-form label; purely descriptive
    rate: 200/s             # Records per second
    error_rate: 0.03        # 3% of records are ERROR level
    log_level: info         # Default severity when not an error
```

You can have as many agents as you need. They all run simultaneously, each producing
their own log stream.

### Rate

Rate controls how many log records an agent produces each second.

```yaml
rate: 100/s          # String form: "N/s"
rate_per_second: 100 # Numeric form; same effect
```

Some rough reference points:
- An nginx instance under moderate load: 100–500/s
- A Postgres database with query logging: 10–50/s
- A background job scheduler: 1–5/s
- A high-traffic API during peak hours: 1000–5000/s

### Error rate

`error_rate` sets what fraction of records come out as ERROR-level entries. At `0.03`,
roughly 3 in 100 are errors. The rest default to the configured `log_level`.

---

## Fields

Fields are the structured data inside each log record. You define what fields each agent
produces and how their values are generated.

```yaml
agents:
  - name: nginx
    rate: 100/s
    message_template: "{method} {path} -> {status_code}"
    fields:
      - name: method
        generator: weighted_choice
        values: [GET, POST, PUT, DELETE]
        weights: [70, 20, 8, 2]       # 70% GET, 20% POST, etc.

      - name: path
        generator: choice
        values: [/api/users, /api/orders, /api/products, /health]

      - name: status_code
        generator: weighted_choice
        values: ["200", "201", "400", "404", "500"]
        weights: [80, 10, 5, 4, 1]

      - name: bytes_sent
        generator: range
        min: 200
        max: 50000
        integer: true
```

The `message_template` uses `{field_name}` placeholders that are filled in from the
generated field values.

### Generators

Every field needs a `generator` — a rule for how to produce values:

| Generator | What it does | Typical use |
|-----------|-------------|-------------|
| `weighted_choice` | Pick from a list; each value has a probability | HTTP status codes, HTTP methods |
| `choice` | Pick uniformly from a list | Usernames, regions, queue names |
| `range` | Random number between min and max | Bytes transferred, port numbers |
| `sequence` | Auto-incrementing counter with optional prefix | Request IDs (`req-1`, `req-2`, …) |
| `static` | Always the same fixed value | Hostname, service version, datacenter |
| `timestamp` | Current simulation time, formatted | CLF timestamp for access logs |
| `normal` | Bell-curve random number | Response times with natural spread |
| `percentile` | Distribution defined by p50/p95/p99 targets | Realistic API/DB latency tail |
| `conditional` | Different generator per value of another field | Body size depends on status code |

The first five (`weighted_choice`, `choice`, `range`, `static`, `sequence`) cover
the majority of real scenarios. Reach for `normal`, `percentile`, and `conditional`
when you need distributions that match production data.

---

## Latency

Latency simulates response time — how fast a service processes a request. It affects
the timing of log emission and can appear as a numeric field if you include one.

```yaml
latency_ms: [10, 50]    # Uniform: random between 10ms and 50ms
```

That works, but real services don't have uniformly random response times. Use a
distribution for more realistic behavior.

### Normal distribution

A bell curve. Most values are close to the mean; few are much faster or slower.

```yaml
latency_ms:
  distribution: normal
  mean: 45       # Centre of the bell: most responses ~45ms
  stddev: 12     # About 68% of responses fall within ±12ms of the mean
```

Good for: in-memory caches, simple read endpoints, services without tail latency.

### Percentile distribution

Define latency by percentile targets — exactly how engineers describe latency in
practice ("our p99 is 300ms").

```yaml
latency_ms:
  distribution: percentile
  p50: 20     # Half of requests faster than 20ms
  p95: 150    # 95% faster than 150ms; 5% slower
  p99: 400    # 99% faster than 400ms; 1% slower
```

#### What are p50, p95, p99?

Imagine you run 1000 requests and sort them by response time, fastest to slowest.
Then you look at specific positions in that sorted list:

```
[8ms, 9ms, 10ms, ..., 20ms, ..., 149ms, 150ms, ..., 399ms, 400ms, ..., 2100ms]
                       ↑ p50          ↑ p95                  ↑ p99
```

- **p50** (the median) — position 500: half of all requests are faster, half are slower.
  This is your "typical" response time.
- **p95** — position 950: 95% of requests are faster than this. This is the "typical
  bad request" — the experience of users who happen to hit a slower path.
- **p99** — position 990: 99% of requests are faster. This is the "tail" — rare but
  real slow outliers caused by GC pauses, lock contention, cold cache misses, or
  slow database queries.

The ratio between p50 and p99 tells you about tail behavior:

| Pattern | What it means |
|---------|--------------|
| p50=20ms, p99=25ms | Very consistent — Redis GET, in-memory lookup |
| p50=20ms, p99=200ms | Moderate tail — typical REST API with occasional DB misses |
| p50=50ms, p99=2000ms | High tail — payment gateway, external API call |
| p50=200ms, p99=10000ms | Severe tail — overloaded database, untuned queries |

Use realistic ratios when you want your logs to exercise SLO alerting properly.

---

## Outputs and formats

Outputs define where logs go. You can have multiple outputs; all agents write to
all outputs simultaneously.

```yaml
outputs:
  - type: console          # Print to stdout
    format: json

  - type: http             # POST to an HTTP endpoint
    url: "http://localhost:9200/_bulk"
    format: ecs
    batch_size: 100
    flush_interval_ms: 1000
```

Output types available in the free CLI:

| Type | Description |
|------|-------------|
| `console` | Print to stdout |
| `file` | Write to disk with optional rotation |
| `http` | Batch HTTP POST (Elasticsearch, Loki, any webhook) |

### Log formats

LogCraft supports 20+ log formats. You don't need to transform output to feed your
tools — generate it in the right format from the start.

Free CLI formats include:

| Format | Looks like |
|--------|-----------|
| `json` | `{"timestamp":"...","level":"info","message":"...",...}` |
| `text` | `2026-01-15 10:23:45 INFO api-gateway: GET /api -> 200` |
| `clf` | `127.0.0.1 - - [15/Jan/2026:10:23:45 +0000] "GET / HTTP/1.1" 200 1024` |
| `nginx_error` | `2026/01/15 10:23:45 [error] 123#0: upstream timed out` |
| `apache_error` | `[Mon Jan 15 10:23:45.123 2026] [error] [pid 123] msg` |
| `log4j` | `2026-01-15 10:23:45,123 ERROR [main] com.example.App: msg` |
| `syslog` | `Jan 15 10:23:45 hostname app[123]: message` |
| `rfc5424` | `<14>1 2026-01-15T10:23:45Z host app 123 - - message` |
| `kv` / `logfmt` | `ts=2026-01-15T10:23:45Z level=info service=api msg="..."` |

Additional formats (`ecs`, `otel`, `cloudwatch`, `systemd_journal`, and more) are
available on [CodeRoast](https://coderoast.fr).

The full format list with examples is in [scenario_reference.md](scenario_reference.md#output-formats).

---

## Phases

Phases let an agent change its behavior over time. Each phase overrides rate, error
rate, or latency for a set duration, then the next phase starts.

```yaml
agents:
  - name: api-server
    rate: 100/s                     # Base rate (used outside any phase)
    phases:
      - name: warmup
        duration: 30s
        rate: 10/s                  # Start slow

      - name: steady-state
        duration: 5m
        rate: 100/s                 # Normal load
        latency_ms:
          distribution: normal
          mean: 30
          stddev: 8

      - name: traffic-spike
        duration: 1m
        rate: 500/s                 # 5× surge
        error_rate: 0.08            # Errors increase under load
        latency_ms: [100, 800]

      - name: recovery
        duration: 2m
        rate: 100/s
        error_rate: 0.01
```

Phases are great for scripting realistic traffic patterns: warmup → steady → peak →
cooldown. They're also useful for simulating deployment events, traffic migrations, or
any time-varying workload.

When all phases end, the agent continues at its base configuration (the values set
directly on the agent, outside `phases:`).

---

## Incidents

Incidents simulate failures and unexpected events. They activate at a specific time
and modify agent behavior for a duration, then auto-resolve.

```yaml
incidents:
  - name: database_overload
    trigger: "time > 5m"          # Fires at the 5-minute mark
    duration: 2m                   # Auto-resolves after 2 minutes
    effects:
      - target: postgres            # Which agent is affected
        latency_multiplier: 8.0    # Database becomes 8× slower
        error_rate: 0.25           # 25% of queries fail
      - target: api-server         # Upstream effect (can affect multiple agents)
        latency_multiplier: 2.5
        error_rate: 0.08
```

You can also use **probabilistic incidents** that fire randomly rather than at a
fixed time:

```yaml
incidents:
  - name: cache_timeout
    trigger_probability: 0.002     # 0.2% chance per second of firing
    duration: 30s
    effects:
      - target: redis
        latency_multiplier: 20.0
        error_rate: 0.60
```

Incidents are the simplest way to build "something breaks at minute 5" training data.
Combine them with good field generators and realistic baseline traffic, and the
resulting logs are genuinely difficult to distinguish from production.

---

## What else can LogCraft do?

The features above cover the starter scenarios. The reference documents many more:

### Multiple agents with interactions

Declare which agents call which others. This enables cascading: when one service
degrades, its callers can automatically degrade too.

```yaml
interactions:
  - from: api-gateway
    to: order-service
    type: request
  - from: order-service
    to: postgres
    type: dependency
```

→ [Interactions](scenario_reference.md#interactions),
[Rules](scenario_reference.md#rules),
[Auto-Cascade](scenario_reference.md#auto-cascade)

### Health state machine

Agents can transition probabilistically between Healthy, Degraded, Failing, and
Recovering states. Each state has its own latency multiplier and error rate.

→ [Health State Machine](scenario_reference.md#health-state-machine)

### Rate modulation

Traffic that varies over time: sinusoidal day/night cycles or business-hours patterns.

```yaml
rate_modulation:
  type: business_hours
  peak_start_hour: 9
  peak_end_hour: 18
  peak_multiplier: 3.0
  off_peak_multiplier: 0.1
```

→ [Rate Modulation](scenario_reference.md#rate-modulation)

### State variables and effects

Agents track internal metrics (queue depth, CPU load, connection count) and change
behavior when they cross thresholds.

→ [State & Effects](scenario_reference.md#state--effects)

### Templates — reusable agent presets

Define a named agent profile once and inherit it with `use: template_name`. Override
only what differs per instance.

```yaml
templates:
  go_service:
    rate: 200/s
    error_rate: 0.005
    latency_ms: {distribution: normal, mean: 15, stddev: 4}

agents:
  - name: user-service
    use: go_service          # inherits everything above
    error_rate: 0.02         # override just this one value
  - name: order-service
    use: go_service          # same baseline
```

Templates keep large multi-agent scenarios DRY. Define your standard microservice
profile, your database profile, your cache profile — then compose.

→ [Templates](scenario_reference.md#templates)

### Includes — splitting scenarios across files

`includes:` merges other YAML files into your scenario before parsing. Useful for
separating shared templates, incident libraries, or topology definitions that you
reuse across multiple scenarios.

```yaml
includes:
  - ./shared/templates.yaml
  - ./incidents/black_friday.yaml

agents:
  - name: api
    use: go_service    # defined in templates.yaml
```

→ [Includes](scenario_reference.md#includes)

### Registry — versioned agent library

The registry is the production-scale version of includes: a named, versioned library
of agent files you instantiate by reference with per-instance overrides. This is how
the `scenario/agents/` directory is designed to be used at scale.

```yaml
registry:
  sources: [scenario/agents/]    # auto-discovers all agent YAML files
  nginx:
    v1: scenario/agents/nginx_v1.yaml
    v2: scenario/agents/nginx_v2.yaml

  agents:
    - ref: "nginx:v2"
      name: frontend
      overrides: {rate_per_second: 500, instances: 3}
    - ref: "nginx:v2"
      name: internal-proxy
      overrides: {rate_per_second: 50}
```

→ [Registry](scenario_reference.md#registry)

### Noise injection

Simulate pipeline imperfections: duplicated records, missing fields, timing jitter.

→ [Noise](scenario_reference.md#noise)

---

## Deterministic mode

By default, every run produces different logs — randomization seeds from the system
clock, so each run is unique.

Add `seed:` to freeze the random seed:

```yaml
scenario:
  seed: 42
```

With `seed:` set, LogCraft produces **bit-for-bit identical output on every run** —
same log records, same field values, same timestamps, same sequence, same count. Run
it today or in six months, on your laptop or in CI, and you get the exact same stream.
Not "statistically similar". Byte-identical. Every weighted choice, every range
sample, every distribution draw, every incident trigger, every phase transition —
all locked.

**This requires [CodeRoast](https://coderoast.fr).** The free CLI always produces
unique randomized runs.

### Why does this matter?

**Regression testing.** You're building a log parser, anomaly detector, or alerting
rule. Does your code change produce different results? Without a fixed input you can't
tell — a change in output might be your code, or it might just be different random
numbers. With `seed:`, the input is frozen. Any change in your tool's output means
exactly one thing: your code changed something.

**CI test fixtures.** Generate a scenario once, check the output JSONL into your
test suite. Every CI run gets identical input — tests never fail because "the random
data was different today".

**Reproducible bug reports.** "Run `logcraft scenario.yaml` with `seed: 42` and
you'll see exactly what I saw." Without `seed:`, the other person gets a different
run and can't reproduce the problem.

**Multi-machine consistency.** Two engineers, two machines, two timezones. With
`seed:`, they get the same logs. Without it, they don't.

The free CLI is the right tool for exploration, development, and one-shot generation.
When you need the scenario to be a stable artifact — something you can pin, version,
share, and rely on in CI — that's `seed:`, and that's CodeRoast.

---

## Agent library

The `scenario/agents/` directory contains pre-built agent definitions you can copy
and customize:

| File | Agent |
|------|-------|
| `agents/nginx_v1.yaml`, `nginx_v2.yaml` | Nginx web server (two variants) |
| `agents/auth.yaml` | Authentication service |
| `agents/database/postgres.yaml` | PostgreSQL with query logging |
| `agents/database/mysql.yaml` | MySQL |
| `agents/cache/redis.yaml` | Redis |
| `agents/messaging/kafka_broker.yaml` | Kafka broker |
| `agents/messaging/rabbitmq.yaml` | RabbitMQ |
| `agents/search/elasticsearch.yaml` | Elasticsearch |
| `agents/infrastructure/kubernetes.yaml` | Kubernetes |
| `agents/infrastructure/load_balancer.yaml` | Load balancer |
| `agents/external/payment_gateway.yaml` | External payment API |
| `agents/simple/minimal_api.yaml` | Minimal REST API (good starting point) |

Copy the fields and latency from these into your scenarios, or use them as reference
when building your own agents from scratch.

---

## Reading the reference

[`scenario_reference.md`](scenario_reference.md) documents every configuration key
with its type, default value, and description.

When you see a key you don't recognize in a scenario file, look it up in the reference:
1. Find the section by feature name (Phases, Incidents, Rate Modulation, etc.)
2. Read the table row for the key you want
3. Copy the example YAML block
4. Try it in a minimal scenario before adding it to a complex one

The reference is deliberately dry — it's a lookup table, not a tutorial. Use this
guide for the "why", the reference for the "what exactly".
