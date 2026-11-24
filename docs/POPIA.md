# POPIA and other South African law: how Setwise is built

This is an engineering map, not legal advice. Have a South African attorney or privacy specialist review it before you launch, especially the privacy notice, the operator agreements and the AI provider arrangement.

Setwise processes **special personal information** (health data: body measurements, training, steps, food restrictions). POPIA sections 26 and 27 allow this with the data subject's consent, so consent and minimisation drive the design.

## The eight conditions

| POPIA condition | What the code does | Where |
|---|---|---|
| 1. Accountability (s8) | One Information Officer contact is shown in the app and returned by `/me`. Security events go to an audit log. | `config.py`, `routers/me.py`, `deps.audit` |
| 2. Processing limitation (s9 to 12) | Collect only what a feature needs. Explicit, separate, withdrawable consent for health data and for the AI coach, stored as an append-only ledger with the policy version. Features check consent on every request. No ads, no trackers, no IP or device IDs stored. | `models.Consent`, `deps.require_consent`, `routers/auth.py` |
| 3. Purpose specification (s13, 14) | Data is used for plan, tracking, meals, coaching. Retention job deletes accounts inactive for 2 years, coach chat after 90 days, audit events after 1 year, stale sessions after 30 days. | `maintenance.py` |
| 4. Further processing limitation (s15) | No secondary use. The AI coach receives only a minimised summary and only with its own consent. | `routers/coach.py`, `services/coach.py` |
| 5. Information quality (s16) | Users can correct profile and weight at any time. Inputs are range-validated. Impossible cardio sessions are rejected. | `schemas.py`, `routers/me.py` |
| 6. Openness (s17, 18) | Plain-language privacy summary at sign-up and in the app. You still need a full privacy notice and a PAIA manual (below). | `mobile/src/screens/Auth.tsx` |
| 7. Security safeguards (s19 to 22) | Argon2id passwords, short-lived tokens with rotating refresh tokens and replay detection, account lockout, per-field encryption of health data, row-level security in PostgreSQL, least-privilege database roles, TLS only, `no-store` caching, size limits, audit log. | see "Safeguards" |
| 8. Data subject participation (s23 to 25) | In-app export of everything held (decrypted JSON), correction, and permanent deletion with password confirmation. | `GET /me/export`, `PUT /me/profile`, `POST /me/delete` |

## Other provisions

- **Special personal information (s26, 27):** health data is processed only after explicit consent. Withdrawing it blocks every health endpoint (HTTP 403) immediately.
- **Children (s34, 35):** the app is for people 18 or older. Sign-up checks the date of birth and refuses under-18s. Self-declared age can be false, so keep the terms clear.
- **Operators (s20, 21):** your hosting provider, backup provider and the AI provider are operators. You need a written contract with each that requires security measures and confidentiality.
- **Cross-border transfer (s72):** if you host outside South Africa or use an overseas AI provider, the recipient must be bound by comparable protection, or the user must consent. The AI coach is off by default and has its own consent that says the data may be processed abroad.
- **Automated decisions (s71):** the coach and plan generator give advice. They make no decision with legal or similarly significant effect. Keep it that way.
- **Security compromises (s22):** you must notify the Information Regulator and affected users as soon as reasonably possible after a breach. Write the response plan before launch.
- **Direct marketing (s69):** none is built. Add separate opt-in consent if you ever add it.

## Other acts to check

- **PAIA (Promotion of Access to Information Act 2 of 2000):** private bodies need a PAIA manual. The Information Regulator publishes a template.
- **ECTA (Electronic Communications and Transactions Act 25 of 2002):** show your name, address and contact details, and make terms available before sign-up.
- **Consumer Protection Act 68 of 2008:** terms must be in plain language. Do not make health or results guarantees.
- **Cybercrimes Act 19 of 2020:** criminalises unlawful access. Review the reporting duties that may apply to you.
- **Health Professions Act 56 of 1974 and HPCSA rules:** dietetics and medical advice are regulated professions. Setwise presents general fitness guidance only. Do not call the coach a dietitian, doctor or biokineticist.
- **National Health Act 61 of 2003:** confidentiality rules for health records bind health establishments. They may apply if you integrate with clinics or practitioners.

## Safeguards in detail

| Threat | Control |
|---|---|
| Stolen database dump | Health data, email, workouts, meals and chats are Fernet-encrypted per field with keys that are not in the database. Passwords are Argon2id. Email lookups use an HMAC hash. |
| One user reading another's data | Every query filters by the signed-in user, and PostgreSQL row-level security enforces it again with a role that cannot bypass it. Tests prove both layers. |
| Bug or SQL injection in the API | The API role cannot create or drop tables, cannot change or delete audit rows, and sees nothing unless the request is bound to a user. |
| Stolen phone or token | Tokens live in the device keychain (not in backups). Access tokens last 15 minutes. Refresh tokens rotate on each use and the whole family is revoked on replay. Users can sign out everywhere. |
| Password guessing | Rate limits, lockout after 5 failures, identical errors for unknown email and wrong password, equal-time hashing. |
| Location privacy | GPS is foreground only and used on the phone. Only totals (distance, steps, time, calories) are sent. Raw routes are never stored. |
| AI data leakage | Optional, separately consented, minimised (age band, goal, targets, recent totals). No name, email, ID, birth date or exact weight. Crisis, medical and eating-disorder messages are answered locally and never sent to the model or stored. Model output is advice only and cannot call tools or change data. |
| Excess retention | Daily retention job under its own database role. |
| Erasure | One `DELETE` on the user cascades to every table. The audit trail keeps events with the user link removed. |

## Before you go live

1. Appoint an Information Officer and register with the Information Regulator.
2. Publish a full privacy notice and a PAIA manual. Update `policy_version` when the notice changes so users re-consent.
3. Sign operator agreements (hosting, backups, AI provider) and decide where data is stored.
4. Put keys in a secrets manager or KMS. Practise key rotation (`FIELD_ENCRYPTION_KEYS` accepts several keys).
5. Terminate TLS in front of the API. Set `FORWARDED_ALLOW_IPS` to your proxy so rate limits see real client IPs.
6. Add what this build does not have yet: email verification, password reset by email, optional two-factor sign-in, a shared rate-limit store (Redis) if you run several API instances, and Alembic migrations.
7. Commission a penetration test and write a breach response plan.
8. Complete the Apple and Google store privacy declarations to match this document.
