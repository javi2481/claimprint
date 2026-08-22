# claim-inject (delta)

### Requirement: Explicit dataset and chat scope

`push_claims` MUST resolve a single dataset and a single chat by name
(defaults `demo_4` and `chat_demo_4`). It MUST NOT mutate other datasets or chats.
If the named target is missing, the process MUST exit non-zero without side effects
on other resources.
