# Performance: API and RapidOCR memory

| Field | Value |
| --- | --- |
| Metric | Peak and retained Linux process tree RSS |
| Condition | One API with sign-in state; 30 synthetic labelled PNGs; one OCR child; no database calls |
| Objective | Below 512 MB; hosted move requires about 400 MB (ADR-0004) |
| Production size | The 30 labelled pages in `data/seed/png`; 15,000 page sizing in `docs/design/docket-hld.md` is not exercised |
| Date | 2026-10-11 |
| Base commit | `e3498488ffd18203d4042eddc132bddc6547b5f7` |
| Change | Uncommitted on `chore/NOTASK-17-MemorySecurityAcceptance` |
| Task | NOTASK-17 |

## Measurement

The original configuration reached 1,083,379,712 bytes over 30 pages in 45.43 seconds. A
prototype with bounded ONNX threads, batches, no CPU arena, maximum detector sizing and
recycling after every page reached 372,084,736 bytes in 45.31 seconds. These initial numbers are one run each,
from `/tmp/docket-memory-probe.py`; the baseline and comparison are retained under
`.scratch/NOTASK-17/memory-before-1.json` and `memory-comparison.json`.

The durable command is `make bench-memory-repeat`. It launches three fresh processes running
`evals.memory_bench`, each reading all 30 pages. It samples parent and descendants at 20 ms.
The first corrected run of the actual implementation reached 379,539,456 bytes in 46.01 seconds.
Repeat measurements are recorded in `.scratch/NOTASK-17/memory-repeat-1.json` through
`memory-repeat-3.json`.

The baseline was repeated twice more with the same 30 page workload, forcing
`RapidOCR(params={})` and a recycle interval of 500, matching the original implementation.
The local script is `.scratch/NOTASK-17/memory-before-probe.py`; the second and third runs
used `make bench-memory MEMORY_COMMAND='/tmp/docket-memory-baseline-repeat.py data/seed/png/SYN-APP-001_10th_marksheet.png all'`.
Its raw readings are retained as `memory-before-1.json` through `memory-before-3.json`.
The before and after harnesses differ in output format, but both construct API sign-in state,
sample the same process tree every 20 ms and read the same ordered pages through `ProcessEngine`.

| Original configuration | Minimum | Median | Maximum | Runs |
| --- | --- | --- | --- | --- |
| Peak bytes | 1,083,379,712 | 1,083,863,040 | 1,085,632,512 | 3 |
| Elapsed seconds | 42.81 | 45.43 | 46.66 | 3 |

| Actual implementation | Minimum | Median | Maximum | Runs |
| --- | --- | --- | --- | --- |
| Peak bytes | 377,880,576 | 379,469,824 | 379,551,744 | 3 |
| Elapsed seconds | 44.80 | 47.46 | 53.15 | 3 |

The median peak is about 65% below the original median. It is about 362 MiB,
leaving about 150 MiB below a 512 MiB limit in the measured scope.
These benchmark runs share a development machine; elapsed times do
not establish a production latency percentile.

An earlier probe accidentally imported the API in the spawned OCR child as well as the parent,
reaching 405,295,104 and 408,678,400 bytes. Moving API imports into the benchmark's main
function corrects that harness overhead. These two exploratory runs are excluded from the
final repeated measurements.

This scope includes constructed API and sign-in objects plus the OCR child. It excludes the
gunicorn supervisor, a running HTTP server, database connection pools, simultaneous requests,
kernel memory and a container memory limit. Process RSS sums shared pages, while a container
limit also counts other memory. Therefore a local result below 512 MB does not establish that
the full deployment stays below its limit.

## Profile and change

The original long lived child retains native OCR allocations across pages. ONNX CPU arenas,
parallel inference and recognition batches contribute to its peak. RapidOCR's default detector
minimum sizing also enlarges the image after Docket has already limited its longest side to
640 pixels. `Det.limit_type=max` prevents this enlargement; the installed library ignores
`Det.limit_side_len` in this mode and uses its own upper limit, so no ineffective 640 setting
is added. The input remains bounded by Docket's existing 640 pixel preprocessing.

