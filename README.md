# Setwise

A mobile fitness coach. You pick a goal, it builds your week and your meals, then guides every set at the gym. It tracks steps, distance and calories for cardio, and has an optional AI coach. Built with **Python (FastAPI)**, **PostgreSQL** and **React Native (Expo)**, with South African privacy law (POPIA) shaping the design. See `docs/POPIA.md`.

```
setwise/
  backend/    FastAPI API, planner, meal generator, progression model, tests
  mobile/     React Native (Expo, TypeScript) app
  infra/db/   PostgreSQL roles (owner, app, retention) created at first start
  docs/       POPIA and security mapping, launch checklist
  docker-compose.yml
```

## What it does

- **Sign up and sign in** with explicit consent screens: required terms and health-data consent, optional AI coach consent. 18+ only.
- **Goal-based plan:** lose weight, build muscle, get stronger or stay fit, for 2 to 6 days a week, with sets, rep ranges, cardio and rest days.
- **Eating guide:** daily calories, protein, carbs and fat for your goal.
- **Meals from what you have:** tick the foods at home, add your protein shakes with label values, mark foods to avoid, and get a day or week of meals sized to your targets. Shakes are added only when they help.
- **Gym mode:** tap "I am at the gym", pick the dumbbell size, then do each set. After every set you log reps and effort and it tells you whether to stay, go up or drop a dumbbell size, and starts a rest timer (longer for hard sets, strength goals and big lifts). Works offline until the final save.
- **Cardio tracker:** live steps (pedometer), distance (GPS) and estimated active calories for walk, run and cycle, plus manual entry for treadmills. Weekly totals and a steps chart.
- **Learning from you:** a per-user progression model estimates your strength from your own sets and sets your next dumbbell weight, deloads when you regress, and adjusts the suggested schedule to your actual adherence.
- **Coach:** answers from your data on the server. With separate consent, an LLM gives open-ended advice from a minimised summary. Crisis, medical red flags and eating-disorder cues get fixed safe replies and never reach a model.
- **Privacy centre:** consent switches, export all your data, change password, sign out everywhere, delete account.

## Run it

Backend with Docker (PostgreSQL, migrations, API, retention job):

```bash
cp backend/.env.example backend/.env      # fill in the secrets (commands are in the file)
docker compose --env-file backend/.env up --build
```

Backend for development (needs PostgreSQL):

```bash
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
./scripts/start_test_pg.sh                # throwaway Postgres for tests; prints the three TEST_* URLs
export TEST_OWNER_URL=... TEST_APP_URL=... TEST_MAINT_URL=...
pytest                                    # 59 tests
```

Mobile:

```bash
cd mobile && npm install
EXPO_PUBLIC_API_URL=https://api.yourdomain.co.za npx expo start     # production builds require https
```

## API

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/signup`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/logout-all`, `/auth/change-password` |
| Account and rights | `GET /me`, `PUT /me/profile`, `POST /me/weight`, `GET /me/weights`, `GET/POST /me/consents`, `GET /me/export`, `POST /me/delete` |
| Training | `GET /plan`, `POST/GET /workouts` |
| Cardio | `POST /cardio/estimate`, `POST/GET /cardio`, `GET /cardio/summary` |
| Nutrition | `GET /nutrition/foods`, `GET/PUT /nutrition/pantry`, `POST /nutrition/plan`, `GET /nutrition/plan/latest` |
| Coach | `POST /coach`, `GET/DELETE /coach/history` |

## What has and has not been verified

Verified in this build:
- 59 backend tests against a real PostgreSQL 16, including encryption at rest, row-level security, a database role that cannot change schema or the audit log, user isolation, consent withdrawal, export, erasure, token theft handling and lockout.
- The app type-checks with no errors and bundles for Android (637 modules).
- A live server accepted signup, onboarding and plan requests.

Not verified yet:
- The app has not been run on a phone or emulator. Step counting, GPS and haptics need a device test, including the permission prompts on iOS and Android.
- Docker Compose was written but not run here.
- The LLM coach is tested with a stand-in. Test it with a real key before launch.
- Food values are typical figures, and calorie estimates carry about 20% error.

## Known limits

- The phone pauses step counting in the background, so cardio needs the app open with the screen on. Health Connect (Android) and HealthKit (iOS) would remove that limit.
- If you close the app with no signal before a workout saves, that workout is lost. An encrypted offline queue is the next step.
- No email verification, password reset by email or two-factor sign-in yet.
- The rate limiter is in memory, so use Redis if you run more than one API instance.
- The `users` and `auth_sessions` tables are readable by the API role because sign-in must look up people before it knows who they are. Everything else is row-level protected.
- Tables are created with SQLAlchemy `create_all`. Use Alembic once the schema starts changing.
