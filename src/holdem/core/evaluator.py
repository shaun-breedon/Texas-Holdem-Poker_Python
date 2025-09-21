# src/holdem/core/evaluator.py

from __future__ import annotations
from typing import Sequence
from dataclasses import dataclass, field

from .enums import Suit, Rank, HandRank
from .cards import Card

__all__ = ["evaluate_player_hand", "HandEval"]

@dataclass(frozen=True, slots=True, order=True)
class HandEval:
    hand_rank: HandRank
    tie_key: tuple[int, ...]
    hand_cards: tuple[Card, ...] = field(compare=False)

def _find_flush(_cards: Sequence[Card], return_all_cards: bool = False) -> list[Card] | None:
    for s in Suit:
        suited_cards = [c for c in _cards if c.suit == s]
        if len(suited_cards) >= 5:
            flush_cards = suited_cards if return_all_cards else suited_cards[:5]
            return flush_cards
    return None

def _find_straight(_cards: Sequence[Card]) -> list[Card] | None:
    ranks: set[int] = {c.rank.value for c in _cards}
    if Rank.ACE.value in ranks:
        ranks.add(1)  # Handles wheel straight

    s_vals = sorted(ranks, reverse=True)
    by_rank: dict[int, Card] = {}
    for c in _cards:
        by_rank.setdefault(c.rank.value, c)

    for v in s_vals:
        straight_seq = [v - offset for offset in range(5)]
        if all(r in ranks for r in straight_seq):  # if straight exists
            straight_cards_w_wheel_handling: list[Card] = [by_rank[14 if x == 1 else x] for x in straight_seq]
            return straight_cards_w_wheel_handling
    return None

def _find_straight_flush(_cards: Sequence[Card]) -> list[Card] | None:
    if flush_cards := _find_flush(_cards, return_all_cards=True):
        if straight_flush_cards := _find_straight(flush_cards):
            return straight_flush_cards
    return None

def _tally_rank_groupings(_cards: Sequence[Card]) -> dict[int, list[Rank]]:
    rank_tally: dict[Rank, int] = {}
    for c in _cards:
        rank_tally[c.rank] = rank_tally.get(c.rank, 0) + 1
    tally_groups: dict[int, list[Rank]] = {4: [], 3: [], 2: [], 1: []}
    for r, n in rank_tally.items():
        tally_groups[n].append(r)
    for n in tally_groups:
        tally_groups[n].sort(reverse=True) # highest ranks first within each group size
    return tally_groups

def _find_quads(_cards: Sequence[Card], _tally_groups: dict[int, list[Rank]]) -> list[Card] | None:
    if not _tally_groups.get(4):  # if not quads
        return None
    quad_rank = _tally_groups[4][0]
    kicker = next(c for c in _cards if c.rank != quad_rank)
    quad_cards = [c for c in _cards if c.rank == quad_rank] + [kicker]
    return quad_cards

def _find_full_house(_cards: Sequence[Card], _tally_groups: dict[int, list[Rank]]) -> list[Card] | None:
    if not _tally_groups.get(3):  # if not trips
        return None

    pair_candidates: list[Rank] = []
    if len(_tally_groups.get(3)) >= 2:
        pair_candidates.append(_tally_groups[3][1])
    if _tally_groups.get(2):
        pair_candidates.append(_tally_groups[2][0])
    if not pair_candidates:
        return None

    trips_rank = _tally_groups[3][0]
    full_of_rank = max(pair_candidates)
    trips = [c for c in _cards if c.rank == trips_rank]
    full_of = [c for c in _cards if c.rank == full_of_rank][:2]
    full_house_cards = trips + full_of
    return full_house_cards

def _find_trips(_cards: Sequence[Card], _tally_groups: dict[int, list[Rank]]) -> list[Card] | None:
    if not _tally_groups.get(3):  # if not trips
        return None
    trips_rank = _tally_groups[3][0]
    kickers = [c for c in _cards if c.rank != trips_rank][:2]
    trips_cards = [c for c in _cards if c.rank == trips_rank] + kickers
    return trips_cards

def _find_two_pair(_cards: Sequence[Card], _tally_groups: dict[int, list[Rank]]) -> list[Card] | None:
    if len(_tally_groups.get(2)) < 2:  # if not pair
        return None
    first_pair_rank, second_pair_rank = _tally_groups[2][0], _tally_groups[2][1]
    first_pair, second_pair = ([c for c in _cards if c.rank == first_pair_rank],
                               [c for c in _cards if c.rank == second_pair_rank])
    kicker = next(c for c in _cards if c.rank not in (first_pair_rank, second_pair_rank))
    two_pair_cards = first_pair + second_pair + [kicker]
    return two_pair_cards

def _find_pair(_cards: Sequence[Card], _tally_groups: dict[int, list[Rank]]) -> list[Card] | None:
    if not _tally_groups.get(2):  # if not pair
        return None
    pair_rank = _tally_groups[2][0]
    kickers = [c for c in _cards if c.rank != pair_rank][:3]
    pair_cards = [c for c in _cards if c.rank == pair_rank] + kickers
    return pair_cards

def _determine_hand(_cards: Sequence[Card], _tally_groups: dict[int, list[Rank]]) \
        -> tuple[list[Card], tuple[HandRank, tuple[int, ...]]]:
    """ Since the output of _find_* helpers is passed into _get_ranks, then _get_ranks output is always in the
                correct group rank order for the hand rank. ie a full-house is [T,T,T,P,P]. Therefore, a tuple of the
                rank values of _hand_cards will have correctly placed kickers for determining a winning hand. """

    def _get_ranks(_hand_cards: list[Card]) -> tuple[int, ...]:
        vals: list[int] = [c.rank.value for c in _hand_cards]
        if vals == [5, 4, 3, 2, 14]:
            vals[-1] = 1              # Normalize wheel straight: [5,4,3,2,A] -> [5,4,3,2,1]
        return tuple(vals)

    if sf := _find_straight_flush(_cards):
        if sf[0].rank == Rank.ACE:
            return sf, (HandRank.ROYAL_FLUSH, _get_ranks(sf))
        else:
            return sf, (HandRank.STRAIGHT_FLUSH, _get_ranks(sf))
    if q := _find_quads(_cards, _tally_groups):
        return q, (HandRank.QUADS, _get_ranks(q))
    if fh := _find_full_house(_cards, _tally_groups):
        return fh, (HandRank.FULL_HOUSE, _get_ranks(fh))
    if f := _find_flush(_cards):
        return f, (HandRank.FLUSH, _get_ranks(f))
    if s := _find_straight(_cards):
        return s, (HandRank.STRAIGHT, _get_ranks(s))
    if t := _find_trips(_cards, _tally_groups):
        return t, (HandRank.TRIPS, _get_ranks(t))
    if tp := _find_two_pair(_cards, _tally_groups):
        return tp, (HandRank.TWO_PAIR, _get_ranks(tp))
    if p := _find_pair(_cards, _tally_groups):
        return p, (HandRank.PAIR, _get_ranks(p))
    top5 = list(_cards[:5])
    return top5, (HandRank.HIGH_CARD, _get_ranks(top5))

def evaluate_player_hand(pl_hole_cards: list[Card], board: list[Card] | None = None) -> HandEval:
    """Return best 5-card hand (or 2-card if pre-flop), and HandRanking, using the two hole cards and the board"""
    cards = sorted(pl_hole_cards + (board or []), reverse=True) # sorts cards high->low. Logic relies on this
    hand, rank_and_key = _determine_hand(cards, _tally_rank_groupings(cards))
    return HandEval(rank_and_key[0], rank_and_key[1], tuple(hand))