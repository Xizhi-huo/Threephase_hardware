# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
import subprocess
import sys

def install_package(package_name):
    """自动安装指定的Python包到当前运行环境"""
    subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])

# 需要安装的依赖包列表
required_packages = [
    "numpy",
    "matplotlib",
    "pandas",
    "scipy"
]

# 自动安装所有依赖
for pkg in required_packages:
    install_package(pkg)

# 安装完成后再导入所有库
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import warnings
import pandas as pd
from datetime import datetime
import scipy.signal as signal
from scipy.linalg import inv

# 你的业务代码可以从这里开始写



# 屏蔽数值计算警告
warnings.filterwarnings('ignore', category=RuntimeWarning)

# 忽略不必要的matplotlib警告
warnings.filterwarnings('ignore', category=UserWarning)

# 设置 matplotlib 后端和中文显示
plt.switch_backend('TkAgg')
plt.rcParams['font.family'] = ['Microsoft YaHei']  # 微软雅黑
plt.rcParams['axes.unicode_minus'] = False        # 负号正常显示

# ====================== 1. 发电机组参数配置（核心）=======================
DEFAULTS = {
    # --- Sim / Load ---
    "t_end": 70,         # 仿真时间50秒
    "dt": 0.001,         # 时间步长1ms
    "period": 2,         # 负载周期10秒
    "t1": 1,              # t1=5秒
    "load_pu1": 0.95,      # 负载1值
    "load_pu2": 0.85,        # 负载2值
    "load_pu": 1.0,       # CSV负载缩放因子
    "P_base_MW": 2.0,     # 负载基准值2MW

    # --- Base ---
    "rpm_base": 1500.0,   # 目标转速
    "V_base_kV": 10.5,

    # --- Speed loop (ECU 调速) - 极速恢复参数 ---
    "H": 1.0,             # 惯性常数（进一步减小=最快响应）
    "D_pu": 10,          # 阻尼系数（增大=抑制超调，平衡快速响应）
    "Kp_gov": 1.0,       # 比例增益（大幅增大=极速响应）
    "Ki_gov": 10.0,       # 积分增益（大幅增大=快速消除静差）
    "T_gov": 0.02,       # 调速器时间常数（极小=几乎无滞后）
    "T_act": 0.02,        # 执行器时间常数（极小=油门瞬间响应）
    "tau_act": 0.02,     # 执行器延迟（极小）
    "T_tc": 0.50,         # 涡轮滞后（极小=动力瞬间输出）
    "K_fuel": 2,        # 燃油增益（大幅增大=燃油快速供给）
    "T_fuel": 0.2,       # 燃油时间常数（极小）
    "T_spd": 0.02,       # 转速传感器延迟（极小=无检测滞后）

    # --- Voltage loop (PMG + AVR) ---
    "Kp_avr": 30.0,
    "Ki_avr": 150.0,
    "T_avr": 0.02,
    "T1": 0.05,
    "T2": 0.01,
    "T_exc": 0.40,
    "K_exc": 1.0,
    "T_gen": 0.15,
    "K_gen": 1.0,
    "T_vs": 0.01,

    # --- Load -> voltage dip model ---
    "K_LV": 0.12,
    "T_LV": 0.08,

    # --- Limits ---
    "gov_min": 0.0,
    "gov_max": 2.5,       # 大幅增大调速器上限（提供充足调节余量）
    "efd_min": 0.0,
    "efd_max": 2.5,
    
    # --- Voltage-based speed control ---
    "enable_voltage_speed_control": True,  # 是否启用V/Hz电压下降控制
    "frequency_deadband": 1.0,  # 频率死区（Hz），在此范围内电压不主动下降
    "voltage_drop_per_hz": 7.0,  # 每1Hz频率偏差的电压下降百分比（%）
}

# ====================== 2. HESS混合储能系统参数 ========================
class HESS_Params:
    def __init__(self):
        # ---------------- 电网基础参数（适配发电机组）----------------
        self.H = 6.0          # 系统惯性常数
        self.D = 3.0          # 频率相关阻尼系数
        self.R_droop = 0.05   # 调压器下垂率
        self.T_g = 0.3        # 调压器时间常数 (s)
        self.f_nom = 60.0     # 电网额定频率 (Hz)
        
        # ---------------- HESS储能器件参数 ----------------
        self.P_ESS_max = 30.0  # 电池储能额定功率 (MW)
        self.P_SC_max = 20.0   # 超级电容额定功率 (MW)
        self.R_ESS_max = 15.0  # 电池最大爬坡率 (MW/s)
        self.R_SC_max = 80.0   # 超级电容最大爬坡率 (MW/s)
        self.tau_ESS = 0.25    # 电池时间常数 (s)
        self.tau_SC = 0.003    # 超级电容时间常数 (s)
        self.eta = 0.97        # 充放电效率
        self.f_c = 0.5         # HPF截止频率 (Hz)
        self.f_d = 3.0         # 微分响应频率 (Hz)
        
        # ---------------- 能量存储参数 ----------------
        self.ESS_max_time = 15 * 60  # BESS最大放电时间（秒）
        self.SC_max_time = 60  # SC最大放电时间（秒）
        self.ESS_initial_soc = 0.8  # BESS初始SOC
        self.SC_initial_soc = 0.8  # SC初始SOC
        self.ESS_min_soc = 0.2  # BESS最小允许SOC
        self.SC_min_soc = 0.2  # SC最小允许SOC
        
        # 计算存储能量（MW·s）
        self.ESS_energy = self.P_ESS_max * self.ESS_max_time
        self.SC_energy = self.P_SC_max * self.SC_max_time
        
        # ---------------- 控制器参数 ----------------
        self.k_p = 1.5         # SC比例增益
        self.k_d = 0.3         # SC微分增益
        self.k_I = 0.8         # BESS漏积分增益
        self.T_leak = 10.0     # BESS泄漏时间常数 (s)
        self.k_RC = 0.6        # 重复控制增益
        self.omega_RC = 2*np.pi*0.05  # 重复控制目标频率 (rad/s)
        self.k_RK = 0.4        # 爬坡跟踪增益
        self.k_q = 0.1         # SOC偏置修正增益
        self.T_q = 50.0        # SOC偏置时间常数 (s)
        self.s_ref = 3.0       # 爬坡激活阈值
        self.A_ref = 15.0      # 加加速度抑制阈值
        
        # ---------------- 充电限制参数 ----------------
        self.light_load_threshold = 0.3  # 轻载阈值：负载 < 基线功率×30%
        self.ess_charge_stop_soc = 0.80  # BESS充电停止SOC阈值：>80%停止充电
        self.sc_charge_stop_soc = 0.80   # SC充电停止SOC阈值：>80%停止充电
        
        # ---------------- 仿真参数 ----------------
        self.T_s = 0.001       # 采样时间1ms
        self.t_sim = None      # 仿真时长 (s)
        self.N = None          # 仿真总步数

# ====================== 3. 卡尔曼滤波器 ========================
class KalmanFilter:
    def __init__(self, T_s, Q=1e-4, R=1e-2):
        self.T_s = T_s
        self.Q = Q * np.diag([1, 1])
        self.R = R
        self.A = np.array([[1, T_s], [0, 0.99]])
        self.C = np.array([[1, 0]])
        self.P = np.eye(2)
        self.x_est = np.array([0, 0])

    def update(self, z):
        x_pred = self.A @ self.x_est
        P_pred = self.A @ self.P @ self.A.T + self.Q
        
        K = P_pred @ self.C.T @ inv(self.C @ P_pred @ self.C.T + self.R)
        self.x_est = x_pred + K @ (z - self.C @ x_pred)
        self.P = (np.eye(2) - K @ self.C) @ P_pred
        
        return self.x_est[0], self.x_est[1]

# ====================== 4. HPF高通滤波器 ========================
def hpf_filter(signal_in, f_c, T_s):
    omega_c = 2 * np.pi * f_c
    b = [1, 0]
    a = [1, omega_c]
    zi = signal.lfilter_zi(b, a)
    signal_out, _ = signal.lfilter(b, a, signal_in, zi=zi*signal_in[0])
    return signal_out

