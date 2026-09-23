# FastBox Delivery Simulation

Simulates a day of deliveries for FastBox: assigns each package to the nearest agent, tracks distance traveled, and reports who delivered what.

## Run it

Single file:

```bash
python3 app.py test_cases/test_case_1.json
```

All test cases at once (this is what I used to check everything works):

```bash
python3 app.py --all test_cases
```

This writes `all_reports.json` (one report per test file) and `all_top_performers.csv` (best agent per test file).

No installs needed, just standard Python 3.

## Assumptions I made

The brief left a few things undefined, so here's what I went with:

- **Agent position updates after each delivery.** "Nearest agent" is checked against wherever the agent currently is, not just their starting point. Felt more like an actual simulation that way.

- **Packages are processed in the order they appear in the JSON.** No priority or timestamp field was given, so this was the simplest fair choice.

- **Efficiency = total_distance / packages_delivered**, lower is better. Matches the numbers in the sample report from the PDF.

- **Best agent = lowest efficiency**, not most packages delivered. "Efficient" reads as output per distance to me, not raw volume.

- **Distance per delivery = agent-to-warehouse + warehouse-to-destination**, since the agent actually travels both legs.

- **Two JSON formats, handled automatically.** `base_case.json` uses lists (`{"id": "W1", "location": [x,y]}`), the `test_case_*.json` files use dicts (`"W1": [x,y]`). The script detects and normalizes either one.

- **An agent with zero deliveries still shows up in the report** (with 0s) but isn't eligible for "best agent". This actually happens in test_case_1, where agent A4 never gets picked.

- **A package pointing to a warehouse that doesn't exist gets skipped** with a warning instead of crashing the whole run.

Verified against `base_case.json` and all 10 `test_case` files. Every package gets delivered in every case.

## Files

- `app.py` - everything: parsing, distance calc, assignment, simulation, report and CSV export
- `test_cases/` - the provided input files
- `all_reports.json` / `all_top_performers.csv` - output from running `--all` against all 11 files
