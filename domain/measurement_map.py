"""Static terminal and measurement maps for external measurement ingress."""

from __future__ import annotations

from domain.measurement_id import loop_id, phase_sequence_id, pt_diff_id, pt_voltage_id
from domain.measurement_schema import MeasurementSpec, Terminal
from domain.node_map import NODES


LOOP_CELLS = ("AA", "BB", "CC", "AB", "AC", "BC")
LINE_PAIRS = ("AB", "BC", "CA")
PT_DIFF_CELLS = tuple(f"{gen_phase}{bus_phase}" for gen_phase in "ABC" for bus_phase in "ABC")

TERMINAL_MAP: dict[str, Terminal] = {
    node_id: {
        "terminal_id": node_id,
        "label": node_data[4],
        "phase": node_data[3],
        "group": node_data[2],
    }
    for node_id, node_data in NODES.items()
}

MEASUREMENT_SPEC: dict[str, MeasurementSpec] = {}

for cell in LOOP_CELLS:
    terminal_ids = [f"LOOP_G1_{cell[0]}", f"LOOP_G2_{cell[1]}"]
    MEASUREMENT_SPEC[loop_id(cell)] = {
        "measurement_id": loop_id(cell),
        "domain": "loop",
        "scope": "global",
        "cell": cell,
        "expected_continuity": "closed" if cell[0] == cell[1] else "open",
        "node_ids": terminal_ids,
        "terminal_ids": terminal_ids,
    }

for pt_name in ("PT1", "PT2", "PT3"):
    for pair in LINE_PAIRS:
        terminal_ids = [f"{pt_name}_{pair[0]}", f"{pt_name}_{pair[1]}"]
        MEASUREMENT_SPEC[pt_voltage_id(pt_name, pair)] = {
            "measurement_id": pt_voltage_id(pt_name, pair),
            "domain": "pt_voltage",
            "scope": pt_name,
            "cell": pair,
            "expected_voltage_pri": 10500.0,
            "node_ids": terminal_ids,
            "terminal_ids": terminal_ids,
        }

for pt_name in ("PT1", "PT3"):
    terminal_ids = [f"{pt_name}_A", f"{pt_name}_B", f"{pt_name}_C"]
    MEASUREMENT_SPEC[phase_sequence_id(pt_name)] = {
        "measurement_id": phase_sequence_id(pt_name),
        "domain": "phase_sequence",
        "scope": pt_name,
        "cell": None,
        "expected_sequence": "ABC",
        "node_ids": terminal_ids,
        "terminal_ids": terminal_ids,
    }

for gen_id, pt_name in ((1, "PT1"), (2, "PT3")):
    for cell in PT_DIFF_CELLS:
        terminal_ids = [f"{pt_name}_{cell[0]}", f"PT2_{cell[1]}"]
        MEASUREMENT_SPEC[pt_diff_id(gen_id, cell)] = {
            "measurement_id": pt_diff_id(gen_id, cell),
            "domain": "pt_diff",
            "scope": f"gen{gen_id}",
            "cell": cell,
            "node_ids": terminal_ids,
            "terminal_ids": terminal_ids,
        }


def get_terminal(node_id: str) -> Terminal | None:
    return TERMINAL_MAP.get(node_id)


def get_terminal_by_channel(channel_id: str) -> Terminal | None:
    pass
    return None


def get_measurements_by_terminal(terminal_id: str) -> list[str]:
    pass
    return []


def get_measurement_spec(measurement_id: str) -> MeasurementSpec | None:
    return MEASUREMENT_SPEC.get(measurement_id)
