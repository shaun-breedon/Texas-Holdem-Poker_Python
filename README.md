# Texas Hold'em Poker (Python)

A Python implementation of Texas Hold'em Poker.

> Status: early, active development

---

## Project Notes
- **Started:** 2 April 2025  
- **Author:** Shaun Breedon  

---

## Features

- **Cards & Evaluator**: `Card`, `Deck`, and a 5-card hand evaluator (High Card → Royal Flush).
- **Table Model**: players, seats, pots, blinds, buttons, antes.
- **Engine**: runs full hands (preflop → showdown) with betting orchestration, handling side pots and awarding winners.
- **Strategies**: simple archetypes (TAG, LAG, Nit, Calling Station) + a base interface
- **RNG**: project-wide RNG with seeding for reproducible shuffles.
- **CLI**: run quick simulations from the terminal.

---

## Roadmap
- [ ] Smarter deterministic player strategy logic
- [ ] Hand-history logging and statistics
- [ ] Database (PostgreSQL) for histories
- [ ] LLM-based AI players
- [ ] GUI

---

## Module Structure
src/holdem/
- core/
  - cards.py
  - enums
  - evaluator
- table/
  - table
  - player
  - pots
  - buttons_blinds
  - peek
- engine/
  - game
  - betting
  - showdown
- strategies/
  - base
  - features
  - simple
- utils/
  - rng
  - errors
- io/
  - cli
  - hh_writer

---

## Requirements
- Python **3.11+**
- OS: Linux/macOS/Windows

---

## Installation
Clone the repository:
```bash
git clone https://github.com/shaun-breedon/Texas-Holdem-Poker_Python.git
cd Texas-Holdem-Poker_Python

# (recommended) create and activate a virtualenv
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# install
pip install -e .            # or: pip install -e .[dev] for tests/linters

---

## Usage
Run the main script:

    python -m holdem
```

---

## CLI

    holdem --help
    holdem simulate --hands 100 --players 6 --buyin 10000
    
    # or run as a module
    python -m holdem --help

---

## Changelog
- **2025-04-02** — Project created  
-  **2025-08-25** — Base Game Complete (Hand completes with winning hand player awarded pot)
- **2025-09-18** — Major Code Refactor. Modularised the code.

---

## License
This project is licensed under the MIT License.