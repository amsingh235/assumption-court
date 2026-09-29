<!-- prompt: grade v1 (citation grader for evaluation; deliberately separate from the Judge) -->
Grade whether the quote supports the claim. Use only the quote.

Claim: "$claim_text"
Quote: "$quote"

- supports: the quote establishes the claim, including all numbers and entities.
- partial: the quote supports part of the claim.
- does-not-support: the quote does not establish the claim or contradicts it.

Reply with JSON only: {"grade": "supports" | "partial" | "does-not-support", "reason": "<one sentence>"}
$_retry_note
