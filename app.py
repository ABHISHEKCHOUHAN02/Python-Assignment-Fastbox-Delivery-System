"""
FastBox Mystery Delivery System
"""

import json
import math
import random
import csv
import os
import sys

DATA_FILE = "data.json"
REPORT_FILE = "report.json"
TOP_PERFORMER_CSV = "top_performer.csv"



# Step 1: Load and normalize the input data

def _normalize_id_position_map(raw):
    """
    Accepts either:
      - a dict:  {"W1": [x, y], ...}                       (Format B)
      - a list:  [{"id": "W1", "location": [x, y]}, ...]    (Format A)
    Returns a plain dict: {"W1": [x, y], ...} either way.
    """
    if isinstance(raw, dict):
        return {k: list(v) for k, v in raw.items()}
    if isinstance(raw, list):
        return {item["id"]: list(item["location"]) for item in raw}
    raise ValueError(f"Unrecognized warehouses/agents structure: {type(raw)}")


def _normalize_packages(raw_packages):
    """
    Normalizes each package so it always has "id", "warehouse" (the
    warehouse id), and "destination", regardless of whether the source
    JSON used the key "warehouse" (Format B) or "warehouse_id" (Format A).
    """
    normalized = []
    for pkg in raw_packages:
        warehouse_id = pkg.get("warehouse", pkg.get("warehouse_id"))
        if warehouse_id is None:
            raise ValueError(f"Package {pkg.get('id')} has no warehouse/warehouse_id field.")
        normalized.append({
            "id": pkg["id"],
            "warehouse": warehouse_id,
            "destination": list(pkg["destination"])
        })
    return normalized


def load_data(path=DATA_FILE):
    # Read, parse, and normalize the JSON input file (handles both schemas)
    if not os.path.exists(path):
        sample_data = {
            "warehouses": {"W1": [0, 0], "W2": [50, 75], "W3": [100, 25]},
            "agents": {"A1": [5, 5], "A2": [60, 60], "A3": [95, 30]},
            "packages": [
                {"id": "P1", "warehouse": "W1", "destination": [30, 40]},
                {"id": "P2", "warehouse": "W2", "destination": [70, 90]},
                {"id": "P3", "warehouse": "W3", "destination": [105, 20]},
                {"id": "P4", "warehouse": "W1", "destination": [10, 10]},
                {"id": "P5", "warehouse": "W2", "destination": [40, 80]}
            ]
        }
        with open(path, "w") as f:
            json.dump(sample_data, f, indent=2)
        print(f"No {path} found — created a sample one to run against.\n")

    with open(path) as f:
        raw = json.load(f)

    return {
        "warehouses": _normalize_id_position_map(raw["warehouses"]),
        "agents": _normalize_id_position_map(raw["agents"]),
        "packages": _normalize_packages(raw["packages"])
    }


# Step 2: Distance calculation

def distance(p1, p2):
    """Straight-line (Euclidean) distance between two [x, y] points."""
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)



# Step 3 & 4: Assign packages to nearest agent, then simulate delivery

def assign_and_simulate(data, new_agent=None, new_agent_after=None, delay_chance=0.3, verbose=True):
    """
    Assign each package to its nearest agent (by agent's current position ->
    warehouse distance) and simulate the delivery.
    """
    warehouses = data["warehouses"]
    packages = data["packages"]

    agents = {
        aid: {"pos": list(pos), "delivered": 0, "distance": 0.0}
        for aid, pos in data["agents"].items()
    }

    if not agents:
        raise ValueError("No agents available to assign packages to.")

    delivery_log = []

    for i, pkg in enumerate(packages):
        if new_agent and new_agent_after is not None and i == new_agent_after:
            aid, pos = new_agent
            agents[aid] = {"pos": list(pos), "delivered": 0, "distance": 0.0}
            if verbose:
                print(f"[Mid-day event] Agent {aid} has joined at position {pos}.")

        warehouse_id = pkg["warehouse"]
        if warehouse_id not in warehouses:
            # Edge case: package references a warehouse not in the data.
            # Skip it rather than crashing, and note it in the log.
            delivery_log.append({
                "package": pkg["id"], "agent": None, "warehouse": warehouse_id,
                "error": "unknown warehouse id, skipped"
            })
            if verbose:
                print(f"[Warning] {pkg['id']} references unknown warehouse '{warehouse_id}' — skipped.")
            continue

        warehouse_pos = warehouses[warehouse_id]
        agent_id = min(agents, key=lambda a: distance(agents[a]["pos"], warehouse_pos))
        agent = agents[agent_id]

        leg_to_warehouse = distance(agent["pos"], warehouse_pos)
        leg_to_destination = distance(warehouse_pos, pkg["destination"])
        trip_distance = leg_to_warehouse + leg_to_destination

        delay_minutes = random.randint(5, 30) if random.random() < delay_chance else 0

        agent["distance"] += trip_distance
        agent["delivered"] += 1
        agent["pos"] = list(pkg["destination"])

        delivery_log.append({
            "package": pkg["id"], "agent": agent_id, "warehouse": warehouse_id,
            "warehouse_pos": warehouse_pos, "destination": pkg["destination"],
            "delay_minutes": delay_minutes
        })

        if verbose:
            delay_note = f" (delayed {delay_minutes} min)" if delay_minutes else ""
            print(f"{pkg['id']} -> {agent_id} | +{trip_distance:.2f} dist{delay_note}")

    return agents, delivery_log



# Step 5: Build the report

