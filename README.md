# ShelfSignal

**Market signals mined from shelf-audit data.** A working prototype of a data product idea: the structured rows an image-recognition pipeline already extracts from field-rep shelf photos (SKU, shelf price, pack weight, in/out of stock) contain signals a whole market would pay for.

| Signal | Question it answers |
|---|---|
| Shrinkflation watch | Which products quietly shrank their pack while the shelf price stayed flat, where, and when? |
| Launch velocity | How fast did a new product actually reach shelves (days to 25% and 50% of stores)? |
| Hidden inflation index | Per city, how far does price *per gram* run ahead of *pack* price? Plus city price-shock alerts. |

> Runs on **simulated data** with planted, known events so every detector is scored against ground truth. No real brand, store, or image data is used.

## Stack
Django 5 + Django REST Framework, PostgreSQL, Celery on Redis (background detector runs), React 18 + TypeScript (Vite), pandas/NumPy, Google Gemini API for the weekly brief (template fallback when no key is set), pytest + pytest-django, GitHub Actions CI.

## Run it
```bash
# backend (needs PostgreSQL and Redis running)
cd backend
pip install -r requirements.txt
export POSTGRES_HOST=localhost POSTGRES_PASSWORD=... CELERY_BROKER_URL=redis://localhost:6379/0
python manage.py migrate
python manage.py generate_shelf_data          # 90 stores, 40 SKUs, ~78k observations
python manage.py drf_create_token <username>  # after createsuperuser
celery -A config worker -l info &             # background job worker
python manage.py runserver

# frontend
cd frontend && npm install && npm run dev      # VITE_API_URL defaults to http://localhost:8000/api
```
No Postgres handy? `DB_ENGINE=sqlite` works too. `GEMINI_API_KEY=...` switches the brief from template to Gemini.

## API
| Method | Endpoint | Notes |
|---|---|---|
| POST | `/api/runs/` | Token auth. Queues a Celery detector run, returns 202 |
| GET | `/api/runs/{id}/` | Poll run status, rows scanned, duration |
| GET | `/api/signals/pack-changes/?kind=shrinkflation` | Latest completed run (or `?run=`) |
| GET | `/api/signals/launches/` | Adoption curve per new SKU |
| GET | `/api/signals/price-index/?city=Kolkata` | Pack vs per-gram index, shock flags |
| GET | `/api/signals/brief/` | Weekly brief; `source` says Gemini or template |
| GET | `/api/observations/?sku=&city=&store=` | Paginated raw rows |
| GET | `/api/skus/` | Catalogue |

## Results (default seed)
6/6 shrinkflation events found, 0 false positives, 9/9 pack changes correctly classified (shrinkflation vs proportional resize vs upsize), 2/2 plain price hikes correctly ignored, Kolkata price shock caught with no false alarms. Detector run over 78,028 rows: ~1.5 s. See `analysis/stress_test.py` for where it breaks, and `TESTING.md`.
