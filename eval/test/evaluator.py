#!/usr/bin/env python3
"""Hidden test evaluator for the solution-sensitivity gym.

Protocol (identical to the visible train slice, different instances):

1. Load the hidden instance set and its answers (``cache/hidden_set.json``;
   regenerated from the private seed below with an independent
   IPOPT/Newton/IFT solver if the cache is missing).  Answers stay in memory.
2. For every experiment in turn, write the public part of its instances (no
   answers) to a temporary file and run the method's predictor
   ``bash scripts/predict.sh INSTANCES PREDICTIONS`` on it.  Each call has a
   compute budget of CPU_FIXED_S + n_instances * cpu_per_instance_s CPU
   seconds, measured over the predictor's whole process tree (children,
   threads and detached descendants included); a call that exceeds it is
   killed.  Wall-clock time is never scored.
3. Recompute every scored number from the raw predictions (u0 and solution
   sensitivities) against the answers.  Nothing the method writes besides those
   raw values is read.  Any method key found in the predictions is scored in
   every experiment; missing, malformed, non-finite or wrong-solution entries
   count as failed instances.  A crashed, empty, timed-out or over-budget call
   fails the run: every method gets the worst value of every metric in every
   experiment.

Scoring needs only the Python standard library.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import os
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CACHE_PATH = os.path.join(HERE, "cache", "hidden_set.json")
DEFAULT_OUTPUT = os.path.join(ROOT, "scoring", "scores_test.json")
TRAIN_SCORES = os.path.join(ROOT, "scoring", "scores_train.json")
PREDICT_CMD = ["bash", os.path.join(ROOT, "scripts", "predict.sh")]

SPLIT_SEED = 905_771_243
SPLIT_SIZES = {"n_pend": 240, "n_smooth": 180, "n_lqr": 160}
ID_PREFIXES = ("ps", "pt", "lq")
EXTRA_SIZES = {"n_near": 150, "n_lqr_large": 470}
EXTRA_PREFIXES = ("pk", "ll")

# Compute budget per predictor call (CPU seconds of the whole process tree).
CPU_FIXED_S = 150.0
EXPERIMENTS = {
    "pendulum_sensitivity_accuracy": {"kind": "scalar", "u0_tol": 1e-5, "cpu_per_instance_s": 1.0},
    "pendulum_smoothed_sensitivity": {"kind": "scalar", "u0_tol": 1e-5, "cpu_per_instance_s": 1.0},
    "pendulum_near_active_set_change": {"kind": "scalar", "u0_tol": 1e-5, "cpu_per_instance_s": 1.0},
    "bounded_lqr_adjoint_accuracy": {
        "kind": "vector", "u0_tol": 1e-5, "n_u": 4, "n_theta": 248, "cpu_per_instance_s": 0.3,
    },
    "bounded_lqr_large_adjoint": {
        "kind": "vector", "u0_tol": 1e-5, "n_u": 8, "n_theta": 976, "cpu_per_instance_s": 0.15,
    },
}
WALL_SAFETY_FACTOR = 4.0   # wall-clock safety stop: 4x the CPU budget + 10 min (never binding for CPU-bound work)
POLL_S = 1.0
SENS_ACCURATE_REL = 1e-4   # relative sensitivity error counted as "accurate"
LOG10_FLOOR = -10.0        # per-instance log10 error is clipped to [LOG10_FLOOR, 0]
METRICS = ("frac_sens_accurate", "mean_log10_sens_rel_err", "frac_u0_accurate")
WORST = {"frac_sens_accurate": 0.0, "mean_log10_sens_rel_err": 0.0, "frac_u0_accurate": 0.0}


def _log(msg: str) -> None:
    print(f"[eval-test] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Hidden set
# ---------------------------------------------------------------------------


def _save_cache(hidden: dict) -> None:
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    tmp = CACHE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(hidden, handle)
    os.replace(tmp, CACHE_PATH)


def load_hidden_set() -> dict:
    groundtruth = None
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as handle:
            hidden = json.load(handle)
    else:
        _log("hidden-set cache missing: regenerating ground truth (needs numpy/scipy/casadi)")
        sys.path.insert(0, HERE)
        import groundtruth  # noqa: E402  (eval/test only)

        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        hidden = groundtruth.build_split(SPLIT_SEED, prefixes=ID_PREFIXES, log=_log,
                                         checkpoint_path=CACHE_PATH + ".partial", **SPLIT_SIZES)
        _save_cache(hidden)
    if any(name not in hidden.get("experiments", {}) for name in EXPERIMENTS):
        _log("hidden-set cache lacks experiments: building them (needs numpy/scipy/casadi)")
        if groundtruth is None:
            sys.path.insert(0, HERE)
            import groundtruth  # noqa: E402,F811  (eval/test only)
        groundtruth.build_extra(hidden, SPLIT_SEED, prefixes=EXTRA_PREFIXES, log=_log, save=_save_cache,
                                **EXTRA_SIZES)
        _save_cache(hidden)
    for name in EXPERIMENTS:
        exp = hidden["experiments"][name]
        ids = [inst["id"] for inst in exp["instances"]]
        if not ids or len(set(ids)) != len(ids) or set(ids) != set(exp["answers"]):
            raise RuntimeError(f"hidden set for {name} is inconsistent")
    return hidden


def public_view(hidden: dict, names=None) -> dict:
    names = list(EXPERIMENTS) if names is None else list(names)
    return {
        "format_version": hidden.get("format_version", 1),
        "experiments": {
            name: {"problem": hidden["experiments"][name]["problem"], "instances": hidden["experiments"][name]["instances"]}
            for name in names
        },
    }


def cpu_budget(hidden: dict, name: str) -> float:
    return CPU_FIXED_S + EXPERIMENTS[name]["cpu_per_instance_s"] * len(hidden["experiments"][name]["instances"])


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
    names = sorted({_clean_name(m, set()) for m in method_names}) or ["submission"]
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
        with open(TRAIN_SCORES, "r", encoding="utf-8") as handle:
            train = json.load(handle)
        names = set()
        for exp in train.get("experiments", {}).values():
            names.update(k for k in exp.get("results", {}) if not str(k).startswith("_"))
        return sorted(names) or ["submission"]
    except Exception:
        return ["submission"]


# ---------------------------------------------------------------------------
# Process-tree CPU accounting
# ---------------------------------------------------------------------------

_CLK = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100
_SUBREAPER = None


def _enable_subreaper() -> bool:
    """Orphaned descendants of the predictor are re-parented to this process,
    so detached workers stay inside the accounted tree (Linux prctl)."""
    global _SUBREAPER
    if _SUBREAPER is None:
        try:
            libc = ctypes.CDLL(None, use_errno=True)
            _SUBREAPER = libc.prctl(36, 1, 0, 0, 0) == 0  # PR_SET_CHILD_SUBREAPER
        except Exception:
            _SUBREAPER = False
    return bool(_SUBREAPER)


def _proc_table() -> dict:
    """pid -> (ppid, cpu seconds of the process incl. its reaped children)."""
    table = {}
    try:
        names = os.listdir("/proc")
    except OSError:
        return table
    for entry in names:
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/stat", "rb") as handle:
                data = handle.read().decode("ascii", "replace")
            fields = data[data.rfind(")") + 2 :].split()
            ppid = int(fields[1])
            ticks = int(fields[11]) + int(fields[12]) + int(fields[13]) + int(fields[14])
        except (OSError, IndexError, ValueError):
            continue
        table[int(entry)] = (ppid, ticks / _CLK)
    return table


def _descendants(table: dict, root: int) -> list:
    children: dict = {}
    for pid, (ppid, _) in table.items():
        children.setdefault(ppid, []).append(pid)
    out, stack = [], [root]
    while stack:
        for child in children.get(stack.pop(), []):
            out.append(child)
            stack.append(child)
    return out


def _children_cpu() -> float:
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


def _kill_and_reap_tree(root: int) -> None:
    for _ in range(50):
        pids = _descendants(_proc_table(), root)
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        reaped = False
        while True:
            try:
                pid, _ = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                break
            if pid == 0:
                break
            reaped = True
        if not pids and not reaped:
            break
        time.sleep(0.1)


def run_predictor(public: dict, predict_cmd, cpu_budget_s: float | None, keep_dir: str | None = None,
                  tag: str = ""):
    """Run one predictor call; returns (predictions or None, failure reason or None, cpu seconds)."""
    _enable_subreaper()
    workroot = os.path.join(ROOT, "tmp")
    os.makedirs(workroot, exist_ok=True)
    workdir = tempfile.mkdtemp(prefix="split_eval_", dir=workroot)
    inst_path = os.path.join(workdir, "instances.json")
    pred_path = os.path.join(workdir, "predictions.json")
    with open(inst_path, "w", encoding="utf-8") as handle:
        json.dump(public, handle)
    me = os.getpid()
    cpu0 = _children_cpu()
    wall_limit = WALL_SAFETY_FACTOR * cpu_budget_s + 600.0 if cpu_budget_s is not None else 3 * 3600.0
    t0 = time.time()
    proc = subprocess.Popen(list(predict_cmd) + [inst_path, pred_path], cwd=ROOT, start_new_session=True)
    code, over = None, None
    while True:
        try:
            code = proc.wait(timeout=POLL_S)
            break
        except subprocess.TimeoutExpired:
            pass
        table = _proc_table()
        live = sum(table[pid][1] for pid in _descendants(table, me))
        used = (_children_cpu() - cpu0) + live
        if cpu_budget_s is not None and used > cpu_budget_s:
            over = f"compute budget exceeded ({used:.0f} > {cpu_budget_s:.0f} CPU s)"
            break
        if time.time() - t0 > wall_limit:
            over = f"wall-clock safety stop after {time.time() - t0:.0f} s"
            break
    _kill_and_reap_tree(me)
    if proc.returncode is None:
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        code = proc.returncode
    cpu_used = _children_cpu() - cpu0
    _log(f"predictor{tag} exit={code} after {time.time() - t0:.1f}s wall, {cpu_used:.1f} CPU s"
         + (f" (budget {cpu_budget_s:.0f})" if cpu_budget_s is not None else " (budget not enforced)"))
    predictions, reason = None, None
    if over is not None:
        reason = over
    elif cpu_budget_s is not None and cpu_used > cpu_budget_s:
        reason = f"compute budget exceeded ({cpu_used:.0f} > {cpu_budget_s:.0f} CPU s)"
    elif code != 0:
        reason = f"predictor exit status {code}"
    elif not os.path.exists(pred_path):
        reason = "predictor wrote no predictions file"
    else:
        try:
            with open(pred_path, "r", encoding="utf-8") as handle:
                predictions = json.load(handle)
        except Exception as exc:
            reason = f"unreadable predictions: {exc}"
    if keep_dir and os.path.exists(pred_path):
        os.makedirs(keep_dir, exist_ok=True)
        shutil.copyfile(pred_path, os.path.join(keep_dir, f"predictions{tag}.json"))
    shutil.rmtree(workdir, ignore_errors=True)
    return predictions, reason, cpu_used


def _write(path: str, scores: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(scores, handle, indent=2)
    os.replace(tmp, path)


def collect_predictions(hidden: dict, predict_cmd, enforce_budget: bool = True, keep_dir: str | None = None):
    """One predictor call per experiment (only that experiment's instances).

    Returns (merged predictions, failure reason or None, cpu record).  Only the
    entries of the experiment a call was given are kept from that call."""
    merged: dict = {}
    cpu: dict = {}
    for name in EXPERIMENTS:
        budget = cpu_budget(hidden, name)
        preds, reason, used = run_predictor(public_view(hidden, [name]), predict_cmd,
                                            budget if enforce_budget else None, keep_dir, tag=f"_{name}")
        cpu[name] = {"cpu_s": round(used, 2), "budget_s": budget, "within_budget": used <= budget}
        methods = preds.get("methods") if isinstance(preds, dict) else None
        if reason is None and not isinstance(methods, dict):
            reason = "predictions lack a 'methods' mapping"
        if isinstance(methods, dict):
            for method, per_exp in methods.items():
                slot = merged.setdefault(method, {})
                if isinstance(per_exp, dict) and name in per_exp:
                    slot[name] = per_exp[name]
        if reason is not None:
            return {"methods": merged}, f"{name}: {reason}", cpu
    return {"methods": merged}, None, cpu


def evaluate(output_path: str = DEFAULT_OUTPUT, predict_cmd=None, keep_predictions: str | None = None,
             predictions_file: str | None = None, enforce_budget: bool = True) -> dict:
    prior_names = fallback_method_names()
    if os.path.exists(output_path):
        os.remove(output_path)
    _write(output_path, failed_scores(prior_names, "evaluation did not complete"))
    hidden = load_hidden_set()
    cpu = None
    if predictions_file is not None:
        with open(predictions_file, "r", encoding="utf-8") as handle:
            predictions, reason = json.load(handle), None
    else:
        keep_dir = os.path.dirname(os.path.abspath(keep_predictions)) if keep_predictions else None
        predictions, reason, cpu = collect_predictions(hidden, predict_cmd or PREDICT_CMD, enforce_budget, keep_dir)
        if keep_predictions and predictions is not None:
            os.makedirs(os.path.dirname(os.path.abspath(keep_predictions)), exist_ok=True)
            with open(keep_predictions, "w", encoding="utf-8") as handle:
                json.dump(predictions, handle)
    if reason is not None:
        names = set(prior_names)
        if isinstance(predictions, dict) and isinstance(predictions.get("methods"), dict):
            names.update(str(m) for m in predictions["methods"])
        scores = failed_scores(names, reason)
    else:
        scores = score_predictions(hidden, predictions)
    if cpu is not None:
        scores["_evaluation"]["cpu"] = cpu
        scores["_evaluation"]["budget_enforced"] = bool(enforce_budget)
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
