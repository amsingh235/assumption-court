<!-- prompt: baseline v1 -->
You are a careful analyst. Decide whether the claim is supported by the retrieved evidence below.

Claim: "$claim"

Retrieved evidence (verbatim quotes):
$pool

Label:
- SUPPORTED: the evidence shows the claim is true.
- REFUTED: the evidence shows the claim is false.
- INCONCLUSIVE: the evidence is insufficient or mixed.

Cite up to 6 items as {pool_id, claim_text} where claim_text is what that quote supports.

Reply with JSON only: {"label": "SUPPORTED" | "REFUTED" | "INCONCLUSIVE", "rationale": "<at most 3 sentences>", "citations": [{"pool_id": "pool-1", "claim_text": "..."}]}
$_retry_note
