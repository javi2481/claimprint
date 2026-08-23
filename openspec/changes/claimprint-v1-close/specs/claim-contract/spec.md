# claim-contract (delta)

### Requirement: Minimal claim integrity

Published claims MUST have non-empty value, a period string, source_page null or > 0,
identity_key consistent with issuer|period|scope|metric when those fields are present,
and source_bbox normalized 0–1 when set. The Claim constructor MUST enforce these checks
(via validate_claim in __post_init__).
