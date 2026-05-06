"""
services/pt_voltage_check_service.py
PT 单体线电压检查服务（第二步）

在进行 PT 相序检查之前，先用万用表逐一测量 PT1/PT2/PT3 各自的三相线电压（AB/BC/CA），
确认各 PT 输出电压量级一致（均约 100V AC），为后续相序比对提供基准验证。

测量方式：红表笔接同一 PT 的一相端子，黑表笔接同一 PT 的另一相端子。
"""

import time
from typing import Callable

from domain.enums import BreakerPosition
from domain.assessment import AssessmentEventType
from domain.measurement_id import pt_voltage_id
from domain.measurement_map import get_measurement_spec
from domain.measurement_schema import (
    is_record_complete,
    store_raw,
    validate_origin,
    validate_record,
)
from domain.test_states import PtVoltageCheckState

_ALL_KEYS = (
    'PT1_AB', 'PT1_BC', 'PT1_CA',
    'PT2_AB', 'PT2_BC', 'PT2_CA',
    'PT3_AB', 'PT3_BC', 'PT3_CA',
)

# 每个记录键对应的实际节点对
_KEY_TO_NODES = {
    'PT1_AB': ('PT1_A', 'PT1_B'), 'PT1_BC': ('PT1_B', 'PT1_C'), 'PT1_CA': ('PT1_C', 'PT1_A'),
    'PT2_AB': ('PT2_A', 'PT2_B'), 'PT2_BC': ('PT2_B', 'PT2_C'), 'PT2_CA': ('PT2_C', 'PT2_A'),
    'PT3_AB': ('PT3_A', 'PT3_B'), 'PT3_BC': ('PT3_B', 'PT3_C'), 'PT3_CA': ('PT3_C', 'PT3_A'),
}

# 反查：frozenset(节点对) → 记录键
_NODES_TO_KEY = {frozenset(v): k for k, v in _KEY_TO_NODES.items()}


