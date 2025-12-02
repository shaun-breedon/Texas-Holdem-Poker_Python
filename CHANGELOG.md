# CHANGELOG.md

All notable changes to this project will be documented in this file.

The format is based on "Keep a Changelog" and follows [Semantic Versioning](https://semver.org/).

## [0.3.3] - 2025/12/03

### Added
- New features that were added but not released yet.

### Changed
- Moved to `Python 3.14`, to utilise native support for `uuid7`
- Minor `README.md` edits
- Minor edits/bugfixes to `rng`, `cards`, `evaluator`, `table`, `player`, `allocate_pots`

### Fixed
- Changed how highest_bet in `game` is defined during game setup with posting blinds. It now correctly handles cases where the highest bet is lower than the blind.
- Fixed `game` and `betting` to correctly handle edge cases where posting blinds causes players to go all-in before a standard betting round can occur.
- In `betting`, fixed what legal actions are available after evaluating *to_call* by adding a small blind exception.

---

## [0.3.2] - 2025/09/12

### Fixed
- Minor bug-fixes: Type-set error for hole_crds, repr issues for Table and Player

---

## [0.3.1] - 2025/09/19

### Changed
- Refactored `betting.py` by taking out the chips-to-pot logic to create a new module `allocate_pots.py` that sits inside `engine`
- `simple.py` strategies (eg `Tag`) now inherit from `Strategy` class in `base.py`, and can use its class methods.

### Fixed
- Fixed game-breaking winning hand bug where winning hands couldn't be evaluated.
- Other various bug fixes that resulted from the modular overhaul refactor from 0.3.0

---

## [0.3.0] - 2025/09/18
### Added
- Refactored file structure of `holdem` to conform to proper development practices
- First entry into a changelog
- This refactor is versioned as 0.3.0
  - The last version of the old monolithic script code was 0.2.7

### Changed
Major Code Refactor. Refactored the old monolith code (which was a complete game engine) to be a modular codebase, split up into sensible packages and sub-packages. These are all contained in the new `holdem` package (under src). The modules and submodules are:
- `core`
  - `enums.py` ----------------> contains all the enum classes: Suit, Rank, HandRank, GameState, Action, Position
  - `cards.py` ----------------> card and deck of cards
  - `evaluator.py` ----------> 5-card hand evaluator: High Card, Pair, Two-Pair, Trips, Straight, Flush, Full-House, Quads, Straight Flush, Royal Flush
- `table`
  - `table.py` ----------------> table. Contains table states like seating, blinds, buttons
  - `player.py` ---------------> player. Contains properties like name, stack, strategy, current bet, etc.
  - `pots.py` ------------------> pots. Owns the repository of chips into pots.
  - `buttons_blinds.py` ---> advances the table buttons and posts blinds for a new hand
  - `peek.py` ------------------> sneaks a peek to discover the next button positions for a new hand
- `engine`
  - `game.py`  ------------------> hand. Is able to run a full hand: pre-flop, flop, turn, river, showdown.
  - `betting.py` --------------> handles betting orchestration during a poker street, as well as allocating chips to pots and handling side pots at end of a betting round
  - `showdown.py` -------------> determines winning players, awards pots
- `strategies`
  - `base.py` --------------------> Interface layer that defines the inputs and outputs strategies can be, to interact with Player and the engine
  - `features.py` --------------> properties of the hand at decision nodes that players use to inform their decisions
  - `simple.py` -----------------> (very) basic deterministic player archetypes: Tight-Aggressive (TAG), Loose-Aggressive (LAG), Tight-Passive (Nit), Loose-Passive (Calling Station) 
- `utils`
  - `rng.py` ----------------------> module to own random, seeds. For things like shuffling the deck. For reproducibility and testing.
  - `errors.py` ------------------> contains custom error states, to be used throughout the modules. Unfinished
- `io`
  - `cli.py` -----------------------> Command Line Interface, for testing and running simulations.
  - `hh_writer.py` ---------------> Currently empty. Will house the logging code to capture the information history that occurs in a hand and in the game. Will be replacing all the print statements that are currently still in the code.

These modules were, for the most part, all built from the code in the original monolith script (last version was 0.2.7). Changes were made, some small, some significant, when moving from the monolith script to the modules.

In addition, some meta code has been created (`__main__.py`, `__init__.py` for each module, `pyproject.toml`, `.gitignore`, `CHANGELOG.md`, `LICENSE`, `MANIFEST.in` (MIT), `README.md`, `py.typed`, `tests` directory that is unfinished )

### Removed
Major Code Refactor
- Old monolith-style code (everything was in one large .py script) is moved to archive (where it can still be accessed). This code was a complete game engine. The last version of this is 0.2.7

---