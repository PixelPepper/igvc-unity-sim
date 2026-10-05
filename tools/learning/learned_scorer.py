"""Numpy-only inference for the route-candidate scorer exported by train_scorer.py.

The JSON model holds ONLY learned tree weights over observed-only candidate
features (no course, world or teacher data). Lower predicted score = lower
predicted teacher regret (metres) = better. No scikit-learn at run time.

Route models rank route candidates (sensor_route_policy ``learned_scorer``);
models with ``"decision": "corridor"`` rank accepted lane-corridor proposals
(lane_corridor_policy ``corridor_scorer``). Usage::

    scorer = load_scorer('artifacts/learning/models/route_scorer.json')
    scores = scorer.score([row_a, row_b])   # rows: {feature_name: value}
"""
import json
import math
from pathlib import Path

import numpy as np

SCHEMA = 'igvc-route-scorer/1'
MAX_MODEL_BYTES = 8 * 1024 * 1024


class LearnedScorer:
    def __init__(self, model):
        if not isinstance(model, dict) or model.get('schema') != SCHEMA:
            raise ValueError('Expected a %s model' % SCHEMA)
        self.features = [str(name) for name in model['features']]
        # Which decision the model ranks: 'route' (default, older files) or 'corridor'.
        self.decision = str(model.get('decision', 'route'))
        self.fill = float(model['fill_value'])
        self.base = float(model['base'])
        self.rate = float(model['learning_rate'])
        if not self.features or not all(map(math.isfinite, (self.fill, self.base, self.rate))):
            raise ValueError('Invalid model header')
        self.trees = []
        for tree in model['trees']:
            arrays = tuple(np.asarray(tree[key], dtype=dtype) for key, dtype in (
                ('feature', np.int64), ('threshold', np.float64), ('left', np.int64),
                ('right', np.int64), ('value', np.float64)))
            feature, threshold, left, right, value = arrays
            size = len(value)
            if not size or any(len(a) != size for a in arrays):
                raise ValueError('Inconsistent tree arrays')
            internal = left >= 0
            if (np.any(feature[internal] < 0) or np.any(feature[internal] >= len(self.features))
                    or np.any(left[internal] >= size) or np.any(right[internal] < 0)
                    or np.any(right[internal] >= size)
                    or np.any(left[internal] <= np.flatnonzero(internal))
                    or np.any(right[internal] <= np.flatnonzero(internal))
                    or not np.all(np.isfinite(value)) or not np.all(np.isfinite(threshold[internal]))):
                raise ValueError('Invalid tree structure')
            self.trees.append(arrays)

    def matrix(self, rows):
        X = np.full((len(rows), len(self.features)), self.fill, dtype=np.float64)
        for i, row in enumerate(rows):
            for j, name in enumerate(self.features):
                value = row.get(name) if isinstance(row, dict) else None
                if type(value) in (int, float) and math.isfinite(value):
                    X[i, j] = value
        return X

    def predict_matrix(self, X):
        # scikit-learn trees compare float32-rounded features; match it so exports stay exact.
        X = np.asarray(X, dtype=np.float32).astype(np.float64)
        out = np.full(len(X), self.base)
        rows = np.arange(len(X))
        for feature, threshold, left, right, value in self.trees:
            node = np.zeros(len(X), dtype=np.int64)
            # Children always have larger indices, so depth is bounded by size.
            for _ in range(len(value)):
                active = left[node] >= 0
                if not active.any():
                    break
                f = feature[node[active]]
                go_left = X[rows[active], f] <= threshold[node[active]]
                node[active] = np.where(go_left, left[node[active]], right[node[active]])
            out += self.rate * value[node]
        return out

    def score(self, rows):
        """Predicted teacher regret per candidate row (lower is better)."""
        if not rows:
            return []
        return [float(v) for v in self.predict_matrix(self.matrix(rows))]

    __call__ = score


def load_scorer(path):
    path = Path(path)
    if path.stat().st_size > MAX_MODEL_BYTES:
        raise ValueError('Model file too large')
    return LearnedScorer(json.loads(path.read_text(encoding='utf-8')))


def score(candidates_features, model):
    """Functional form: ``model`` is a LearnedScorer, a dict, or a JSON path."""
    if not isinstance(model, LearnedScorer):
        model = LearnedScorer(model) if isinstance(model, dict) else load_scorer(model)
    return model.score(candidates_features)
