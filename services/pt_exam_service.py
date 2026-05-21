"""
services/pt_exam_service.py
PT 二次端子压差考核服务
"""

from __future__ import annotations

import time
from typing import Any, Callable

import numpy as np

from domain.assessment import AssessmentEventType
from domain.enums import BreakerPosition
from domain.measurement_id import pt_diff_id
from domain.measurement_map import get_measurement_spec
from domain.measurement_schema import (
    is_record_complete,
    store_raw,
    validate_origin,
    validate_record,
)
from domain.test_states import PtExamState


class PtExamService:
    """
    PT 二次端子压差考核业务逻辑。
    gen_id 由调用方（UI/Controller）显式传入，服务层不再直接读取任何 UI 控件状态。
    """

    def __init__(
        self,
        *,
        sim_state,
        flow_mgr,
        get_physics: Callable[[], object],
        get_pt_exam_states: Callable[[], dict],
        is_loop_test_complete: Callable[[], bool],
        is_pt_voltage_check_complete: Callable[[], bool],
        is_pt_phase_check_complete: Callable[[], bool],
        append_assessment_event: Callable,
        mark_fault_detected: Callable | None = None,
    ):
        self._sim_state = sim_state
        self._flow_mgr = flow_mgr
        self._get_physics = get_physics
        self._get_pt_exam_states = get_pt_exam_states
        self._is_loop_test_complete = is_loop_test_complete
        self._is_pt_voltage_check_complete = is_pt_voltage_check_complete
        self._is_pt_phase_check_complete = is_pt_phase_check_complete
        self._append_assessment_event = append_assessment_event
        self._mark_fault_detected = mark_fault_detected

    # ── 状态工厂 ──────────────────────────────────────────────────────────────
    def create_pt_exam_state(self) -> PtExamState:
        return PtExamState()

    def start_pt_exam(self, gen_id) -> None:
        self._get_pt_exam_states()[gen_id].started = True

    def stop_pt_exam(self, gen_id) -> None:
        self._get_pt_exam_states()[gen_id].started = False

    def _set_pt_exam_feedback(self, gen_id, message, color='#444444') -> None:
        state = self._get_pt_exam_states()[gen_id]
        state.feedback = message
        state.feedback_color = color

    # Legacy dead interface retained as comments during dead-code verification:
    # def _expected_pt_probe_pair(self, gen_id, gen_phase, bus_phase):
    #     return {f"PT{'1' if gen_id == 1 else '3'}_{gen_phase}", f"PT2_{bus_phase}"}

    def _get_current_pt_phase_match(self, gen_id) -> tuple[str, str] | None:
        """返回 (gen_phase, bus_phase) 元组，或 None（表笔未对准有效 PT 端子）。"""
        sim = self._sim_state
        if not sim.probe1_node or not sim.probe2_node:
            return None
        gen_prefix = 'PT1_' if gen_id == 1 else 'PT3_'
        for a, b in [
            (sim.probe1_node, sim.probe2_node),
            (sim.probe2_node, sim.probe1_node),
        ]:
            if a.startswith(gen_prefix) and b.startswith('PT2_'):
                return (a[-1], b[-1])  # (gen_phase, bus_phase)
        return None

    @staticmethod
    def _format_reading(record: dict) -> str:
        voltage_sec = record.get("voltage_sec")
        if record.get("quality") == "unknown":
            return "未判定"
        if voltage_sec is None:
            return "无效"
        return f"矢量压差 {voltage_sec:.2f} V"

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

    def _build_pt_diff_record(
        self,
        gen_id: int,
        key: str,
        *,
        origin: str,
        voltage_sec: float | None,
        instrument: str | None,
        instrument_id: str | None,
        terminal_ids: list[str] | None,
        channel_ids: list[str] | None,
        timestamp: float | None,
        raw: str | dict | None,
        raw_ref: str | None,
    ) -> dict:
        measurement_id = pt_diff_id(gen_id, key)
        spec = get_measurement_spec(measurement_id) or {}
        terminal_ids_final = list(terminal_ids or spec.get("terminal_ids", []))
        quality = "unknown" if origin == "unknown" else "ok"
        record: dict = {
            "measurement_id": measurement_id,
            "value": None if voltage_sec is None else float(voltage_sec),
            "unit": "V",
            "origin": origin,
            "instrument": instrument,
            "instrument_id": self._instrument_id_for_origin(origin, instrument_id),
            "node_ids": list(spec.get("node_ids", terminal_ids_final)),
            "terminal_ids": terminal_ids_final,
            "channel_ids": list(channel_ids or []),
            "timestamp": self._timestamp_for_origin(origin, timestamp),
            "raw": None,
            "raw_ref": raw_ref,
            "quality": quality,
            "passed": None,
            "voltage_sec": None if voltage_sec is None else float(voltage_sec),
        }
        if raw_ref is None:
            store_raw(record, raw)
        else:
            record["raw"] = raw
        record["reading"] = self._format_reading(record)
        validate_record(record)
        return record

    def reset_pt_exam(self, gen_id=None) -> None:
        target_ids = (gen_id,) if gen_id in (1, 2) else (1, 2)
        states = self._get_pt_exam_states()
        for gid in target_ids:
            states[gid] = self.create_pt_exam_state()

    # def _is_pt_exam_setup_ready(self, gen_id):
    #     sim = self._sim_state
    #     gen1, gen2 = sim.gen1, sim.gen2
    #     gnd_ok = sim.grounding_mode == "小电阻接地"
    #     gen1_on = gen1.breaker_position == BreakerPosition.WORKING and gen1.breaker_closed
    #     if gen_id == 1:
    #         return gnd_ok and gen1_on and not gen2.breaker_closed
    #     return gnd_ok and gen1_on and gen2.running and not gen2.breaker_closed

    def record_pt_diff_measurement(
        self,
        gen_id: int,
        gen_phase: str,
        bus_phase: str,
        *,
        origin: str,
        voltage_sec: float | None = None,
        instrument: str | None = "multimeter",
        instrument_id: str | None = None,
        terminal_ids: list[str] | None = None,
        channel_ids: list[str] | None = None,
        timestamp: float | None = None,
        raw: str | dict | None = None,
        raw_ref: str | None = None,
    ) -> None:
        """
        记录 PT 二次端子矢量压差测量结果。
        """
        validate_origin(origin)
        if gen_id not in (1, 2):
            gen_id = 1
        gen_phase = gen_phase.upper()
        bus_phase = bus_phase.upper()
        key = f"{gen_phase}{bus_phase}"  # 'AA'/'AB'/.../'CC'
        if key not in {f"{g}{b}" for g in "ABC" for b in "ABC"}:
            return
        measurement_id = pt_diff_id(gen_id, key)
        spec = get_measurement_spec(measurement_id) or {}
        terminal_ids_final = list(terminal_ids or spec.get("terminal_ids", []))
        channel_ids_final = list(channel_ids or [])
        sim = self._sim_state
        states = self._get_pt_exam_states()
        state = states[gen_id]
        gen1, gen2 = sim.gen1, sim.gen2

        def _record_invalid(reason) -> None:
            self._append_assessment_event(
                AssessmentEventType.MEASUREMENT_INVALID,
                step=4,
                target=f'Gen{gen_id}',
                point=key,
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
                unit="V",
                passed=None,
                event_schema_version=2,
            )

        if origin == "simulated" and voltage_sec is not None:
            raise ValueError("simulated PT diff measurement reads voltage_sec from physics")
        if origin == "hardware":
            if timestamp is None:
                raise ValueError("hardware measurement requires timestamp")
            if not instrument_id:
                raise ValueError("hardware measurement requires instrument_id")

        # ── 门禁：必须先点击"开始第四步测试" ──────────────────────────────
        if origin != "unknown" and not state.started:
            _record_invalid("step_not_started")
            self._set_pt_exam_feedback(
                gen_id,
                f'请先点击"开始第四步测试 Gen{gen_id}"，再进行 PT 二次端子压差测量。',
                "red",
            )
            return

        if origin != "unknown" and not self._is_loop_test_complete():
            _record_invalid("loop_test_incomplete")
            self._set_pt_exam_feedback(
                gen_id,
                "请先完成第一步【回路连通性测试】，再进行 PT 二次端子压差测量。",
                "red",
            )
            return
        if origin != "unknown" and not self._is_pt_voltage_check_complete():
            _record_invalid("pt_voltage_incomplete")
            self._set_pt_exam_feedback(
                gen_id,
                "请先完成第二步【PT 单体线电压检查】，再进行 PT 二次端子压差测量。",
                "red",
            )
            return
        if origin != "unknown" and not self._is_pt_phase_check_complete():
            _record_invalid("pt_phase_incomplete")
            self._set_pt_exam_feedback(
                gen_id,
                "请先完成第三步【PT 相序检查】，确认 PT1/PT3 各相连线正确后，再进行压差测量。",
                "red",
            )
            return

        if origin != "unknown" and sim.grounding_mode != "小电阻接地":
            _record_invalid("grounding_not_ready")
            self._set_pt_exam_feedback(
                gen_id,
                "请先恢复中性点小电阻接地，再进行 PT 二次端子压差测量。",
                "red",
            )
            return

        if origin != "unknown" and gen_id == 1:
            if gen1.breaker_position != BreakerPosition.WORKING or not gen1.breaker_closed:
                _record_invalid("gen1_not_on_bus")
                self._set_pt_exam_feedback(
                    1,
                    "请将 Gen1 切至工作位置并合闸，建立母排参考电压。",
                    "red",
                )
                return
            if gen2.breaker_closed:
                _record_invalid("gen2_breaker_closed")
                self._set_pt_exam_feedback(
                    1,
                    "测试 Gen1 时请先断开 Gen2 断路器，Gen2 不应并入母排。",
                    "red",
                )
                return
        elif origin != "unknown":
            if gen1.breaker_position != BreakerPosition.WORKING or not gen1.breaker_closed:
                _record_invalid("gen1_not_on_bus")
                self._set_pt_exam_feedback(
                    2,
                    "请先确保 Gen1 已并入母排，作为母排参考电压来源。",
                    "red",
                )
                return
            if not gen2.running:
                _record_invalid("gen2_not_running")
                self._set_pt_exam_feedback(
                    2,
                    "请先启动 Gen2，再进行 PT 二次端子压差测量。",
                    "red",
                )
                return
            if gen2.breaker_closed:
                _record_invalid("gen2_breaker_closed")
                self._set_pt_exam_feedback(
                    2,
                    "Gen2 断路器应保持断开，并入前才能测量有效压差。",
                    "red",
                )
                return

        if origin == "simulated" and not sim.multimeter_mode:
            _record_invalid("multimeter_disabled")
            self._set_pt_exam_feedback(
                gen_id,
                "请先开启万用表，再到母排拓扑页放置表笔。",
                "red",
            )
            return
        if origin == "simulated" and (not sim.probe1_node or not sim.probe2_node):
            _record_invalid("probe_missing")
            self._set_pt_exam_feedback(
                gen_id,
                "表笔尚未放置完成，请在母排拓扑页连接对应 PT 端子。",
                "red",
            )
            return

        if origin == "simulated":
            matched = self._get_current_pt_phase_match(gen_id)
            if matched != (gen_phase, bus_phase):
                _record_invalid("probe_pair_mismatch")
                if matched is None:
                    gen_label = 'PT1' if gen_id == 1 else 'PT3'
                    msg = f"当前表笔不在 {gen_label}_{gen_phase} 与 PT2_{bus_phase} 之间，请重新放置。"
                else:
                    msg = f"当前表笔落在 {matched[0]}-{matched[1]} 组合，请记录对应组合或重新放置。"
                self._set_pt_exam_feedback(gen_id, msg, "red")
                return

            physics = self._get_physics()
            voltage_sec = getattr(physics, 'meter_voltage', None)
            meter_status = getattr(physics, 'meter_status', 'idle')
            if voltage_sec is None or meter_status != 'ok':
                _record_invalid("invalid_meter_status")
                self._set_pt_exam_feedback(
                    gen_id,
                    "当前测量结果无效，请确认表笔接在有效 PT 端子上。",
                    "red",
                )
                return
            terminal_ids_final = [sim.probe1_node, sim.probe2_node]
        elif origin in ("manual", "hardware"):
            if voltage_sec is None:
                raise ValueError("manual/hardware PT diff measurement requires voltage_sec")
        elif voltage_sec is not None and not isinstance(voltage_sec, (int, float)):
            raise ValueError("unknown PT diff measurement voltage_sec must be numeric or None")

        record = self._build_pt_diff_record(
            gen_id,
            key,
            origin=origin,
            voltage_sec=voltage_sec,
            instrument=instrument,
            instrument_id=instrument_id,
            terminal_ids=terminal_ids_final,
            channel_ids=channel_ids_final,
            timestamp=timestamp,
            raw=raw,
            raw_ref=raw_ref,
        )
        state.records[key] = record
        self._append_assessment_event(
            AssessmentEventType.MEASUREMENT_RECORDED,
            step=4,
            target=f'Gen{gen_id}',
            point=key,
            **self._measurement_event_payload(record),
        )
        if origin == "unknown":
            self._set_pt_exam_feedback(gen_id, f"Gen {gen_id} {key} 已导入未知来源记录，该记录不参与完成判定。", "#64748b")
            return
        done_count = sum(1 for value in state.records.values() if is_record_complete(value))
        if done_count == 9:
            msg = f"Gen {gen_id} 全部 9 组 PT 端子矢量压差已记录完成。"
        else:
            msg = f"Gen {gen_id} {key} 记录完成（{done_count}/9）：矢量压差 {voltage_sec:.2f} V。"
        self._set_pt_exam_feedback(gen_id, msg, "#006600")

    def get_pt_exam_steps(self, gen_id) -> list[tuple[str, bool]]:
        state = self._get_pt_exam_states()[gen_id]
        records = state.records
        sim = self._sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        gnd_ok = sim.grounding_mode == "小电阻接地"
        gen1_on_bus = gen1.breaker_position == BreakerPosition.WORKING and gen1.breaker_closed
        all_9_done = all(is_record_complete(value) for value in records.values())

        if gen_id == 1:
            steps = [
                ("1. 恢复中性点小电阻接地", gnd_ok),
                ("2. 将 Gen1 切至工作位置并合闸（建立母排参考）", gen1_on_bus),
                ("3. 确认 Gen2 断路器处于断开状态", not gen2.breaker_closed),
                ("4. 开启万用表并依次测量 PT1/PT2 各端子组合", sim.multimeter_mode),
                ("5. 记录全部 9 组矢量压差（AA/AB/AC/BA/BB/BC/CA/CB/CC）", all_9_done),
            ]
        else:
            gen2_running_not_closed = gen2.running and not gen2.breaker_closed
            steps = [
                ("1. 恢复中性点小电阻接地", gnd_ok),
                ("2. 确认 Gen1 已并入母排（作为母排参考）", gen1_on_bus),
                ("3. 启动 Gen2，保持断路器断开", gen2_running_not_closed),
                ("4. 开启万用表并依次测量 PT3/PT2 各端子组合", sim.multimeter_mode),
                ("5. 记录全部 9 组矢量压差（AA/AB/AC/BA/BB/BC/CA/CB/CC）", all_9_done),
            ]
        if state.completed:
            return [(text, True) for text, _ in steps]
        return steps

    # def get_pt_exam_close_blockers(self, gen_id):
    #     generator = self._get_generator_state(gen_id)
    #     records = self._get_pt_exam_states()[gen_id].records
    #     sim = self._sim_state
    #     blockers = []
    #     if not any(value is not None for value in records.values()):
    #         if sim.grounding_mode != "小电阻接地":
    #             blockers.append("未恢复中性点小电阻接地")
    #         if generator.breaker_position != BreakerPosition.WORKING or not generator.breaker_closed:
    #             blockers.append("未在工作位置并入母排完成 PT 二次端子测量")
    #         if not sim.multimeter_mode:
    #             blockers.append("未开启万用表")
    #     for key in (f'{g}{b}' for g in 'ABC' for b in 'ABC'):
    #         if records[key] is None:
    #             blockers.append(f"未记录 {key} 组合 PT 矢量压差")
    #     return blockers

    # def is_pt_exam_ready(self, gen_id):
    #     return self._get_pt_exam_states()[gen_id].completed

    # def finalize_pt_exam(self, gen_id):
    #     state = self._get_pt_exam_states()[gen_id]
    #     if not self._are_pt_exam_records_complete(gen_id):
    #         self._set_pt_exam_feedback(
    #             gen_id,
    #             '请先完成全部 9 组 PT 矢量压差记录（AA~CC），再点击“完成第四步测试”。',
    #             "red",
    #         )
    #         return
    #     state.completed = True
    #     self._set_pt_exam_feedback(
    #         gen_id,
    #         f"第四步【Gen{gen_id} PT 二次端子压差测试】已确认完成，后续操作将不再影响该步骤状态。",
    #         "#006600",
    #     )

    def finalize_all_pt_exams(self) -> None:
        """完成第四步：Gen1 和 Gen2 均须完成三相记录，才能锁定结果。"""
        gen1_ok = self._are_pt_exam_records_complete(1)
        gen2_ok = self._are_pt_exam_records_complete(2)
        if self._flow_mgr.is_assessment_mode() and not (gen1_ok and gen2_ok):
            self._set_pt_exam_feedback(1, "", "#444444")
            self._set_pt_exam_feedback(2, "", "#444444")
            return
        if not gen1_ok:
            self._set_pt_exam_feedback(
                1,
                'Gen1 尚未完成三相 PT 二次端子压差记录，请先切换至 Gen1 完成测量，再点击“完成第四步测试”。',
                'red',
            )
            if not gen2_ok:
                self._set_pt_exam_feedback(
                    2,
                    'Gen1 和 Gen2 均尚未完成三相 PT 二次端子压差记录。',
                    'red',
                )
            else:
                self._set_pt_exam_feedback(
                    2,
                    'Gen2 已完成，但 Gen1 尚未完成测量，请切换至 Gen1 完成后再点击完成。',
                    '#cc6600',
                )
            return
        if not gen2_ok:
            self._set_pt_exam_feedback(
                2,
                'Gen2 尚未完成三相 PT 二次端子压差记录，请先切换至 Gen2 完成测量，再点击“完成第四步测试”。',
                'red',
            )
            self._set_pt_exam_feedback(
                1,
                'Gen1 已完成，但 Gen2 尚未完成测量，请切换至 Gen2 完成后再点击完成。',
                '#cc6600',
            )
            return
        states = self._get_pt_exam_states()
        for gid in (1, 2):
            states[gid].completed = True
            self._set_pt_exam_feedback(
                gid,
                '第四步【PT 二次端子压差测试】Gen1 和 Gen2 均已确认完成，后续操作将不再影响该步骤状态。',
                '#006600',
            )

    def record_all_pt_measurements_quick(self) -> None:
        """
        快捷记录：跳过表笔放置检查，直接从物理引擎当前 PT 二次电压
        计算 Gen1 和 Gen2 全部 18 组压差并一次性写入记录。
        """
        states = self._get_pt_exam_states()
        if not (states[1].started and states[2].started):
            self._set_pt_exam_feedback(1, '请先点击"开始第四步测试"。', 'red')
            return
        if not self._is_loop_test_complete():
            self._set_pt_exam_feedback(1, '请先完成第一步【回路连通性测试】。', 'red')
            return
        if not self._is_pt_voltage_check_complete():
            self._set_pt_exam_feedback(1, '请先完成第二步【PT 单体线电压检查】。', 'red')
            return
        if not self._is_pt_phase_check_complete():
            self._set_pt_exam_feedback(1, '请先完成第三步【PT 相序检查】。', 'red')
            return

        sqrt3 = np.sqrt(3)
        physics: Any = self._get_physics()
        fc = self._sim_state.fault_config

        for gen_id in (1, 2):
            pt_name = 'PT1' if gen_id == 1 else 'PT3'
            gen_line = physics.pt1_v if gen_id == 1 else physics.pt3_v
            bus_line = physics.pt2_v
            gen_ph = gen_line / sqrt3
            bus_ph = bus_line / sqrt3

            for gen_term in ('A', 'B', 'C'):
                for bus_phase in ('A', 'B', 'C'):
                    key = f"{gen_term}{bus_phase}"

                    gen_phase_actual = physics._resolve_terminal_actual_phase(pt_name, gen_term)
                    bus_phase_actual = physics._resolve_terminal_actual_phase('PT2', bus_phase)
                    is_same_phase = gen_phase_actual == bus_phase_actual

                    e03_fault = (
                        fc.active and not fc.repaired
                        and fc.scenario_id == 'E03'
                        and gen_id == 2 and gen_term == 'A'
                    )

                    if e03_fault:
                        if is_same_phase:
                            meter_v = gen_ph + bus_ph
                        else:
                            meter_v = np.sqrt(max(0.0, gen_ph**2 + bus_ph**2 - gen_ph * bus_ph))
                    elif is_same_phase:
                        meter_v = abs(gen_ph - bus_ph)
                    else:
                        meter_v = np.sqrt(max(0.0, gen_ph**2 + bus_ph**2 + gen_ph * bus_ph))

                    if self._mark_fault_detected is not None and fc.active and not fc.repaired:
                        if e03_fault:
                            self._mark_fault_detected(
                                step=4,
                                source='pt_exam_quick_record',
                                target=pt_name,
                                point=f'{gen_term}-{bus_phase}',
                            )
                        elif fc.scenario_id == 'E04' and gen_id == 2 and is_same_phase:
                            self._mark_fault_detected(
                                step=4,
                                source='pt_exam_quick_record',
                                target=pt_name,
                                point=f'{gen_term}-{bus_phase}',
                            )
                        elif (
                            pt_name == 'PT1'
                            and fc.params.get('pt1_phase_order') is not None
                            and not is_same_phase
                        ):
                            self._mark_fault_detected(
                                step=4,
                                source='pt_exam_quick_record',
                                target=pt_name,
                                point=f'{gen_term}-{bus_phase}',
                            )
                        elif fc.params.get('pt2_sec_blackbox_order') is not None and not is_same_phase:
                            self._mark_fault_detected(
                                step=4,
                                source='pt_exam_quick_record',
                                target='PT2',
                                point=f'{pt_name}_{gen_term}-PT2_{bus_phase}',
                            )

                    states[gen_id].records[key] = self._build_pt_diff_record(
                        gen_id,
                        key,
                        origin="simulated",
                        voltage_sec=round(meter_v, 4),
                        instrument="multimeter",
                        instrument_id=None,
                        terminal_ids=None,
                        channel_ids=None,
                        timestamp=None,
                        raw=None,
                        raw_ref=None,
                    )
                    self._append_assessment_event(
                        AssessmentEventType.MEASUREMENT_RECORDED,
                        step=4,
                        target=f'Gen{gen_id}',
                        point=key,
                        **self._measurement_event_payload(states[gen_id].records[key]),
                    )

            self._set_pt_exam_feedback(
                gen_id,
                f"✅ Gen{gen_id} 快捷记录完成，全部 9 组压差已写入。",
                "#006600",
            )

    def _should_enforce_pt_exam_before_close(self) -> bool:
        return self._sim_state.grounding_mode != "断开"

    def is_pt_exam_recorded(self, gen_id) -> bool:
        """流程门禁：只有用户点击"完成第四步测试"后才返回 True。"""
        return self._get_pt_exam_states()[gen_id].completed

    def _are_pt_exam_records_complete(self, gen_id) -> bool:
        """内部辅助：全部 9 组是否已记录（用于 finalize 前置校验）。"""
        records = self._get_pt_exam_states()[gen_id].records
        return all(is_record_complete(records[key]) for key in (f'{g}{b}' for g in 'ABC' for b in 'ABC'))

    def _get_generator_state(self, gen_id) -> object:
        return self._sim_state.gen1 if gen_id == 1 else self._sim_state.gen2
