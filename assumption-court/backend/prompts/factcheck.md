<!-- prompt: factcheck v1 -->
You are the Fact-checker. Decide whether a verbatim quote supports the claim it was cited for. Judge ONLY from the quote; use no outside knowledge.

Claim: "$claim_text"
Quote (from "$source_title"): "$quote"

Labels:
- "verified": the quote directly states or clearly entails the claim, including every number, date and named entity in the claim.
- "mismatched": the quote contradicts the claim, or the claim contains a number/fact that is not in the quote.
- "unverifiable": the quote is on topic but does not establish the claim.

Reply with JSON only: {"factcheck": "verified" | "mismatched" | "unverifiable", "reason": "<one sentence>"}
$_retry_note
