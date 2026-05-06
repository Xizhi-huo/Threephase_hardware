"""UI-only measurement record view helpers."""

from __future__ import annotations

from typing import Any


def continuity_to_status(continuity: str | None) -> str:
    if continuity == "closed":
        return "ok"
    if continuity == "open":
        return "danger"
    return "invalid"


def status_text(record) -> str:
    if not record:
        return "未记录"
    quality = record.get("quality")
    if quality == "unknown":
        return "未判定"
    if quality == "invalid":
        return "无效"
    continuity = record.get("continuity")
    if continuity == "closed":
        return "导通"
    if continuity == "open":
        return "断路"
    if record.get("sequence") is not None:
        return "相序正确" if record.get("passed") is True else "相序异常"
    return "已记录"


def reading_text(record) -> str:
    if not record:
        return "未记录"
    if record.get("continuity") is not None:
        reading = record.get("reading")
        return str(reading) if reading else status_text(record)
    if record.get("voltage_pri") is not None:
        return f"{record['voltage_pri'] / 1000:.2f} kV"
    if record.get("voltage_sec") is not None:
        return f"{record['voltage_sec']:.2f} V"
    if record.get("sequence") is not None:
        reading = record.get("reading")
        return str(reading) if reading else str(record["sequence"])
    reading = record.get("reading")
    if reading:
        return str(reading)
    return status_text(record)


def origin_text(record) -> str:
    if not record:
        return "?"
    origin = record.get("origin")
    return {
        "simulated": "虚拟",
        "manual": "手动",
        "hardware": "硬件",
        "unknown": "?",
    }.get(origin, "?")


def expand_phase_sequence_to_columns(record) -> dict[str, dict[str, Any]]:
    if not record:
        return {}
    measurement_id = record.get("measurement_id", "")
    parts = measurement_id.split(".")
    pt_name = parts[1] if len(parts) >= 2 else ""
    if pt_name not in {"PT1", "PT3"}:
        return {}
    return {
        f"{pt_name}_{phase}": {
            "measurement_id": measurement_id,
            "phase": phase,
            "sequence": record.get("sequence"),
            "quality": record.get("quality"),
            "reading": record.get("reading"),
            "passed": record.get("passed"),
            "origin": record.get("origin"),
        }
        for phase in ("A", "B", "C")
    }
