# QM9 four-property extension

This independent32-case matrix covers HOMO, LUMO, dipole magnitude and isotropic
polarizability × original CGCNN/ALIGNN/MACE/NequIP × pretrained/scratch, seed123.
The original48-case matrix and prior retries remain untouched. `definitions.py`
inherits the original scalar recipes: float32, complete training partition,
300epoch cap/patience30, learning rate3e-4, reset randomly initialized mean graph
readout, trainable whole backbone. CGCNN/ALIGNN use nonperiodic radius6angstrom;
MACE/NequIP retain their official nonperiodic inputs and original model cutoffs.

`scripts/run_qm9.py prepare` converts all clean author data and freezes the32
configs. Data semantics and source identities are in the
[preparation module](../../data/preparation/qm9/README.md).

`runtime.py` provides three Slurm-only numerical stages:

- `smoke`: eight two-epoch CPU controls per model on an explicitly separate24-row
  fixture. Finite nonzero backbone gradients and standard checkpoint reload are
  required. This is numerical integration evidence, not a full training result.
- `preflight`: complete native CUDA training-graph scan, worst-size and ordinary
  candidates, then each property's original paired100-measured-batch capacity
  protocol. Only typed CUDA OOM may reduce batch, and both initializations are
  rechecked at the common size. Unknown errors/timeouts fail. MACE/NequIP scratch
  normalization uses the full training partition only. Targets remain together
  in source records, so graph statistics/fingerprint can be reused across heads.
- `train`: verifies that only batch and bound scratch statistics changed, then
  uses existing mini-batch training, train-only scaling, complete validation
  selection, early stopping and complete validation-best held-out scoring.

`assessment.py` independently checks every saved test ID/order/target against
the frozen source, recomputes MAE/RMSE, verifies best-checkpoint SHA and publishes
the final passed status. It loads no model and runs no new DFT.

`submission.py:submit_campaign(source)` runs lightweight Slurm management from a
clean immutable checkout. Each job first has a unique intent, original request,
RPC and held receipt; all identities/resources/dependencies validate before
release. Any ambiguous receipt stops submission and requires reconciliation.
There are32 full GPU training jobs,4 GPU capacity jobs,4 CPU control jobs, one
CPU preparation,32 CPU independent assessments and73 afterany terminal recorders.
The146 Slurm jobs represent32 experiments. Training gets a14-day per-job Slurm
limit and the scientific300/patience30 limit; this allocation is not an ETA.

Every raw dataset, result, checkpoint and log remains ignored. Full controls and
metadata results are separate from scientific completion. A CPU pass does not
certify GPU capacity, and a queued training job is not a trained result.
