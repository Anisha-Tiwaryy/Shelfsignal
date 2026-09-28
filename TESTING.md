# Testing

`cd backend && pytest -q` : **18 tests** (10 unit, 8 integration), all passing against PostgreSQL 16.

**Unit (`tests/test_detectors.py`)**, hand-built frames, no database: OCR misread filtering, one-off misread not reported as a pack change, shrinkflation vs proportional resize, price hike ignored, minimum-store threshold, launch detection and days-to-50%, per-gram index exposing shrinkflation the pack index misses, city shock flag, brief built only from detector numbers.

**Integration (`tests/test_api.py`)**, real database + API + background task: 404 before any run, anonymous POST rejected (401), full run via API recovers exactly the planted shrinkflation SKUs, price-hike SKUs never flagged, launches and Kolkata shock via endpoints, brief works with no API key, observation filters, full-size dataset scored against ground truth.

## Bug caught by the suite
The first integration run failed 4 tests with `Retry limit exceeded while trying to reconnect to the Celery result store`. Tests were meant to run background tasks inline, but I set that flag in `tests/conftest.py`, and pytest-django loads Django settings **before** any conftest runs, so Celery still tried to reach Redis. Fix: the inline switch now lives in `config/settings.py` (on under pytest). Moving the same flag into the test file a second time did not fix it; reading the traceback did.

## Stress test (`analysis/stress_test.py`, 3 seeds per setting)
| Setting | Shrinkflation recall | Precision | False pack signals | Launch error (days to 50%) |
|---|---|---|---|---|
| 10 / 20 / 40 / 90 stores | 1.0 | 1.0 | 0 | 5 to 7 |
| OCR misreads 1.5% / 5% / 10% | 1.0 | 1.0 | 0 | 7 to 8 |
| OCR misreads 20% | 1.0 | 0.92 | 1.7 per run | 5 |
| Visits every 7 / 14 / 28 days | 1.0 | 1.0 / 1.0 / 0.95 | 0 | 5.5 / 7.1 / 15.8 |

## Known limitations (honest)
- The detectors are scored on a world I designed; real shelf data will be messier (partial shelf coverage, relabelled SKUs, regional pack variants).
- At 20% OCR noise, repeated misreads on consecutive visits pass the persistence filter and create false pack signals.
- With monthly visits, a proportional resize was once labelled shrinkflation: sparse price reads around the switch pushed the per-gram change over the 5% line.
- Launch speed runs late by roughly half the visit interval, because adoption is only visible at the next visit.
- The Gemini brief path is wired but was not exercised (no API key in the build environment); the template fallback is what the tests and screenshots show.
