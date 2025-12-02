# src/holdem/utils/rng.py
from __future__ import annotations
from contextlib import contextmanager
from random import Random
from typing import List, Sequence, TypeVar

__all__ = ["RNG", "DEFAULT_RNG"]

T = TypeVar("T")

class RNG:

    def __init__(self, seed: int | None = None):
        self._rand = Random(seed)

    def seed(self, seed: int | None) -> None:
        self._rand.seed(seed)

    def getstate(self):
        return self._rand.getstate()

    def setstate(self, state) -> None:
        self._rand.setstate(state)

    @contextmanager
    def temp_seed(self, seed: int | None):
        """Temporarily set a seed, then restore previous RNG state."""
        prev = self.getstate()
        try:
            self.seed(seed)
            yield
        finally:
            self.setstate(prev)

    def random(self) -> float:
        return self._rand.random()

    def randint(self, a: int, b: int) -> int:
        return self._rand.randint(a, b)

    def choice(self, seq: Sequence[T]) -> T:
        return self._rand.choice(seq)

    def sample(self, population: Sequence[T], k: int) -> list[T]:
        return self._rand.sample(population, k)

    def shuffle(self, x: List[T]) -> None:
        self._rand.shuffle(x)

DEFAULT_RNG = RNG()