"""Bounded adaptive gap search, strictly post-validated by the nesting engine.

Heuristic nesting is not monotonic in gap, so this is the largest *verified
candidate* found by the bounded search, not a proof of a global maximum.
Only PackingFailure is recoverable; malformed artwork and validation assertions
must never be silently treated as packing infeasibility.
"""
from __future__ import annotations
import math
import time


def optimize_gap(requested, solve, failure_type, *, seconds=35.0, progress=None,
                 precision_mm=0.02, coarse_divisions=8):
    """Call solve(gap, discovery: bool), return (solution, effective_gap, audit).

    A requested-gap attempt is always made first. Then a descending grid finds
    a feasible lower gap and a bounded binary search improves it. Every solution
    returned by solve has already passed complete object-level geometry checks.
    """
    if not math.isfinite(requested) or requested < 0:
        raise ValueError("Requested gap must be finite and non-negative")
    start = time.monotonic()
    attempted = []
    def check(gap, discovery):
        try:
            answer = solve(gap, discovery)
        except failure_type:
            attempted.append({"gap_mm": round(gap, 5), "feasible": False})
            return None
        attempted.append({"gap_mm": round(gap, 5), "feasible": True})
        return answer

    full = check(requested, False)
    if full is not None:
        return full, requested, {
            "requested_mm": requested, "used_mm": requested, "reduced": False,
            "checked": attempted, "approximate": False, "budget_exceeded": False}
    if requested == 0:
        return None, None, {"requested_mm": requested, "checked": attempted}

    # The first lower check always proceeds even if the initial search exhausted
    # its soft budget. Later probes stop at the time limit.
    budget = seconds if seconds > 0 else 35.
    best = None
    low = None
    upper = requested
    total_checks = coarse_divisions + 10
    for i in range(1, coarse_divisions + 1):
        if i > 1 and time.monotonic() - start >= budget:
            break
        trial_gap = requested * (coarse_divisions - i) / coarse_divisions
        candidate = check(trial_gap, True)
        if progress:
            progress('gap_search', i, total_checks)
        if candidate is not None:
            best, low = candidate, trial_gap
            break
        upper = trial_gap

    if best is None:
        return None, None, {
            "requested_mm": requested, "checked": attempted,
            "budget_exceeded": time.monotonic() - start >= budget}

    iterations = 0
    while (upper - low > precision_mm and iterations < 10
           and time.monotonic() - start < budget):
        midpoint = (low + upper) / 2
        candidate = check(midpoint, True)
        iterations += 1
        if progress:
            progress('gap_search', coarse_divisions + iterations, total_checks)
        if candidate is not None:
            best, low = candidate, midpoint
        else:
            upper = midpoint

    audit = {
        "requested_mm": round(requested, 5),
        "used_mm": round(low, 5),
        "reduced": low < requested - 1e-5,
        "checked": attempted,
        "approximate": True,
        "precision_target_mm": precision_mm,
        "budget_exceeded": time.monotonic() - start >= budget,
        "note": "Largest feasible tested gap; heuristic packing cannot certify the mathematical maximum."
    }
    return best, low, audit
