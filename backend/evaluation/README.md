# Evaluation

`evaluate.py` is a deterministic smoke evaluator. Extend `CASES` with the required dataset classes:
10 normal, 5 ambiguous, 5 missing-information, 5 tool-failure, 5 adversarial/prompt-injection,
5 policy-conflict and 5 human-approval cases.

For the promotion classifier itself, track macro F1, high-risk recall, precision at review capacity,
PR-AUC, calibration and category stability. Keep an immutable evaluation set separate from synthetic training/test data.
