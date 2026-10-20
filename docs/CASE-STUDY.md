# SunSOC case study

## Problem

A learner can spot a suspicious keyword without being able to reconstruct an incident. SunSOC asks for the reconstruction: which account, which destination, which moment, and which event proves each one.

## What was built

A searchable UTC event stream sits beside a case list. Learners correlate several log sources, keep a timeline in a notebook and submit three findings per incident, each with an evidence note. The server checks the literal answer and stores the note for a facilitator to read. It does not pretend to grade reasoning automatically. Two optional hints each cost 10 points once. SQLite keeps progress; a token-protected facilitator desk shows answer keys, evidence notes, local metrics and a reversible "release solutions" switch.

Eight original synthetic cases cover phishing, password spraying, lateral movement, recovery inhibition, DNS tunnelling indicators, cloud-key misuse, removable-media copying and web execution evidence. Each case has English and Malay source text, exact answers, hints and a response-focused debrief. The interface renders English only.

## What testing found

- Two Flask apps on the same localhost shared Flask's default session cookie, which broke sign-in and CSRF checks. A product-specific cookie name (`sunsoc_session`) fixed it.
- On phones, the desktop table squeezed into unreadable columns. Event rows now stack as labelled cards.
- Opening a hint lost keyboard focus, and the header overflowed with enlarged text. Both were fixed.
- Log search matched JSON field names, so searching `detail` returned every row. Search now matches field values only, with a regression test.

## Trade-offs

- **Normalised synthetic evidence vs raw vendor logs.** Simple, consistent fields make the reasoning the hard part, not the parsing. The cost is realism.
- **Exact-answer scoring vs reasoning review.** A string match is fair and instant; the evidence note keeps the reasoning visible for a human.
- **Local classroom vs public competition.** Open registration, no password recovery and one shared facilitator token are fine for a supervised room, not for the open internet.