def build_report(agents):
    report = {}
    for aid, info in agents.items():
        delivered = info["delivered"]
        total_dist = info["distance"]
        efficiency = (total_dist / delivered) if delivered else 0.0
        report[aid] = {
            "packages_delivered": delivered,
            "total_distance": round(total_dist, 2),
            "efficiency": round(efficiency, 2)
        }

    active_agents = [a for a in agents if report[a]["packages_delivered"] > 0]
    report["best_agent"] = min(active_agents, key=lambda a: report[a]["efficiency"]) if active_agents else None
    return report



# Step 6: Save the report

def save_report(report, path=REPORT_FILE):
    with open(path, "w") as f:
        json.dump(report, f, indent=2)



# Bonus: ASCII visualization of the map

def ascii_visualize(data, width=40, height=15):
    all_points = list(data["warehouses"].values()) + list(data["agents"].values())
    all_points += [p["destination"] for p in data["packages"]]
    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    def scale(x, y):
        col = int((x - min_x) / (max_x - min_x + 1e-9) * (width - 1))
        row = int((y - min_y) / (max_y - min_y + 1e-9) * (height - 1))
        return row, col

    grid = [["." for _ in range(width)] for _ in range(height)]
    for pos in data["warehouses"].values():
        r, c = scale(*pos)
        grid[r][c] = "W"
    for pos in data["agents"].values():
        r, c = scale(*pos)
        grid[r][c] = "A"
    for pkg in data["packages"]:
        r, c = scale(*pkg["destination"])
        if grid[r][c] == ".":
            grid[r][c] = "D"

    print("\nASCII Map (W=warehouse, A=agent start, D=delivery destination)")
    for row in grid:
        print("".join(row))
    print()


# Bonus: Export top performer to CSV

def export_top_performer(report, path=TOP_PERFORMER_CSV):
    best = report.get("best_agent")
    if not best:
        return
    stats = report[best]
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["agent_id", "packages_delivered", "total_distance", "efficiency"])
        writer.writerow([best, stats["packages_delivered"], stats["total_distance"], stats["efficiency"]])


# Main

def run_single(path, show_ascii=False, verbose=True):
    """Run the full pipeline for one input file and return the report."""
    data = load_data(path)
    agents_state, log = assign_and_simulate(data, verbose=verbose)
    report = build_report(agents_state)

    total_delivered = sum(v["packages_delivered"] for k, v in report.items() if k != "best_agent")
    total_packages = len(data["packages"])
    if total_delivered != total_packages:
        print(f"[Warning] {path}: {total_delivered}/{total_packages} packages delivered "
              f"(some may reference unknown warehouses).")

    if show_ascii:
        ascii_visualize(data)

    return report, total_delivered, total_packages


# ---------------------------------------------------------------------------
# Batch mode: run every test file and write ONE consolidated report + CSV
# ---------------------------------------------------------------------------
def run_all(folder, combined_report_path="all_reports.json", combined_csv_path="all_top_performers.csv"):
    """
    Runs the pipeline against every .json file in `test_cases folder` and writes:
      - one combined_report_path (a single valid JSON file: a dict mapping
        each input filename -> its full report), and
      - one combined_csv_path (a single CSV with one row per test file,
        showing that file's best agent and its stats).

    
    """
    # Exclude this script's own output files, in case they were previously
    # written into the same folder (report.json, data.json, all_reports.json).
    excluded = {"report.json", "data.json", "all_reports.json"}
    input_files = sorted(
        f for f in os.listdir(folder)
        if f.endswith(".json") and f not in excluded and not f.startswith("all_")
    )
    if not input_files:
        print(f"No .json files found in {folder}")
        return

    all_reports = {}
    csv_rows = []

    for fname in input_files:
        full_path = os.path.join(folder, fname)
        print(f"\n=== {fname} ===")
        try:
            report, delivered, total = run_single(full_path, show_ascii=False, verbose=False)
        except Exception as e:
            print(f"[Error] {fname} failed: {e}")
            all_reports[fname] = {"error": str(e)}
            continue

        all_reports[fname] = report
        print(f"{delivered}/{total} packages delivered. Best agent: {report.get('best_agent')}")

        best = report.get("best_agent")
        if best:
            stats = report[best]
            csv_rows.append([
                fname, best,
                stats["packages_delivered"], stats["total_distance"], stats["efficiency"]
            ])
        else:
            csv_rows.append([fname, None, 0, 0, 0])

    # Write the combined JSON report in a single pass (valid JSON, one object).
    with open(combined_report_path, "w") as f:
        json.dump(all_reports, f, indent=2)
    print(f"\nCombined report for all {len(input_files)} files written to {combined_report_path}")

    # Write the combined CSV (header once, then one row per test file).
    with open(combined_csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["test_file", "best_agent", "packages_delivered", "total_distance", "efficiency"])
        writer.writerows(csv_rows)
    print(f"Combined top-performer CSV for all {len(input_files)} files written to {combined_csv_path}")


if __name__ == "__main__":
                                             
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        folder = sys.argv[2] if len(sys.argv) > 2 else "test_cases"
        run_all(folder)
    else:
        input_path = sys.argv[1] if len(sys.argv) > 1 else DATA_FILE

        print(f"Simulating deliveries for {input_path}...\n")
        report, delivered, total = run_single(input_path, show_ascii=True, verbose=True)

        print("\nFinal Report:")
        print(json.dumps(report, indent=2))

        save_report(report)
        print(f"\nReport saved to {REPORT_FILE}")

        export_top_performer(report)
        print(f"Top performer exported to {TOP_PERFORMER_CSV}")

        print(f"\nSanity check: {delivered}/{total} packages delivered.")