# Estuary — YeNo paper competition entry

Independent Python standard-library strategy. Run `python3 server.py`; POST JSON observations to `http://127.0.0.1:8097/decide`. Bind another host/port with `--host` / `--port`. No credentials, wallet, trade client, database or third-party packages are required. One process per evaluator account/session; restart between independent evaluation runs.

## Strategy

Estuary converts the observable BTC/target distance into a diffusion probability over the remaining market time. It estimates dollar volatility from up to 60 monotonically timestamped public reference observations, with a conservative $12/sqrt(second) floor. This is an uncalibrated modeling assumption, not a measured forecasting edge. It evaluates both outcomes, walks the complete supplied ask/bid ladders, charges crypto fees and the 1% overlay on each side, and selects among 41 quantity candidates including the minimum size. It requires at least 2.5 cents of modeled entry advantage after entry fees and a two-cent entry cushion. The projected round-trip loss, including two cents adverse movement on each side, must fit 8% of available cash. Total bid depth must cover twice the intended quantity. Fee-inclusive spend stays below cash, the supplied limit and $5.

Entries are allowed only with 45–240 seconds remaining. Future/stale/provisional references, malformed/nonfinite inputs, crossed books, inadequate depth and completed target volume suppress entries. Owned positions exit at nonnegative cycle PnL, an estimated 6% capital loss, reference direction reversal, missing full exit depth, or 30 seconds to expiry. Cycle PnL includes already received partial-sale proceeds and fees. Exit requests can execute against bids without asks and without complete exit liquidity. The evaluator remains responsible for fills, partial execution, position/cash state and scored volume.

Differences from House Bot are architectural: probabilistic time/volatility-adjusted reference signal, bidirectional candidate selection, cash/depth-dependent sizing, stressed loss gating, and partial exit handling. This is independently implemented from the public contract, not a copied HouseBot with changed constants.

## Verification

Run `python3 fetch_official.py` to obtain SHA256-pinned official fixtures from Builderr, then `python3 verify.py`. The verification runner starts a temporary loopback server, runs the unmodified official smoke program, tests strategy boundaries, performs 100 local HTTP requests against the 200 ms limit, checks malformed JSON rejection, and shuts down the server. Results are in `verification-results.json`.

All fixtures used by the boundary tests/comparison are handcrafted or the single official sample. They are not real market replay. Builderr does not publish its replay harness or recorded development paths. There is no official score, qualification, profitability, or 24-hour volume result for Estuary. A 30-second exit request does not guarantee flatness when no executable bids remain, and local latency does not guarantee remote latency. Two-cent stress is a deterministic cushion, not an execution guarantee. There is no global evaluation-end timestamp in the public sample; flatness near the final run boundary remains evaluator-dependent. Book freshness is evaluator-owned under the published contract; the sample exposes no book timestamps. Runtime state is only volatility history, so restart falls back to the prior.

## Sources and rights

Rules: https://builderr.ai/downloads/yeno-evaluator-contract.md
Starter instructions: https://builderr.ai/downloads/yeno-starter-readme.md
Benchmark: https://builderr.ai/downloads/yeno-house-bot-benchmark.md
Source URLs and verified fixture hashes: `sources.json`.

No explicit redistribution license was found in the inspected official Python headers or contract. Therefore official House Bot, smoke program, sample and contract are kept outside this submission archive and fetched directly for local verification. Independent entry files are provided for entrant review/evaluation; this package does not assert an upstream license or grant an unapproved public license on the owner's behalf.

## Submission and contact

Entrant: Xiaoxue, maintained through the gougousongsong GitHub account. Contact: https://github.com/gougousongsong/estuary-yeno/issues . The notification sender is outbound-only; use repository Issues for replies. The exact submitted Git commit identifies the frozen build. No official score, qualification or prize is claimed.
