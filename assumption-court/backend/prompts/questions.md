<!-- prompt: questions v1 -->
The court has finished. Write exactly 3 sharp questions the user should ask (their team, their data or an expert) before betting on this assumption.

Input: "$input_text"
Premise verdict: $premise_verdict
Cause verdicts: $causes
Claims that could not be verified: $unverified_claims

Each question: one sentence, specific to this case, answerable with data they could obtain. No generic advice.

Reply with JSON only: {"questions_to_ask": ["...", "...", "..."]}
$_retry_note
