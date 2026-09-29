<!-- prompt: classify v1 -->
You classify user input for an evidence-based "assumption court".

Input: "$text"

Decide:
- "assumption": a statement that can be tested as true or false (e.g. "D2C brands fail because of ads").
- "why-question": a question asking WHY something happens (e.g. "Why do D2C brands fail?"). It takes a premise for granted.

Also write `premise`: the single testable statement to put on trial.
- For an assumption: restate it as a clear declarative claim (keep its meaning; do not soften or strengthen it).
- For a why-question: the premise the question takes for granted (e.g. "Most D2C brands fail").

Reply with JSON only: {"input_type": "assumption" | "why-question", "premise": "<statement>"}
$_retry_note
