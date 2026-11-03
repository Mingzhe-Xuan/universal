"""Validation-only best selection, with replay-verified continuation metadata."""

import copy
import math


class ValidationTracker:
    def __init__(self, manifest_sha256, *, patience=None, min_delta=0., state=None):
        if patience is not None and (not isinstance(patience, int) or isinstance(patience, bool) or patience < 1):
            raise ValueError("evaluation.patience must be a positive integer or null")
        if (isinstance(min_delta, bool) or not isinstance(min_delta, (int, float)) or
                not math.isfinite(min_delta) or min_delta < 0):
            raise ValueError("evaluation.min_delta must be finite and nonnegative")
        self.state = {"version": 1, "manifest_sha256": manifest_sha256,
                      "patience": patience, "min_delta": min_delta, "history": [],
                      "best_epoch": None, "best_loss": None, "patience_reference": None,
                      "bad_epochs": 0}
        if state is not None:
            if any(state.get(key) != self.state[key] for key in
                   ("version", "manifest_sha256", "patience", "min_delta")):
                raise ValueError("Evaluation split/protocol differs from checkpoint")
            for entry in state.get("history", []):
                self.update(entry["epoch"], entry["loss"])
            if self.state != state:
                raise ValueError("Invalid validation selection continuation state")

    def update(self, epoch, loss):
        if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch != len(self.state["history"]) + 1:
            raise ValueError("Validation epochs must be consecutive from one")
        if (isinstance(loss, bool) or not isinstance(loss, (int, float)) or
                not math.isfinite(loss) or loss < 0):
            raise FloatingPointError("Validation loss must be finite and nonnegative")
        state = self.state
        improved = state["best_loss"] is None or loss < state["best_loss"]
        if improved:
            state.update(best_epoch=epoch, best_loss=loss)
        # Always save the actual minimum; min_delta controls stopping patience only.
        if state["patience_reference"] is None or loss < state["patience_reference"] - state["min_delta"]:
            state.update(patience_reference=loss, bad_epochs=0)
        else:
            state["bad_epochs"] += 1
        state["history"].append({"epoch": epoch, "loss": loss})
        return improved

    @property
    def should_stop(self):
        return self.state["patience"] is not None and self.state["bad_epochs"] >= self.state["patience"]

    def snapshot(self):
        return copy.deepcopy(self.state)