# ====================== 5. HESS核心控制器 ========================
class HESS_Controller:
    def __init__(self, params):
        self.params = params
        self.kf = KalmanFilter(params.T_s)
        
        # 储能状态初始化
        self.SOC_ESS = params.ESS_initial_soc  # 使用新的初始SOC值
        self.SOC_SC = params.SC_initial_soc    # 使用新的初始SOC值
        self.P_ESS = 0.0
        self.P_SC = 0.0
        self.q_ESS = 0.0
        self.q_SC = 0.0
        
        # 历史误差
        self.eps_ESS_prev = 0.0
        self.eps_SC_prev = 0.0
        
        # 滤波器状态
        self.P_ESS_filtered = 0.0
        self.P_SC_filtered = 0.0
        
        # 负载突变检测和预响应机制
        self.P_DC_prev = 0.0
        self.load_ramp_prev = 0.0
        self.mutant_detected = False
        
        # 充电限制状态记录
        self.ess_charge_limited = False
        self.sc_charge_limited = False
        self.limited_time = 0
        self.limited_steps = 0
        self.ess_limited_time = 0
        self.sc_limited_time = 0
        
        # 负载历史缓冲区（200秒）
        self.load_buffer = []
        self.max_buffer_size = int(200 / params.T_s)  # 200秒的采样点数

    def sigmoid(self, x):
        return 1 / (1 + np.exp(-x))
    
    def get_omega_ramp(self, R_DC_est):
        gamma_ramp = self.sigmoid(abs(R_DC_est) / self.params.s_ref)
        gamma_jerk = 1 / (1 + abs(R_DC_est) / self.params.A_ref)
        return gamma_ramp * gamma_jerk
    
    def update_soc_bias(self):
        self.q_ESS += self.params.T_s * (-self.q_ESS/self.params.T_q - self.params.k_q*(self.SOC_ESS-0.5))
        self.q_SC += self.params.T_s * (-self.q_SC/self.params.T_q - self.params.k_q*(self.SOC_SC-0.5))
        
        self.q_ESS = np.clip(self.q_ESS, -self.params.P_ESS_max*0.1, self.params.P_ESS_max*0.1)
        self.q_SC = np.clip(self.q_SC, -self.params.P_SC_max*0.1, self.params.P_SC_max*0.1)
        
        return self.q_ESS, self.q_SC
    
    def power_limiter(self, P_cmd, P_prev, P_max, R_max):
        P_ramp_lim = np.clip(P_cmd, P_prev - R_max*self.params.T_s, P_prev + R_max*self.params.T_s)
        P_lim = np.clip(P_ramp_lim, -P_max, P_max)
        return P_lim
    
    def low_pass_filter(self, input_signal, filtered_signal_prev, tau, T_s):
        alpha = T_s / (tau + T_s)
        filtered_signal = alpha * input_signal + (1 - alpha) * filtered_signal_prev
        return filtered_signal
    
    def detect_load_mutant(self, P_DC):
        load_ramp = (P_DC - self.P_DC_prev) / self.params.T_s if self.params.T_s > 0 else 0
        jerk = (load_ramp - self.load_ramp_prev) / self.params.T_s if self.params.T_s > 0 else 0
        
        if abs(load_ramp) > 50 or abs(jerk) > 1000:
            self.mutant_detected = True
        else:
            if self.mutant_detected:
                self.mutant_timer = getattr(self, 'mutant_timer', 0) + 1
                if self.mutant_timer > 20:
                    self.mutant_detected = False
                    self.mutant_timer = 0
        
        self.P_DC_prev = P_DC
        self.load_ramp_prev = load_ramp
        
        return self.mutant_detected
    
    def is_light_load(self, P_DC, P_DC_0):
        return P_DC < P_DC_0 * self.params.light_load_threshold
    
    def limit_ess_charge(self, P_ESS_cmd):
        if self.is_light_load_flag and P_ESS_cmd < 0 and self.SOC_ESS > self.params.ess_charge_stop_soc:
            self.ess_charge_limited = True
            self.ess_limited_time += self.params.T_s
            self.limited_time += self.params.T_s
            self.limited_steps += 1
            return 0.0
        else:
            self.ess_charge_limited = False
            return P_ESS_cmd
    
    def limit_sc_charge(self, P_SC_cmd):
        if self.is_light_load_flag and P_SC_cmd < 0 and self.SOC_SC > self.params.sc_charge_stop_soc:
            self.sc_charge_limited = True
            self.sc_limited_time += self.params.T_s
            self.limited_time += self.params.T_s
            self.limited_steps += 1
            return 0.0
        else:
            self.sc_charge_limited = False
            return P_SC_cmd
    
    def step(self, P_DC, P_DC_0):
        params = self.params
        
        # 1. 初始化P_DC_prev为当前负载值，避免第一次计算时的异常
        if self.P_DC_prev == 0.0:
            self.P_DC_prev = P_DC
        
        # 2. 初始化实时负载平均值计算所需的变量
        if not hasattr(self, 'load_buffer'):
            self.load_buffer = []  # 存储负载数据点的缓冲区
        if not hasattr(self, 'current_time'):
            self.current_time = 0.0  # 当前仿真时间
        if not hasattr(self, 'last_sample_time'):
            self.last_sample_time = 0.0  # 上次采样时间
        
        # 3. 更新当前时间
        self.current_time += params.T_s
        
        # 4. 每0.1秒取一个原始负载值
        if self.current_time - self.last_sample_time >= 0.1:
            self.load_buffer.append(P_DC)
            self.last_sample_time = self.current_time
            # 保持缓冲区大小不超过500个点
            max_buffer_size = 500
            if len(self.load_buffer) > max_buffer_size:
                self.load_buffer.pop(0)
        
        # 5. 计算实时平均负载
        if len(self.load_buffer) > 0:
            P_load_average = np.mean(self.load_buffer)
        else:
            P_load_average = P_DC  # 如果缓冲区为空，使用当前负载值
        
        # 6. 计算原始负载功率和实时平均负载的差值
        # 差值 = 原始负载 - 实时平均负载
        load_delta = P_DC - P_load_average
        
        # 7. 根据差值确定HESS输出功率
        # 差值为正：BESS和SC放电（功率为正），补充功率
        # 差值为负：BESS和SC充电（功率为负），吸收多余功率
        required_storage_power = load_delta
        
        # 检测负载突变
        is_mutant = self.detect_load_mutant(P_DC)
        
        # 记录轻载状态（基于实时负载平均值）
        self.is_light_load_flag = self.is_light_load(P_DC, P_load_average)
        
        # 6. 卡尔曼滤波估计爬坡率
        _, R_DC_est = self.kf.update(required_storage_power)
        
        # 7. HPF分频 - 实现BESS反应慢，SC反应快的要求
        # SC处理高频分量（反应快），BESS处理低频分量（反应慢）
        required_hpf = hpf_filter(np.array([required_storage_power]), params.f_c, params.T_s)[0]
        required_lpf = required_storage_power - required_hpf
        
        # 8. 超级电容参考指令（反应快）
        omega_ramp = self.get_omega_ramp(R_DC_est)
        
        if is_mutant:
            # 负载突变时，SC快速响应
            P_SC_ref0 = required_hpf * 3
        else:
            P_SC_ref0 = required_hpf
            
        P_SC_ref1 = P_SC_ref0 + omega_ramp * params.tau_SC * R_DC_est
        q_SC, q_ESS = self.update_soc_bias()
        P_SC_ref = P_SC_ref1 + q_SC
        
        # 9. 电池参考指令（反应慢）
        P_ESS_ref0 = required_lpf
        P_ESS_ref = P_ESS_ref0 + q_ESS
        
        # 8. 超级电容控制器
        eps_SC = P_SC_ref - self.P_SC
        omega_d = 2*np.pi*params.f_d
        D_term = (omega_d * (eps_SC - self.eps_SC_prev)) / (params.T_s * omega_d + 1)
        PD_out = params.k_p * eps_SC + params.k_d * D_term
        
        FF_SC = (1/params.T_s + 1/params.tau_SC) * (P_SC_ref - self.P_SC)
        R_SC_est = (self.P_SC - self.eps_SC_prev) / params.T_s if params.T_s>0 else 0
        RK_out = params.k_RK * (R_DC_est - R_SC_est)
        
        U_SC = PD_out + FF_SC + RK_out
        P_SC_cmd = U_SC / (params.tau_SC/params.T_s + 1)
        
        # 应用SC充电限制
        P_SC_cmd_limited = self.limit_sc_charge(P_SC_cmd)
        self.P_SC = self.power_limiter(P_SC_cmd_limited, self.P_SC, params.P_SC_max, params.R_SC_max)
        self.P_SC_filtered = self.low_pass_filter(self.P_SC, self.P_SC_filtered, 0.01, params.T_s)
        
        # 9. 电池控制器
        eps_ESS = P_ESS_ref - self.P_ESS
        I_out = self.eps_ESS_prev + params.T_s * (params.k_I * eps_ESS - self.eps_ESS_prev/params.T_leak)
        RC_out = params.k_RC * params.omega_RC * eps_ESS / (params.omega_RC + 1/params.T_s)
        FF_ESS = (1/params.T_s + 1/params.tau_ESS) * (P_ESS_ref - self.P_ESS)
        U_ESS = I_out + RC_out + FF_ESS
        P_ESS_cmd = U_ESS / (params.tau_ESS/params.T_s + 1)
        
        # 应用BESS充电限制
        P_ESS_cmd_limited = self.limit_ess_charge(P_ESS_cmd)
        self.P_ESS = self.power_limiter(P_ESS_cmd_limited, self.P_ESS, params.P_ESS_max, params.R_ESS_max)
        self.P_ESS_filtered = self.low_pass_filter(self.P_ESS, self.P_ESS_filtered, 0.05, params.T_s)
        
        # 10. SOC更新（按照电池储存能量计算）
        if params.ESS_energy > 0:
            # 计算能量变化（MW·s）
            energy_change_ESS = self.P_ESS_filtered * params.T_s
            # 更新SOC
            self.SOC_ESS -= energy_change_ESS / params.ESS_energy
            # 限制SOC范围
            self.SOC_ESS = max(params.ESS_min_soc, min(1.0, self.SOC_ESS))
        else:
            self.SOC_ESS = params.ESS_initial_soc  # 禁用时固定SOC为初始值

        # SC SOC更新（按照储存能量计算）
        if params.SC_energy > 0:
            # 计算能量变化（MW·s）
            energy_change_SC = self.P_SC_filtered * params.T_s
            # 更新SOC
            self.SOC_SC -= energy_change_SC / params.SC_energy
            # 限制SOC范围
            self.SOC_SC = max(params.SC_min_soc, min(1.0, self.SOC_SC))
        else:
            self.SOC_SC = params.SC_initial_soc  # 禁用时固定SOC为初始值

        # 11. 状态更新
        self.eps_ESS_prev = eps_ESS
        self.eps_SC_prev = eps_SC

        # 12. 计算HESS总输出功率
        # 保留控制器的动态响应逻辑，确保平滑过渡
        P_storage_total = self.P_ESS_filtered + self.P_SC_filtered
        
        # 计算目标HESS输出功率与实际输出功率的差值
        storage_delta = required_storage_power - P_storage_total
        
        # 缓慢调整HESS输出功率，使其逐渐接近目标值
        # 这样可以保持平滑的动态响应
        adjustment_rate = 0.1  # 调整速率，控制响应速度
        P_storage_total += storage_delta * adjustment_rate
        
        # 按照BESS反应慢，SC反应快的原则重新分配功率
        # SC处理高频分量（反应快），BESS处理低频分量（反应慢）
        self.P_ESS_filtered = required_lpf + storage_delta * adjustment_rate * 0.3  # BESS反应慢，调整幅度小
        self.P_SC_filtered = required_hpf + storage_delta * adjustment_rate * 0.7  # SC反应快，调整幅度大
        
        # 确保功率限制
        self.P_ESS_filtered = np.clip(self.P_ESS_filtered, -params.P_ESS_max, params.P_ESS_max)
        self.P_SC_filtered = np.clip(self.P_SC_filtered, -params.P_SC_max, params.P_SC_max)
        
        # 重新计算总输出功率
        P_storage_total = self.P_ESS_filtered + self.P_SC_filtered
        
        # 13. 计算机组功率并确保不小于零
        # 机组功率 = 原始负载 - BESS功率 - SC功率
        P_gen = P_DC - P_storage_total
        
        # 确保机组功率不小于零
        if P_gen < 0:
            # 如果机组功率小于零，调整HESS输出功率
            P_storage_total = P_DC  # 使机组功率为零
            # 重新分配功率到BESS和SC，保持SC反应快的特性
            # SC处理大部分功率，BESS处理小部分功率
            self.P_ESS_filtered = P_storage_total * 0.3  # 30%分配给BESS（反应慢）
            self.P_SC_filtered = P_storage_total * 0.7  # 70%分配给SC（反应快）
            P_storage_total = self.P_ESS_filtered + self.P_SC_filtered

        # 返回HESS总输出功率（用于平抑机组负载）
        return (P_storage_total, self.P_ESS_filtered, self.P_SC_filtered, 
                self.SOC_ESS, self.SOC_SC, self.ess_charge_limited, self.sc_charge_limited)
