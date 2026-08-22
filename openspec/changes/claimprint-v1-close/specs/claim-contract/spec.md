# claim-contract (delta)

### Requirement: Minimal claim integrity

Published claims MUST have non-empty value, a period string, source_page null or > 0,
and identity_key consistent with issuer|period|scope|metric when those fields are present.
