"""The small ML model that gives planets plausible physical properties.

A polynomial regression is fitted once (deterministically) on synthetic
"observations" that encode real trends: inner planets are small and dense,
outer planets get large and light. Generation then samples around the
model's prediction with a per-planet seeded RNG, so results are both
plausible and reproducible.
"""
from __future__ import annotations

import numpy as np

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import PolynomialFeatures
    _HAS_SKLEARN = True
except ImportError:  # pragma: no cover - fallback keeps the game playable
    _HAS_SKLEARN = False


class PlanetPropertyModel:
    """Predicts (size, density) in 0..1 from normalised orbital distance."""

    def __init__(self, seed: int = 42):
        rng = np.random.default_rng(seed)
        d = np.linspace(0.0, 1.0, 240).reshape(-1, 1)
        size = np.clip(0.15 + 0.75 * d[:, 0] ** 1.4 + rng.normal(0, 0.12, len(d)), 0, 1)
        density = np.clip(0.95 - 0.7 * d[:, 0] ** 0.8 + rng.normal(0, 0.08, len(d)), 0.05, 1)
        targets = np.column_stack([size, density])
        if _HAS_SKLEARN:
            self._poly = PolynomialFeatures(degree=3, include_bias=False)
            self._model = LinearRegression().fit(self._poly.fit_transform(d), targets)
        else:
            self._coef = [np.polyfit(d[:, 0], targets[:, i], 3) for i in range(2)]

    def predict(self, distance01: float) -> tuple[float, float]:
        if _HAS_SKLEARN:
            out = self._model.predict(self._poly.transform([[distance01]]))[0]
            return float(out[0]), float(out[1])
        return tuple(float(np.polyval(c, distance01)) for c in self._coef)

    def sample(self, distance01: float, rng) -> tuple[float, float]:
        size, density = self.predict(distance01)
        size = min(1.0, max(0.05, size + rng.gauss(0, 0.13)))
        density = min(1.0, max(0.05, density + rng.gauss(0, 0.08)))
        return size, density


MODEL = PlanetPropertyModel()
