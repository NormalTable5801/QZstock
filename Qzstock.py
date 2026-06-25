import customtkinter as ctk
from tkinter import messagebox, simpledialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import numpy as np
from datetime import datetime
import akshare as ak
from threading import Thread, Lock
import queue
import sys
import re

class NocturneTheme:
    # 背景色 - 多层级深度
    BG_PRIMARY = "#0D1117"      # 主背景
    BG_SECONDARY = "#161B22"    # 卡片/面板背景
    BG_TERTIARY = "#21262D"     # 悬浮/输入框背景
    BG_QUATERNARY = "#30363D"   # 边框/分割线
    
    # 文字色 - 四级灰度
    TEXT_PRIMARY = "#E6EDF3"    # 主文字
    TEXT_SECONDARY = "#8B949E"  # 次要文字
    TEXT_TERTIARY = "#6E7681"   # 辅助文字
    TEXT_DISABLED = "#484F58"   # 禁用文字
    
    # 涨跌色 - 中国惯例：红涨绿跌
    UP = "#F85149"              # 上涨
    DOWN = "#3FB950"            # 下跌
    FLAT = "#8B949E"            # 平盘
    UP_LIGHT = "rgba(248, 81, 73, 0.15)"
    DOWN_LIGHT = "rgba(63, 185, 80, 0.15)"
    
    # 品牌色
    BRAND_PRIMARY = "#58A6FF"   # 主品牌色
    BRAND_SECONDARY = "#1F6FEB" # 深色品牌色
    
    # 功能色
    SUCCESS = "#3FB950"
    WARNING = "#D29922"
    ERROR = "#F85149"
    INFO = "#58A6FF"
    
    # 图表色
    CHART_LINE1 = "#58A6FF"     # 蓝 - 主数据
    CHART_LINE2 = "#F85149"     # 红 - 对比数据
    CHART_LINE3 = "#3FB950"     # 绿
    CHART_LINE4 = "#D29922"     # 金
    CHART_GRID = "#21262D"      # 网格线
    CHART_AXIS = "#30363D"      # 坐标轴

# 设置customtkinter主题
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# 设置matplotlib深色主题
plt.rcParams.update({
    'figure.facecolor': NocturneTheme.BG_SECONDARY,
    'axes.facecolor': NocturneTheme.BG_SECONDARY,
    'axes.edgecolor': NocturneTheme.CHART_AXIS,
    'axes.labelcolor': NocturneTheme.TEXT_SECONDARY,
    'text.color': NocturneTheme.TEXT_PRIMARY,
    'xtick.color': NocturneTheme.TEXT_SECONDARY,
    'ytick.color': NocturneTheme.TEXT_SECONDARY,
    'grid.color': NocturneTheme.CHART_GRID,
    'grid.alpha': 0.5,
    'legend.facecolor': NocturneTheme.BG_TERTIARY,
    'legend.edgecolor': NocturneTheme.BG_QUATERNARY,
    'legend.labelcolor': NocturneTheme.TEXT_PRIMARY,
    'font.sans-serif': ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'sans-serif'],
    'axes.unicode_minus': False,
})

global gpn
gpn = ""

