from __future__ import annotations

from domain.constants import GRID_AMP, GRID_FREQ
from domain.enums import BreakerPosition
from domain.test_states import SyncTestState
from services.flow_mode_manager import FlowModeManager
from services.sync_test_service import SyncTestService
from tests.support.stubs import make_sim_state


class _FaultManagerStub:
    def has_unrepaired_wiring_fault(self):
        return False


def _build_service():
    sim = make_sim_state()
    state = SyncTestState(round1_done=True, round2_done=True, started=True)
    service = SyncTestService(
        sim_state=sim,
        flow_mgr=FlowModeManager(),
        fault_mgr=_FaultManagerStub(),
        get_physics=lambda: None,
        get_sync_test_state=lambda: state,
        set_sync_test_state=lambda new_state: None,
        is_loop_test_complete=lambda: True,
        is_pt_voltage_check_complete=lambda: True,
        is_pt_phase_check_complete=lambda: True,
        is_pt_exam_recorded=lambda gen_id: True,
    )
    return sim, state, service


def test_finalize_sync_test_leaves_generators_in_stable_parallel_auto_state():
    sim, state, service = _build_service()
    sim.remote_start_signal = False
    sim.gen1.running = False
    sim.gen1.breaker_closed = False
    sim.gen1.breaker_position = BreakerPosition.DISCONNECTED
    sim.gen1.actual_amp = 0.0
    sim.gen2.running = True
    sim.gen2.breaker_closed = True
    sim.gen2.breaker_position = BreakerPosition.WORKING

    service.finalize_sync_test()

    assert state.completed is True
    assert sim.remote_start_signal is True
    for gen in (sim.gen1, sim.gen2):
        assert gen.mode == "auto"
        assert gen.running is True
        assert gen.breaker_position == BreakerPosition.WORKING
        assert gen.breaker_closed is True
        assert gen.cmd_close is False
        assert gen.freq == GRID_FREQ
        assert gen.amp == GRID_AMP
        assert gen.actual_amp == GRID_AMP
        assert gen.phase_deg == 0.0
