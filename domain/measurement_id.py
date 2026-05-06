"""Measurement id builders for the four pre-closing test domains."""


def loop_id(cell: str) -> str:
    return f"loop.global.{cell}"


def pt_voltage_id(pt: str, pair: str) -> str:
    return f"pt_voltage.{pt}.{pair}"


def phase_sequence_id(pt: str) -> str:
    return f"phase_sequence.{pt}"


def pt_diff_id(gen_id: int, cell: str) -> str:
    return f"pt_diff.gen{gen_id}.{cell}"
