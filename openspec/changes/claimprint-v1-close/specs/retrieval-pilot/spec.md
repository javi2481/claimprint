# retrieval-pilot (delta)

### Requirement: Hits require a resolved page

`chunk_to_hit` MUST return `None` when page cannot be resolved. It MUST NOT invent page `1`.
