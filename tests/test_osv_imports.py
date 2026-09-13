"""Test package imports and core module APIs."""

import numpy as np
import osv
from osv.eval import compute_dice
from osv.eval.bias import evaluate_automation_bias
from osv.deploy import get_latency_budget
from osv.models import list_baselines
from osv.serve import get_server_metadata
from osv.deid import verify_no_phi
from osv.datasets import load


def test_version_and_metadata():
    assert osv.__version__ == "0.1.0"
    assert "RESEARCH USE ONLY" in osv.__doc__


def test_eval_dice():
    mask1 = np.array([[1, 1], [0, 0]], dtype=np.uint8)
    mask2 = np.array([[1, 1], [0, 0]], dtype=np.uint8)
    score = compute_dice(mask1, mask2)
    assert np.isclose(score, 1.0)


def test_bias_evaluator():
    res = evaluate_automation_bias([0.95, 0.92, 0.94], acceptance_rate=0.45)
    assert res["pass_threshold"] is True


def test_latency_budget():
    budget = get_latency_budget()
    assert budget["target_latency_p95_ms"] <= 50.0
    assert budget["target_fps"] >= 30.0


def test_baselines_catalog():
    baselines = list_baselines()
    assert len(baselines) == 5
    assert "M1" in baselines


def test_server_disclaimer():
    meta = get_server_metadata()
    assert "RESEARCH USE ONLY — NOT FOR CLINICAL USE" in meta["disclaimer"]


def test_deid_verification(tmp_path):
    from PIL import Image

    sample = tmp_path / "test_sample.png"
    Image.new("RGB", (32, 32), color=(100, 100, 100)).save(sample)
    res = verify_no_phi(sample)
    assert res["clean"] is True




def test_datasets_loader():
    res = load("cholecseg8k", split="train")
    assert res["status"] == "ready"