# ====================== 6. 发电机组+HESS联合仿真核心函数 ========================
def simulate_dg_hess_ode(p, hess_params, csv_load_data=None):
    t_end = p["t_end"]
    dt = p["dt"]

    rpm_base = p["rpm_base"]
    V_base_kV = p["V_base_kV"]

    # 发电机组参数读取
    H = p["H"]
    D_pu = p["D_pu"]
    Kp_gov = p["Kp_gov"]
    Ki_gov = p["Ki_gov"]
    T_gov = p["T_gov"]
    T_act = p["T_act"]
    tau_act = p["tau_act"]
    T_tc = p["T_tc"]
    K_fuel = p["K_fuel"]
    T_fuel = p["T_fuel"]
    T_spd = p["T_spd"]

    Kp_avr = p["Kp_avr"]
    Ki_avr = p["Ki_avr"]
    T_avr = p["T_avr"]
    T1 = p["T1"]
    T2 = p["T2"]
    T_exc = p["T_exc"]
    K_exc = p["K_exc"]
    T_gen = p["T_gen"]
    K_gen = p["K_gen"]
    T_vs = p["T_vs"]

    K_LV = p["K_LV"]
    T_LV = p["T_LV"]

    gov_min = p["gov_min"]
    gov_max = p["gov_max"]
    efd_min = p["efd_min"]
    efd_max = p["efd_max"]

    t = np.arange(0, t_end + dt, dt)

    # =========================
    # 负载生成（原始负载）+ 预加载逻辑
    # =========================
    if csv_load_data is not None and len(csv_load_data) > 0:
        csv_time = csv_load_data[:, 0]
        csv_load = csv_load_data[:, 1]
        P_load_original = np.interp(t, csv_time, csv_load) * p["load_pu"]
    else:
        period = p["period"]
        t1 = p["t1"]
        t2 = period - t1
        load_pu1 = p["load_pu1"]
        load_pu2 = p["load_pu2"]
        P_load_original = np.zeros_like(t)
        for k in range(int(np.floor(t_end / period)) + 1):
            start = k * period
            t1_end = start + t1
            t2_end = t1_end + t2
            P_load_original[(t >= start) & (t < t1_end)] = load_pu1
            P_load_original[(t >= t1_end) & (t < t2_end)] = load_pu2

    # 获取t=0时刻的初始负载值
    initial_load_value = P_load_original[0] if len(P_load_original) > 0 else 0.0
    # 直接使用原始负载值，取消预加载曲线

    # 创建预加载值曲线（整个仿真过程中保持为t=0时刻的负载值）
    P_preload_curve = np.full_like(P_load_original, initial_load_value)

    # 初始化负载基线值和实时平均值
    P_load_base = 0.0
    P_load_average = 0.0
    
    # 计算整个仿真周期的平均值（用于显示）
    P_load_average_total = np.mean(P_load_original)
    
    # 计算实时负载平均线（过去100秒，使用每0.2秒的数据点）
    P_load_average_real_time = np.zeros_like(P_load_original)
    # 每0.2秒取一个数据点
    interval = 0.2
    interval_indices = np.arange(0, len(P_load_original), int(interval / dt))
    interval_data = P_load_original[interval_indices]
    
    # 计算每个时刻的实时平均值（过去100秒，最多500个点）
    for i in range(len(P_load_original)):
        # 计算当前时间对应的秒数
        current_time = i * dt
        # 找到100秒前对应的索引
        start_time = max(0, current_time - 100)
        start_idx = int(start_time * (1.0 / dt))
        # 找到对应的0.2秒间隔数据索引
        interval_start_idx = np.searchsorted(interval_indices, start_idx)
        # 计算平均值，最多取500个点
        if interval_start_idx < len(interval_data):
            # 确保不超过500个点
            end_idx = min(interval_start_idx + 500, len(interval_data))
            P_load_average_real_time[i] = np.mean(interval_data[interval_start_idx:end_idx])
        else:
            P_load_average_real_time[i] = P_load_original[i]
    
    # 初始化HESS控制器
    hess_controller = HESS_Controller(hess_params)
    hess_params.t_sim = t_end
    hess_params.N = len(t)
    
    # =========================
    # 初始化存储数组
    # =========================
    # 发电机组状态
    rpm_log = np.ones_like(t) * rpm_base
    VkV_log = np.ones_like(t) * V_base_kV
    omega_log = np.ones_like(t) * 1.0
    
    # HESS相关
    P_storage_total_log = np.zeros_like(t)
    P_ESS_log = np.zeros_like(t)
    P_SC_log = np.zeros_like(t)
    SOC_ESS_log = np.ones_like(t) * 0.5
    SOC_SC_log = np.ones_like(t) * 0.5
    
    # 功率相关
    P_load_hess_log = np.zeros_like(t)  # 经过HESS平抑后的机组负载
    P_load_original_log = P_load_original.copy()  # 原始负载
    
    # 把负载的第一个值赋给机组功率的第一个值
    if len(P_load_original) > 0:
        P_load_hess_log[0] = P_load_original[0]
    
    # =========================
    # 预加载稳态初始化：让机组先运行到预加载的稳态
    # =========================
    # 预加载值（t=0的负载）
    preload_value = P_load_original[0] if len(P_load_original) > 0 else 0.0

    # 稳态初始化：迭代计算到转速/电压稳定
    omega = 1.0
    x_spd = 1.0
    x_gov_i = 0.0
    x_gov = 0.0
    x_act = 0.0
    x_tc = 0.0
    x_fuel = 0.0

    x_vs = 1.0
    x_avr_i = 0.0
    x_avr = 0.0
    x_ll = 0.0
    x_exc = 0.0
    x_gen = 1.0
    x_lv = 0.0

    b = T1 / T2
    a = 1.0 - b

    def clamp(x, lo, hi):
        return lo if x < lo else hi if x > hi else x

    # 预加载稳态迭代（模拟t=0前的预加载过程）
    for _ in range(1000):  # 足够多的迭代次数确保稳态
        # 转速环稳态计算
        e_w = 1.0 - x_spd
        u_p = Kp_gov * e_w
        u_i = Ki_gov * x_gov_i
        u_unsat = u_p + u_i
        u_sat = clamp(u_unsat, gov_min, gov_max)
        if u_unsat == u_sat:
            x_gov_i += dt * e_w
        x_gov += dt * ((u_sat - x_gov) / T_gov)
        x_act += dt * ((x_gov - x_act) / T_act)
        x_tc += dt * ((x_act - x_tc) / T_tc)
        x_fuel += dt * ((K_fuel * x_tc - x_fuel) / T_fuel)
        Pm = clamp(x_fuel, gov_min, gov_max)
        domega = (Pm - preload_value - D_pu * (omega - 1.0)) / (2.0 * H)
        omega += dt * domega
        x_spd += dt * ((omega - x_spd) / T_spd)
        
        # 电压环稳态计算
        x_lv += dt * ((preload_value - x_lv) / T_LV)
        Vt = x_gen - K_LV * x_lv
        x_vs += dt * ((Vt - x_vs) / T_vs)
        e_v = 1.0 - x_vs
        x_avr_i += dt * e_v
        u_avr = Kp_avr * e_v + Ki_avr * x_avr_i
        x_avr += dt * ((u_avr - x_avr) / T_avr)
        x_ll += dt * ((x_avr - x_ll) / T2)
        y_ll = a * x_ll + b * x_avr
        x_exc += dt * ((K_exc * y_ll - x_exc) / T_exc)
        Efd = clamp(x_exc, efd_min, efd_max)
        x_gen += dt * ((K_gen * Efd - x_gen) / T_gen)

    # 计算初始电阻值（基于预加载时的负载和电压）
    Vt_initial = x_gen - K_LV * x_lv
    R_load = Vt_initial**2 / preload_value if preload_value > 0 else 1.0

    # =========================
    # 找到第一次负载变化（预加载后）
    # =========================
    dPe = np.abs(np.diff(P_load_original))
    idx_change = np.where(dPe > 1e-9)[0]

    if len(idx_change) > 0:
        start_idx = idx_change[0] + 1
    else:
        start_idx = len(t)

    # =========================
    # 延迟缓存
    # =========================
    n_delay = int(round(tau_act / dt))
    delay_buf = np.zeros(n_delay + 1)
    buf_idx = 0

    Vref = 1.0
    omegaref = 1.0
    base_omegaref = 1.0  # 基础目标转速

    # =========================
    # 预初始化HESS控制器
    # =========================
    # 在第一次负载变化之前，让HESS控制器运行几次以初始化状态
    for i in range(min(100, start_idx)):
        P_load_original_i = P_load_original[i]
        if hess_params.P_ESS_max > 0 and hess_params.P_SC_max > 0:
            (P_storage_total, P_ESS, P_SC, SOC_ESS, SOC_SC, 
             ess_limited, sc_limited) = hess_controller.step(P_load_original_i, preload_value)

    # =========================
    # 动态仿真（发电机组+HESS联合仿真）
    # =========================
    for i in range(0, len(t)):
        # 计算当前电压
        Vt = x_gen - K_LV * x_lv
        
        # 获取原始负载曲线的当前值
        P_load_original_i = P_load_original[i]
        
        # 根据原始负载曲线的变化规律调整电阻值
        # 电阻 = 额定电压² / 原始负载功率（在额定电压下，负载功率等于原始负载曲线的值）
        V_ref = 1.0  # 额定电压（标幺值）
        if P_load_original_i > 0:
            R_load_current = V_ref**2 / P_load_original_i
        else:
            # 当原始负载为0时，使用一个很大的电阻值（但不是无穷大）
            R_load_current = 1e9  # 1G欧姆，相当于开路
        
        # 计算恒阻性负载功率（P = V² / R）
        P_load_resistive = Vt**2 / R_load_current
        
        # HESS控制：计算储能输出功率（平抑负载波动）- 从t=0时刻开始
        if hess_params.P_ESS_max > 0 and hess_params.P_SC_max > 0:
            (P_storage_total, P_ESS, P_SC, SOC_ESS, SOC_SC, 
             ess_limited, sc_limited) = hess_controller.step(P_load_resistive, preload_value)
            # 机组功率 = 恒阻性负载 - HESS输出功率（HESS平抑波动）
            P_gen_i = P_load_resistive - P_storage_total
        else:
            # 禁用HESS时，直接使用恒阻性负载作为机组功率
            P_storage_total = 0.0
            P_ESS = 0.0
            P_SC = 0.0
            SOC_ESS = 0.5
            SOC_SC = 0.5
            ess_limited = False
            sc_limited = False
            P_gen_i = P_load_resistive
        
        # 存储HESS数据
        P_storage_total_log[i] = P_storage_total
        P_ESS_log[i] = P_ESS
        P_SC_log[i] = P_SC
        SOC_ESS_log[i] = SOC_ESS
        SOC_SC_log[i] = SOC_SC
        P_load_hess_log[i] = P_gen_i  # 保留原变量名以保持兼容性，但实际存储的是机组功率
        
        # =========================
        # V/Hz电压下降控制：根据频率偏差调整电压
        # =========================
        # 当启用HESS时，也启用V/Hz控制
        hess_enabled = hess_params.P_ESS_max > 0 and hess_params.P_SC_max > 0
        vhz_enabled = p.get("enable_voltage_speed_control", False) or hess_enabled
        
        if vhz_enabled:
            # 计算频率
            rpm_base = p.get("rpm_base", 1500.0)
            f_nom = rpm_base / 60 * 2  # 标准频率（Hz）
            f_actual = omega * rpm_base / 60 * 2  # 实际频率（Hz）
            
            # 计算频率偏差
            f_deviation = f_actual - f_nom  # 频率偏差（Hz）
            
            # 检查频率是否超出死区
            frequency_deadband = p.get("frequency_deadband", 1.0)
            if abs(f_deviation) > frequency_deadband:
                # 计算电压下降百分比
                voltage_drop_per_hz = p.get("voltage_drop_per_hz", 7.0)  # 每1Hz的电压下降百分比
                
                # 计算目标电压
                if f_deviation < 0:  # 频率低于标准频率
                    # 频率下降，电压下降
                    voltage_drop_pct = voltage_drop_per_hz * abs(f_deviation)
                    Vref_target = max(0.8, 1.0 - voltage_drop_pct / 100)  # 最低电压限制为0.8 p.u.
                else:  # 频率高于标准频率
                    # 频率上升，电压恢复
                    Vref_target = 1.0
                
                # 平滑过渡到目标电压
                Vref = min(1.0, max(0.8, Vref + (Vref_target - Vref) * 0.1))  # 调整速率
            else:
                # 频率在死区内，电压恢复到基础值
                Vref = min(1.0, Vref + 0.1 * dt)  # 恢复速率为0.1 p.u./s

        # =========================
        # 发电机组转速环仿真
        # =========================
        # speed sensor
        x_spd += dt * ((omega - x_spd) / T_spd)
        e_w = omegaref - x_spd

        # governor
        u_p = Kp_gov * e_w
        u_i = Ki_gov * x_gov_i
        u_unsat = u_p + u_i
        u_sat = clamp(u_unsat, gov_min, gov_max)

        if u_unsat == u_sat:
            x_gov_i += dt * e_w

        x_gov += dt * ((u_sat - x_gov) / T_gov)

        # delay
        delay_buf[buf_idx] = x_gov
        buf_out = delay_buf[(buf_idx - n_delay) % (n_delay + 1)]
        buf_idx = (buf_idx + 1) % (n_delay + 1)

        x_act += dt * ((buf_out - x_act) / T_act)
        x_tc += dt * ((x_act - x_tc) / T_tc)
        x_fuel += dt * ((K_fuel * x_tc - x_fuel) / T_fuel)

        Pm = clamp(x_fuel, gov_min, gov_max)

        domega = (Pm - P_gen_i - D_pu * (omega - 1.0)) / (2.0 * H)
        omega += dt * domega
        omega_log[i] = omega

        # =========================
        # 发电机组电压环仿真
        # =========================
        x_lv += dt * ((P_gen_i - x_lv) / T_LV)

        Vt = x_gen - K_LV * x_lv
        x_vs += dt * ((Vt - x_vs) / T_vs)
        e_v = Vref - x_vs

        x_avr_i += dt * e_v
        u_avr = Kp_avr * e_v + Ki_avr * x_avr_i
        x_avr += dt * ((u_avr - x_avr) / T_avr)

        x_ll += dt * ((x_avr - x_ll) / T2)
        y_ll = a * x_ll + b * x_avr

        x_exc += dt * ((K_exc * y_ll - x_exc) / T_exc)
        Efd = clamp(x_exc, efd_min, efd_max)

        x_gen += dt * ((K_gen * Efd - x_gen) / T_gen)

        # 更新转速和电压记录
        rpm_log[i] = omega * rpm_base
        VkV_log[i] = (x_gen - K_LV * x_lv) * V_base_kV

    return (t, P_load_original_log, P_load_hess_log, P_storage_total_log, 
            P_ESS_log, P_SC_log, SOC_ESS_log, SOC_SC_log,
            rpm_log, VkV_log, omega_log, P_load_base, P_load_average_total, P_load_average_real_time, P_preload_curve)