class StockStrategyApp:
    
    def __init__(self, master):
        self.master = master
        self.setup_main_window()
        self.initialize_variables()
        self.setup_ui_components()
        self.start_worker_thread()
        self.current_code = ""
        self.code_label.configure(text="请输入代码")
        self.status_var.set("请点击「输入代码」按钮开始")
        self.run_btn.configure(state="disabled")
    
    def setup_main_window(self):
        """配置主窗口"""
        self.master.title("QZStock")
        self.master.geometry("1280x800")
        self.master.configure(fg_color=NocturneTheme.BG_PRIMARY)
        self.master.protocol("WM_DELETE_WINDOW", self.safe_exit)
    
    def initialize_variables(self):
        """初始化变量"""
        self.SETTINGS = {
            'ema_periods': [5, 13, 30],
            'macd_fast': 9,
            'macd_slow': 21,
            'macd_signal': 6,
            'adx_period': 14,
            'adx_threshold': 20,
            'volume_ratio_threshold': 0.5,
            'max_stop_loss': 0.30,
            'rsi_overbought': 75,
            'rsi_oversold': 30,
            'commission_rate': 0.0003,
            'slippage_rate': 0.0005
        }
        self.current_code = ""
        self.history = []
        self.running = True
        self.task_queue = queue.Queue()
        self.lock = Lock()
        # 保存滑块引用，用于重置参数时更新滑块位置
        self.sliders = {}
    
    def setup_ui_components(self):
        """构建UI组件"""
        # 主框架
        main_frame = ctk.CTkFrame(
            self.master, 
            fg_color=NocturneTheme.BG_PRIMARY,
            corner_radius=0
        )
        main_frame.pack(fill="both", expand=True, padx=12, pady=12)
        
        # 控制面板
        control_frame = ctk.CTkFrame(
            main_frame, 
            fg_color=NocturneTheme.BG_SECONDARY,
            corner_radius=8,
            border_width=1,
            border_color=NocturneTheme.BG_QUATERNARY
        )
        control_frame.pack(side="left", fill="y", padx=(0, 6))
        
        # 控制面板标题
        control_title = ctk.CTkLabel(
            control_frame,
            text="参数控制",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=NocturneTheme.TEXT_PRIMARY
        )
        control_title.pack(padx=16, pady=(12, 8), anchor="w")
        
        # 结果面板
        result_frame = ctk.CTkFrame(
            main_frame, 
            fg_color=NocturneTheme.BG_SECONDARY,
            corner_radius=8,
            border_width=1,
            border_color=NocturneTheme.BG_QUATERNARY
        )
        result_frame.pack(side="right", fill="both", expand=True, padx=(6, 0))
        
        # 结果面板标题
        result_title = ctk.CTkLabel(
            result_frame,
            text="策略表现",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=NocturneTheme.TEXT_PRIMARY
        )
        result_title.pack(padx=16, pady=(12, 8), anchor="w")
        
        # 控制面板组件
        self.create_control_panel(control_frame)
        self.create_result_panel(result_frame)
        
        # 状态栏
        self.status_var = ctk.StringVar(value="就绪")
        status_bar = ctk.CTkLabel(
            self.master,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=12),
            text_color=NocturneTheme.TEXT_TERTIARY,
            fg_color=NocturneTheme.BG_SECONDARY,
            anchor="w",
            padx=12,
            pady=6
        )
        status_bar.pack(side="bottom", fill="x")
    
    def create_control_panel(self, parent):
        """创建控制面板（带滚动条）"""
        # 修复：使用CTkScrollableFrame替代普通Frame，支持垂直滚动
        content = ctk.CTkScrollableFrame(
            parent,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_fg_color=NocturneTheme.BG_QUATERNARY,
            scrollbar_button_color=NocturneTheme.BG_TERTIARY,
            scrollbar_button_hover_color=NocturneTheme.TEXT_TERTIARY,
            width=260
        )
        content.pack(fill="both", expand=True, padx=8, pady=(0, 12))
        
        # 股票代码显示
        code_frame = ctk.CTkFrame(
            content,
            fg_color=NocturneTheme.BG_TERTIARY,
            corner_radius=6
        )
        code_frame.pack(fill="x", pady=(0, 12))
        
        ctk.CTkLabel(
            code_frame,
            text="当前代码",
            font=ctk.CTkFont(size=11),
            text_color=NocturneTheme.TEXT_SECONDARY
        ).pack(padx=10, pady=(8, 0), anchor="w")
        
        self.code_label = ctk.CTkLabel(
            code_frame,
            text="未加载",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=NocturneTheme.TEXT_PRIMARY
        )
        self.code_label.pack(padx=10, pady=(0, 8), anchor="w")
        
        # 参数控制滑块
        self.create_slider_controls(content)
        
        # 功能按钮
        btn_frame = ctk.CTkFrame(
            content,
            fg_color="transparent",
            corner_radius=0
        )
        btn_frame.pack(fill="x", pady=(16, 0))
        
        self.run_btn = ctk.CTkButton(
            btn_frame,
            text="执行策略",
            command=lambda: self.add_task('run_strategy'),
            state="disabled",
            fg_color=NocturneTheme.BRAND_PRIMARY,
            hover_color=NocturneTheme.BRAND_SECONDARY,
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=6,
            height=36
        )
        self.run_btn.pack(fill="x", pady=(0, 8))
        
        ctk.CTkButton(
            btn_frame,
            text="输入代码",
            command=lambda: self.add_task('change_code'),
            fg_color=NocturneTheme.BG_TERTIARY,
            hover_color=NocturneTheme.BG_QUATERNARY,
            text_color=NocturneTheme.TEXT_PRIMARY,
            font=ctk.CTkFont(size=13),
            corner_radius=6,
            height=36,
            border_width=1,
            border_color=NocturneTheme.BG_QUATERNARY
        ).pack(fill="x", pady=(0, 8))
        
        ctk.CTkButton(
            btn_frame,
            text="重置参数",
            command=self.reset_parameters,
            fg_color="transparent",
            hover_color=NocturneTheme.BG_TERTIARY,
            text_color=NocturneTheme.TEXT_SECONDARY,
            font=ctk.CTkFont(size=12),
            corner_radius=6,
            height=32
        ).pack(fill="x")
    
    def create_slider_controls(self, parent):
        """创建参数滑块控件"""
        # EMA参数组
        self._create_param_group(parent, "EMA 周期")
        
        ema_params = [
            ('ema_short', '短周期', 3, 20, 0),
            ('ema_mid', '中周期', 10, 40, 1),
            ('ema_long', '长周期', 20, 60, 2),
        ]
        for key, label, frm, to, idx in ema_params:
            self._create_slider(parent, label, frm, to, 
                              int(self.SETTINGS['ema_periods'][idx]),
                              lambda val, i=idx: self.update_ema_period(i, int(val)),
                              key, is_int=True)
        
        # MACD参数组
        self._create_param_group(parent, "MACD 参数")
        
        macd_params = [
            ('macd_fast', '快线', 5, 20),
            ('macd_slow', '慢线', 12, 40),
            ('macd_signal', '信号周期', 3, 14)
        ]
        for key, label, frm, to in macd_params:
            self._create_slider(parent, label, frm, to,
                              int(self.SETTINGS[key]),
                              lambda val, k=key: self.update_setting(k, int(val)),
                              key, is_int=True)
        
        # 风险参数组
        self._create_param_group(parent, "风险控制")
        
        # 止损比例
        self._create_slider(parent, '止损比例', 0, 50,
                          int(self.SETTINGS['max_stop_loss'] * 100),
                          lambda val: self.update_risk_param('max_stop_loss', int(val)),
                          'max_stop_loss', is_int=True, suffix="%")
        
        # 量比阈值
        self._create_slider(parent, '量比阈值', 0.1, 3.0,
                          self.SETTINGS['volume_ratio_threshold'],
                          lambda val: self.update_risk_param('volume_ratio_threshold', val),
                          'volume_ratio_threshold', is_int=False)
        
        # ADX参数组
        self._create_param_group(parent, "趋势过滤")
        
        self._create_slider(parent, 'ADX 阈值', 10, 40,
                          int(self.SETTINGS['adx_threshold']),
                          lambda val: self.update_setting('adx_threshold', int(val)),
                          'adx_threshold', is_int=True)
    
    def _create_param_group(self, parent, title):
        """创建参数分组标题"""
        group_frame = ctk.CTkFrame(
            parent,
            fg_color="transparent",
            corner_radius=0
        )
        group_frame.pack(fill="x", pady=(12, 4))
        
        ctk.CTkLabel(
            group_frame,
            text=title,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=NocturneTheme.BRAND_PRIMARY
        ).pack(anchor="w")
        
        # 分隔线
        separator = ctk.CTkFrame(
            parent,
            height=1,
            fg_color=NocturneTheme.BG_QUATERNARY,
            corner_radius=0
        )
        separator.pack(fill="x", pady=(0, 8))
    
    def _create_slider(self, parent, label, from_, to, default, command, var_name, 
                       is_int=True, suffix=""):
        """创建单个滑块控件"""
        slider_frame = ctk.CTkFrame(
            parent,
            fg_color="transparent",
            corner_radius=0
        )
        slider_frame.pack(fill="x", pady=4)
        
        # 标签行
        label_row = ctk.CTkFrame(
            slider_frame,
            fg_color="transparent",
            corner_radius=0
        )
        label_row.pack(fill="x")
        
        ctk.CTkLabel(
            label_row,
            text=label,
            font=ctk.CTkFont(size=12),
            text_color=NocturneTheme.TEXT_SECONDARY
        ).pack(side="left")
        
        # 值显示标签（修复：不使用textvariable，统一用configure更新，避免冲突）
        if is_int:
            value_text = f"{int(default)}{suffix}"
        else:
            value_text = f"{float(default):.1f}{suffix}"
        
        value_label = ctk.CTkLabel(
            label_row,
            text=value_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=NocturneTheme.TEXT_PRIMARY
        )
        value_label.pack(side="right")
        
        # 更新值显示的函数
        def update_value(val):
            if is_int:
                value_label.configure(text=f"{int(val)}{suffix}")
            else:
                value_label.configure(text=f"{float(val):.1f}{suffix}")
            command(val)
        
        # 滑块
        slider = ctk.CTkSlider(
            slider_frame,
            from_=from_,
            to=to,
            number_of_steps=int((to - from_) / (1 if is_int else 0.1)),
            command=update_value,
            fg_color=NocturneTheme.BG_TERTIARY,
            progress_color=NocturneTheme.BRAND_PRIMARY,
            button_color=NocturneTheme.BRAND_PRIMARY,
            button_hover_color=NocturneTheme.BRAND_SECONDARY,
            height=4
        )
        slider.set(default)
        slider.pack(fill="x", pady=(4, 0))
        
        # 保存滑块引用，用于重置参数
        self.sliders[var_name] = slider
    
    def create_result_panel(self, parent):
        """创建结果展示面板"""
        # 内容容器
        content = ctk.CTkFrame(
            parent,
            fg_color="transparent",
            corner_radius=0
        )
        content.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        
        # 净值曲线图
        chart_frame = ctk.CTkFrame(
            content,
            fg_color=NocturneTheme.BG_TERTIARY,
            corner_radius=6
        )
        chart_frame.pack(fill="both", expand=True, pady=(0, 12))
        
        self.fig, self.ax = plt.subplots(figsize=(12, 5))
        self.fig.patch.set_facecolor(NocturneTheme.BG_TERTIARY)
        self.ax.set_facecolor(NocturneTheme.BG_TERTIARY)
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)
        
        # 底部区域：交易信号 + 回测报告
        bottom_frame = ctk.CTkFrame(
            content,
            fg_color="transparent",
            corner_radius=0
        )
        bottom_frame.pack(fill="x")
        
        # 交易信号表格
        signal_frame = ctk.CTkFrame(
            bottom_frame,
            fg_color=NocturneTheme.BG_TERTIARY,
            corner_radius=6
        )
        signal_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))
        
        ctk.CTkLabel(
            signal_frame,
            text="最近交易信号",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=NocturneTheme.TEXT_PRIMARY
        ).pack(padx=12, pady=(8, 4), anchor="w")
        
        # 信号表格（用CTkScrollableFrame + 标签）
        self.signal_container = ctk.CTkScrollableFrame(
            signal_frame,
            fg_color="transparent",
            scrollbar_fg_color=NocturneTheme.BG_QUATERNARY,
            scrollbar_button_color=NocturneTheme.BG_TERTIARY,
            scrollbar_button_hover_color=NocturneTheme.TEXT_TERTIARY,
            height=180
        )
        self.signal_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        # 表头
        header_frame = ctk.CTkFrame(
            self.signal_container,
            fg_color="transparent",
            corner_radius=0
        )
        header_frame.pack(fill="x", pady=(0, 4))
        
        for col, text, w in [('date', '日期', 100), ('action', '操作', 60), ('price', '价格', 80)]:
            lbl = ctk.CTkLabel(
                header_frame,
                text=text,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=NocturneTheme.TEXT_SECONDARY,
                width=w,
                anchor="center"
            )
            lbl.pack(side="left", padx=2)
        
        # 回测报告
        report_frame = ctk.CTkFrame(
            bottom_frame,
            fg_color=NocturneTheme.BG_TERTIARY,
            corner_radius=6,
            width=220
        )
        report_frame.pack(side="right", fill="y", padx=(6, 0))
        report_frame.pack_propagate(False)
        
        ctk.CTkLabel(
            report_frame,
            text="策略统计",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=NocturneTheme.TEXT_PRIMARY
        ).pack(padx=12, pady=(8, 4), anchor="w")
        
        # 统计项（可滚动）
        stats_scroll = ctk.CTkScrollableFrame(
            report_frame,
            fg_color="transparent",
            scrollbar_fg_color=NocturneTheme.BG_QUATERNARY,
            scrollbar_button_color=NocturneTheme.BG_TERTIARY,
            scrollbar_button_hover_color=NocturneTheme.TEXT_TERTIARY
        )
        stats_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        self.stats_labels = {}
        stats = [
            ('equity', '策略净值', '--'),
            ('return', '累计收益率', '--'),
            ('drawdown', '最大回撤率', '--'),
            ('trades', '总交易次数', '--'),
        ]
        
        for key, label, default in stats:
            stat_item = ctk.CTkFrame(
                stats_scroll,
                fg_color="transparent",
                corner_radius=0
            )
            stat_item.pack(fill="x", padx=4, pady=4)
            
            ctk.CTkLabel(
                stat_item,
                text=label,
                font=ctk.CTkFont(size=11),
                text_color=NocturneTheme.TEXT_SECONDARY
            ).pack(anchor="w")
            
            value_label = ctk.CTkLabel(
                stat_item,
                text=default,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=NocturneTheme.TEXT_PRIMARY
            )
            value_label.pack(anchor="w", pady=(2, 0))
            
            self.stats_labels[key] = value_label
    
    def start_worker_thread(self):
        """启动工作线程"""
        self.worker_thread = Thread(target=self.process_tasks, daemon=True)
        self.worker_thread.start()
    
    def process_tasks(self):
        """处理任务队列"""
        while self.running:
            try:
                task_type = self.task_queue.get(timeout=0.1)
                with self.lock:
                    if task_type == 'load_data':
                        self.cxmc()
                        self.execute_load_data()
                    elif task_type == 'run_strategy':
                        self.execute_strategy()
                    elif task_type == 'change_code':
                        self.execute_change_code()
            except queue.Empty:
                continue
            except Exception as e:
                self.show_error(f"任务处理错误: {str(e)}")
    
    def add_task(self, task_type):
        """添加任务到队列"""
        if self.running:
            self.task_queue.put(task_type)
    
    def init_data_loading(self):
        """初始化数据加载"""
        code = self.get_stock_code()
        if code:
            self.current_code = code
            self.code_label.configure(text=f"{code} (加载中...)", text_color=NocturneTheme.WARNING)
            self.add_task('load_data')
        else:
            self.status_var.set("请输入股票代码！")
            self.run_btn.configure(state="normal")
    
    def get_stock_code(self):
        """获取股票代码输入"""
        while True:
            code = simpledialog.askstring("输入代码", "请输入6位股票代码:", parent=self.master)
            if code is None:
                return None
            
            if not code.isdigit():
                self.show_error("代码必须为纯数字！")
                continue
                
            if len(code) != 6:
                self.show_error("代码必须为6位长度！")
                continue
                
            return code
    
    def cxmc(self):
        global gpn
        try:
            stki = ak.stock_individual_info_em(symbol=self.current_code)
            filtered_df = stki[stki['item'] == '股票简称']
            gpp = filtered_df['value'].values
            gpa = str(gpp)
            match = re.search(r"['\"](.*?)['\"]", gpa)
            gpn = match.group(1) if match else None
        except Exception as e:
            gpn = f"获取失败：{str(e)}"
        return gpn
        
    def execute_load_data(self):
        """执行数据加载任务"""
        try:
            # 修复：UI更新通过after调度到主线程，保证线程安全
            self.master.after(0, lambda: self.status_var.set("正在下载数据..."))
            dtt = datetime.now().strftime("%Y%m%d")
            edtt = datetime.now().replace(year=datetime.now().year - 5)
            edtl = edtt.strftime("%Y%m%d")
            
            # 转换股票代码格式（新浪需要sh/sz前缀）
            code = self.current_code
            if code.startswith('6'):
                sina_code = f'sh{code}'
            else:
                sina_code = f'sz{code}'
            
            # 使用新浪数据源
            df = ak.stock_zh_a_daily(
                symbol=sina_code,
                start_date=edtl,
                end_date=dtt,
                adjust='qfq'
            )
            
            # 转换列名为中文格式
            df = df.rename(columns={
                'date': '日期',
                'open': '开盘',
                'high': '最高',
                'low': '最低',
                'close': '收盘',
                'volume': '成交量',
                'turnover': '换手率'
            })
            
            # 计算涨跌幅
            df['涨跌幅'] = df['收盘'].pct_change() * 100
            
            # 只保留需要的列
            df = df[['日期', '开盘', '最高', '最低', '收盘', '成交量', '换手率', '涨跌幅']]
            
            df.to_csv(f'stock_{self.current_code}.csv', index=False, encoding='utf_8_sig')
            self.master.after(0, self.on_data_loaded_success)
        except Exception as e:
            self.show_error(f"数据加载失败: {str(e)}")
            self.master.after(0, self.init_data_loading)
    
    def on_data_loaded_success(self):
        """数据加载成功处理"""
        self.code_label.configure(text=f"{self.current_code} (已加载)", text_color=NocturneTheme.SUCCESS)
        self.status_var.set("数据加载完成，正在执行策略...")
        self.run_btn.configure(state="normal")
        if self.current_code not in self.history:
            self.history.append(self.current_code)
        # 自动执行策略（方便测试）
        self.add_task('run_strategy')
    
    def execute_strategy(self):
        """执行策略任务"""
        try:
            # 修复：UI更新通过after调度到主线程，保证线程安全
            self.master.after(0, lambda: self.run_btn.configure(state="disabled", text="执行中..."))
            self.master.after(0, lambda: self.status_var.set("正在执行策略..."))
            
            # 加载数据
            df = pd.read_csv(
                f'stock_{self.current_code}.csv', 
                parse_dates=['日期'],
                usecols=['日期','开盘','最高','最低','收盘','成交量','换手率','涨跌幅'],
                dtype={'开盘':float, '最高':float, '最低':float, '收盘':float, '成交量':float, '换手率':float}
            )
            df.columns = ['date','open','high','low','close','volume','turnover','pct_chg']
            df = df.sort_values('date').reset_index(drop=True)
            
            # 计算指标
            df = self.calculate_technical_indicators(df)
            
            # 生成信号
            df = self.generate_trading_signals(df)
            
            # 执行回测
            result_df = self.backtest_strategy(df)
            
            # 显示结果
            self.master.after(0, lambda: self.display_results(result_df))
            
        except Exception as e:
            self.show_error(f"策略执行错误: {str(e)}")
        finally:
            self.master.after(0, lambda: self.run_btn.configure(state="normal", text="执行策略"))
            self.master.after(0, lambda: self.status_var.set("策略执行完成"))
    
    def wilder_smooth(self, series, period):
        """Wilder平滑法计算ADX"""
        return series.ewm(alpha=1/period, adjust=False).mean()
    
    def calculate_technical_indicators(self, df):
        """计算技术指标"""
        df = df.copy()
        
        # 参数安全检查
        ema_periods = []
        for p in self.SETTINGS['ema_periods']:
            period = max(1, int(p))
            ema_periods.append(period)
        self.SETTINGS['ema_periods'] = ema_periods
        
        macd_fast = max(1, int(self.SETTINGS['macd_fast']))
        macd_slow = max(1, int(self.SETTINGS['macd_slow']))
        macd_signal = max(1, int(self.SETTINGS['macd_signal']))
        
        # EMA指标
        for period in ema_periods:
            df[f'ema{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        
        # MACD指标
        df['macd_fast'] = df['close'].ewm(span=macd_fast, adjust=False).mean()
        df['macd_slow'] = df['close'].ewm(span=macd_slow, adjust=False).mean()
        df['macd_diff'] = df['macd_fast'] - df['macd_slow']
        df['macd_dea'] = df['macd_diff'].ewm(span=macd_signal, adjust=False).mean()
        df['macd_hist'] = df['macd_diff'] - df['macd_dea']
        
        # 波动率指标
        df['atr'] = (df['high'] - df['low']).rolling(self.SETTINGS['adx_period']).mean()
        df['std20'] = df['close'].rolling(20).std()
        
        # 量能指标
        df['vol_ma5'] = df['volume'].rolling(5).mean()
        df['vol_ma20'] = df['volume'].rolling(20).mean()
        df['vol_ratio'] = df['volume'] / df['vol_ma20'].replace(0, 1)
        
        # ADX指标
        tr = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift()),
                abs(df['low'] - df['close'].shift())
            )
        )
        plus_dm = df['high'].diff().where(
            (df['high'].diff() > 0) & 
            (df['high'].diff() > -df['low'].diff()), 
            0
        )
        minus_dm = -df['low'].diff().where(
            (-df['low'].diff() > 0) & 
            (-df['low'].diff() > df['high'].diff()), 
            0
        )
        atr = self.wilder_smooth(tr, self.SETTINGS['adx_period'])
        plus_di = 100 * self.wilder_smooth(plus_dm, self.SETTINGS['adx_period']) / atr
        minus_di = 100 * self.wilder_smooth(minus_dm, self.SETTINGS['adx_period']) / atr
        dx = 100 * np.abs((plus_di - minus_di) / (plus_di + minus_di + 1e-10))
        df['adx'] = self.wilder_smooth(dx, self.SETTINGS['adx_period'])
        
        # RSI指标
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        return df.dropna().reset_index(drop=True)
    
    def generate_trading_signals(self, df):
        """生成交易信号 - 完整多指标策略 + ADX过滤"""
        df = df.copy()
        df['buy'] = 0
        df['sell'] = 0
        position = False
        entry_price = 0.0
        
        # 获取EMA周期
        ema_short_period = int(self.SETTINGS['ema_periods'][0])
        ema_mid_period = int(self.SETTINGS['ema_periods'][1])
        ema_long_period = int(self.SETTINGS['ema_periods'][2])
        
        ema_short = f'ema{ema_short_period}'
        ema_mid = f'ema{ema_mid_period}'
        ema_long = f'ema{ema_long_period}'
        
        # 趋势回看周期
        trend_lookback = 5
        
        for i in range(max(ema_long_period + 1, trend_lookback + 1), len(df)):
            
            # 买入条件
            if not position:
                # 1. 趋势过滤
                price_above_ema = df['close'].iloc[i] > df[ema_long].iloc[i]
                ema_trending_up = df[ema_long].iloc[i] > df[ema_long].iloc[i-trend_lookback]
                
                # 2. 均线排列
                ma_bullish = (df[ema_short].iloc[i] > df[ema_mid].iloc[i]) and \
                             (df[ema_mid].iloc[i] > df[ema_long].iloc[i])
                
                # 3. MACD动量
                macd_bullish = df['macd_hist'].iloc[i] > 0
                macd_increasing = df['macd_hist'].iloc[i] > df['macd_hist'].iloc[i-1]
                
                # 4. 量能过滤
                volume_ok = df['vol_ratio'].iloc[i] > self.SETTINGS['volume_ratio_threshold']
                
                # 5. ADX趋势强度过滤
                adx_ok = df['adx'].iloc[i] > self.SETTINGS['adx_threshold']
                
                # 综合买入条件
                if price_above_ema and ema_trending_up and ma_bullish and macd_bullish and macd_increasing and volume_ok and adx_ok:
                    df.at[i, 'buy'] = 1
                    position = True
                    entry_price = df['close'].iloc[i]
            
            # 卖出条件
            else:
                # 1. 趋势破位
                price_below_ema = df['close'].iloc[i] < df[ema_long].iloc[i]
                
                # 2. MACD转空
                macd_bearish = df['macd_hist'].iloc[i] < 0
                
                # 3. 均线破位
                ma_bearish = df[ema_short].iloc[i] < df[ema_mid].iloc[i]
                
                # 4. 动态止损
                stop_loss = min(self.SETTINGS['max_stop_loss'], df['std20'].iloc[i] * 2.0 / entry_price)
                stop_loss_price = entry_price * (1 - stop_loss)
                stop_loss_hit = df['close'].iloc[i] < stop_loss_price
                
                # 综合卖出条件
                if price_below_ema or macd_bearish or ma_bearish or stop_loss_hit:
                    df.at[i, 'sell'] = 1
                    position = False
        
        return df
    
    def backtest_strategy(self, df, initial_capital=10000):
        """执行策略回测"""
        df = df.copy()
        df['position'] = 0
        df['equity'] = initial_capital
        df['returns'] = 0.0
        cash = initial_capital
        shares = 0
        
        for i in range(1, len(df)):
            # 买入执行
            if df['buy'].iloc[i-1] and shares == 0:
                price = df['open'].iloc[i] * (1 + self.SETTINGS['slippage_rate'])
                fee = price * 100 * self.SETTINGS['commission_rate']
                max_shares = (cash - fee) // (price * 100) * 100
                
                if max_shares > 0:
                    shares = max_shares
                    cash -= shares * price + fee
                    df.at[i, 'position'] = 1
            
            # 卖出执行
            if df['sell'].iloc[i-1] and shares > 0:
                price = df['open'].iloc[i] * (1 + self.SETTINGS['slippage_rate'])
                fee = price * shares * self.SETTINGS['commission_rate']
                cash += shares * price - fee
                shares = 0
                df.at[i, 'position'] = 0
            
            # 更新净值
            df.at[i, 'equity'] = cash + shares * df['close'].iloc[i]
        
        # 计算绩效指标
        df['returns'] = df['equity'].pct_change()
        df['cumulative'] = (1 + df['returns']).cumprod()
        df['peak'] = df['equity'].cummax()
        df['drawdown'] = (df['equity'] - df['peak']) / df['peak']
        df['max_drawdown'] = df['drawdown'].cummin()
        
        return df
    
    def display_results(self, df):
        global gpn
        """显示策略结果"""
        self.ax.clear()
    
        df['date'] = pd.to_datetime(df['date'])
      
        temp_df = df.set_index('date')
        monthly_returns = temp_df['equity'].resample('M').last().pct_change() * 100
        monthly_dates = monthly_returns.index + pd.offsets.MonthBegin(-1) + pd.DateOffset(days=14)
        
        # 绘制策略净值
        self.ax.plot(df['date'], df['equity'], label='策略净值', 
                    color=NocturneTheme.CHART_LINE1, linewidth=1.5)
        
        # 绘制股票价格（归一化）
        self.ax.plot(df['date'], df['close']/df['close'].iloc[0]*10000, 
                    label=self.current_code, color=NocturneTheme.CHART_LINE2, linewidth=1, alpha=0.8)
        
        # 绘制月度收益柱状图
        ax2 = self.ax.twinx()
        colors = [NocturneTheme.UP if x > 0 else NocturneTheme.DOWN for x in monthly_returns]
        ax2.bar(monthly_dates, monthly_returns, 
                width=20, alpha=0.2, color=colors)
        
        # 图表样式
        self.ax.set_title('策略净值曲线', fontsize=12, pad=10, color=NocturneTheme.TEXT_PRIMARY)
        self.ax.legend(loc='upper left', fontsize=9)
        self.ax.grid(True, alpha=0.3)
        self.ax.tick_params(axis='both', labelsize=9)
        ax2.tick_params(axis='y', labelsize=9)
        
        # 设置坐标轴颜色
        for spine in self.ax.spines.values():
            spine.set_color(NocturneTheme.CHART_AXIS)
        for spine in ax2.spines.values():
            spine.set_color(NocturneTheme.CHART_AXIS)
        
        self.canvas.draw()
        
        # 更新交易信号表格
        for widget in self.signal_container.winfo_children():
            if widget not in [self.signal_container.winfo_children()[0]]:
                widget.destroy()
        
        signals = df[(df['buy'] > 0) | (df['sell'] > 0)].tail(10)
        for _, row in signals.iterrows():
            is_buy = row['buy'] > 0
            action = '买入' if is_buy else '卖出'
            color = NocturneTheme.UP if is_buy else NocturneTheme.DOWN
            
            signal_row = ctk.CTkFrame(
                self.signal_container,
                fg_color="transparent",
                corner_radius=0
            )
            signal_row.pack(fill="x", pady=2)
            
            # 日期
            ctk.CTkLabel(
                signal_row,
                text=row['date'].strftime('%Y-%m-%d'),
                font=ctk.CTkFont(size=11),
                text_color=NocturneTheme.TEXT_SECONDARY,
                width=100,
                anchor="center"
            ).pack(side="left", padx=2)
            
            # 操作
            ctk.CTkLabel(
                signal_row,
                text=action,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=color,
                width=60,
                anchor="center"
            ).pack(side="left", padx=2)
            
            # 价格
            ctk.CTkLabel(
                signal_row,
                text=f"{row['close']:.2f}",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=NocturneTheme.TEXT_PRIMARY,
                width=80,
                anchor="center"
            ).pack(side="left", padx=2)
        
        # 更新策略统计
        equity = df['equity'].iloc[-1]
        total_return = (equity / 10000 - 1) * 100
        max_dd = abs(df['drawdown'].min()) * 100
        trade_count = int(df['buy'].sum())
        
        self.stats_labels['equity'].configure(text=f"{equity:,.2f}")
        
        return_color = NocturneTheme.UP if total_return >= 0 else NocturneTheme.DOWN
        self.stats_labels['return'].configure(text=f"{total_return:+.2f}%", text_color=return_color)
        
        self.stats_labels['drawdown'].configure(text=f"{max_dd:.2f}%", text_color=NocturneTheme.DOWN)
        self.stats_labels['trades'].configure(text=str(trade_count))
    
    def execute_change_code(self):
        """执行更换代码"""
        # 修复：UI更新通过after调度到主线程，保证线程安全
        self.master.after(0, lambda: self.run_btn.configure(state="disabled"))
        self.master.after(0, self.init_data_loading)
    
    def update_setting(self, key, value):
        """更新参数设置"""
        self.SETTINGS[key] = value
    
    def update_ema_period(self, index, value):
        """更新EMA周期数组中指定位置的值"""
        periods = list(self.SETTINGS['ema_periods'])
        periods[index] = value
        self.SETTINGS['ema_periods'] = periods
    
    def update_risk_param(self, key, value):
        """更新风险参数"""
        self.SETTINGS[key] = value / 100 if key == 'max_stop_loss' else value
    
    def reset_parameters(self):
        """重置参数到默认值"""
        defaults = {
            'ema_periods': [5, 13, 30],
            'macd_fast': 9,
            'macd_slow': 21,
            'macd_signal': 6,
            'volume_ratio_threshold': 0.5,
            'max_stop_loss': 0.30,
            'adx_threshold': 20
        }
        
        # 重置SETTINGS
        self.SETTINGS['ema_periods'] = [5, 13, 30]
        self.SETTINGS['macd_fast'] = 9
        self.SETTINGS['macd_slow'] = 21
        self.SETTINGS['macd_signal'] = 6
        self.SETTINGS['volume_ratio_threshold'] = 0.5
        self.SETTINGS['max_stop_loss'] = 0.30
        self.SETTINGS['adx_threshold'] = 20
        
        # 修复：重置滑块位置（通过保存的slider引用）
        # EMA周期
        ema_vars = ['ema_short', 'ema_mid', 'ema_long']
        for i, var_name in enumerate(ema_vars):
            slider = self.sliders.get(var_name)
            if slider:
                slider.set(defaults['ema_periods'][i])
        
        # MACD参数
        for key in ['macd_fast', 'macd_slow', 'macd_signal']:
            slider = self.sliders.get(key)
            if slider:
                slider.set(defaults[key])
        
        # 风险参数
        slider = self.sliders.get('max_stop_loss')
        if slider:
            slider.set(int(defaults['max_stop_loss'] * 100))
        
        slider = self.sliders.get('volume_ratio_threshold')
        if slider:
            slider.set(defaults['volume_ratio_threshold'])
        
        # ADX阈值
        slider = self.sliders.get('adx_threshold')
        if slider:
            slider.set(defaults['adx_threshold'])
        
        self.status_var.set("参数已重置到默认值")
    
    def show_error(self, msg):
        """显示错误信息"""
        if self.master.winfo_exists():
            messagebox.showerror("错误", msg)
    
    def safe_exit(self):
        """安全退出程序"""
        self.running = False
        if self.master.winfo_exists():
            self.master.destroy()
        sys.exit(0)

if __name__ == "__main__":
    root = ctk.CTk()
    try:
        app = StockStrategyApp(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("致命错误", f"程序崩溃: {str(e)}")
        sys.exit(1)