`app/gateway/rapidocr_engine.py` selects one ONNX intra/inter operation thread, batches of one,
and disables the CPU allocation arena. `app/core/config.py` defaults to recycling the child
after each page, releasing native buffers before the next page. Recycling adds repeated model
loading. The login hash default is one; Argon2's memory and strength are unchanged. The task's
shared compute admission serializes upload normalization, hashing and OCR to avoid combining
their separate memory peaks. Increasing `ENGINE_RECYCLE_AFTER`, `LOGIN_HASH_CONCURRENCY` or
`WEB_CONCURRENCY` leaves the measured profile.

The benchmark records RSS after every page and all recognized words. Native allocations are
measured through `/proc`, because Python allocation tracing alone cannot account for ONNX
buffers. A Python allocation flame graph was not collected; no per-frame allocation shares
are claimed.

## Output and regression evidence

Actual tuned words match the prototype's words exactly on all 30 pages. Against the labels,
classification and field accuracy are 100%, with zero read errors. The original configuration
had 100% classification and 99.5% field accuracy. Original and tuned OCR outputs are not byte
identical: values or review decisions change on nine documents. The comparison is recorded in
`memory-comparison.json`; this is a visible consequence of preventing detector enlargement,
and the old recording and confidence threshold have not been rewritten.

The regression `test_default_recycling_releases_the_child_after_each_page` failed against
the original default with a live child remaining after a read. After the change,
`make test-memory` reports `21 passed in 8.84s`, including real engine extraction, coordinate,
offline operation and synthetic phone photo tests. `make typecheck` reports
`Success: no issues found in 158 source files`. The final repository gate is recorded by the
task's consolidated report.

A second regression demonstrated that a failed OCR page originally bypassed recycling even
at the limit. The recycle check now runs before the engine error is raised, releasing the
child's native allocations before shared compute admission permits hashing or normalization.
That test failed with a live child remaining, and passed after the check was moved.

## Not tried

- A 15,000 page stress run.
- Real student documents, additional scripts or non-English model variants.
- Smaller models or reduced password hashing strength.

## Complete runtime workload

`make bench-memory-runtime` drives an already running isolated local API at
`http://127.0.0.1:8187`. It creates a unique synthetic staff account and imports 20 applications,
uploads all 30 labelled PNGs, then submits four concurrent 25 megapixel PNG uploads and four
concurrent real sign-ins while the OCR worker processes its queue. All 34 documents must finish
with status `read` and `read_engine=rapidocr`; the driver fails on unexpected HTTP status codes
or failed documents. It generates the large PNGs on the host, keeping host fixture construction
outside the measured container. The JSON summary is `.scratch/NOTASK-17/memory-runtime.json`.

The caller starts the existing Docker image with one gunicorn worker, the processing loop on,
`--memory=512000000 --memory-swap=512000000 --cpus=1`, an isolated local Postgres network and no
environment file mount. This uses a decimal 512 MB limit, stricter than 512 MiB. The caller must
record `/sys/fs/cgroup/memory.peak`, `memory.events` and container OOM state after the workload,
including the HTTP server, supervisor, connections and OCR subprocesses.

The completed runtime run on 2026-10-11 used image
`sha256:b246acd006debaeb442953092b8328c93f90ede5e32d98dd059b3edb693004cb`.
All 34 documents completed with RapidOCR, four sign-ins succeeded, and there were zero
unexpected HTTP errors in 97.29 seconds. The final cgroup counters were:

```text
memory.peak: 449486848
memory.max: 512000000
memory.events: max 0, oom 0, oom_kill 0
container: running, OOMKilled=false
```

This is 449.49 MB (428.66 MiB), leaving 62.51 MB below the strict decimal limit.
The peak includes the API process tree, HTTP server, database connections and container
memory accounting. Postgres itself runs in a separate isolated container and is outside
the API budget. This establishes that the measured synthetic mixed workload fits. It does
not establish a bound for arbitrary traffic, multiple workers, other engines or external
Vision responses. The runtime does not meet ADR-0004's approximate 400 MB hosting target.

## How to repeat

1. Use this task branch with the locked environment installed and synthetic PNG fixtures present.
2. Run `make test-memory`.
3. Run `make bench-memory-repeat`; inspect the three JSON files under `.scratch/NOTASK-17`.
4. Start the isolated one worker image with the limits above, run `make bench-memory-runtime`,
   and record the final cgroup counters. Use a fresh container to reset the peak counter.
