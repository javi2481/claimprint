# Proposal: claimprint-v1-close

## Intent

Close Claimprint **v1.0.0** as a defendable release: ops-safe inject, honest pilot metrics,
minimal claim contracts, and a single narrative SoT in README. Not a feature expansion.

## In scope

- Gate A: `push_claims` mutates only `demo_4` / `chat_demo_4` (fail-closed)
- Gate B: rename chat scores; drop invented page=1 in `chunk_to_hit`; remeasure + freeze once
- Gate C/D: Claim validation; zero-value validate fix; drop dead recipe `threshold`; content-first period when safe
- Gate E: README pipeline gold≠SoT; two-experiment framing; OpenSpec = design history

## Out of scope

bbox / geometry / document_id / source_hash; prompt-vs-claim ablations; portable cache fingerprint;
weighted page select; LinkedIn glamour; Legal vertical.

## Rollback

Revert this change folder and the code commits. Fail-closed inject is safe.
