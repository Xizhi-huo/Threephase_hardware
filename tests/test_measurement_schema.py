from __future__ import annotations

import pytest

from domain.measurement_schema import parse_measurement_id, validate_origin, validate_record


def test_validate_origin_accepts_only_schema_origins():
    validate_origin("simulated")
    validate_origin("manual")
    validate_origin("hardware")
    validate_origin("unknown")
    with pytest.raises(ValueError):
        validate_origin("operator")


def test_parse_measurement_id_handles_all_domains():
    assert parse_measurement_id("loop.global.AA") == ("loop", "global", "AA")
    assert parse_measurement_id("pt_voltage.PT1.AB") == ("pt_voltage", "PT1", "AB")
    assert parse_measurement_id("phase_sequence.PT3") == ("phase_sequence", "PT3", None)
    assert parse_measurement_id("pt_diff.gen2.CC") == ("pt_diff", "gen2", "CC")
    with pytest.raises(ValueError):
        parse_measurement_id("phase_sequence.PT1.seq")


def test_validate_record_rejects_legacy_record_fields():
    record = {
        "measurement_id": "loop.global.AA",
        "origin": "manual",
        "quality": "ok",
        "status": "ok",
    }
    with pytest.raises(ValueError):
        validate_record(record)


def test_validate_record_accepts_new_loop_shape():
    validate_record(
        {
            "measurement_id": "loop.global.AA",
            "value": "closed",
            "unit": None,
            "origin": "manual",
            "instrument": "multimeter",
            "instrument_id": None,
            "node_ids": ["LOOP_G1_A", "LOOP_G2_A"],
            "terminal_ids": ["LOOP_G1_A", "LOOP_G2_A"],
            "channel_ids": [],
            "timestamp": 1.0,
            "quality": "ok",
            "reading": "导通 [≈0Ω]",
            "passed": True,
            "continuity": "closed",
        }
    )