class PtVoltageCheckService:
    """PT 单体线电压检查业务逻辑。"""

    def __init__(
        self,
        *,
        sim_state,
        flow_mgr,
        get_physics: Callable[[], object],
        get_pt_voltage_check_state: Callable[[], PtVoltageCheckState],
        set_pt_voltage_check_state: Callable[[PtVoltageCheckState], None],
        is_loop_test_complete: Callable[[], bool],
        append_assessment_event: Callable,
    ):
        self._sim_state = sim_state
        self._flow_mgr = flow_mgr
        self._get_physics = get_physics
        self._get_pt_voltage_check_state = get_pt_voltage_check_state
        self._set_pt_voltage_check_state = set_pt_voltage_check_state
        self._is_loop_test_complete = is_loop_test_complete
        self._append_assessment_event = append_assessment_event

    # ── 状态工厂 ──────────────────────────────────────────────────────────────
    def create_pt_voltage_check_state(self) -> PtVoltageCheckState:
        return PtVoltageCheckState()

    def start_pt_voltage_check(self) -> None:
        self._get_pt_voltage_check_state().started = True

    def stop_pt_voltage_check(self) -> None:
        self._get_pt_voltage_check_state().started = False

    def _set_feedback(self, message, color='#444444') -> None:
        state = self._get_pt_voltage_check_state()
        state.feedback = message
        state.feedback_color = color

    @staticmethod
    def _format_reading(record: dict) -> str:
        if record.get("quality") == "unknown":
            return "未判定"
        voltage_sec = record.get("voltage_sec")
        voltage_pri = record.get("voltage_pri")
        if voltage_sec is None:
            return "无效"
        if voltage_pri is None:
            return f"{voltage_sec:.1f} V"
        return f"一次侧 {voltage_pri:.0f} V / 二次侧 {voltage_sec:.1f} V"

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

    @staticmethod
    def _record_passed(record: dict | None) -> bool:
        return bool(is_record_complete(record) and record is not None and record.get("passed") is True)

    @staticmethod
    def _voltage_pri_kv(record: dict | None) -> float:
        return float((record or {}).get("voltage_pri") or 0.0) / 1000.0

    def _pt_ratio_for_record(self, pt_name: str) -> float:
        sim = self._sim_state
        return (
            sim.pt_gen_ratio if pt_name == 'PT1'
            else sim.pt3_ratio if pt_name == 'PT3'
            else sim.pt_bus_ratio
        )

    # ── 步骤列表 ──────────────────────────────────────────────────────────────
    def get_pt_voltage_check_steps(self) -> list[tuple[str, bool]]:
        sim = self._sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        state = self._get_pt_voltage_check_state()
        loop_done = self._is_loop_test_complete()
        gnd_ok = sim.grounding_mode == "小电阻接地"
        gen1_on_bus = (gen1.breaker_position == BreakerPosition.WORKING and gen1.breaker_closed)
        gen2_running_open = gen2.running and not gen2.breaker_closed
        rec = state.records

        pt1_done = all(is_record_complete(rec[k]) for k in ('PT1_AB', 'PT1_BC', 'PT1_CA'))
        pt2_done = all(is_record_complete(rec[k]) for k in ('PT2_AB', 'PT2_BC', 'PT2_CA'))
        pt3_done = all(is_record_complete(rec[k]) for k in ('PT3_AB', 'PT3_BC', 'PT3_CA'))

        steps = [
            ("1. 前提：第一步回路连通性测试已完成", loop_done),
            ("2. 恢复中性点小电阻接地", gnd_ok),
            ("3. 参数核对：在停机状态下，确认控制器内已正确设置各 PT 变比（绝不可在运行中修改）",
             sim.pt_gen_ratio > 1.0 and sim.pt_bus_ratio > 1.0),
            ("4. 启动 Gen1，确认其建压并直接合闸并入无压母排（提供 PT1/PT2 参考电压）", gen1_on_bus),
            ("5. 启动 Gen2，控制器自动进入同期追赶模式，保持断路器断开（提供 PT3 参考电压）", gen2_running_open),
            ("6. 开启万用表，在母排拓扑页测量同一 PT 的两相端子", sim.multimeter_mode),
            ("7. 记录 PT1 三相线电压（AB/BC/CA）", pt1_done),
            ("8. 记录 PT2 三相线电压（AB/BC/CA）", pt2_done),
            ("9. 记录 PT3 三相线电压（AB/BC/CA）", pt3_done),
        ]
        if state.completed:
            return [(text, True) for text, _ in steps]
        return steps

    # ── 逐项记录 ──────────────────────────────────────────────────────────────
    def record_pt_voltage_measurement(
        self,
        pt_name: str,
        phase_pair: str,
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
        记录 pt_name（'PT1'/'PT2'/'PT3'）的 phase_pair（'AB'/'BC'/'CA'）线电压。
        仅当 started=True 时对 records 进行写入。
        """
        validate_origin(origin)
        pt_name = pt_name.upper()
        phase_pair = phase_pair.upper()
        key = f"{pt_name}_{phase_pair}"
        if key not in _ALL_KEYS:
            return
        measurement_id = pt_voltage_id(pt_name, phase_pair)
        spec = get_measurement_spec(measurement_id) or {}
        terminal_ids_final = list(terminal_ids or spec.get("terminal_ids", []))
        channel_ids_final = list(channel_ids or [])
        sim = self._sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        state = self._get_pt_voltage_check_state()

        def _record_invalid(reason) -> None:
            self._append_assessment_event(
                AssessmentEventType.MEASUREMENT_INVALID,
                step=2,
                target=pt_name,
                point=phase_pair,
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
            raise ValueError("simulated PT voltage measurement reads voltage_sec from physics")
        if origin == "hardware":
            if timestamp is None:
                raise ValueError("hardware measurement requires timestamp")
            if not instrument_id:
                raise ValueError("hardware measurement requires instrument_id")

        if origin != "unknown" and not state.started:
            _record_invalid("step_not_started")
            self._set_feedback("请先点击「开始第二步测试」，再进行测量记录。", "red")
            return

        if origin != "unknown" and not self._is_loop_test_complete():
            _record_invalid("loop_test_incomplete")
            self._set_feedback("请先完成第一步【回路连通性测试】，再进行 PT 线电压检查。", "red")
            return
        if origin != "unknown" and sim.grounding_mode != "小电阻接地":
            _record_invalid("grounding_not_ready")
            self._set_feedback("请先恢复中性点小电阻接地，再进行 PT 线电压检查。", "red")
            return
        if origin != "unknown" and (gen1.breaker_position != BreakerPosition.WORKING or not gen1.breaker_closed):
            _record_invalid("gen1_not_on_bus")
            self._set_feedback("请先确认 Gen1 已并入母排（工作位+合闸），作为 PT1/PT2 参考电压。", "red")
            return
        if origin != "unknown" and pt_name == 'PT3':
            if not gen2.running:
                _record_invalid("gen2_not_running")
                self._set_feedback("测量 PT3 线电压时，请先启动 Gen2（保持断路器断开）。", "red")
                return
            if gen2.breaker_closed:
                _record_invalid("gen2_breaker_closed")
                self._set_feedback("测量 PT3 线电压时，Gen2 断路器应保持断开状态。", "red")
                return
        if origin == "simulated" and not sim.multimeter_mode:
            _record_invalid("multimeter_disabled")
            self._set_feedback("请先开启万用表。", "red")
            return

        # 校验表笔是否放在正确的节点对上
        meter_status = "ok"
        if origin == "simulated":
            n1, n2 = sim.probe1_node, sim.probe2_node
            if not n1 or not n2:
                _record_invalid("probe_missing")
                self._set_feedback(
                    f"请先在母排拓扑页将表笔放在 {pt_name} 的两相端子上，再点击记录。", "red")
                return

            expected_nodes = frozenset(_KEY_TO_NODES[key])
            actual_nodes = frozenset({n1, n2})
            if actual_nodes != expected_nodes:
                _record_invalid("probe_pair_mismatch")
                n1_expect, n2_expect = _KEY_TO_NODES[key]
                self._set_feedback(
                    f"当前表笔不在 {n1_expect} 与 {n2_expect} 上，请重新放置后再记录。", "red")
                return

            physics = self._get_physics()
            voltage_sec = getattr(physics, 'meter_voltage', None)   # 二次侧 ≈100V
            meter_status = getattr(physics, 'meter_status', 'idle')
            if voltage_sec is None or meter_status not in ('ok', 'danger'):
                _record_invalid("invalid_meter_status")
                self._set_feedback("当前测量结果无效，请确认表笔接在同一 PT 的两相端子上。", "red")
                return
            terminal_ids_final = [n1, n2]
        elif origin in ("manual", "hardware"):
            if voltage_sec is None:
                raise ValueError("manual/hardware PT voltage measurement requires voltage_sec")
        elif voltage_sec is not None and not isinstance(voltage_sec, (int, float)):
            raise ValueError("unknown PT voltage measurement voltage_sec must be numeric or None")

        # 换算回一次侧线电压（教学中关心的实际电压量）
        _pt_name = pt_name
        _pt_ratio = self._pt_ratio_for_record(_pt_name)
        # E04：一次侧换算使用额定变比，使学员能发现二次侧读数与额定不符
        _fc = sim.fault_config
        if (_pt_name == 'PT3' and _fc.active and not _fc.repaired
                and _fc.scenario_id == 'E04'):
            _pt_ratio = 11000.0 / 193.0
        primary_v = None if voltage_sec is None else float(voltage_sec) * _pt_ratio
        in_range = primary_v is not None and 8925.0 <= primary_v <= 12075.0
        quality = "unknown" if origin == "unknown" else ("ok" if in_range else "out_of_range")
        passed = None if origin == "unknown" else bool(in_range)

        record: dict = {
            "measurement_id": measurement_id,
            "value": primary_v,
            "unit": "V",
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
            "voltage_sec": None if voltage_sec is None else float(voltage_sec),
            "voltage_pri": primary_v,
            "pt_ratio": _pt_ratio,
        }
        if raw_ref is None:
            store_raw(record, raw)
        else:
            record["raw"] = raw
        record["reading"] = self._format_reading(record)
        validate_record(record)
        state.records[key] = record

        self._append_assessment_event(
            AssessmentEventType.MEASUREMENT_RECORDED,
            step=2,
            target=pt_name,
            point=phase_pair,
            **self._measurement_event_payload(record),
        )
        if origin == "unknown":
            self._set_feedback(f"{key} 已导入未知来源记录，该记录不参与完成判定。", "#64748b")
            return
        all_rec = all(is_record_complete(state.records[k]) for k in _ALL_KEYS)
        # 额定二次侧线电压 = 一次侧额定（10500V）/ 变比
        _nominal_sec = 10500.0 / _pt_ratio
        # 一次侧额定线电压 10500V，±15% 容差由二次侧 status 已判定
        if meter_status != 'ok' or quality == "out_of_range":
            rec_color = "#cc6600"
            rec_note = (f"（⚠️ 一次侧测量值 {primary_v:.0f} V，"
                        f"二次侧 {voltage_sec:.1f} V，偏离额定 {_nominal_sec:.0f} V，请调整后重新测量）")
        else:
            rec_color = "#006600"
            rec_note = f"（一次侧 {primary_v:.0f} V ≈ 10500 V，正常）"

        if all_rec:
            msg = f"PT1/PT2/PT3 三组线电压已全部记录完成{rec_note}，请点击「完成第二步测试」确认。"
        else:
            msg = f"{key} 线电压已记录{rec_note}，请继续测量其余项目。"
        self._set_feedback(msg, rec_color)

    def _get_probe_key(self) -> str | None:
        """根据当前表笔位置返回对应记录键，未对准返回 None。"""
        sim = self._sim_state
        n1, n2 = sim.probe1_node, sim.probe2_node
        if not n1 or not n2:
            return None
        return _NODES_TO_KEY.get(frozenset({n1, n2}))

    def reset_pt_voltage_check(self) -> None:
        self._set_pt_voltage_check_state(self.create_pt_voltage_check_state())

    def is_pt_voltage_check_complete(self) -> bool:
        """流程门禁：只有用户点击「完成第二步测试」后才返回 True。"""
        return self._get_pt_voltage_check_state().completed

    def _are_records_complete(self) -> bool:
        """内部辅助：九项是否已全部记录且均在合格范围内（用于 finalize 前置校验）。
        voltage_pri 字段存一次侧值（V），额定 10500V，±15% → [8925, 12075V]。
        """
        records = self._get_pt_voltage_check_state().records
        return all(
            self._record_passed(records[k])
            for k in _ALL_KEYS
        )

    def _are_all_records_filled(self) -> bool:
        """九项是否已全部测量（无论是否在合格范围内）。"""
        records = self._get_pt_voltage_check_state().records
        return all(is_record_complete(records[k]) for k in _ALL_KEYS)

    def finalize_pt_voltage_check(self) -> None:
        state = self._get_pt_voltage_check_state()
        fc = self._sim_state.fault_config
        fault_training = (
            fc.active and fc.detected and not fc.repaired
            and self._flow_mgr.can_advance_with_fault()
        )

        if fault_training:
            # 当前流程策略允许带异常完成，但仍要求本步测量项齐全
            if not self._are_all_records_filled():
                records = state.records
                missing = [k for k in _ALL_KEYS if not is_record_complete(records[k])]
                self._set_feedback(
                    f'以下项目尚未完成记录：{", ".join(missing)}。请补充测量后再点击「完成第二步测试」。',
                    "red")
                return
            state.completed = True
            state.started = False
            records = state.records
            bad = [k for k in _ALL_KEYS if not self._record_passed(records[k])]
            if bad:
                bad_str = "、".join(
                    f"{k}={self._voltage_pri_kv(records[k]):.2f} kV" for k in bad)
                self._set_feedback(
                    f"第二步完成（发现异常）：{bad_str} 电压偏离额定范围，"
                    f"已记录故障证据，请继续后续步骤收集更多数据，将在第五步前统一检修。",
                    "#92400e")
            else:
                self._set_feedback(
                    "第二步【PT 单体线电压检查】已确认完成，后续操作将不再影响该步骤状态。",
                    "#006600")
        else:
            # 当前流程策略要求本步全部通过后才能完成
            if not self._are_records_complete():
                records = state.records
                missing = [k for k in _ALL_KEYS if not is_record_complete(records[k])]
                bad = [k for k in _ALL_KEYS
                       if is_record_complete(records[k])
                       and not self._record_passed(records[k])]
                if missing:
                    self._set_feedback(
                        f'以下项目尚未完成记录：{", ".join(missing)}。请补充测量后再点击「完成第二步测试」。',
                        "red")
                else:
                    bad_str = "、".join(
                        f"{k}={self._voltage_pri_kv(records[k]):.2f} kV" for k in bad)
                    self._set_feedback(
                        f'以下线电压偏离目标 10.5 kV（需在 8.925～12.075 kV 内）：{bad_str}。'
                        '请调整发电机输出电压，使各 PT 一次侧线电压均约为 10.5 kV，再点击「完成第二步测试」。',
                        "red")
                return
            state.completed = True
            state.started = False
            self._set_feedback(
                "第二步【PT 单体线电压检查】已确认完成，后续操作将不再影响该步骤状态。",
                "#006600")

    def get_pt_voltage_check_blockers(self) -> list[str]:
        return [text for text, done in self.get_pt_voltage_check_steps() if not done]
