"""Shared measurement schema and runtime validation."""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Literal, TypedDict


Origin = Literal["simulated", "manual", "hardware", "unknown"]
Instrument = Literal["multimeter", "phase_seq_meter", "loop_tester"]
Quality = Literal["ok", "out_of_range", "invalid", "stale", "unknown"]
Continuity = Literal["closed", "open"]

VALID_ORIGINS = {"simulated", "manual", "hardware", "unknown"}
VALID_INSTRUMENTS = {"multimeter", "phase_seq_meter", "loop_tester"}
VALID_QUALITIES = {"ok", "out_of_range", "invalid", "stale", "unknown"}
VALID_CONTINUITIES = {"closed", "open"}
VALID_PHASE_SEQUENCES = {"ABC", "BCA", "CAB", "ACB", "BAC", "CBA", "FAULT"}
COMPLETED_QUALITIES = {"ok", "out_of_range"}

_OLD_RECORD_FIELDS = {
    "status",
    "expected_status",
    "voltage",
    "phase_match",
    "source",
    "channel_id",
}
_LOOP_CELLS = {"AA", "BB", "CC", "AB", "AC", "BC"}
_LINE_PAIRS = {"AB", "BC", "CA"}
_PT_NAMES = {"PT1", "PT2", "PT3"}
_PHASE_SEQUENCE_PTS = {"PT1", "PT3"}
_PT_DIFF_SCOPES = {"gen1", "gen2"}
_PT_DIFF_CELLS = {f"{g}{b}" for g in "ABC" for b in "ABC"}


class MeasurementRecord(TypedDict, total=False):
    measurement_id: str
    value: float | str | bool | None
    unit: str | None
    origin: Origin
    instrument: Instrument | None
    instrument_id: str | None
    node_ids: list[str]
    terminal_ids: list[str]
    channel_ids: list[str]
    timestamp: float | None
    raw: str | dict | None
    raw_ref: str | None
    quality: Quality
    reading: str
    passed: bool | None
    continuity: Continuity | None
    voltage_sec: float | None
    voltage_pri: float | None
    pt_ratio: float | None
    sequence: str | None


class MeasurementSpec(TypedDict, total=False):
    measurement_id: str
    domain: str
    scope: str
    cell: str | None
    expected_continuity: Continuity | None
    expected_voltage_sec: float | None
    expected_voltage_pri: float | None
    expected_sequence: str | None
    node_ids: list[str]
    terminal_ids: list[str]


class Terminal(TypedDict):
    terminal_id: str
    label: str
    phase: str | None
    group: str


def validate_origin(origin: str) -> None:
    if origin not in VALID_ORIGINS:
        raise ValueError(f"Invalid measurement origin: {origin!r}")


def parse_measurement_id(mid: str) -> tuple[str, str, str | None]:
    parts = str(mid or "").split(".")
    if len(parts) == 2:
        domain, scope = parts
        cell = None
    elif len(parts) == 3:
        domain, scope, cell = parts
    else:
        raise ValueError(f"Invalid measurement_id format: {mid!r}")

    if domain == "loop":
        if scope != "global" or cell not in _LOOP_CELLS:
            raise ValueError(f"Invalid loop measurement_id: {mid!r}")
    elif domain == "pt_voltage":
        if scope not in _PT_NAMES or cell not in _LINE_PAIRS:
            raise ValueError(f"Invalid PT voltage measurement_id: {mid!r}")
    elif domain == "phase_sequence":
        if scope not in _PHASE_SEQUENCE_PTS or cell is not None:
            raise ValueError(f"Invalid phase sequence measurement_id: {mid!r}")
    elif domain == "pt_diff":
        if scope not in _PT_DIFF_SCOPES or cell not in _PT_DIFF_CELLS:
            raise ValueError(f"Invalid PT diff measurement_id: {mid!r}")
    else:
        raise ValueError(f"Unsupported measurement domain: {domain!r}")
    return domain, scope, cell


def validate_record(record: MeasurementRecord | dict) -> None:
    old_fields = sorted(_OLD_RECORD_FIELDS.intersection(record))
    if old_fields:
        raise ValueError(f"Legacy measurement fields are not allowed: {', '.join(old_fields)}")

    mid = record.get("measurement_id")
    if not isinstance(mid, str) or not mid:
        raise ValueError("measurement_id is required")
    parse_measurement_id(mid)

    origin = record.get("origin")
    if not isinstance(origin, str):
        raise ValueError("origin is required")
    validate_origin(origin)

    quality = record.get("quality")
    if quality not in VALID_QUALITIES:
        raise ValueError(f"Invalid measurement quality: {quality!r}")

    instrument = record.get("instrument")
    if instrument is not None and instrument not in VALID_INSTRUMENTS:
        raise ValueError(f"Invalid measurement instrument: {instrument!r}")

    continuity = record.get("continuity")
    if continuity is not None and continuity not in VALID_CONTINUITIES:
        raise ValueError(f"Invalid continuity: {continuity!r}")

    if "terminal_ids" in record and not isinstance(record["terminal_ids"], list):
        raise ValueError("terminal_ids must be a list")
    if "node_ids" in record and not isinstance(record["node_ids"], list):
        raise ValueError("node_ids must be a list")
    if "channel_ids" in record and not isinstance(record["channel_ids"], list):
        raise ValueError("channel_ids must be a list")


def is_completed_quality(quality: str | None) -> bool:
    return quality in COMPLETED_QUALITIES


def is_record_complete(record: MeasurementRecord | dict | None) -> bool:
    if not record:
        return False
    return is_completed_quality(record.get("quality"))


def store_raw(record: MeasurementRecord | dict, raw_obj: str | dict | None) -> None:
    if raw_obj is None:
        record["raw"] = None
        return

    payload = json.dumps(raw_obj, ensure_ascii=False, sort_keys=True)
    if len(payload.encode("utf-8")) <= 2048:
        record["raw"] = raw_obj
        record["raw_ref"] = None
        return

    ts = record.get("timestamp") or time.time()
    record["timestamp"] = ts
    mid = record.get("measurement_id")
    if not mid:
        raise ValueError("measurement_id is required before storing raw payloads")
    day = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
    safe_ts = f"{ts:.6f}".replace(".", "_")
    path = Path("raws") / day / f"{mid}-{safe_ts}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    record["raw"] = None
    record["raw_ref"] = str(path)
