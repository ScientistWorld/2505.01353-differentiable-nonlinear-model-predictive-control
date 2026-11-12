#!/usr/bin/env python3
"""Visible train evaluator for the solution-sensitivity gym.

Protocol (identical to the hidden test slice, different instances):

1. Load the visible instance set and its answers (``cache/train_set.json``;
   regenerated from the public seed below with an independent
   IPOPT/Newton/IFT solver if the cache is missing).  Answers stay in memory.
2. Write the public part of the instances (no answers) to a temporary file and
   run the method's predictor ``bash scripts/predict.sh INSTANCES PREDICTIONS``.
3. Recompute every scored number from the raw predictions (u0 and solution
   sensitivities) against the answers.  Nothing the method writes besides those
   raw values is read.  Any method key found in the predictions is scored in
   every experiment; missing, malformed, non-finite or wrong-solution entries
   count as failed instances, and a failed run gets the worst value of every
   metric in every experiment.

Scoring needs only the Python standard library.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CACHE_PATH = os.path.join(HERE, "cache", "train_set.json")
DEFAULT_OUTPUT = os.path.join(ROOT, "scoring", "scores_train.json")
PREVIOUS_SCORES = os.path.join(ROOT, "scoring", "scores_train.json")
PREDICT_CMD = ["bash", os.path.join(ROOT, "scripts", "predict.sh")]
PREDICT_TIMEOUT_S = 3 * 3600

SPLIT_SEED = 20_250_502
SPLIT_SIZES = {"n_pend": 120, "n_smooth": 90, "n_lqr": 80}
ID_PREFIXES = ("tr_ps", "tr_pt", "tr_lq")

EXPERIMENTS = {
    "pendulum_sensitivity_accuracy": {"kind": "scalar", "u0_tol": 1e-5},
    "pendulum_smoothed_sensitivity": {"kind": "scalar", "u0_tol": 1e-5},
    "bounded_lqr_adjoint_accuracy": {"kind": "vector", "u0_tol": 1e-5, "n_u": 4, "n_theta": 248},
}
SENS_ACCURATE_REL = 1e-4   # relative sensitivity error counted as "accurate"
LOG10_FLOOR = -10.0        # per-instance log10 error is clipped to [LOG10_FLOOR, 0]
METRICS = ("frac_sens_accurate", "mean_log10_sens_rel_err", "frac_u0_accurate")
WORST = {"frac_sens_accurate": 0.0, "mean_log10_sens_rel_err": 0.0, "frac_u0_accurate": 0.0}


def _log(msg: str) -> None:
    print(f"[eval-train] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Hidden set
# ---------------------------------------------------------------------------


def load_hidden_set() -> dict:
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as handle:
            hidden = json.load(handle)
    else:
        _log("train-set cache missing: regenerating ground truth (needs numpy/scipy/casadi)")
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        sys.path.insert(0, HERE)
        import groundtruth  # noqa: E402  (eval/train only)

        hidden = groundtruth.build_split(SPLIT_SEED, prefixes=ID_PREFIXES, log=_log,
                                         checkpoint_path=CACHE_PATH + ".partial", **SPLIT_SIZES)
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        tmp = CACHE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(hidden, handle)
        os.replace(tmp, CACHE_PATH)
    for name in EXPERIMENTS:
        exp = hidden["experiments"][name]
        ids = [inst["id"] for inst in exp["instances"]]
        if not ids or len(set(ids)) != len(ids) or set(ids) != set(exp["answers"]):
            raise RuntimeError(f"train set for {name} is inconsistent")
    return hidden


def public_view(hidden: dict) -> dict:
    return {
        "format_version": hidden.get("format_version", 1),
        "experiments": {
            name: {"problem": hidden["experiments"][name]["problem"], "instances": hidden["experiments"][name]["instances"]}
            for name in EXPERIMENTS
        },
    }


# ---------------------------------------------------------------------------
# Scoring (pure Python)
# ---------------------------------------------------------------------------


def _num(value):
    if type(value) not in (int, float):  # rejects bool, str, None, containers
        return None
    try:
        value = float(value)
    except (OverflowError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _num_list(value, length):
    if not isinstance(value, list) or len(value) != length:
        return None
    out = [_num(v) for v in value]
    return None if any(v is None for v in out) else out


def _norm(values) -> float:
    big = max((abs(v) for v in values), default=0.0)
    if big == 0.0:
        return 0.0
    if not math.isfinite(big):
        return math.inf
    return big * math.sqrt(sum((v / big) ** 2 for v in values))


def score_instance(spec: dict, answer: dict, pred) -> dict:
    """Per-instance record: validity, solution check, relative sensitivity error."""
    rec = {"valid": False, "u0_ok": False, "u0_err": None, "rel_err": None, "sens_ok": False, "log10": 0.0}
    if not isinstance(pred, dict):
        return rec
    if spec["kind"] == "scalar":
        u0, sens = _num(pred.get("u0")), _num(pred.get("du0_dtheta"))
        if u0 is None or sens is None:
            return rec
        u0_true, sens_true = float(answer["u0"]), float(answer["du0_dtheta"])
        u0_err = abs(u0 - u0_true) / max(1.0, abs(u0_true))
        rel = abs(sens - sens_true) / max(1.0, abs(sens_true))
    else:
        u0 = _num_list(pred.get("u0"), spec["n_u"])
        adj = _num_list(pred.get("adjoint"), spec["n_theta"])
        if u0 is None or adj is None:
            return rec
        u0_true = [float(v) for v in answer["u0"]]
        adj_true = [float(v) for v in answer["adjoint"]]
        u0_err = max(abs(a - b) for a, b in zip(u0, u0_true)) / max(1.0, max(abs(b) for b in u0_true))
        rel = _norm([a - b for a, b in zip(adj, adj_true)]) / max(1.0, _norm(adj_true))
    u0_ok = math.isfinite(u0_err) and u0_err <= spec["u0_tol"]
    rec["valid"] = True
    rec["u0_err"] = u0_err
    rec["u0_ok"] = bool(u0_ok)
    rec["rel_err"] = rel
    if u0_ok and math.isfinite(rel):
        rec["sens_ok"] = rel <= SENS_ACCURATE_REL
        rec["log10"] = LOG10_FLOOR if rel <= 0.0 else min(0.0, max(LOG10_FLOOR, math.log10(rel)))
    return rec


def instance_records(hidden: dict, method_preds) -> dict:
    """experiment -> list of per-instance records (fixed order and size)."""
    out = {}
    for name, spec in EXPERIMENTS.items():
        exp = hidden["experiments"][name]
        preds = method_preds.get(name) if isinstance(method_preds, dict) else None
        if not isinstance(preds, dict):
            preds = {}
        out[name] = [score_instance(spec, exp["answers"][inst["id"]], preds.get(inst["id"])) for inst in exp["instances"]]
    return out


def aggregate(records: list) -> dict:
    n = len(records)  # math.fsum: exactly rounded, identical on every Python version
    return {
        "frac_sens_accurate": math.fsum(1.0 for r in records if r["sens_ok"]) / n,
        "mean_log10_sens_rel_err": math.fsum(r["log10"] for r in records) / n,
        "frac_u0_accurate": math.fsum(1.0 for r in records if r["u0_ok"]) / n,
    }


def _clean_name(name: str, taken: set) -> str:
    base = str(name).lstrip("_") or "unnamed"
    cand, k = base, 1
    while cand in taken:
        k += 1
        cand = f"{base}_{k}"
    return cand


def failed_scores(method_names, reason: str) -> dict:
    names = list(method_names) or ["submission"]
    return {
        "experiments": {
            name: {"results": {m: dict(WORST) for m in names}} for name in EXPERIMENTS
        },
        "_evaluation": {"status": "failed", "reason": reason},
    }


def score_predictions(hidden: dict, predictions) -> dict:
    if not isinstance(predictions, dict) or not isinstance(predictions.get("methods"), dict) or not predictions["methods"]:
        return failed_scores(fallback_method_names(), "predictions missing or contain no methods")
    scores = {"experiments": {name: {"results": {}} for name in EXPERIMENTS}}
    taken: set = set()
    for raw_name in sorted(predictions["methods"], key=str):
        name = _clean_name(raw_name, taken)
        taken.add(name)
        recs = instance_records(hidden, predictions["methods"][raw_name])
        for exp_name in EXPERIMENTS:
            scores["experiments"][exp_name]["results"][name] = aggregate(recs[exp_name])
    scores["_evaluation"] = {"status": "ok", "n_instances": {n: len(hidden["experiments"][n]["instances"]) for n in EXPERIMENTS}}
    return scores


def fallback_method_names() -> list:
    try:
        with open(PREVIOUS_SCORES, "r", encoding="utf-8") as handle:
            train = json.load(handle)
        names = set()
        for exp in train.get("experiments", {}).values():
            names.update(k for k in exp.get("results", {}) if not str(k).startswith("_"))
        return sorted(names) or ["submission"]
    except Exception:
        return ["submission"]


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _write(path: str, scores: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(scores, handle, indent=2)
    os.replace(tmp, path)


def run_predictor(public: dict, predict_cmd, timeout_s: float, keep_predictions: str | None = None):
    workroot = os.path.join(ROOT, "tmp")
    os.makedirs(workroot, exist_ok=True)
    workdir = tempfile.mkdtemp(prefix="split_eval_", dir=workroot)
    inst_path = os.path.join(workdir, "instances.json")
    pred_path = os.path.join(workdir, "predictions.json")
    with open(inst_path, "w", encoding="utf-8") as handle:
        json.dump(public, handle)
    t0 = time.time()
    try:
        proc = subprocess.run(list(predict_cmd) + [inst_path, pred_path], cwd=ROOT, timeout=timeout_s)
        code = proc.returncode
    except subprocess.TimeoutExpired:
        code = "timeout"
    _log(f"predictor exit={code} after {time.time() - t0:.1f}s")
    predictions, reason = None, None
    if code != 0:
        reason = f"predictor exit status {code}"
    elif not os.path.exists(pred_path):
        reason = "predictor wrote no predictions file"
    else:
        try:
            with open(pred_path, "r", encoding="utf-8") as handle:
                predictions = json.load(handle)
        except Exception as exc:
            reason = f"unreadable predictions: {exc}"
    if keep_predictions and os.path.exists(pred_path):
        os.makedirs(os.path.dirname(os.path.abspath(keep_predictions)), exist_ok=True)
        shutil.copyfile(pred_path, keep_predictions)
    shutil.rmtree(workdir, ignore_errors=True)
    return predictions, reason


def evaluate(output_path: str = DEFAULT_OUTPUT, predict_cmd=None, keep_predictions: str | None = None,
             timeout_s: float = PREDICT_TIMEOUT_S, predictions_file: str | None = None) -> dict:
    names = fallback_method_names()
    if os.path.exists(output_path):
        os.remove(output_path)
    _write(output_path, failed_scores(names, "evaluation did not complete"))
    hidden = load_hidden_set()
    if predictions_file is not None:
        with open(predictions_file, "r", encoding="utf-8") as handle:
            predictions, reason = json.load(handle), None
    else:
        predictions, reason = run_predictor(public_view(hidden), predict_cmd or PREDICT_CMD, timeout_s, keep_predictions)
    if reason is not None:
        scores = failed_scores(names, reason)
    else:
        scores = score_predictions(hidden, predictions)
    _write(output_path, scores)
    _log(f"wrote {output_path} ({scores['_evaluation']['status']})")
    return scores


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--build-cache-only", action="store_true", help="only (re)build the hidden-set cache")
    parser.add_argument("--rescore", default=None, help="score an existing predictions JSON instead of running the predictor")
    args = parser.parse_args()
    if args.build_cache_only:
        load_hidden_set()
        return
    scores = evaluate(args.output, predictions_file=args.rescore)
    print(json.dumps(scores["experiments"], indent=2))


if __name__ == "__main__":
    main()
