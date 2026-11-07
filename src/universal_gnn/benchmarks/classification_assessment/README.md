# Validation-only classification thresholds

This separate assessment fulfills the campaign's validation-selected decision
threshold protocol. It consumes a complete training report and the original full
CPU inference JSONL, with its SHA256 and byte count. It never loads a GNN, changes
weights, retrains, changes the original argmax metrics or promotes a case to
scientific acceptance.

`selection.py` stores validation scores in SQLite and selects maximum balanced
accuracy using exact integer objectives. Candidates include each distinct score,
0.5 and an explicit all-negative rule; equal scores always move together. Ties
choose the finite threshold closest to0.5, then the higher threshold; the
all-negative rule is last. Probabilities at the selected threshold predict class1.
Both validation classes are required. The frozen selection is written before
test scoring. Test labels never enter the selection function.

`runtime.py` verifies source/split/best identities and the complete inference
header, ordered IDs, shapes, finite values, completion marker and SHA. Validation
and test probabilities both come from that same complete CPU stream, through the
existing dtype-preserving CPU softmax. This avoids mixing validation CPU scores
with original GPU test scores. The report retains both the same-stream argmax
baseline and the unchanged original heldout metrics, and explicitly identifies
the score source. AUROC is independent of the selected decision threshold.

Run the public command from a clean pinned checkout in a CPU Slurm allocation using a provider environment
with Torch installed:

```bash
PYTHONPATH=src "$UGNN_PYTHON" scripts/evaluate_classification_threshold.py \
  --report "$TRAINING_REPORT" --predictions "$FULL_CPU_PREDICTIONS" \
  --prediction-sha256 "$PREDICTION_SHA256" --prediction-bytes "$PREDICTION_BYTES" \
  --output runs/NEW-classification-threshold-assessment
```

Inputs and earlier outputs remain unchanged. Existing destinations are refused.
Outputs are `selection.json`, disk score spools and `report.json`, including source,
prediction, checkpoint and selection hashes, population counts and all test
metrics. These are supplemental decision metrics, separate from the original
training selection and official/native-head results. They do not claim any
pretraining benefit or cross-seed significance.

Executed CPU controls: source `4d01907`, Slurm1967/1968 both completed0:0;
50 pure checks, six actual float32/float64 softmax and public-CLI fixtures,207
source Gitblobs and78 archived artifacts verified. Torch2.7.1+cu128 was used only
for small CPU score calculations; model loading and module forward were forbidden.
These fixtures do not represent the full7590-validation/7580-test classification
experiments, which remain subject to their original scientific acceptance.