# ====================== 7. 主应用类（保留Tkinter界面）=======================
class DG_HESS_SimulatorApp:
    def __init__(self, root):
        print("初始化应用实例...")
        self.root = root
        print("设置窗口标题和大小...")
        self.root.title("柴油发电机组+HESS混合储能系统动态仿真")
        self.root.geometry("1600x1000")
        
        # 存储参数值的字典
        print("初始化参数字典...")
        self.params = DEFAULTS.copy()
        self.param_vars = {}
        
        # 初始化HESS参数
        print("初始化HESS参数...")
        self.hess_params = HESS_Params()
        self.hess_param_vars = {}
        
        # CSV负载数据
        print("初始化CSV负载数据...")
        self.csv_load_data = None
        self.csv_filename = tk.StringVar(value="未选择CSV文件")
        self.raw_csv_load_data = None
        
        # 先初始化所有参数变量
        print("初始化参数变量...")
        self.init_param_vars()
        print("初始化HESS参数变量...")
        self.init_hess_param_vars()
        
        # 初始化结果变量（修复：提前初始化，解决AttributeError）
        print("初始化结果变量...")
        self.result_vars = {
            "rpm_min": tk.StringVar(value="--"),
            "rpm_max": tk.StringVar(value="--"),
            "v_min": tk.StringVar(value="--"),
            "v_max": tk.StringVar(value="--"),
            "dv_range": tk.StringVar(value="--"),
            "rpm_recovery": tk.StringVar(value="--"),
            "recovery_check": tk.StringVar(value="--"),
            "power_suppression": tk.StringVar(value="--"),
            "ess_avg_soc": tk.StringVar(value="--"),
            "sc_avg_soc": tk.StringVar(value="--"),
            "rpm_fluctuation_at_time": tk.StringVar(value="--"),
            "rpm_fluctuation_at_time2": tk.StringVar(value="--"),
            "rpm_fluctuation_at_time3": tk.StringVar(value="--"),
            "rpm_fluctuation_at_time4": tk.StringVar(value="--"),
            "v_fluctuation_at_time": tk.StringVar(value="--"),
            "v_fluctuation_at_time2": tk.StringVar(value="--"),
            "v_fluctuation_at_time3": tk.StringVar(value="--"),
            "v_fluctuation_at_time4": tk.StringVar(value="--"),
        }
        
        # 保存仿真结果数据，用于X轴范围变化时更新注释位置
        self.simulation_results = None
        
        # 图例显示状态
        self.show_legend_var = tk.BooleanVar(value=True)
        
        # 创建主布局
        print("创建主布局...")
        self.create_main_layout()
        
        # 初始化参数控件
        print("创建参数控件...")
        self.create_parameter_controls()
        print("创建HESS参数控件...")
        self.create_hess_parameter_controls()
        
        # 初始化结果显示区域
        print("创建结果显示区域...")
        self.create_result_display()
        
        # 初始化绘图区域
        print("创建绘图区域...")
        self.create_plot_area()
        
        # 首次运行仿真
        print("首次运行仿真...")
        self.run_simulation()
        print("应用实例初始化完成...")

    def init_param_vars(self):
        """初始化发电机组参数变量"""
        for key in DEFAULTS.keys():
            self.param_vars[key] = tk.DoubleVar(value=self.params[key])

    def init_hess_param_vars(self):
        """初始化HESS参数变量（修复：添加遗漏的k_RC和k_RK）"""
        hess_param_list = [
            ("P_ESS_max", self.hess_params.P_ESS_max),
            ("P_SC_max", self.hess_params.P_SC_max),
            ("R_ESS_max", self.hess_params.R_ESS_max),
            ("R_SC_max", self.hess_params.R_SC_max),
            ("tau_ESS", self.hess_params.tau_ESS),
            ("tau_SC", self.hess_params.tau_SC),
            ("k_p", self.hess_params.k_p),
            ("k_d", self.hess_params.k_d),
            ("k_I", self.hess_params.k_I),
            ("k_RC", self.hess_params.k_RC),  # 修复：添加k_RC
            ("k_RK", self.hess_params.k_RK),  # 修复：添加k_RK
            ("light_load_threshold", self.hess_params.light_load_threshold),
            ("ess_charge_stop_soc", self.hess_params.ess_charge_stop_soc),
            ("sc_charge_stop_soc", self.hess_params.sc_charge_stop_soc),
        ]
        for key, value in hess_param_list:
            self.hess_param_vars[key] = tk.DoubleVar(value=value)

    def create_main_layout(self):
        # 创建主面板
        main_panel = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_panel.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧参数面板（带标签页）
        param_notebook = ttk.Notebook(main_panel)
        main_panel.add(param_notebook, weight=9)  # 左侧宽度缩减10%
        
        # 发电机组参数标签页
        self.param_frame = ttk.Frame(param_notebook)
        param_notebook.add(self.param_frame, text="发电机组参数")
        
        # HESS参数标签页
        self.hess_param_frame = ttk.Frame(param_notebook)
        param_notebook.add(self.hess_param_frame, text="HESS储能参数")
        
        # 右侧结果面板
        self.result_frame = ttk.LabelFrame(main_panel, text="仿真结果（发电机组+HESS混合系统）")
        main_panel.add(self.result_frame, weight=41)  # 右侧宽度增大
        
        # 发电机组参数面板滚动条
        param_canvas = tk.Canvas(self.param_frame)
        param_scrollbar = ttk.Scrollbar(self.param_frame, orient=tk.VERTICAL, command=param_canvas.yview)
        self.param_inner_frame = ttk.Frame(param_canvas)
        self.param_inner_frame.bind("<Configure>", lambda e: param_canvas.configure(scrollregion=param_canvas.bbox("all")))
        param_canvas.create_window((0, 0), window=self.param_inner_frame, anchor="nw")
        param_canvas.configure(yscrollcommand=param_scrollbar.set)
        param_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        param_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # HESS参数面板滚动条
        hess_param_canvas = tk.Canvas(self.hess_param_frame)
        hess_param_scrollbar = ttk.Scrollbar(self.hess_param_frame, orient=tk.VERTICAL, command=hess_param_canvas.yview)
        self.hess_param_inner_frame = ttk.Frame(hess_param_canvas)
        self.hess_param_inner_frame.bind("<Configure>", lambda e: hess_param_canvas.configure(scrollregion=hess_param_canvas.bbox("all")))
        hess_param_canvas.create_window((0, 0), window=self.hess_param_inner_frame, anchor="nw")
        hess_param_canvas.configure(yscrollcommand=hess_param_scrollbar.set)
        hess_param_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        hess_param_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 顶部按钮区域
        button_frame = ttk.Frame(self.param_inner_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        # CSV文件选择按钮
        self.csv_btn = ttk.Button(button_frame, text="📂 选择CSV负载文件", command=self.load_csv_load)
        self.csv_btn.pack(side=tk.LEFT, padx=5)
        
        # 显示当前选择的CSV文件
        csv_label = ttk.Label(button_frame, textvariable=self.csv_filename, font=("Arial", 8))
        csv_label.pack(side=tk.LEFT, padx=5)
        
        # 分隔线
        ttk.Separator(button_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        self.run_btn = ttk.Button(button_frame, text="▶️ 运行仿真", command=self.run_simulation)
        self.run_btn.pack(side=tk.LEFT, padx=5)
        
        self.reset_btn = ttk.Button(button_frame, text="♻️ 复位参数", command=self.reset_to_defaults)
        self.reset_btn.pack(side=tk.LEFT, padx=5)
        
        # 负载模式切换
        self.load_mode_var = tk.StringVar(value="csv" if self.csv_load_data is not None else "square")
        mode_frame = ttk.Frame(self.param_inner_frame)
        mode_frame.pack(fill=tk.X, padx=5, pady=3)
        ttk.Label(mode_frame, text="负载模式：").pack(side=tk.LEFT)
        ttk.Radiobutton(mode_frame, text="CSV文件负载", variable=self.load_mode_var, 
                       value="csv", command=self.switch_load_mode).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="方波负载", variable=self.load_mode_var, 
                       value="square", command=self.switch_load_mode).pack(side=tk.LEFT)
        
        # HESS开关
        self.hess_enable_var = tk.BooleanVar(value=True)
        hess_switch_frame = ttk.Frame(self.param_inner_frame)
        hess_switch_frame.pack(fill=tk.X, padx=5, pady=3)
        ttk.Label(hess_switch_frame, text="HESS控制：").pack(side=tk.LEFT)
        ttk.Checkbutton(hess_switch_frame, text="启用HESS混合储能", variable=self.hess_enable_var,
                       command=self.run_simulation).pack(side=tk.LEFT, padx=5)
        
        # 图例显示和波动时间设置
        legend_time_frame = ttk.Frame(self.param_inner_frame)
        legend_time_frame.pack(fill=tk.X, padx=5, pady=3)
        
        # 图例显示开关
        ttk.Label(legend_time_frame, text="图例显示：").pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(legend_time_frame, text="显示图例", variable=self.show_legend_var,
                       command=self.run_simulation).pack(side=tk.LEFT, padx=5)
        
        # 波动时间设置
        ttk.Label(legend_time_frame, text="波动计算时间 (s):").pack(side=tk.LEFT, padx=10)
        self.fluctuation_time_var = tk.DoubleVar(value=1.0)
        ttk.Entry(legend_time_frame, textvariable=self.fluctuation_time_var, width=6).pack(side=tk.LEFT, padx=2)


    def switch_load_mode(self):
        mode = self.load_mode_var.get()
        if mode == "csv" and self.csv_load_data is None:
            messagebox.showwarning("提示", "请先选择CSV负载文件！")
            self.load_mode_var.set("square")
        self.run_simulation()

    def load_csv_load(self):
        file_path = filedialog.askopenfilename(
            title="选择CSV负载文件",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        if file_path:
            try:
                df = pd.read_csv(file_path)
                
                if df.shape[1] >= 2:
                    time_data = df.iloc[:, 0].values
                    load_data = df.iloc[:, 1].values
                else:
                    load_data = df.iloc[:, 0].values
                    time_data = np.arange(0, len(load_data) * 0.01, 0.01)[:len(load_data)]
                
                valid_mask = np.isfinite(time_data) & np.isfinite(load_data)
                time_data = time_data[valid_mask]
                load_data = load_data[valid_mask]
                
                self.raw_csv_load_data = np.column_stack((time_data, load_data))
                
                max_load = np.max(np.abs(load_data))
                if max_load > 0:
                    normalized_load = load_data / max_load
                else:
                    normalized_load = load_data
                
                self.csv_load_data = np.column_stack((time_data, normalized_load))
                self.csv_filename.set(f"已加载: {file_path.split('/')[-1]}")
                self.load_mode_var.set("csv")
                
                max_time = np.max(time_data)
                self.param_vars["t_end"].set(max_time)
                self.params["t_end"] = max_time
                
                messagebox.showinfo("成功", f"CSV负载文件加载成功！\n数据点数量：{len(self.csv_load_data)}\n时间范围：0~{max_time:.2f}秒\n原始负载范围：{np.min(load_data):.2f}~{np.max(load_data):.2f}\n可通过load_pu参数调整负载大小")
                
                self.run_simulation()
                
            except Exception as e:
                messagebox.showerror("错误", f"加载CSV文件失败：{str(e)}")
                import traceback
                traceback.print_exc()

    def on_slider_change(self, value, key, min_val, max_val, is_hess=False):
        try:
            val = float(value)
            val = max(min_val, min(max_val, val))
            if is_hess:
                self.hess_param_vars[key].set(val)
                setattr(self.hess_params, key, val)
            else:
                self.param_vars[key].set(val)
                self.params[key] = val
            
            if key == "load_pu" and self.load_mode_var.get() == "csv":
                self.run_simulation()
        except:
            pass

    def on_entry_change(self, key, min_val, max_val, is_hess=False):
        try:
            if is_hess:
                val = float(self.hess_param_vars[key].get())
                val = max(min_val, min(max_val, val))
                self.hess_param_vars[key].set(f"{val:.4f}")
                setattr(self.hess_params, key, val)
            else:
                val = float(self.param_vars[key].get())
                val = max(min_val, min(max_val, val))
                self.param_vars[key].set(f"{val:.4f}")
                self.params[key] = val
            
            if key == "load_pu" and self.load_mode_var.get() == "csv":
                self.run_simulation()
        except ValueError:
            if is_hess:
                self.hess_param_vars[key].set(getattr(self.hess_params, key))
            else:
                self.param_vars[key].set(self.params[key])

    def on_checkbox_change(self, key):
        """处理复选框状态变化"""
        try:
            val = self.param_vars[key].get()
            self.params[key] = val
            self.run_simulation()
        except Exception as e:
            pass

    def create_parameter_controls(self):
        """创建发电机组参数控件"""
        param_groups = {
            "仿真与负载": [
                ("t_end (s)", "t_end", 0.01, 500.0, 0.01, "%.3f"),
                ("dt (s)", "dt", 0.0005, 0.01, 0.0001, "%.5f"),
                ("period (s)", "period", 0.01, 50.0, 0.01, "%.3f"),
                ("t1 (s)", "t1", 0.005, 50.0, 0.001, "%.4f"),
                ("load1 (p.u.)", "load_pu1", 0.0, 2.0, 0.01, "%.2f"),
                ("load2 (p.u.)", "load_pu2", 0.0, 2.0, 0.01, "%.2f"),
                ("load_pu (CSV)", "load_pu", 0.0, 2.0, 0.01, "%.2f"),
            ],
            "V/Hz电压控制": [
                ("启用V/Hz电压控制", "enable_voltage_speed_control", 0, 1, 1, "%d"),
                ("频率死区 (Hz)", "frequency_deadband", 0.0, 5.0, 0.1, "%.1f"),
                ("每Hz电压下降 (%%)", "voltage_drop_per_hz", 0.0, 20.0, 0.1, "%.1f"),
            ],
            "基值": [
                ("rpm_base (rpm)", "rpm_base", 600.0, 3600.0, 10.0, "%.0f"),
                ("V_base (kV)", "V_base_kV", 0.4, 35.0, 0.1, "%.1f"),
            ],
            "转速环（ECU 调速）": [
                ("H (s)", "H", 0.1, 6.0, 0.1, "%.1f"),
                ("D (p.u.)", "D_pu", 0.0, 50, 0.05, "%.2f"),
                ("Kp_gov", "Kp_gov", 0.0, 30.0, 0.1, "%.1f"),
                ("Ki_gov", "Ki_gov", 0.0, 100.0, 0.1, "%.1f"),
                ("T_gov (s)", "T_gov", 0.001, 0.5, 0.001, "%.3f"),
                ("T_act (s)", "T_act", 0.001, 1.0, 0.001, "%.3f"),
                ("tau_act 延迟 (s)", "tau_act", 0.0, 0.5, 0.001, "%.3f"),
                ("T_tc 涡轮滞后 (s)", "T_tc", 0.01, 2.0, 0.01, "%.2f"),
                ("K_fuel", "K_fuel", 0.2, 100, 0.05, "%.2f"),
                ("T_fuel (s)", "T_fuel", 0.01, 1.0, 0.01, "%.2f"),
                ("T_spd 传感器 (s)", "T_spd", 0.001, 0.5, 0.001, "%.3f"),
            ],
            "电压环（PMG + AVR）": [
                ("Kp_avr", "Kp_avr", 0.0, 200.0, 1.0, "%.0f"),
                ("Ki_avr", "Ki_avr", 0.0, 800.0, 5.0, "%.0f"),
                ("T_avr (s)", "T_avr", 0.005, 0.2, 0.005, "%.3f"),
                ("T1 (s)", "T1", 0.0, 0.5, 0.005, "%.3f"),
                ("T2 (s)", "T2", 0.001, 0.5, 0.005, "%.3f"),
                ("T_exc (s)", "T_exc", 0.02, 2.0, 0.02, "%.2f"),
                ("K_exc", "K_exc", 0.2, 5.0, 0.05, "%.2f"),
                ("T_gen (s)", "T_gen", 0.02, 2.0, 0.02, "%.2f"),
                ("K_gen", "K_gen", 0.2, 5.0, 0.05, "%.2f"),
                ("T_vs (s)", "T_vs", 0.005, 0.2, 0.005, "%.3f"),
            ],
            "负载导致电压下陷": [
                ("K_LV (p.u./p.u.)", "K_LV", 0.0, 0.5, 0.01, "%.2f"),
                ("T_LV (s)", "T_LV", 0.005, 0.5, 0.005, "%.3f"),
            ],
            "限幅（防止积分发散）": [
                ("gov_min", "gov_min", -1.0, 1.0, 0.1, "%.1f"),
                ("gov_max", "gov_max", 0.1, 5.0, 0.1, "%.1f"),
                ("efd_min", "efd_min", -1.0, 1.0, 0.1, "%.1f"),
                ("efd_max", "efd_max", 0.1, 5.0, 0.1, "%.1f"),
            ],
        }
        
        for group_name, params in param_groups.items():
            group_frame = ttk.LabelFrame(self.param_inner_frame, text=group_name)
            group_frame.pack(fill=tk.X, padx=5, pady=3)
            
            for label_text, param_key, min_val, max_val, step, fmt in params:
                row_frame = ttk.Frame(group_frame)
                row_frame.pack(fill=tk.X, padx=5, pady=2)
                
                ttk.Label(row_frame, text=label_text, width=20, anchor="w").pack(side=tk.LEFT)
                
                # 对于布尔类型的参数，使用复选框
                if param_key == "enable_voltage_speed_control":
                    # 确保参数变量是布尔类型
                    if not isinstance(self.param_vars[param_key], tk.BooleanVar):
                        self.param_vars[param_key] = tk.BooleanVar(value=self.params[param_key])
                    
                    checkbox = ttk.Checkbutton(
                        row_frame, 
                        variable=self.param_vars[param_key],
                        command=lambda k=param_key: self.on_checkbox_change(k)
                    )
                    checkbox.pack(side=tk.LEFT, padx=5)
                else:
                    # 对于数值类型的参数，使用滑块和输入框
                    slider = ttk.Scale(
                        row_frame, 
                        from_=min_val, 
                        to=max_val, 
                        variable=self.param_vars[param_key],
                        command=lambda v, k=param_key, mn=min_val, mx=max_val: self.on_slider_change(v, k, mn, mx)
                    )
                    slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
                    
                    entry = ttk.Entry(
                        row_frame, 
                        textvariable=self.param_vars[param_key],
                        width=10
                    )
                    entry.pack(side=tk.LEFT, padx=2)
                    
                    entry.bind(
                        "<FocusOut>",
                        lambda e, k=param_key, mn=min_val, mx=max_val: self.on_entry_change(k, mn, mx)
                    )
                
                # 设置参数值
                if param_key == "enable_voltage_speed_control":
                    self.param_vars[param_key].set(self.params[param_key])
                else:
                    self.param_vars[param_key].set(fmt % self.params[param_key])

    def create_hess_parameter_controls(self):
        """创建HESS参数控件"""
        hess_param_groups = {
            "HESS储能参数": [
                ("P_ESS_max (MW)", "P_ESS_max", 5.0, 50.0, 1.0, "%.1f"),
                ("P_SC_max (MW)", "P_SC_max", 5.0, 40.0, 1.0, "%.1f"),
                ("R_ESS_max (MW/s)", "R_ESS_max", 5.0, 30.0, 0.5, "%.1f"),
                ("R_SC_max (MW/s)", "R_SC_max", 50.0, 100.0, 1.0, "%.1f"),
                ("tau_ESS (s)", "tau_ESS", 0.05, 1.0, 0.05, "%.2f"),
                ("tau_SC (s)", "tau_SC", 0.001, 0.01, 0.001, "%.3f"),
            ],
            "HESS控制器参数": [
                ("k_p", "k_p", 0.1, 5.0, 0.1, "%.1f"),
                ("k_d", "k_d", 0.05, 1.0, 0.05, "%.2f"),
                ("k_I", "k_I", 0.1, 2.0, 0.1, "%.1f"),
                ("k_RC", "k_RC", 0.1, 1.0, 0.05, "%.2f"),  # 修复：添加k_RC
                ("k_RK", "k_RK", 0.1, 1.0, 0.05, "%.2f"),  # 修复：添加k_RK
            ],
            "HESS充电限制参数": [
                ("light_load_threshold", "light_load_threshold", 0.1, 0.5, 0.01, "%.2f"),
                ("ess_charge_stop_soc", "ess_charge_stop_soc", 0.5, 0.8, 0.01, "%.2f"),
                ("sc_charge_stop_soc", "sc_charge_stop_soc", 0.5, 0.8, 0.01, "%.2f"),
            ],
        }
        
        for group_name, params in hess_param_groups.items():
            group_frame = ttk.LabelFrame(self.hess_param_inner_frame, text=group_name)
            group_frame.pack(fill=tk.X, padx=5, pady=3)
            
            for label_text, param_key, min_val, max_val, step, fmt in params:
                row_frame = ttk.Frame(group_frame)
                row_frame.pack(fill=tk.X, padx=5, pady=2)
                
                ttk.Label(row_frame, text=label_text, width=25, anchor="w").pack(side=tk.LEFT)
                
                slider = ttk.Scale(
                    row_frame, 
                    from_=min_val, 
                    to=max_val, 
                    variable=self.hess_param_vars[param_key],
                    command=lambda v, k=param_key, mn=min_val, mx=max_val: self.on_slider_change(v, k, mn, mx, True)
                )
                slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
                
                entry = ttk.Entry(
                    row_frame, 
                    textvariable=self.hess_param_vars[param_key],
                    width=10
                )
                entry.pack(side=tk.LEFT, padx=2)
                
                entry.bind(
                    "<FocusOut>",
                    lambda e, k=param_key, mn=min_val, mx=max_val: self.on_entry_change(k, mn, mx, True)
                )
                
                self.hess_param_vars[param_key].set(fmt % getattr(self.hess_params, param_key))

    def reset_to_defaults(self):
        """复位到默认参数"""
        # 复位发电机组参数
        for key, value in DEFAULTS.items():
            self.params[key] = value
            self.param_vars[key].set(value)
        
        # 复位HESS参数
        self.hess_params = HESS_Params()
        self.init_hess_param_vars()
        
        messagebox.showinfo("提示", "所有参数已复位为默认值")
        self.run_simulation()

    def calculate_recovery_time(self, t, rpm):
        target_rpm = self.params["rpm_base"]
        tolerance = target_rpm * 0.001
        recovery_time = "未恢复"
        is_reach_target = "未达标"
        
        load_change_idx = np.where(np.diff(np.concatenate([[0], (abs(rpm - target_rpm) > tolerance).astype(int)])) > 0)[0]
        if len(load_change_idx) > 0:
            start_idx = load_change_idx[0]
            for i in range(start_idx, len(t)):
                if abs(rpm[i] - target_rpm) <= tolerance:
                    recovery_time = f"{t[i]:.2f} s"
                    if t[i] < 2.0:
                        is_reach_target = "✅ 达标(<2秒)"
                    else:
                        is_reach_target = "❌ 不达标(≥2秒)"
                    break
        return recovery_time, is_reach_target

    def create_result_display(self):
        """创建结果显示区域"""
        result_header = ttk.Frame(self.result_frame)
        result_header.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(result_header, text="关键结果（发电机组+HESS混合系统）：", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=5)
        
        # 结果指标 - 除了转速和电压的最大值最小值
        metrics_frame = ttk.Frame(self.result_frame)
        metrics_frame.pack(fill=tk.X, padx=5, pady=3)
        
        # 第一行参数
        metrics = [
            ("转速恢复时间", "rpm_recovery"),
            ("是否达标", "recovery_check"),
            ("功率波动抑制率", "power_suppression"),
            ("时刻1转速波动率", "rpm_fluctuation_at_time"),
            ("时刻2转速波动率", "rpm_fluctuation_at_time2"),
            ("时刻3转速波动率", "rpm_fluctuation_at_time3"),
            ("时刻4转速波动率", "rpm_fluctuation_at_time4"),
            ("时刻1电压波动率", "v_fluctuation_at_time"),
            ("时刻2电压波动率", "v_fluctuation_at_time2"),
            ("时刻3电压波动率", "v_fluctuation_at_time3"),
            ("时刻4电压波动率", "v_fluctuation_at_time4"),
            ("BESS平均SOC", "ess_avg_soc"),
            ("SC平均SOC", "sc_avg_soc"),
        ]
        
        # 添加第一行参数
        for label_text, var_name in metrics:
            frame = ttk.Frame(metrics_frame)
            frame.pack(side=tk.LEFT, padx=10, pady=5)
            ttk.Label(frame, text=label_text).pack()
            ttk.Label(frame, textvariable=self.result_vars[var_name], font=('Arial', 10, 'bold')).pack()
        
        # 电压偏差和转速电压最大值最小值
        dv_frame = ttk.Frame(self.result_frame)
        dv_frame.pack(fill=tk.X, padx=5, pady=3)
        
        # 转速最小值
        rpm_min_frame = ttk.Frame(dv_frame)
        rpm_min_frame.pack(side=tk.LEFT, padx=10)
        ttk.Label(rpm_min_frame, text="转速最小值").pack()
        ttk.Label(rpm_min_frame, textvariable=self.result_vars["rpm_min"], font=("Arial", 10, "bold")).pack()
        
        # 转速最大值
        rpm_max_frame = ttk.Frame(dv_frame)
        rpm_max_frame.pack(side=tk.LEFT, padx=10)
        ttk.Label(rpm_max_frame, text="转速最大值").pack()
        ttk.Label(rpm_max_frame, textvariable=self.result_vars["rpm_max"], font=("Arial", 10, "bold")).pack()
        
        # 电压最小值
        v_min_frame = ttk.Frame(dv_frame)
        v_min_frame.pack(side=tk.LEFT, padx=10)
        ttk.Label(v_min_frame, text="电压最小值").pack()
        ttk.Label(v_min_frame, textvariable=self.result_vars["v_min"], font=("Arial", 10, "bold")).pack()
        
        # 电压最大值
        v_max_frame = ttk.Frame(dv_frame)
        v_max_frame.pack(side=tk.LEFT, padx=10)
        ttk.Label(v_max_frame, text="电压最大值").pack()
        ttk.Label(v_max_frame, textvariable=self.result_vars["v_max"], font=("Arial", 10, "bold")).pack()
        
        # 电压偏差
        ttk.Label(dv_frame, text="Δ电压范围：").pack(side=tk.LEFT, padx=10)
        ttk.Label(dv_frame, textvariable=self.result_vars["dv_range"], font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

    def create_plot_area(self):
        """创建绘图区域 —— 优化比例，看清转速电压"""
        # 绘图控制区域
        control_frame = ttk.Frame(self.result_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # X轴范围控制
        x_control_frame = ttk.LabelFrame(control_frame, text="X轴范围控制")
        x_control_frame.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Label(x_control_frame, text="起始时间:").pack(side=tk.LEFT, padx=2)
        self.x_min_var = tk.DoubleVar(value=0.0)
        ttk.Entry(x_control_frame, textvariable=self.x_min_var, width=6).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(x_control_frame, text="结束时间:").pack(side=tk.LEFT, padx=2)
        self.x_max_var = tk.DoubleVar(value=70.0)
        ttk.Entry(x_control_frame, textvariable=self.x_max_var, width=6).pack(side=tk.LEFT, padx=2)
        
        # Y轴范围控制
        y_control_frame = ttk.LabelFrame(control_frame, text="Y轴范围控制")
        y_control_frame.pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
        
        # 负载功率轴范围控制
        ttk.Label(y_control_frame, text="负载功率:").pack(side=tk.LEFT, padx=2)
        self.y_load_min_var = tk.DoubleVar(value=0.5)
        ttk.Entry(y_control_frame, textvariable=self.y_load_min_var, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Label(y_control_frame, text="到").pack(side=tk.LEFT, padx=2)
        self.y_load_max_var = tk.DoubleVar(value=2.0)
        ttk.Entry(y_control_frame, textvariable=self.y_load_max_var, width=6).pack(side=tk.LEFT, padx=2)
        
        # HESS功率轴范围控制
        ttk.Label(y_control_frame, text="  HESS功率:").pack(side=tk.LEFT, padx=2)
        self.y_hess_min_var = tk.DoubleVar(value=-2.0)
        ttk.Entry(y_control_frame, textvariable=self.y_hess_min_var, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Label(y_control_frame, text="到").pack(side=tk.LEFT, padx=2)
        self.y_hess_max_var = tk.DoubleVar(value=2.0)
        ttk.Entry(y_control_frame, textvariable=self.y_hess_max_var, width=6).pack(side=tk.LEFT, padx=2)
        
        # 转速轴范围控制
        ttk.Label(y_control_frame, text="  转速:").pack(side=tk.LEFT, padx=2)
        self.y_rpm_min_var = tk.DoubleVar(value=1300.0)
        ttk.Entry(y_control_frame, textvariable=self.y_rpm_min_var, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Label(y_control_frame, text="到").pack(side=tk.LEFT, padx=2)
        self.y_rpm_max_var = tk.DoubleVar(value=1600.0)
        ttk.Entry(y_control_frame, textvariable=self.y_rpm_max_var, width=6).pack(side=tk.LEFT, padx=2)
        
        # 电压轴范围控制
        ttk.Label(y_control_frame, text="  电压:").pack(side=tk.LEFT, padx=2)
        self.y_voltage_min_var = tk.DoubleVar(value=8)
        ttk.Entry(y_control_frame, textvariable=self.y_voltage_min_var, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Label(y_control_frame, text="到").pack(side=tk.LEFT, padx=2)
        self.y_voltage_max_var = tk.DoubleVar(value=12.0)
        ttk.Entry(y_control_frame, textvariable=self.y_voltage_max_var, width=6).pack(side=tk.LEFT, padx=2)
        
        # SOC轴范围控制
        ttk.Label(y_control_frame, text="  SOC:").pack(side=tk.LEFT, padx=2)
        self.y_soc_min_var = tk.DoubleVar(value=0.0)
        ttk.Entry(y_control_frame, textvariable=self.y_soc_min_var, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Label(y_control_frame, text="到").pack(side=tk.LEFT, padx=2)
        self.y_soc_max_var = tk.DoubleVar(value=1.0)
        ttk.Entry(y_control_frame, textvariable=self.y_soc_max_var, width=6).pack(side=tk.LEFT, padx=2)
        

        
        # 标注控制
        annot_control_frame = ttk.LabelFrame(control_frame, text="标注控制")
        annot_control_frame.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 显示注释文本选项
        self.show_annotations_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(annot_control_frame, text="显示注释文本", variable=self.show_annotations_var, command=self.apply_plot_ranges).pack(side=tk.LEFT, padx=5)
        
        # 应用按钮
        apply_btn = ttk.Button(control_frame, text="应用范围", command=self.apply_plot_ranges)
        apply_btn.pack(side=tk.LEFT, padx=10)

        # 第一个图：功率相关
        self.fig1, self.axs1 = plt.subplots(2, 1, figsize=(12, 3), sharex=True)
        plt.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.1, hspace=0.4)
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=self.result_frame)
        self.canvas1.draw()
        self.canvas1.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 第二个图：转速电压 —— 放大高度，专门看曲线
        self.fig2, self.axs2 = plt.subplots(2, 1, figsize=(12, 3), sharex=True)
        plt.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.12, hspace=0.4)
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=self.result_frame)
        self.canvas2.draw()
        self.canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 第三个图：SOC
        self.fig3, self.axs3 = plt.subplots(1, 1, figsize=(12, 3))
        plt.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.2)
        self.canvas3 = FigureCanvasTkAgg(self.fig3, master=self.result_frame)
        self.canvas3.draw()
        self.canvas3.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 启用标注拖动功能
        self.make_annotations_draggable()

    def apply_plot_ranges(self):
        """应用用户设置的坐标轴范围"""
        try:
            # 获取用户设置的范围值
            x_min = float(self.x_min_var.get())
            x_max = float(self.x_max_var.get())
            y_load_min = float(self.y_load_min_var.get())
            y_load_max = float(self.y_load_max_var.get())
            y_hess_min = float(self.y_hess_min_var.get())
            y_hess_max = float(self.y_hess_max_var.get())
            y_rpm_min = float(self.y_rpm_min_var.get())
            y_rpm_max = float(self.y_rpm_max_var.get())
            y_voltage_min = float(self.y_voltage_min_var.get())
            y_voltage_max = float(self.y_voltage_max_var.get())
            y_soc_min = float(self.y_soc_min_var.get())
            y_soc_max = float(self.y_soc_max_var.get())
            
            # 应用X轴范围到所有图表
            for ax in self.axs1:
                ax.set_xlim(x_min, x_max)
            for ax in self.axs2:
                ax.set_xlim(x_min, x_max)
            self.axs3.set_xlim(x_min, x_max)
            
            # 应用Y轴范围到图表
            self.axs1[0].set_ylim(y_load_min, y_load_max)  # 负载功率
            self.axs1[1].set_ylim(y_hess_min, y_hess_max)  # HESS功率
            self.axs2[0].set_ylim(y_rpm_min, y_rpm_max)    # 转速
            self.axs2[1].set_ylim(y_voltage_min, y_voltage_max)  # 电压
            
            # 只有当HESS启用时才设置SOC图表的Y轴范围
            if hasattr(self, 'hess_enable_var') and self.hess_enable_var.get():
                self.axs3.set_ylim(y_soc_min, y_soc_max)      # SOC
            
            # 如果有保存的仿真结果，重新更新绘图以确保注释在正确的位置
            if self.simulation_results is not None:
                self.update_plots(*self.simulation_results)
            else:
                # 重绘图表
                self.canvas1.draw()
                self.canvas2.draw()
                self.canvas3.draw()
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值")

    def make_annotations_draggable(self):
        """使标注可拖动"""
        # 存储拖动状态
        self.dragging = False
        self.drag_annotation = None
        self.drag_start = None
        self.dragging_vertical_line = False
        self.vertical_lines = []  # 存储多条垂直线
        self.vertical_lines2 = []  # 存储电压图表中的垂直线
        self.current_line_index = -1  # 当前拖动的线的索引
        self.click_count = 0  # 用于检测双击
        self.last_click_time = 0  # 用于检测双击时间间隔
        self.double_click_threshold = 300  # 双击时间阈值（毫秒）
        
        # 连接事件处理函数到画布1（功率图表）
        self.canvas1.mpl_connect('pick_event', self.on_pick)
        self.canvas1.mpl_connect('motion_notify_event', self.on_motion)
        self.canvas1.mpl_connect('button_release_event', self.on_release)
        
        # 连接事件处理函数到画布2（转速和电压图表）
        self.canvas2.mpl_connect('pick_event', self.on_pick)
        self.canvas2.mpl_connect('motion_notify_event', self.on_motion)
        self.canvas2.mpl_connect('button_release_event', self.on_release)
        self.canvas2.mpl_connect('button_press_event', self.on_button_press)
        self.canvas2.mpl_connect('button_press_event', self.on_double_click)
        
    def on_button_press(self, event):
        """处理鼠标按下事件，开始拖动垂直线"""
        if event.inaxes == self.axs2[0] or event.inaxes == self.axs2[1]:
            # 检查是否点击了现有垂直线
            clicked_line_index = -1
            for i, line in enumerate(self.vertical_lines):
                # 检查鼠标是否靠近垂直线
                line_x = line.get_xdata()[0]
                if abs(event.xdata - line_x) < 0.1:  # 0.1为点击容差
                    clicked_line_index = i
                    break
            
            if clicked_line_index != -1:
                # 开始拖动现有垂直线
                self.current_line_index = clicked_line_index
                self.dragging_vertical_line = True
                self.drag_start = event.xdata
            else:
                # 添加新垂直线（最多4条）
                if len(self.vertical_lines) < 4:
                    # 颜色列表
                    colors = ['red', 'blue', 'green', 'purple']
                    # 创建垂直线
                    line_color = colors[len(self.vertical_lines)]
                    line = self.axs2[0].axvline(x=event.xdata, color=line_color, linestyle='--', linewidth=1.5, label=f'时间线{len(self.vertical_lines)+1}')
                    self.vertical_lines.append(line)
                    
                    # 在电压图表中也添加垂直线
                    line2 = self.axs2[1].axvline(x=event.xdata, color=line_color, linestyle='--', linewidth=1.5, label=f'时间线{len(self.vertical_lines)}')
                    self.vertical_lines2.append(line2)
                    
                    # 开始拖动新添加的垂直线
                    self.current_line_index = len(self.vertical_lines) - 1
                    self.dragging_vertical_line = True
                    self.drag_start = event.xdata
                    
                    # 计算并显示波动率
                    self.update_fluctuations_at_times()
            
            self.canvas2.draw()
    
    def on_motion(self, event):
        """处理鼠标移动事件"""
        try:
            if self.dragging and self.drag_start is not None and self.drag_annotation is not None and event.xdata is not None and event.ydata is not None:
                # 计算新位置
                dx = event.xdata - self.drag_start[0]
                dy = event.ydata - self.drag_start[1]
                
                # 获取当前位置
                current_pos = self.drag_annotation.xy
                new_pos = (current_pos[0] + dx, current_pos[1] + dy)
                
                # 更新标注位置
                self.drag_annotation.set_position(new_pos)
                self.drag_start = (event.xdata, event.ydata)
                self.canvas1.draw()
            elif self.dragging_vertical_line and event.xdata is not None and self.current_line_index != -1:
                # 更新垂直线位置
                self.vertical_lines[self.current_line_index].set_xdata([event.xdata])
                self.vertical_lines2[self.current_line_index].set_xdata([event.xdata])
                
                # 计算并显示波动率
                self.update_fluctuations_at_times()
                
                self.canvas2.draw()
        except (TypeError, AttributeError):
            # 忽略错误，确保程序不会崩溃
            pass
    
    def on_release(self, event):
        """处理鼠标释放事件"""
        self.dragging = False
        self.drag_annotation = None
        self.drag_start = None
        self.dragging_vertical_line = False
        self.current_line_index = -1
    
    def on_double_click(self, event):
        """处理双击事件，取消时刻线"""
        import time
        
        # 计算点击时间间隔
        current_time = time.time() * 1000  # 转换为毫秒
        time_diff = current_time - self.last_click_time
        
        if time_diff < self.double_click_threshold:
            # 检测是否点击了现有垂直线
            clicked_line_index = -1
            for i, line in enumerate(self.vertical_lines):
                # 检查鼠标是否靠近垂直线
                line_x = line.get_xdata()[0]
                if abs(event.xdata - line_x) < 0.1:  # 0.1为点击容差
                    clicked_line_index = i
                    break
            
            if clicked_line_index != -1:
                # 移除垂直线
                try:
                    self.vertical_lines[clicked_line_index].remove()
                except:
                    pass
                try:
                    self.vertical_lines2[clicked_line_index].remove()
                except:
                    pass
                
                # 从列表中删除
                try:
                    del self.vertical_lines[clicked_line_index]
                except:
                    pass
                try:
                    del self.vertical_lines2[clicked_line_index]
                except:
                    pass
                
                # 更新波动率显示
                self.update_fluctuations_at_times()
                
                # 重绘画布
                self.canvas2.draw()
        
        # 更新最后点击时间
        self.last_click_time = current_time
    
    def update_fluctuations_at_times(self):
        """更新四条时刻线的转速和电压波动率"""
        if self.simulation_results is None:
            return
        
        # 重置所有波动率显示
        self.result_vars["rpm_fluctuation_at_time"].set("--")
        self.result_vars["rpm_fluctuation_at_time2"].set("--")
        self.result_vars["rpm_fluctuation_at_time3"].set("--")
        self.result_vars["rpm_fluctuation_at_time4"].set("--")
        self.result_vars["v_fluctuation_at_time"].set("--")
        self.result_vars["v_fluctuation_at_time2"].set("--")
        self.result_vars["v_fluctuation_at_time3"].set("--")
        self.result_vars["v_fluctuation_at_time4"].set("--")
        
        t, P_load_original, P_load_hess, P_storage_total, P_ESS, P_SC, SOC_ESS, SOC_SC, rpm, VkV, omega, P_load_base, P_load_average_total, P_load_average_real_time, P_preload_curve, hess_disabled = self.simulation_results
        
        # 颜色列表
        colors = ['red', 'blue', 'green', 'purple']
        
        # 计算每条时刻线的转速和电压波动率
        rpm_base = self.params["rpm_base"]
        v_base = self.params["V_base_kV"]
        
        # 清除旧的标注
        if hasattr(self, 'annotations'):
            for annot in self.annotations:
                try:
                    annot.remove()
                except:
                    pass
        self.annotations = []
        
        for i, line in enumerate(self.vertical_lines):
            time = line.get_xdata()[0]
            time_idx = np.argmax(t >= time)
            
            if time_idx < len(rpm):
                # 计算转速波动率
                rpm_at_time = rpm[time_idx]
                rpm_fluctuation_percent = ((rpm_at_time - rpm_base) / rpm_base) * 100
                
                # 计算电压波动率
                v_at_time = VkV[time_idx]
                v_fluctuation_percent = ((v_at_time - v_base) / v_base) * 100
                
                # 更新结果变量，添加时间信息
                time_str = f"{time:.2f}s"
                if i == 0:
                    self.result_vars["rpm_fluctuation_at_time"].set(f"{time_str} {rpm_fluctuation_percent:.2f}%")
                    self.result_vars["v_fluctuation_at_time"].set(f"{time_str} {v_fluctuation_percent:.2f}%")
                elif i == 1:
                    self.result_vars["rpm_fluctuation_at_time2"].set(f"{time_str} {rpm_fluctuation_percent:.2f}%")
                    self.result_vars["v_fluctuation_at_time2"].set(f"{time_str} {v_fluctuation_percent:.2f}%")
                elif i == 2:
                    self.result_vars["rpm_fluctuation_at_time3"].set(f"{time_str} {rpm_fluctuation_percent:.2f}%")
                    self.result_vars["v_fluctuation_at_time3"].set(f"{time_str} {v_fluctuation_percent:.2f}%")
                elif i == 3:
                    self.result_vars["rpm_fluctuation_at_time4"].set(f"{time_str} {rpm_fluctuation_percent:.2f}%")
                    self.result_vars["v_fluctuation_at_time4"].set(f"{time_str} {v_fluctuation_percent:.2f}%")
                
                # 添加转速波动率标注
                color = colors[i % len(colors)]
                time_str = f"{time:.2f}s"
                rpm_annot = self.axs2[0].annotate(
                    f'{time_str} {rpm_fluctuation_percent:.2f}%',
                    xy=(time, rpm_at_time),
                    xytext=(10, 10), textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.3', color=color),
                    color=color
                )
                self.annotations.append(rpm_annot)
                
                # 添加电压波动率标注
                v_annot = self.axs2[1].annotate(
                    f'{time_str} {v_fluctuation_percent:.2f}%',
                    xy=(time, v_at_time),
                    xytext=(10, 10), textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.3', color=color),
                    color=color
                )
                self.annotations.append(v_annot)
        
        # 重绘画布
        self.canvas2.draw()
    
    def update_fluctuation_at_time(self, time):
        """更新指定时间的波动率"""
        if self.simulation_results is None:
            return
        
        t, P_load_original, P_load_hess, P_storage_total, P_ESS, P_SC, SOC_ESS, SOC_SC, rpm, VkV, omega, P_load_base, P_load_average_total, P_load_average_real_time, P_preload_curve, hess_disabled = self.simulation_results
        
        # 找到时间对应的索引
        time_idx = np.argmax(t >= time)
        
        # 计算指定时刻的转速波动率
        rpm_base = self.params["rpm_base"]
        if time_idx < len(rpm):
            rpm_at_time = rpm[time_idx]
            rpm_fluctuation_percent = ((rpm_at_time - rpm_base) / rpm_base) * 100
            self.result_vars["rpm_fluctuation_at_time"].set(f"{rpm_fluctuation_percent:.2f}%")
        
        # 计算指定时刻的电压波动率
        v_base = self.params["V_base_kV"]
        if time_idx < len(VkV):
            v_at_time = VkV[time_idx]
            v_fluctuation_percent = ((v_at_time - v_base) / v_base) * 100
            self.result_vars["v_fluctuation_at_time"].set(f"{v_fluctuation_percent:.2f}%")
    
    def on_pick(self, event):
        """处理标注选择事件"""
        if isinstance(event.artist, plt.Annotation) and event.mouseevent.xdata is not None and event.mouseevent.ydata is not None:
            self.dragging = True
            self.drag_annotation = event.artist
            self.drag_start = (event.mouseevent.xdata, event.mouseevent.ydata)
    
    def on_motion(self, event):
        """处理鼠标移动事件"""
        try:
            if self.dragging and self.drag_start is not None and self.drag_annotation is not None and event.xdata is not None and event.ydata is not None:
                # 计算新位置
                dx = event.xdata - self.drag_start[0]
                dy = event.ydata - self.drag_start[1]
                
                # 获取当前位置
                current_pos = self.drag_annotation.xy
                new_pos = (current_pos[0] + dx, current_pos[1] + dy)
                
                # 更新标注位置
                self.drag_annotation.set_position(new_pos)
                self.drag_start = (event.xdata, event.ydata)
                self.canvas1.draw()
        except (TypeError, AttributeError):
            # 忽略错误，确保程序不会崩溃
            pass
    
    def on_release(self, event):
        """处理鼠标释放事件"""
        self.dragging = False
        self.drag_annotation = None
        self.drag_start = None

    def update_plots(self, t, P_load_original, P_load_hess, P_storage_total,
                     P_ESS, P_SC, SOC_ESS, SOC_SC, rpm, VkV, omega, P_load_base, P_load_average_total, P_load_average_real_time, P_preload_curve, hess_disabled=False):
        """更新绘图 —— 纵坐标显示最大值和最小值 + 预加载标注"""
        rpm_base = self.params["rpm_base"]
        V_base_kV = self.params["V_base_kV"]
        P_base_MW = self.params.get("P_base_MW", 2.0)  # 负载基准值2MW
        
        # 清除旧的垂直线和标注
        if hasattr(self, 'vertical_lines'):
            for line in self.vertical_lines:
                try:
                    line.remove()
                except:
                    pass
            self.vertical_lines = []
        else:
            self.vertical_lines = []
        
        if hasattr(self, 'vertical_lines2'):
            for line in self.vertical_lines2:
                try:
                    line.remove()
                except:
                    pass
            self.vertical_lines2 = []
        else:
            self.vertical_lines2 = []
        
        if hasattr(self, 'annotations'):
            for annot in self.annotations:
                try:
                    annot.remove()
                except:
                    pass
            self.annotations = []
        else:
            self.annotations = []
        
        # 计算实际功率值（MW）
        P_load_original_MW = P_load_original * P_base_MW
        P_load_hess_MW = P_load_hess * P_base_MW
        P_storage_total_MW = P_storage_total * P_base_MW
        P_ESS_MW = P_ESS * P_base_MW
        P_SC_MW = P_SC * P_base_MW
        P_load_base_MW = P_load_base * P_base_MW

        # 清空轴
        for ax in self.axs1:
            ax.clear()
        for ax in self.axs2:
            ax.clear()
        self.axs3.clear()
        
        # 应用用户设置的X轴范围
        try:
            x_min = float(self.x_min_var.get())
            x_max = float(self.x_max_var.get())
            for ax in self.axs1:
                ax.set_xlim(x_min, x_max)
            for ax in self.axs2:
                ax.set_xlim(x_min, x_max)
            self.axs3.set_xlim(x_min, x_max)
        except ValueError:
            pass

        # 应用用户设置的Y轴范围
        try:
            y_load_min = float(self.y_load_min_var.get())
            y_load_max = float(self.y_load_max_var.get())
            y_hess_min = float(self.y_hess_min_var.get())
            y_hess_max = float(self.y_hess_max_var.get())
            y_rpm_min = float(self.y_rpm_min_var.get())
            y_rpm_max = float(self.y_rpm_max_var.get())
            y_voltage_min = float(self.y_voltage_min_var.get())
            y_voltage_max = float(self.y_voltage_max_var.get())
            y_soc_min = float(self.y_soc_min_var.get())
            y_soc_max = float(self.y_soc_max_var.get())
            show_annotations = self.show_annotations_var.get()
        except ValueError:
            y_load_min, y_load_max = None, None
            y_hess_min, y_hess_max = None, None
            y_rpm_min, y_rpm_max = None, None
            y_voltage_min, y_voltage_max = None, None
            y_soc_min, y_soc_max = None, None
            show_annotations = True

        # ---------------- 功率图 ----------------
        self.axs1[0].plot(t, P_load_original_MW, 'k--', linewidth=1.8, label='原始负载功率 (MW)')
        # 无论是否启用HESS，都显示机组功率曲线（绿色）
        self.axs1[0].plot(t, P_load_hess_MW, 'g-', linewidth=2.2, label='机组功率 (MW)')
        if not hess_disabled:
            # 加入HESS功率曲线
            self.axs1[0].plot(t, P_storage_total_MW, 'm-', linewidth=1.8, label='HESS功率 (MW)')
        # 使用整个仿真周期的平均值作为参考线
        P_load_average_MW = P_load_average_total * P_base_MW
        self.axs1[0].axhline(y=P_load_average_MW, color='purple', ls='-', lw=2, label=f'原始负载平均线: {P_load_average_MW:.2f} MW')
        
        # 绘制实时负载平均线（过去200秒）
        P_load_average_real_time_MW = P_load_average_real_time * P_base_MW
        
        self.axs1[0].plot(t, P_load_average_real_time_MW, 'cyan', linewidth=2, label='实时负载平均线')
        self.axs1[0].axhline(y=P_load_base_MW, color='r', ls='--', lw=1.5, label=f'负载基线: {P_load_base_MW:.2f} MW')
        self.axs1[0].set_ylabel("功率 (MW)", fontsize=11)
        if hess_disabled:
            self.axs1[0].set_title("原始负载功率（无HESS平抑）", fontsize=12, pad=8, color='darkred')
        else:
            self.axs1[0].set_title("负载功率、机组功率和HESS功率对比（HESS平抑效果）", fontsize=12, pad=8)
        if self.show_legend_var.get():
            self.axs1[0].legend(fontsize=9, loc='upper right')
        self.axs1[0].grid(True, alpha=0.3)
        
        # 应用用户设置的Y轴范围
        if y_load_min is not None and y_load_max is not None:
            self.axs1[0].set_ylim(y_load_min, y_load_max)
            # 显示纵坐标最大最小值（可拖动，字体小一号，放在最左侧）
            if show_annotations:
                # Get current X-axis limits
                x_min, x_max = self.axs1[0].get_xlim()
                self.max_annot = self.axs1[0].annotate(f'Max: {y_load_max:.3f}', 
                                                      xy=(x_min, y_load_max), 
                                                      ha='left', va='bottom', 
                                                      fontsize=7, color='blue',
                                                      bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                                                      picker=5)
                self.min_annot = self.axs1[0].annotate(f'Min: {y_load_min:.3f}', 
                                                      xy=(x_min, y_load_min), 
                                                      ha='left', va='top', 
                                                      fontsize=7, color='blue',
                                                      bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                                                      picker=5)
        else:
            # 自动设置范围
            y_min, y_max = self.axs1[0].get_ylim()
            # 显示纵坐标最大最小值（可拖动，字体小一号，放在最左侧）
            if show_annotations:
                # Get current X-axis limits
                x_min, x_max = self.axs1[0].get_xlim()
                self.max_annot = self.axs1[0].annotate(f'Max: {y_max:.3f}', 
                                                      xy=(x_min, y_max), 
                                                      ha='left', va='bottom', 
                                                      fontsize=7, color='blue',
                                                      bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                                                      picker=5)
                self.min_annot = self.axs1[0].annotate(f'Min: {y_min:.3f}', 
                                                      xy=(x_min, y_min), 
                                                      ha='left', va='top', 
                                                      fontsize=7, color='blue',
                                                      bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                                                      picker=5)
        

        


        self.axs1[1].axhline(0, c='k', lw=0.8, alpha=0.6)
        if not hess_disabled:
            # 绘制曲线
            self.axs1[1].plot(t, P_storage_total_MW, 'm-', linewidth=2.2, label='HESS总功率 (MW)')
            self.axs1[1].plot(t, P_ESS_MW, 'b-', linewidth=1.8, label='BESS功率 (MW)')
            self.axs1[1].plot(t, P_SC_MW, 'r-', linewidth=1.8, label='SC功率 (MW)')
            self.axs1[1].set_title("HESS输出功率", fontsize=12, pad=8)
            


        else:
            self.axs1[1].text(0.5, 0.5, 'HESS已禁用\n无储能输出', ha='center', va='center', transform=self.axs1[1].transAxes, fontsize=12)
            self.axs1[1].set_title("HESS输出功率（禁用状态）", fontsize=12, pad=8, color='darkred')
        self.axs1[1].set_ylabel("功率 (MW)", fontsize=11)
        if self.show_legend_var.get() and not hess_disabled:
            self.axs1[1].legend(fontsize=10, loc='upper right')
        self.axs1[1].grid(True, alpha=0.3)
        # 应用用户设置的Y轴范围
        if y_hess_min is not None and y_hess_max is not None:
            self.axs1[1].set_ylim(y_hess_min, y_hess_max)
            # 显示纵坐标最大最小值（可拖动，字体小一号，放在最左侧）
            if show_annotations:
                # Get current X-axis limits
                x_min, x_max = self.axs1[1].get_xlim()
                self.hess_max_annot = self.axs1[1].annotate(f'Max: {y_hess_max:.3f}', 
                                      xy=(x_min, y_hess_max), 
                                      ha='left', va='bottom', 
                                      fontsize=7, color='blue',
                                      bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                                      picker=5)
                self.hess_min_annot = self.axs1[1].annotate(f'Min: {y_hess_min:.3f}', 
                                      xy=(x_min, y_hess_min), 
                                      ha='left', va='top', 
                                      fontsize=7, color='blue',
                                      bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                                      picker=5)
        else:
            # 自动设置范围
            y_min, y_max = self.axs1[1].get_ylim()
            # 显示纵坐标最大最小值（可拖动，字体小一号，放在最左侧）
            if show_annotations:
                # Get current X-axis limits
                x_min, x_max = self.axs1[1].get_xlim()
                self.hess_max_annot = self.axs1[1].annotate(f'Max: {y_max:.3f}', 
                                      xy=(x_min, y_max), 
                                      ha='left', va='bottom', 
                                      fontsize=7, color='blue',
                                      bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                                      picker=5)
                self.hess_min_annot = self.axs1[1].annotate(f'Min: {y_min:.3f}', 
                                      xy=(x_min, y_min), 
                                      ha='left', va='top', 
                                      fontsize=7, color='blue',
                                      bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                                      picker=5)

        # ---------------- 转速图 ----------------
        self.axs2[0].plot(t, rpm, 'b', linewidth=2.0, label=f'实际转速')
        self.axs2[0].axhline(rpm_base, color="red", lw=2, label=f"目标转速 {rpm_base:.0f} rpm")

        if hess_disabled:
            rpm_fluctuation = rpm - rpm_base
            max_dev_idx = np.argmax(np.abs(rpm_fluctuation))
            max_dev = rpm_fluctuation[max_dev_idx]
            if show_annotations:
                self.axs2[0].annotate(
                    f'最大偏差: {max_dev:.2f}rpm',
                    xy=(t[0], rpm[max_dev_idx]),
                    xytext=(10, 20), textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.3', fc='yellow', alpha=0.7),
                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.3')
                )
            self.axs2[0].axhline(rpm_base * 1.005, color="orange", ls="--", lw=1.2, label="±0.5% 容差")
            self.axs2[0].axhline(rpm_base * 0.995, color="orange", ls="--", lw=1.2)
        
        # 指定时刻波动率标注
        fluctuation_time = 1.0  # 默认值，实际会从参数中获取
        if hasattr(self, 'fluctuation_time_var'):
            fluctuation_time = float(self.fluctuation_time_var.get())
        
        time_idx = np.argmax(t >= fluctuation_time)
        if time_idx < len(rpm) and show_annotations:
            rpm_at_time = rpm[time_idx]
            rpm_fluctuation_percent = ((rpm_at_time - rpm_base) / rpm_base) * 100
            
            # 绘制指定时刻标记线
            self.axs2[0].axvline(x=fluctuation_time, color='green', linestyle='--', linewidth=1.0, label=f'{fluctuation_time}秒标记')
            
            # 标注波动率
            self.axs2[0].annotate(
                f'{fluctuation_time}秒时转速波动率: {rpm_fluctuation_percent:.2f}%',
                xy=(fluctuation_time, rpm_at_time),
                xytext=(10, 10), textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.3', fc='green', alpha=0.7),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.3')
            )

        self.axs2[0].set_ylabel("转速 (rpm)", fontsize=11)
        if hess_disabled:
            self.axs2[0].set_title("发电机组转速（原始负载，无HESS）", fontsize=12, pad=8, color='darkred')
        else:
            self.axs2[0].set_title("发电机组转速（HESS稳定效果）", fontsize=12, pad=8)
        if self.show_legend_var.get():
            self.axs2[0].legend(fontsize=10, loc='upper right')
        self.axs2[0].grid(True, alpha=0.3)
        




        # 应用用户设置的Y轴范围
        if y_rpm_min is not None and y_rpm_max is not None:
            self.axs2[0].set_ylim(y_rpm_min, y_rpm_max)
            # 显示纵坐标最大最小值（可拖动，字体小一号，放在最左侧）
            if show_annotations:
                # Get current X-axis limits
                x_min, x_max = self.axs2[0].get_xlim()
                self.rpm_max_annot = self.axs2[0].annotate(f'Max: {y_rpm_max:.2f}', 
                                                     xy=(x_min, y_rpm_max), 
                                                     ha='left', va='bottom', 
                                                     fontsize=7, color='blue',
                                                     bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                                                     picker=5)
                self.rpm_min_annot = self.axs2[0].annotate(f'Min: {y_rpm_min:.2f}', 
                                     xy=(x_min, y_rpm_min), 
                                     ha='left', va='top', 
                                     fontsize=7, color='blue',
                                     bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                                     picker=5)
        else:
            # 自动设置范围
            rpm_min_plot = min(rpm) * 0.999
            rpm_max_plot = max(rpm) * 1.001
            self.axs2[0].set_ylim(rpm_min_plot, rpm_max_plot)
            # 显示纵坐标最大最小值（可拖动，字体小一号，放在最左侧）
            if show_annotations:
                # Get current X-axis limits
                x_min, x_max = self.axs2[0].get_xlim()
                self.rpm_max_annot = self.axs2[0].annotate(f'Max: {rpm_max_plot:.2f}', 
                                                     xy=(x_min, rpm_max_plot), 
                                                     ha='left', va='bottom', 
                                                     fontsize=7, color='blue',
                                                     bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                                                     picker=5)
                self.rpm_min_annot = self.axs2[0].annotate(f'Min: {rpm_min_plot:.2f}', 
                                     xy=(x_min, rpm_min_plot), 
                                     ha='left', va='top', 
                                     fontsize=7, color='blue',
                                     bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                                     picker=5)
        


        # ---------------- 电压图 ----------------
        self.axs2[1].plot(t, VkV, 'r', linewidth=2.0, label=f'实际电压')
        self.axs2[1].axhline(V_base_kV, color="gray", ls="--", lw=1.5, label=f"额定电压 {V_base_kV:.2f} kV")

        if hess_disabled:
            v_fluctuation = VkV - V_base_kV
            max_v_dev_idx = np.argmax(np.abs(v_fluctuation))
            max_v_dev = v_fluctuation[max_v_dev_idx]
            if show_annotations:
                self.axs2[1].annotate(
                    f'最大偏差: {max_v_dev:.3f}kV',
                    xy=(t[0], VkV[max_v_dev_idx]),
                    xytext=(10, -20), textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.3', fc='lightblue', alpha=0.7),
                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.3')
                )
        
        # 指定时刻波动率标注
        fluctuation_time = 1.0  # 默认值，实际会从参数中获取
        if hasattr(self, 'fluctuation_time_var'):
            fluctuation_time = float(self.fluctuation_time_var.get())
        
        time_idx = np.argmax(t >= fluctuation_time)
        if time_idx < len(VkV) and show_annotations:
            v_at_time = VkV[time_idx]
            v_fluctuation_percent = ((v_at_time - V_base_kV) / V_base_kV) * 100
            
            # 绘制指定时刻标记线
            self.axs2[1].axvline(x=fluctuation_time, color='green', linestyle='--', linewidth=1.0, label=f'{fluctuation_time}秒标记')
            
            # 标注波动率
            self.axs2[1].annotate(
                f'{fluctuation_time}秒时电压波动率: {v_fluctuation_percent:.2f}%',
                xy=(fluctuation_time, v_at_time),
                xytext=(10, 10), textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.3', fc='green', alpha=0.7),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.3')
            )

        self.axs2[1].set_ylabel("电压 (kV)", fontsize=11)
        self.axs2[1].set_xlabel("时间 (s)", fontsize=11)
        if hess_disabled:
            self.axs2[1].set_title("发电机组电压（原始负载，无HESS）", fontsize=12, pad=8, color='darkred')
        else:
            self.axs2[1].set_title("发电机组电压（HESS稳定效果）", fontsize=12, pad=8)
        if self.show_legend_var.get():
            self.axs2[1].legend(fontsize=10, loc='upper right')
        self.axs2[1].grid(True, alpha=0.3)
        




        # 应用用户设置的Y轴范围
        if y_voltage_min is not None and y_voltage_max is not None:
            self.axs2[1].set_ylim(y_voltage_min, y_voltage_max)
            # 显示纵坐标最大最小值（可拖动，字体小一号，放在最左侧）
            if show_annotations:
                # Get current X-axis limits
                x_min, x_max = self.axs2[1].get_xlim()
                self.voltage_max_annot = self.axs2[1].annotate(f'Max: {y_voltage_max:.3f}', 
                                                     xy=(x_min, y_voltage_max), 
                                                     ha='left', va='bottom', 
                                                     fontsize=7, color='blue',
                                                     bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                                                     picker=5)
                self.voltage_min_annot = self.axs2[1].annotate(f'Min: {y_voltage_min:.3f}', 
                                     xy=(x_min, y_voltage_min), 
                                     ha='left', va='top', 
                                     fontsize=7, color='blue',
                                     bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                                     picker=5)
        else:
            # 自动设置范围
            v_min_plot = min(VkV) * 0.999
            v_max_plot = max(VkV) * 1.001
            self.axs2[1].set_ylim(v_min_plot, v_max_plot)
            # 显示纵坐标最大最小值（可拖动，字体小一号，放在最左侧）
            if show_annotations:
                # Get current X-axis limits
                x_min, x_max = self.axs2[1].get_xlim()
                self.voltage_max_annot = self.axs2[1].annotate(f'Max: {v_max_plot:.3f}', 
                                                     xy=(x_min, v_max_plot), 
                                                     ha='left', va='bottom', 
                                                     fontsize=7, color='blue',
                                                     bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                                                     picker=5)
                self.voltage_min_annot = self.axs2[1].annotate(f'Min: {v_min_plot:.3f}', 
                                     xy=(x_min, v_min_plot), 
                                     ha='left', va='top', 
                                     fontsize=7, color='blue',
                                     bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                                     picker=5)
        


        # ---------------- SOC图 ----------------
        if not hess_disabled:
            self.axs3.plot(t, SOC_ESS, 'b-', linewidth=2, label='BESS SOC')
            self.axs3.plot(t, SOC_SC, 'r-', linewidth=2, label='SC SOC')
            self.axs3.axhline(self.hess_params.ess_charge_stop_soc, c='g', ls='--', lw=1.5, label='充电停止阈值')
            self.axs3.set_xlabel('时间 (s)', fontsize=11)
            self.axs3.set_ylabel('SOC', fontsize=11)
            self.axs3.set_title('储能SOC变化', fontsize=12, pad=8)
            

            
            # 应用用户设置的Y轴范围
            if y_soc_min is not None and y_soc_max is not None:
                self.axs3.set_ylim(y_soc_min, y_soc_max)
                # 显示纵坐标最大最小值（可拖动，字体小一号，放在最左侧）
                if show_annotations:
                    # Get current X-axis limits
                    x_min, x_max = self.axs3.get_xlim()
                    self.soc_max_annot = self.axs3.annotate(f'Max: {y_soc_max:.3f}', 
                                                          xy=(x_min, y_soc_max), 
                                                          ha='left', va='bottom', 
                                                          fontsize=7, color='blue',
                                                          bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                                                          picker=5)
                    self.soc_min_annot = self.axs3.annotate(f'Min: {y_soc_min:.3f}', 
                                             xy=(x_min, y_soc_min), 
                                             ha='left', va='top', 
                                             fontsize=7, color='blue',
                                             bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                                             picker=5)
                

            else:
                # 自动设置范围
                self.axs3.set_ylim(0.15, 0.85)
                y_min, y_max = self.axs3.get_ylim()
                # 显示纵坐标最大最小值（可拖动，字体小一号，放在最左侧）
                if show_annotations:
                    # Get current X-axis limits
                    x_min, x_max = self.axs3.get_xlim()
                    self.soc_max_annot = self.axs3.annotate(f'Max: {y_max:.3f}', 
                                                          xy=(x_min, y_max), 
                                                          ha='left', va='bottom', 
                                                          fontsize=7, color='blue',
                                                          bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                                                          picker=5)
                    self.soc_min_annot = self.axs3.annotate(f'Min: {y_min:.3f}', 
                                             xy=(x_min, y_min), 
                                             ha='left', va='top', 
                                             fontsize=7, color='blue',
                                             bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                                             picker=5)
                

            
            if self.show_legend_var.get():
                self.axs3.legend(fontsize=10, loc='upper right')
            self.axs3.grid(True, alpha=0.3)
        else:
            self.axs3.clear()
            self.axs3.text(0.5, 0.5, 'HESS已禁用\n无储能SOC变化', ha='center', va='center', transform=self.axs3.transAxes, fontsize=14, color='darkred')
            self.axs3.set_title('储能SOC（禁用状态）', fontsize=12, pad=8, color='darkred')
            self.axs3.set_xlabel('时间 (s)', fontsize=11)

        self.canvas1.draw()
        self.canvas2.draw()
        self.canvas3.draw()


    def run_simulation(self):
        """运行仿真 - 强化禁用HESS时的原始数据分析"""
        # 更新参数
        for key in self.params.keys():
            try:
                self.params[key] = float(self.param_vars[key].get())
            except ValueError:
                messagebox.showerror("错误", f"参数 {key} 的值无效")
                return
        
        # 更新HESS参数
        for key in self.hess_param_vars.keys():
            try:
                setattr(self.hess_params, key, float(self.hess_param_vars[key].get()))
            except ValueError:
                pass
        
        # 禁用运行按钮
        self.run_btn.config(state=tk.DISABLED)
        self.root.update()
        
        try:
            # 根据负载模式选择数据
            load_data = None
            if self.load_mode_var.get() == "csv" and self.csv_load_data is not None:
                load_data = self.csv_load_data
            
            # 标记是否禁用HESS
            hess_disabled = not self.hess_enable_var.get()
            
            # 如果禁用HESS，创建空的HESS参数（完全不参与调节）
            if hess_disabled:
                dummy_hess_params = HESS_Params()
                dummy_hess_params.P_ESS_max = 0.0
                dummy_hess_params.P_SC_max = 0.0
                dummy_hess_params.R_ESS_max = 0.0
                dummy_hess_params.R_SC_max = 0.0
                hess_params_to_use = dummy_hess_params
            else:
                hess_params_to_use = self.hess_params
            
            # 运行联合仿真
            (t, P_load_original, P_load_hess, P_storage_total, 
             P_ESS, P_SC, SOC_ESS, SOC_SC, rpm, VkV, omega, P_load_base, P_load_average_total, P_load_average_real_time, P_preload_curve) = simulate_dg_hess_ode(
                self.params, hess_params_to_use, load_data)
            
            # ===================== 强化：禁用HESS时的原始数据深度分析 =====================
            rpm_base = self.params["rpm_base"]
            v_base = self.params["V_base_kV"]
            P_base_MW = self.params.get("P_base_MW", 2.0)  # 负载基准值2MW
            
            # 1. 转速分析（原始负载下）
            rpm_fluctuation = rpm - rpm_base  # 转速偏差
            rpm_max_deviation = np.max(np.abs(rpm_fluctuation))  # 最大转速偏差
            rpm_rms = np.sqrt(np.mean(rpm_fluctuation**2))  # 转速偏差均方根
            rpm_recovery_time, rpm_recovery_status = self.calculate_recovery_time(t, rpm)
            
            # 2. 电压分析（原始负载下）
            v_fluctuation = VkV - v_base  # 电压偏差
            v_max_deviation = np.max(np.abs(v_fluctuation))  # 最大电压偏差
            v_rms = np.sqrt(np.mean(v_fluctuation**2))  # 电压偏差均方根
            
            # 3. 功率波动分析
            load_fluctuation = P_load_original - P_load_base
            load_max_fluctuation = np.max(np.abs(load_fluctuation))
            load_rms = np.sqrt(np.mean(load_fluctuation**2))
            
            # 4. 波动计算
            # 获取用户设置的波动计算时间
            fluctuation_time = float(self.fluctuation_time_var.get())
            
            # 找到波动计算时间对应的索引
            time_idx = np.argmax(t >= fluctuation_time)
            
            # 计算指定时刻的转速波动率
            if time_idx < len(rpm):
                rpm_at_time = rpm[time_idx]
                rpm_fluctuation_percent = ((rpm_at_time - rpm_base) / rpm_base) * 100
            else:
                rpm_fluctuation_percent = 0.0
            
            # 计算指定时刻的电压波动率
            if time_idx < len(VkV):
                v_at_time = VkV[time_idx]
                v_fluctuation_percent = ((v_at_time - v_base) / v_base) * 100
            else:
                v_fluctuation_percent = 0.0
            
            # 计算实际功率值（MW）
            P_load_original_MW = P_load_original * P_base_MW
            P_load_hess_MW = P_load_hess * P_base_MW
            P_storage_total_MW = P_storage_total * P_base_MW
            P_ESS_MW = P_ESS * P_base_MW
            P_SC_MW = P_SC * P_base_MW
            
            # ===================== 更新结果显示 =====================
            # 基础指标
            self.result_vars["rpm_min"].set(f"{np.min(rpm):.2f}")
            self.result_vars["rpm_max"].set(f"{np.max(rpm):.2f}")
            self.result_vars["v_min"].set(f"{np.min(VkV):.3f}")
            self.result_vars["v_max"].set(f"{np.max(VkV):.3f}")
            
            # 禁用HESS时显示更详细的原始波动分析
            if hess_disabled:
                # 转速偏差详情
                self.result_vars["rpm_recovery"].set(f"{rpm_recovery_time} (最大偏差:{rpm_max_deviation:.2f}rpm)")
                self.result_vars["recovery_check"].set(f"{rpm_recovery_status} (RMS:{rpm_rms:.2f}rpm)")
                # 电压偏差详情
                self.result_vars["dv_range"].set(f"最大偏差:{v_max_deviation:.3f}kV (RMS:{v_rms:.3f}kV) | 原始负载波动:{load_max_fluctuation:.2f}p.u. ({load_max_fluctuation*P_base_MW:.2f}MW)")
                # 功率波动抑制率（禁用HESS时为0）
                self.result_vars["power_suppression"].set("0.00% (无HESS平抑)")
                # SOC（禁用HESS时无意义）
                self.result_vars["ess_avg_soc"].set("N/A")
                self.result_vars["sc_avg_soc"].set("N/A")
            else:
                # 启用HESS时的常规分析
                orig_range = np.max(P_load_original) - np.min(P_load_original)
                hess_range = np.max(P_load_hess) - np.min(P_load_hess)
                suppression_rate = (orig_range - hess_range) / orig_range * 100 if orig_range > 0 else 0
                
                self.result_vars["rpm_recovery"].set(rpm_recovery_time)
                self.result_vars["recovery_check"].set(rpm_recovery_status)
                self.result_vars["dv_range"].set(f"{np.min(v_fluctuation):.3f} ~ {np.max(v_fluctuation):.3f} kV (相对 {v_base} kV)")
                self.result_vars["power_suppression"].set(f"{suppression_rate:.2f}%")
                
                # SOC平均值
                self.result_vars["ess_avg_soc"].set(f"{np.mean(SOC_ESS):.4f}")
                self.result_vars["sc_avg_soc"].set(f"{np.mean(SOC_SC):.4f}")
            
            # 更新指定时刻的波动率
            self.result_vars["rpm_fluctuation_at_time"].set(f"{rpm_fluctuation_percent:.2f}%")
            self.result_vars["v_fluctuation_at_time"].set(f"{v_fluctuation_percent:.2f}%")
            
            # 保存仿真结果数据
            self.simulation_results = (t, P_load_original, P_load_hess, P_storage_total,
                                      P_ESS, P_SC, SOC_ESS, SOC_SC, rpm, VkV, omega, P_load_base, P_load_average_total, P_load_average_real_time, P_preload_curve, hess_disabled)
            
            # 更新绘图（强化禁用HESS时的波形标注）
            self.update_plots(t, P_load_original, P_load_hess, P_storage_total,
                             P_ESS, P_SC, SOC_ESS, SOC_SC, rpm, VkV, omega, P_load_base, P_load_average_total, P_load_average_real_time, P_preload_curve, hess_disabled)
            
        except Exception as e:
            messagebox.showerror("仿真错误", f"运行仿真时出错：{str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # 启用运行按钮
            self.run_btn.config(state=tk.NORMAL)

# ====================== 8. 主程序入口 ========================
if __name__ == "__main__":
    print("启动程序...")
    print("创建Tk根窗口...")
    root = tk.Tk()
    print("创建应用实例...")
    app = DG_HESS_SimulatorApp(root)
    
    # 处理窗口关闭
    def on_closing():
        print("关闭窗口...")
        plt.close('all')
        root.destroy()
        sys.exit(0)
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    print("进入主循环...")
    root.mainloop()
    print("程序结束")
