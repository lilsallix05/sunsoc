# Guest scenario intake

No sponsor scenario has been received. This form supports future authorized contributions.

- Title, author, organization and contact (keep contact outside the public artifact)
- Permission/license for educational reuse and publication; source artifact hashes
- Original, synthetic, or anonymized data; document the transformation and residual privacy risks
- Learning objective, prerequisite knowledge, expected difficulty, expected duration (estimate)
- Coherent incident truth: initiating event, affected identity, host, timestamps/time zone, supported conclusion, and what cannot be inferred
- Three scored findings, accepted literal answers, evidence IDs and explanation
- Two progressive hints with English and Malay text
- Facilitator debrief, suggested response steps and known false-positive alternatives
- Participant CSV/JSON artifacts; no malware, live credentials, real personal data, executable scripts or external-target dependency
- Reviewer: technical consistency; translation; permission; accessibility; pilot feedback
- Release state and planned retirement date

To integrate, author a case matching `data/cases.json`, validate with `python tools/validate_cases.py reviewed-cases.json`, review in a fresh local database, then replace the dataset and restart. The static dataset is loaded at startup; never accept arbitrary participant content as server code. Changing IDs/questions during a workshop invalidates comparability. Archive the reviewed dataset and its checksum with the workshop record.
