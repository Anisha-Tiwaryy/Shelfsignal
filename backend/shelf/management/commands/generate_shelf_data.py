import json
from pathlib import Path

from django.core.management.base import BaseCommand

from shelf import synthetic
from shelf.services import load_dataset


class Command(BaseCommand):
    help = "Generate synthetic shelf-audit data with planted events and load it into the database."

    def add_arguments(self, parser):
        parser.add_argument("--stores", type=int, default=90)
        parser.add_argument("--seed", type=int, default=7)
        parser.add_argument("--truth-out", default="ground_truth.json")

    def handle(self, *args, **opts):
        ds = synthetic.generate(n_stores=opts["stores"], seed=opts["seed"])
        n = load_dataset(ds)
        Path(opts["truth_out"]).write_text(json.dumps(ds.truth, indent=2, default=str))
        self.stdout.write(self.style.SUCCESS(
            f"Loaded {len(ds.stores)} stores, {len(ds.skus)} SKUs, {n} observations. Ground truth: {opts['truth_out']}"))
