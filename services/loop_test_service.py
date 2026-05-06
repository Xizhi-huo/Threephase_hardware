"""
services/loop_test_service.py
回路连通性测试服务
"""

import time
from typing import Callable

from domain.enums import BreakerPosition
from domain.assessment import AssessmentEventType
from domain.measurement_id import loop_id
from domain.measurement_map import get_measurement_spec
from domain.measurement_schema import (
    is_record_complete,
    store_raw,
    validate_origin,
    validate_record,
)
from domain.test_states import LOOP_TEST_RECORD_KEYS, LoopTestState


_LOOP_CONDUCTIVE_KEYS = frozenset(('AA', 'BB', 'CC'))


class LoopTestService:
    """
    回路连通性测试业务逻辑。
    状态以 LoopTestState dataclass 持有，避免裸字典的字段漂移。
    """

    def __init__(
        self,
        *,
        sim_state,
        flow_mgr,
        get_physics: Callable[[], object],
        get_loop_test_state: Callable[[], LoopTestState],
        set_loop_test_state: Callable[[LoopTestState], None],
        append_assessment_event: Callable,
        exit_loop_test_mode: Callable[[], None],
        mark_fault_detected: Callable | None = None,
    ):
        self._sim_state = sim_state
        self._flow_mgr = flow_mgr
        self._get_physics = get_physics
        self._get_loop_test_state = get_loop_test_state
        self._set_loop_test_state = set_loop_test_state
        self._append_assessment_event = append_assessment_event
        self._exit_loop_test_mode = exit_loop_test_mode
        self._mark_fault_detected = mark_fault_detected or (lambda **_: False)

    # ── 状态工厂 ──────────────────────────────────────────────────────────────
    def create_loop_test_state(self) -> LoopTestState:
        return LoopTestState()

    def _set_loop_test_feedback(self, message, color='#444444') -> None:
        state = self._get_loop_test_state()
        state.feedback = message
        state.feedback_color = color

    @staticmethod
    def _normalize_loop_pair(pair) -> str | None:
        text = str(pair or "").upper().strip()
        if len(text) != 2 or any(ch not in 'ABC' for ch in text):
            return None
        if text[0] == text[1]:
            key = text
        else:
            key = ''.join(sorted(text))
        return key if key in LOOP_TEST_RECORD_KEYS else None

    @staticmethod
    def _expected_loop_continuity(pair: str) -> str:
        return "closed" if pair in _LOOP_CONDUCTIVE_KEYS else "open"

    @staticmethod
    def _is_expected_loop_result(pair: str, continuity: str) -> bool:
        return continuity == LoopTestService._expected_loop_continuity(pair)

    @staticmethod
    def _continuity_from_meter_status(meter_status: str) -> str | None:
        if meter_status == "ok":
            return "closed"
        if meter_status == "danger":
            return "open"
        return None

    @staticmethod
    def _format_reading(record: dict) -> str:
        if record.get("quality") == "unknown":
            return "未判定"
        continuity = record.get("continuity")
        if continuity == "closed":
            return "导通 [≈0Ω]"
        if continuity == "open":
            return "断路 [∞Ω]"
        return "无效"

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
            return "sim:multimeter"
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

    def get_current_loop_pair(self) -> str | None:
        sim = self._sim_state
        n1, n2 = sim.probe1_node, sim.probe2_node
        if not n1 or not n2:
            return None
        n1 = n1.upper()
        n2 = n2.upper()
        if not (n1.startswith('LOOP_G') and n2.startswith('LOOP_G')):
            return None
        parts1 = n1.split('_')   # ['LOOP', 'G1', 'A']
        parts2 = n2.split('_')   # ['LOOP', 'G2', 'A']
        if len(parts1) != 3 or len(parts2) != 3:
            return None
        by_gen = {parts1[1]: parts1[2], parts2[1]: parts2[2]}
        if set(by_gen) != {'G1', 'G2'}:
            return None
        return self._normalize_loop_pair(by_gen['G1'] + by_gen['G2'])

    def _get_current_loop_phase_match(self) -> str | None:
        pair = self.get_current_loop_pair()
        if pair and pair[0] == pair[1]:
            return pair[0]
        return None

    def get_loop_test_steps(self) -> list[tuple[str, bool]]:
        sim = self._sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        state = self._get_loop_test_state()
        records = state.records
        all_rec = all(records.get(pair) is not None for pair in LOOP_TEST_RECORD_KEYS)
        steps = [
            ("1. 断开中性点小电阻连接",
             sim.grounding_mode == "断开"),
            ("2. 将 Gen 1 切至手动模式并切至工作位置",
             gen1.mode == "manual" and gen1.breaker_position == BreakerPosition.WORKING),
            ("3. 将 Gen 2 切至手动模式并切至工作位置",
             gen2.mode == "manual" and gen2.breaker_position == BreakerPosition.WORKING),
            ("4. 合闸 Gen 1（不要起机，仅闭合开关）",
             gen1.breaker_position == BreakerPosition.WORKING and gen1.breaker_closed),
            ("5. 合闸 Gen 2（不要起机，仅闭合开关）",
             gen2.breaker_position == BreakerPosition.WORKING and gen2.breaker_closed),
            ("6. 开启万用表，在母排拓扑页进行三相通断测试",
             sim.multimeter_mode),
            ("7. 记录 AA/BB/CC 导通与 AB/AC/BC 隔离结果",
             all_rec),
        ]
        if state.completed:
            return [(text, True) for text, _ in steps]
        return steps

    def record_loop_measurement(
        self,
        pair: str,
        *,
        origin: str,
        continuity: str | None = None,
        instrument: str | None = "multimeter",
        instrument_id: str | None = None,
        terminal_ids: list[str] | None = None,
        channel_ids: list[str] | None = None,
        timestamp: float | None = None,
        raw: str | dict | None = None,
        raw_ref: str | None = None,
    ) -> None:
        validate_origin(origin)
        sim = self._sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        normalized_pair = self._normalize_loop_pair(pair)
        if normalized_pair is None:
            return
        pair = normalized_pair
        measurement_id = loop_id(pair)
        spec = get_measurement_spec(measurement_id) or {}
        terminal_ids_final = list(terminal_ids or spec.get("terminal_ids", []))
        channel_ids_final = list(channel_ids or [])

        def _record_invalid(reason) -> None:
            self._append_assessment_event(
                AssessmentEventType.MEASUREMENT_INVALID,
                step=1,
                target='loop',
                point=pair,
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

        if origin == "simulated" and continuity is not None:
            raise ValueError("simulated loop measurement reads continuity from physics")
        if origin == "hardware":
            if timestamp is None:
                raise ValueError("hardware measurement requires timestamp")
            if not instrument_id:
                raise ValueError("hardware measurement requires instrument_id")

        if origin != "unknown" and sim.grounding_mode != "断开":
            _record_invalid("grounding_not_disconnected")
            self._set_loop_test_feedback('请先断开中性点小电阻连接（接地系统选"断开"）。', "red")
            return
        if origin != "unknown" and (gen1.mode != "manual" or gen2.mode != "manual"):
            _record_invalid("generators_not_manual")
            self._set_loop_test_feedback("请先将两台发电机都切至手动（Manual）模式。", "red")
            return
        if origin != "unknown" and (gen1.running or gen2.running):
            _record_invalid("generator_running")
            self._set_loop_test_feedback(
                "通断测试须在发电机停机状态下进行（万用表靠自身电池注入微小电流，"
                "发电机运行时高压会干扰测量并损坏万用表）。", "red")
            return
        if origin != "unknown" and not (gen1.breaker_closed and gen1.breaker_position == BreakerPosition.WORKING):
            _record_invalid("gen1_not_closed")
            self._set_loop_test_feedback("请先将 Gen 1 切至工作位置并合闸。", "red")
            return
        if origin != "unknown" and not (gen2.breaker_closed and gen2.breaker_position == BreakerPosition.WORKING):
            _record_invalid("gen2_not_closed")
            self._set_loop_test_feedback("请先将 Gen 2 切至工作位置并合闸。", "red")
            return
        if origin == "simulated" and not sim.multimeter_mode:
            _record_invalid("multimeter_disabled")
            self._set_loop_test_feedback("请先开启万用表。", "red")
            return

        if origin == "simulated":
            current_pair = self.get_current_loop_pair()
            if current_pair != pair:
                _record_invalid("probe_phase_mismatch")
                if current_pair is None:
                    msg = (f"当前表笔未正确对准 {pair} 回路，"
                           f"请在母排拓扑页将表笔分别放在 G1 与 G2 的 {pair} 测点。")
                else:
                    msg = f"当前表笔对准的是 {current_pair}，请记录对应测点或重新放置表笔。"
                self._set_loop_test_feedback(msg, "red")
                return

            physics = self._get_physics()
            meter_status = getattr(physics, 'meter_status', 'idle')
            continuity = self._continuity_from_meter_status(meter_status)
            if continuity is None:
                _record_invalid("invalid_meter_status")
                self._set_loop_test_feedback("测量结果无效，请确认表笔放在 G1 与 G2 的回路测点上。", "red")
                return
            terminal_ids_final = [sim.probe1_node, sim.probe2_node]
        elif origin in ("manual", "hardware"):
            if continuity not in ("closed", "open"):
                raise ValueError("manual/hardware loop measurement requires continuity closed/open")
        elif continuity not in (None, "closed", "open"):
            raise ValueError("unknown loop measurement continuity must be closed/open/None")

        quality = "unknown" if origin == "unknown" else "ok"
        passed = None if origin == "unknown" else self._is_expected_loop_result(pair, str(continuity))
        ts = self._timestamp_for_origin(origin, timestamp)
        record: dict = {
            "measurement_id": measurement_id,
            "value": continuity,
            "unit": None,
            "origin": origin,
            "instrument": instrument,
            "instrument_id": self._instrument_id_for_origin(origin, instrument_id),
            "node_ids": list(spec.get("node_ids", terminal_ids_final)),
            "terminal_ids": terminal_ids_final,
            "channel_ids": channel_ids_final,
            "timestamp": ts,
            "raw": None,
            "raw_ref": raw_ref,
            "quality": quality,
            "passed": passed,
            "continuity": continuity,
        }
        if raw_ref is None:
            store_raw(record, raw)
        else:
            record["raw"] = raw
        record["reading"] = self._format_reading(record)
        validate_record(record)

        # 记录测量结果（是否异常按测点期望值判断，完成阶段统一分析）
        state = self._get_loop_test_state()
        state.records[pair] = record
        self._append_assessment_event(
            AssessmentEventType.MEASUREMENT_RECORDED,
            step=1,
            target='loop',
            point=pair,
            **self._measurement_event_payload(record),
        )
        if passed is False:
            self._mark_loop_fault_detected(pair)

        all_rec = all(is_record_complete(state.records.get(key)) for key in LOOP_TEST_RECORD_KEYS)
        if passed:
            reading_text = self._format_reading(record)
            if all_rec:
                self._set_loop_test_feedback(
                    "六组回路数据已全部记录，请点击「完成第一步测试」确认结果。", "#006600")
            else:
                self._set_loop_test_feedback(f"{pair} 测点{reading_text}，符合预期，请继续测量其余测点。", "#006600")
        elif passed is False:
            abnormal_text = "异常导通 [≈0Ω]" if continuity == 'closed' else "异常断路 [∞Ω]"
            if all_rec:
                self._set_loop_test_feedback(
                    f"{pair} 测点{abnormal_text}，六组已全部记录，请点击「完成第一步测试」查看故障分析。",
                    "#cc6600")
            else:
                self._set_loop_test_feedback(
                    f"{pair} 测点{abnormal_text}（疑似接线错误），已记录结果，请继续测量其余测点。",
                    "#cc6600")

    def _mark_loop_fault_detected(self, pair: str) -> None:
        fc = self._sim_state.fault_config
        if (fc.active and not fc.repaired
                and (fc.scenario_id in ('E01', 'E02')
                     or fc.params.get('g1_loop_swap')
                     or fc.params.get('g2_loop_swap'))):
            self._mark_fault_detected(
                step=1,
                source='loop_measurement',
                target='loop',
                point=pair,
            )

    def reset_loop_test(self) -> None:
        self._set_loop_test_state(self.create_loop_test_state())

    def is_loop_test_complete(self) -> bool:
        """流程门禁：只有用户点击"完成第一步测试"后才返回 True。"""
        return self._get_loop_test_state().completed

    def _are_loop_records_complete(self) -> bool:
        """内部辅助：六组回路记录是否齐全（用于 finalize 前置校验）。"""
        records = self._get_loop_test_state().records
        return all(is_record_complete(records.get(pair)) for pair in LOOP_TEST_RECORD_KEYS)

    def finalize_loop_test(self) -> None:
        if not self._are_loop_records_complete():
            self._set_loop_test_feedback(
                '请先完成 AA/BB/CC 与 AB/AC/BC 六组回路记录，再点击"完成第一步测试"。', "red")
            return
        # 检查是否存在不符合期望的回路测点
        state = self._get_loop_test_state()
        records = state.records
        fault_pairs = []
        for pair in LOOP_TEST_RECORD_KEYS:
            record = records.get(pair)
            if record is not None and record.get('passed') is False:
                fault_pairs.append(pair)
        fc = self._sim_state.fault_config
        fault_training = (
            fc.active and fc.detected and not fc.repaired
            and self._flow_mgr.can_advance_with_fault()
        )
        if fault_pairs and not fault_training:
            # 当前流程策略要求先纠正异常后再完成该步
            fault_str = '、'.join(fault_pairs)
            if self._flow_mgr.should_show_diagnostic_hints():
                msg = (
                    f"回路测试发现故障：{fault_str} 测点结果异常，说明对应相接线错误。"
                    f"请检查并纠正接线后重置重测。"
                )
            else:
                msg = (
                    f"回路测试发现异常：{fault_str} 测点结果异常。"
                    f"请继续排查并在修正后重新测量。"
                )
            self._set_loop_test_feedback(msg, "red")
            return
        self._exit_loop_test_mode()   # 退出回路检查模式，恢复断路器联锁
        state.completed = True
        if fault_pairs:
            # 当前流程策略允许带异常完成，提示继续后续步骤
            fault_str = '、'.join(fault_pairs)
            self._set_loop_test_feedback(
                f"第一步完成（发现异常）：{fault_str} 测点结果异常，"
                f"已记录故障证据，请继续后续步骤收集更多数据，将在第五步前统一检修。",
                "#92400e")
        else:
            self._set_loop_test_feedback(
                "第一步【回路连通性测试】已确认完成：同相回路导通、异相回路隔离，接线正确。",
                "#006600")
