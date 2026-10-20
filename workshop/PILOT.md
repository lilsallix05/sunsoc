# Pilot workshop kit

Status: a prepared protocol, not a completed event. No participants, university attendance, satisfaction gains or sponsor involvement have been claimed.

## Before the session

Recruit a small voluntary cohort through the organizer's authorized channel; no invitation is sent by this package. Confirm a facilitator and accessibility support, review the Malay text with a fluent speaker, and give each learner a pseudonym. Test the loopback installation or approved team access. Start with a clean database, confirm that retired solutions are hidden, and avoid distributing the instructor folder. Explain that examples are synthetic and clocks are UTC.

Collect informed opt-in consent separately from attendance. Participation in scoring does not require feedback. Avoid real names in the app. Store any attendance/consent list separately under the organizer's retention policy; never merge it into exported public scoreboards. Agree the deletion date before collecting data. The application collects one optional end-of-session response per account; its pre-confidence field is retrospective. For a genuine prospective baseline, record the baseline form below at the start under the pseudonym and reconcile only with consent.

## 90-minute facilitation

| Time | Activity | Facilitator prompt |
|---|---|---|
| 0–10 | Consent, baseline and orientation | “What can this log establish, and what remains uncertain?” |
| 10–30 | Invoice case in pairs | Follow MSG-104 through delivery, proxy and identity events. |
| 30–60 | Lateral movement or DNS case | Cite event IDs, distinguish original identity from runtime account, or correlate host inventory. |
| 60–80 | Group debrief | Compare two plausible hypotheses; explain the decisive event. |
| 80–90 | Optional survey and export | Save notes and export progress. Explain what metrics can and cannot show. |

Use hints after learners state a hypothesis. Each native-range hint costs 10 points per case; this is a game mechanic and must not be treated as an ability ranking. The optional CTFd import differs: each finding is a challenge and its hints are charged separately by CTFd. Do not compare scores across these modes.

## Baseline / borang awal

- Pseudonym / nama samaran: ______
- Confidence interpreting security logs, 1–5 / keyakinan mentafsir log keselamatan, 1–5: ______
- Familiarity with UTC timelines / kebiasaan dengan garis masa UTC: none / some / frequent
- Optional university / universiti pilihan: ______
- Consent for aggregate learning evaluation / persetujuan penilaian pembelajaran agregat: yes / no

## Measures and interpretation

- Actual attendance: organizer's consented check-in count. **Registered accounts are not attendance.**
- Case completion: three validated answers; rate = completed cases / started cases. Report denominators.
- Time: wall-clock from first case open to final correct answer. Pauses and hints are not excluded. No start/completion means no measured duration, not zero.
- Confidence: paired post minus pre on a five-point self-report scale. Label retrospective or prospective. It is not proof of skill improvement or causal impact.
- Universities represented: distinct nonempty voluntary strings, cleaned manually after permission. Spellings can inflate this count.
- Educational value: review anonymized free text and record themes with denominators. Do not invent survey ratings.

Export facilitator JSON, inspect notes for personal details, and redact before sharing. Keep raw consented data private. The `metrics-schema.json` records measurement definitions; `pilot-results-template.json` intentionally contains nulls and an empty participant list. Replace nulls only after actual collection.

## Retiring cases and future events

After the exercise, use the facilitator panel to release selected solutions. Review the library in a signed-out browser. Publication outside the local range requires separate approval and rights review. Use `GUEST-SCENARIO.md` for sponsor inputs and document attribution and permission before release.
