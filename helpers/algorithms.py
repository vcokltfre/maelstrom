from typing import Tuple
from math import sqrt


class Algorithm:
    """A base levelling algorithm."""

    @classmethod
    def calc(cls, before: int, after: int, inc: int) -> Tuple[int, int, bool]:
        """Returns the level, xp required to level up, whether the current levelup is a levelup."""
        bl, _ = cls.get_level(before, inc)
        al, nx = cls.get_level(after, inc)

        return al, nx, al > bl


class Linear(Algorithm):
    """A fully linear levelling algorithm."""

    @staticmethod
    def get_level(xp: int, inc: int) -> tuple:
        return xp // inc, inc - (xp % inc)


class LinearIncremental(Algorithm):
    """A linearly incremental levelling algorithm."""

    @staticmethod
    def get_level(xp: int, inc: int) -> tuple:
        level = 0
        sub = inc

        while xp > sub:
            xp -= sub
            sub += inc
            level += 1

        return level, abs(sub - xp)


class Quadratic(Algorithm):
    """A ^0.5 based levelling algorithm."""

    @staticmethod
    def get_level(xp: int, thr: int) -> tuple:
        level = int((1 + sqrt(1 + 8* (xp / thr))) / 2)

        x = ((level + 1)**2 * thr - (level + 1)*thr) * 0.5

        return level, int(x - xp)
