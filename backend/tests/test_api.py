"""Integration tests: API + database + background task (Celery eager)."""
import pytest
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from shelf import detectors, synthetic
from shelf.services import load_dataset

pytestmark = pytest.mark.django_db


@pytest.fixture
def loaded():
    ds = synthetic.generate(n_stores=40, seed=11)
    load_dataset(ds)
    return ds


@pytest.fixture
def client_auth():
    user = User.objects.create(username="analyst")
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=user).key)
    return c


def test_signals_404_before_any_run(loaded):
    assert APIClient().get("/api/signals/pack-changes/").status_code == 404


def test_anonymous_cannot_start_a_run(loaded):
    assert APIClient().post("/api/runs/").status_code == 401


def test_run_end_to_end_recovers_planted_shrinkflation(loaded, client_auth):
    resp = client_auth.post("/api/runs/")
    assert resp.status_code == 202
    run = client_auth.get(f"/api/runs/{resp.data['id']}/").data
    assert run["status"] == "done" and run["observations_scanned"] == len(loaded.observations)

    found = client_auth.get("/api/signals/pack-changes/?kind=shrinkflation").data["results"]
    planted = {k for k, v in loaded.truth["pack_events"].items() if v["kind"] == "shrinkflation"}
    assert {r["sku"]["code"] for r in found} == planted


def test_price_hike_skus_never_appear_as_pack_changes(loaded, client_auth):
    client_auth.post("/api/runs/")
    codes = {r["sku"]["code"] for r in client_auth.get("/api/signals/pack-changes/").data["results"]}
    hikes = {k for k, v in loaded.truth["pack_events"].items() if v["kind"] == "price_hike"}
    assert codes.isdisjoint(hikes)


def test_launches_and_index_endpoints(loaded, client_auth):
    client_auth.post("/api/runs/")
    launches = client_auth.get("/api/signals/launches/").data["results"]
    assert {l["sku"]["code"] for l in launches} == set(loaded.truth["launches"])
    kolkata = client_auth.get("/api/signals/price-index/?city=Kolkata").data["results"]
    assert any(p["shock"] and p["month"] == "2026-05" for p in kolkata)


def test_brief_works_without_api_key(loaded, client_auth):
    client_auth.post("/api/runs/")
    data = client_auth.get("/api/signals/brief/").data
    assert data["source"].startswith("template")
    assert "shrank their pack" in data["text"]


def test_observation_filters(loaded):
    data = APIClient().get("/api/observations/?sku=SKU001&city=Delhi").data
    assert data["count"] > 0
    assert all(r["sku"] == "SKU001" and r["city"] == "Delhi" for r in data["results"])


def test_full_dataset_scores_against_ground_truth():
    ds = synthetic.generate()
    import pandas as pd
    city = {s["code"]: s["city"] for s in ds.stores}
    df = pd.DataFrame(ds.observations)
    df["city"] = df["store"].map(city)
    pack = detectors.detect_pack_changes(df)
    launches = detectors.detect_launches(df, synthetic.START)
    index = detectors.price_index(df, {l["sku"] for l in launches})
    m = detectors.evaluate(pack, launches, index, ds.truth)
    assert m["shrinkflation_recall"] == 1.0 and m["shrinkflation_precision"] == 1.0
    assert m["pack_events_kind_correct"] == m["pack_events_planted"]
    assert m["false_pack_signals"] == [] and m["shock_found"] and m["shock_false_alarms"] == []
