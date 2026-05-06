"""
services/pt_phase_check_service.py
PT 相序检查服务（第三步）

通过万用表手动测量 PT1_X/PT2_X 和 PT3_X/PT2_X 端子对（共6组），
根据物理引擎返回的 meter_phase_match 判断 ABC 各相是否连线正确。

电气状态与第二步相同：
  - Gen1：手动工作位，起机，合闸并入母排（提供 PT1/PT2 参考电压）
  - Gen2：手动工作位，起机，断路器断开（提供 PT3 参考电压）
相序判断以 meter_phase_match 为准（物理引擎比较两路波形的实际相位），
与电压大小无关。
"""

import time
from typing import Callable

from domain.enums import BreakerPosition
from domain.assessment import AssessmentEventType
from domain.measurement_id import phase_sequence_id
from domain.measurement_map import get_measurement_spec
from domain.measurement_schema import (
    VALID_PHASE_SEQUENCES,
    is_record_complete,
    store_raw,
    validate_origin,
    validate_record,
)
from domain.test_states import PtPhaseCheckState

_ALL_KEYS = ('PT1', 'PT3')
_POSITIVE_PHASE_SEQUENCES = {'ABC', 'BCA', 'CAB'}


class PtPhaseCheckService:
    """PT 相序检查业务逻辑。"""

    def __init__(
        self,
        *,
        sim_state,
        flow_mgr,
        get_physics: Callable[[], object],
        get_pt_phase_check_state: Callable[[], PtPhaseCheckState],
        set_pt_phase_check_state: Callable[[PtPhaseCheckState], None],
        is_loop_test_complete: Callable[[], bool],
        is_pt_voltage_check_complete: Callable[[], bool],
        append_assessment_event: Callable,
        mark_fault_detected: Callable,
        set_pt_phase_check_feedback: Callable[[str, str], None],
        mark_pt_phase_check_completed: Callable[[], None],
    ):
        self._sim_state = sim_state
        self._flow_mgr = flow_mgr
        self._get_physics = get_physics
        self._get_pt_phase_check_state = get_pt_phase_check_state
        self._set_pt_phase_check_state = set_pt_phase_check_state
        self._is_loop_test_complete = is_loop_test_complete
        self._is_pt_voltage_check_complete = is_pt_voltage_check_complete
        self._append_assessment_event = append_assessment_event
        self._mark_fault_detected = mark_fault_detected
        self._set_pt_phase_check_feedback = set_pt_phase_check_feedback
        self._mark_pt_phase_check_completed = mark_pt_phase_check_completed

    @staticmethod
    def _sequence_display_text(seq: str) -> str:
        if seq in {'ABC', 'BCA', 'CAB'}:
            return "正序"
        if seq == 'FAULT':
            return "异常"
        if isinstance(seq, str) and len(seq) == 3:
            return "反序"
        return "异常"

    @staticmethod
    def _format_reading(record: dict) -> str:
        sequence = record.get("sequence")
        if record.get("quality") == "unknown":
            return "相序未判定"
        if sequence is None:
            return "相序无效"
        return f"相序仪检测: {record['measurement_id'].split('.')[1]} → {PtPhaseCheckService._sequence_display_text(sequence)}"

    @staticmethod
    def _timestamp_for_origin(origin: str, timestamp: float | None) -> float | None:
        if origin in ("simulated", "manual"):
            return time.time()
        if origin == "hardware":
            if timestamp is None:
                raise ValueError("hardware measurement requires timestamp")
            return timestamp
        return timestamp

    @staticmethod
    def _instrument_id_for_origin(origin: str, instrument_id: str | None) -> str | None:
        if origin == "simulated":
            return "sim:phase_seq_meter"
        if origin == "hardware" and not instrument_id:
            raise ValueError("hardware measurement requires instrument_id")
        return instrument_id

    @staticmethod
    def _measurement_event_payload(record: dict) -> dict:
        return {
            "measurement_id": record["measurement_id"],
            "origin": record["origin"],
            "instrument": record.get("instrument"),
            "instrument_id": record.get("instrument_id"),
            "node_ids": list(record.get("node_ids", [])),
            "terminal_ids": list(record.get("terminal_ids", [])),
            "channel_ids": list(record.get("channel_ids", [])),
            "timestamp": record.get("timestamp"),
            "quality": record.get("quality"),
            "value": record.get("value"),
            "unit": record.get("unit"),
            "passed": record.get("passed"),
            "event_schema_version": 2,
        }

    @staticmethod
    def _record_passed(record: dict | None) -> bool:
        return bool(is_record_complete(record) and record is not None and record.get("passed") is True)

    # ── 状态工厂 ──────────────────────────────────────────────────────────────
    def create_pt_phase_check_state(self) -> PtPhaseCheckState:
        return PtPhaseCheckState()

    def start_pt_phase_check(self) -> None:
        self._get_pt_phase_check_state().started = True

    def stop_pt_phase_check(self) -> None:
        self._get_pt_phase_check_state().started = False

    def _set_feedback(self, message, color='#444444') -> None:
        self._set_pt_phase_check_feedback(message, color)

    # ── 步骤列表 ──────────────────────────────────────────────────────────────
    def get_pt_phase_check_steps(self) -> list[tuple[str, bool]]:
        sim = self._sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        state = self._get_pt_phase_check_state()
        loop_done = self._is_loop_test_complete()
        gnd_ok = sim.grounding_mode == "小电阻接地"
        gen1_on_bus = (gen1.breaker_position == BreakerPosition.WORKING and gen1.breaker_closed)
        gen2_running_open = gen2.running and not gen2.breaker_closed
        rec = state.records

        vol_done = self._is_pt_voltage_check_complete()
        steps = [
            ("1. 前提：第一步回路连通性测试已完成", loop_done),
            ("2. 前提：第二步 PT 单体线电压检查已完成", vol_done),
            ("3. 恢复中性点小电阻接地", gnd_ok),
            ("4. 确认 Gen1 在工作位并入母排（提供 PT1/PT2 参考电压）", gen1_on_bus),
            ("5. 启动 Gen2，保持断路器断开（提供 PT3 参考电压）", gen2_running_open),
            ("6. 接入相序仪至 PT1，记录 PT1 三相相序", is_record_complete(rec.get('PT1'))),
            ("7. 接入相序仪至 PT3，记录 PT3 三相相序", is_record_complete(rec.get('PT3'))),
        ]
        if state.completed:
            return [(text, True) for text, _ in steps]
        return steps

    # ── 逐相记录 ──────────────────────────────────────────────────────────────
    def record_pt_phase_check(self, pt_name, phase) -> None:
        pt_name = pt_name.upper()
        phase = phase.upper()
        key = f"{pt_name}_{phase}"
        sim = self._sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        state = self._get_pt_phase_check_state()

        def _record_invalid(reason) -> None:
            self._append_assessment_event(
                AssessmentEventType.MEASUREMENT_INVALID,
                step=3,
                target=pt_name,
                point=phase,
                reason=reason,
            )

        if not state.started:
            _record_invalid("step_not_started")
            self._set_feedback("请先点击「开始第三步测试」，再进行相序记录。", "red")
            return
        if not self._is_loop_test_complete():
            _record_invalid("loop_test_incomplete")
            self._set_feedback("请先完成第一步【回路连通性测试】，再进行 PT 相序检查。", "red")
            return
        if not self._is_pt_voltage_check_complete():
            _record_invalid("pt_voltage_incomplete")
            self._set_feedback("请先完成第二步【PT 单体线电压检查】，再进行 PT 相序检查。", "red")
            return
        if sim.grounding_mode != "小电阻接地":
            _record_invalid("grounding_not_ready")
            self._set_feedback("请先恢复中性点小电阻接地，再进行 PT 相序检查。", "red")
            return
        if gen1.breaker_position != BreakerPosition.WORKING or not gen1.breaker_closed:
            _record_invalid("gen1_not_on_bus")
            self._set_feedback("请先确认 Gen1 已并入母排，建立 PT1/PT2 参考电压。", "red")
            return

        if pt_name == 'PT3':
            if not gen2.running:
                _record_invalid("gen2_not_running")
                self._set_feedback(
                    "测量 PT3 相序时，请先启动 Gen2（保持断路器断开）。", "red")
                return
            if gen2.breaker_closed:
                _record_invalid("gen2_breaker_closed")
                self._set_feedback(
                    "测量 PT3 相序时，Gen2 断路器应保持断开状态。", "red")
                return

        expected_pair = {key, f"PT2_{phase}"}
        actual_pair = (
            {sim.probe1_node, sim.probe2_node}
            if sim.probe1_node and sim.probe2_node else set()
        )
        if actual_pair != expected_pair:
            _record_invalid("probe_pair_mismatch")
            self._set_feedback(
                f"请在母排拓扑页将表笔放在 {key} 和 PT2_{phase} 端子上，再点击记录。", "red")
            return

        physics = self._get_physics()
        phase_match = getattr(physics, 'meter_phase_match', None)
        if phase_match is None:
            _record_invalid("invalid_meter_status")
            self._set_feedback("当前测量结果无效，请确认表笔接在 PT 和 PT2 同相端子上。", "red")
            return

        self.record_phase_sequence(pt_name, "ABC" if phase_match else "FAULT", origin="simulated")

    def record_phase_sequence(
        self,
        pt_name: str,
        seq: str | None,
        *,
        origin: str,
        instrument: str | None = "phase_seq_meter",
        instrument_id: str | None = None,
        terminal_ids: list[str] | None = None,
        channel_ids: list[str] | None = None,
        timestamp: float | None = None,
        raw: str | dict | None = None,
        raw_ref: str | None = None,
    ) -> bool:
        validate_origin(origin)
        pt_name = pt_name.upper()
        state = self._get_pt_phase_check_state()
        sim = self._sim_state
        measurement_id = phase_sequence_id(pt_name)
        spec = get_measurement_spec(measurement_id) or {}
        terminal_ids_final = list(terminal_ids or spec.get("terminal_ids", []))
        channel_ids_final = list(channel_ids or [])

        def _record_invalid(reason: str) -> None:
            self._append_assessment_event(
                AssessmentEventType.MEASUREMENT_INVALID,
                step=3,
                target=pt_name,
                point='sequence',
                reason=reason,
                measurement_id=measurement_id,
                origin=origin,
                instrument=instrument,
                instrument_id=instrument_id,
                node_ids=list(spec.get("node_ids", [])),
                terminal_ids=terminal_ids_final,
                channel_ids=channel_ids_final,
                timestamp=time.time(),
                quality="invalid",
                value=None,
                unit=None,
                passed=None,
                event_schema_version=2,
            )

        if origin in ("simulated", "manual", "hardware") and seq is None:
            raise ValueError("phase sequence measurement requires seq")
        if origin == "hardware":
            if timestamp is None:
                raise ValueError("hardware measurement requires timestamp")
            if not instrument_id:
                raise ValueError("hardware measurement requires instrument_id")

        if origin != "unknown" and not state.started:
            _record_invalid("step_not_started")
            self._set_feedback("请先点击“开始第三步测试”再记录。", "red")
            return False
        if origin != "unknown" and not self._is_loop_test_complete():
            _record_invalid("loop_test_incomplete")
            self._set_feedback("请先完成第一步【回路连通性测试】，再进行相序检查。", "red")
            return False
        if origin != "unknown" and not self._is_pt_voltage_check_complete():
            _record_invalid("pt_voltage_incomplete")
            self._set_feedback("请先完成第二步【PT 单体线电压检查】，再进行相序检查。", "red")
            return False
        if origin != "unknown" and sim.grounding_mode != "小电阻接地":
            _record_invalid("grounding_not_ready")
            self._set_feedback("请先恢复中性点小电阻接地，再进行相序检查。", "red")
            return False

        gen1 = sim.gen1
        if origin != "unknown" and (gen1.breaker_position != BreakerPosition.WORKING or not gen1.breaker_closed):
            _record_invalid("gen1_not_on_bus")
            self._set_feedback("请先确认 Gen1 已并入母排，建立 PT1/PT2 参考电压。", "red")
            return False

        if origin != "unknown" and pt_name == 'PT3':
            gen2 = sim.gen2
            if not gen2.running:
                _record_invalid("gen2_not_running")
                self._set_feedback("测量 PT3 相序时，请先启动 Gen2（保持断路器断开）。", "red")
                return False
            if gen2.breaker_closed:
                _record_invalid("gen2_breaker_closed")
                self._set_feedback("测量 PT3 相序时，Gen2 断路器应保持断开状态。", "red")
                return False

        seq = seq.upper() if isinstance(seq, str) else seq
        is_valid_seq = isinstance(seq, str) and seq in VALID_PHASE_SEQUENCES
        display_seq = self._sequence_display_text(seq or "")
        passed = None if origin == "unknown" else bool(is_valid_seq and seq in _POSITIVE_PHASE_SEQUENCES)
        if origin == "unknown":
            quality = "unknown"
        elif not is_valid_seq:
            quality = "invalid"
        else:
            quality = "ok" if passed else "out_of_range"

        record: dict = {
            "measurement_id": measurement_id,
            "value": seq,
            "unit": None,
            "origin": origin,
            "instrument": instrument,
            "instrument_id": self._instrument_id_for_origin(origin, instrument_id),
            "node_ids": list(spec.get("node_ids", terminal_ids_final)),
            "terminal_ids": terminal_ids_final,
            "channel_ids": channel_ids_final,
            "timestamp": self._timestamp_for_origin(origin, timestamp),
            "raw": None,
            "raw_ref": raw_ref,
            "quality": quality,
            "passed": passed,
            "sequence": seq,
        }
        if raw_ref is None:
            store_raw(record, raw)
        else:
            record["raw"] = raw
        record["reading"] = self._format_reading(record)
        validate_record(record)
        state.records[pt_name] = record

        if passed is False and self._sim_state.fault_config.active:
            self._mark_fault_detected(
                step=3,
                source='phase_seq_meter',
                target=pt_name,
                sequence=seq,
            )

        self._append_assessment_event(
            AssessmentEventType.MEASUREMENT_RECORDED,
            step=3,
            target=pt_name,
            point='sequence',
            **self._measurement_event_payload(record),
            raw_sequence=seq,
        )

        result_txt = f"{display_seq}✓" if passed is True else f"{display_seq}✗"
        self._refresh_phase_check_result()
        if origin == "unknown":
            color = "#64748b"
            state.feedback = f"{pt_name} 已导入未知来源相序记录，该记录不参与完成判定。"
        elif passed is False:
            color = "#dc2626"
            state.feedback = f"{pt_name} 相序已记录：{result_txt}"
        elif state.result == 'pass':
            color = "#15803d"
            state.feedback = f"{pt_name} 相序已记录：{result_txt}。PT1/PT3 全部通过。"
        elif state.result == 'fail':
            color = "#cc6600"
            state.feedback = f"{pt_name} 相序已记录：{result_txt}，但仍存在已记录异常项。"
        else:
            color = "#15803d"
            state.feedback = f"{pt_name} 相序已记录：{result_txt}，请继续记录另一侧。"
        state.feedback_color = color
        return True

    def reset_pt_phase_check(self) -> None:
        self._set_pt_phase_check_state(self.create_pt_phase_check_state())

    def is_pt_phase_check_complete(self) -> bool:
        """流程门禁：只有用户点击"完成第三步测试"后才返回 True。"""
        return self._get_pt_phase_check_state().completed

    def _are_all_records_filled(self) -> bool:
        """PT1/PT3 两条相序记录是否已全部测量（无论通过与否）。"""
        records = self._get_pt_phase_check_state().records
        return all(is_record_complete(records.get(k)) for k in _ALL_KEYS)

    def _refresh_phase_check_result(self) -> None:
        """总结果只由全部记录派生，避免单侧 PT 记录覆盖另一侧结果。"""
        state = self._get_pt_phase_check_state()
        records = state.records
        filled = [records.get(k) for k in _ALL_KEYS]
        if any(is_record_complete(record) and record is not None and record.get('passed') is False for record in filled):
            state.result = 'fail'
        elif all(is_record_complete(record) for record in filled):
            state.result = 'pass'
        else:
            state.result = None

    def _are_phase_check_records_complete(self) -> bool:
        """两条相序记录是否齐全且全部通过（正常模式 finalize 校验用）。"""
        records = self._get_pt_phase_check_state().records
        return all(
            self._record_passed(records.get(k))
            for k in _ALL_KEYS
        )

    def finalize_pt_phase_check(self) -> None:
        state = self._get_pt_phase_check_state()
        fc = self._sim_state.fault_config
        fault_training = (
            fc.active and fc.detected and not fc.repaired
            and self._flow_mgr.can_advance_with_fault()
        )

        if fault_training:
            # 当前流程策略允许带异常完成，但仍要求本步测量项齐全
            if not self._are_all_records_filled():
                self._set_feedback(
                    '请先完成 PT1/PT3 两条相序记录，再点击"完成第三步测试"。', "red")
                return
            self._mark_pt_phase_check_completed()
            fail_keys = [k for k in _ALL_KEYS
                         if is_record_complete(state.records.get(k))
                         and not self._record_passed(state.records.get(k))]
            if fail_keys:
                fail_str = '、'.join(fail_keys)
                self._set_feedback(
                    f"第三步完成（发现异常）：{fail_str} 相序错误，"
                    f"已记录故障证据，请继续后续步骤收集更多数据，将在第五步前统一检修。",
                    "#92400e")
            else:
                self._set_feedback(
                    "第三步【PT 相序检查】已确认完成，后续操作将不再影响该步骤状态。",
                    "#006600")
        else:
            # 当前流程策略要求本步全部通过后才能完成
            if not self._are_phase_check_records_complete():
                self._set_feedback(
                    '请先完成 PT1/PT3 两条相序记录（且全部通过），再点击"完成第三步测试"。',
                    "red")
                return
            self._mark_pt_phase_check_completed()
            self._set_feedback(
                "第三步【PT 相序检查】已确认完成，后续操作将不再影响该步骤状态。",
                "#006600")

    def get_pt_phase_check_blockers(self) -> list[str]:
        return [text for text, done in self.get_pt_phase_check_steps() if not done]
