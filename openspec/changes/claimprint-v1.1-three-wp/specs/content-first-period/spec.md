# Spec delta: content-first-period

## Requirement: Period from document body first

WHEN extracting press or presentation period
THEN the system MUST read period from parsed body text (front matter / content_list page 0)
BEFORE reading quarter tokens from the PDF filename.

### Scenario: Portada date wins over missing filename token

- GIVEN a press PDF whose filename has no `1t26` token
- AND content_list block on page 0 contains `31 de marzo de 2026` and `1T26`
- WHEN `fill_press_release` runs
- THEN `period` MUST be `2026-03-31`

### Scenario: Filename fallback

- GIVEN body text has no resolvable period
- AND filename contains `2t26`
- WHEN extraction runs
- THEN `period` MUST be `2026-06-30`
