# src/holdem/core/enums.py

from __future__ import annotations
from enum import IntEnum, StrEnum, unique, auto # Suit, Rank, HandRank, GameState
from typing import ClassVar # Suit

__all__ = ["Suit", "Rank", "HandRank", "GameState", "Action", "Position"]

@unique
class Suit(StrEnum):
    SPADES = 's'
    HEARTS = 'h'
    DIAMONDS = 'd'
    CLUBS = 'c'

    __SYMBOLS: ClassVar[dict[str, str]] = {
        's': '♠',
        'h': '♥',
        'd': '♦',
        'c': '♣'
    }

    @property
    def symbol(self) -> str:
        return type(self).__SYMBOLS[self]

    @property
    def colour(self) -> str:
        return "black" if self in {Suit.SPADES, Suit.CLUBS} else "red"

@unique
class Rank(IntEnum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

    @property
    def face(self) -> str:
        """ Gets T, J, Q, K, A for those respective cards, else the integer as a string. """
        return self.name[0] if self.value >= 10 else str(self.value)

    def __str__(self):
        return self.face

@unique
class HandRank(IntEnum):
    ROYAL_FLUSH = 10
    STRAIGHT_FLUSH = 9
    QUADS = 8
    FULL_HOUSE = 7
    FLUSH = 6
    STRAIGHT = 5
    TRIPS = 4
    TWO_PAIR = 3
    PAIR = 2
    HIGH_CARD = 1

    def __str__(self):
        return self.name.replace("_", " ")

@unique
class GameState(StrEnum):
    SETUP = auto()
    PRE_FLOP = auto()
    FLOP = auto()
    TURN = auto()
    RIVER = auto()
    SHOWDOWN = auto()
    END_HAND = auto()

    def __str__(self):
        return self.name.replace("_", " ")

@unique
class Action(StrEnum):
    CHECK = auto()
    BET = auto()
    CALL = auto()
    RAISE = auto()
    FOLD = auto()
    ALL_IN = auto()

    def __str__(self):
        return self.name.replace("_", " ")

@unique
class Position(IntEnum):
    def __new__(cls, value: int, label: str):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj._label_ = label
        return obj

    SMALL_BLIND = (0, "SB")
    BIG_BLIND = (1, "BB")
    UNDER_THE_GUN = (2, "UTG")
    UNDER_THE_GUN_1 = (3, "UTG+1")
    UNDER_THE_GUN_2 = (4, "UTG+2")
    LOJACK = (5, "LJ")
    HIJACK = (6, "HJ")
    CUTOFF = (7, "CO")
    BUTTON = (8, "BU")

    @property
    def label(self) -> str:
        return self._label_

    def __str__(self):
        return self._label_
