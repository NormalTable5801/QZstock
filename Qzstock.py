import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
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

global gpn
gpn=""

class StockStrategyApp:

    

    def __init__(self, master):
        self.master = master
        self.setup_main_window()
        self.initialize_variables()
        self.setup_ui_components()
        self.start_worker_thread()
        self.init_data_loading()

    def setup_main_window(self):
        """配置主窗口"""
        self.master.title("QZStock")
        self.master.geometry("1280x800")
        self.master.protocol("WM_DELETE_WINDOW", self.safe_exit)

    def initialize_variables(self):
        """初始化变量"""
        self.SETTINGS = {
            'ema_periods': [5, 13, 21],
            'macd_fast': 9,
            'macd_slow': 21,
            'macd_signal': 6,
            'adx_period': 14,
            'volume_ratio_threshold': 1.2,
            'max_stop_loss': 0.05,
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

    def setup_ui_components(self):
        """构建UI组件"""
        # 主框架
        main_frame = ttk.Frame(self.master, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 控制面板
        control_frame = ttk.LabelFrame(main_frame, text="参数控制", padding=10)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # 结果面板
        result_frame = ttk.LabelFrame(main_frame, text="策略表现", padding=10)
        result_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 控制面板组件
        self.create_control_panel(control_frame)
        self.create_result_panel(result_frame)

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.master, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_control_panel(self, parent):
        """创建控制面板"""
        # 股票代码显示
        ttk.Label(parent, text="当前代码:").grid(row=0, column=0, sticky="w")
        self.code_label = ttk.Label(parent, text="未加载")
        self.code_label.grid(row=0, column=1, sticky="w")

        # 参数控制滑块
        self.create_slider_controls(parent)

        # 功能按钮
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=7, columnspan=3, pady=10)

        self.run_btn = ttk.Button(btn_frame, text="执行策略", 
                                command=lambda: self.add_task('run_strategy'),
                                state=tk.DISABLED)
        self.run_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="输入代码", 
                  command=lambda: self.add_task('change_code')).pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="重置参数", 
                  command=self.reset_parameters).pack(side=tk.LEFT, padx=5)

    def create_slider_controls(self, parent):
        """创建参数滑块控件"""
        # EMA参数
        ttk.Label(parent, text="EMA短周期 (3-10):").grid(row=1, column=0, sticky="w")
        self.ema_short = tk.IntVar(value=self.SETTINGS['ema_periods'][0])
        ttk.Scale(parent, from_=3, to=10, variable=self.ema_short,
                 command=lambda e: self.update_setting('ema_periods', [self.ema_short.get(), 13, 21])).grid(row=1, column=1)
        ttk.Label(parent, textvariable=self.ema_short).grid(row=1, column=2)

        # MACD参数
        macd_params = [
            ('macd_fast', 'MACD快线 (5-20):', 5, 20),
            ('macd_slow', 'MACD慢线 (12-30):', 12, 30),
            ('macd_signal', '信号周期 (3-14):', 3, 14)
        ]
        for row, (key, label, frm, to) in enumerate(macd_params, start=2):
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w")
            var = tk.IntVar(value=self.SETTINGS[key])
            ttk.Scale(parent, from_=frm, to=to, variable=var,
                     command=lambda e, k=key: self.update_setting(k, var.get())).grid(row=row, column=1)
            ttk.Label(parent, textvariable=var).grid(row=row, column=2)
            setattr(self, key, var)

        # 风险参数
        risk_params = [
            ('max_stop_loss', '止损比例 (0-15%):', 0, 15),
            ('volume_ratio_threshold', '量比阈值 (1.0-3.0):', 1.0, 3.0)
        ]
        for row, (key, label, frm, to) in enumerate(risk_params, start=5):
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w")
            var = tk.DoubleVar(value=self.SETTINGS[key] * (100 if key == 'max_stop_loss' else 1))
            ttk.Scale(parent, from_=frm, to=to, variable=var,
                     command=lambda e, k=key: self.update_risk_param(k, var.get())).grid(row=row, column=1)
            ttk.Label(parent, textvariable=var).grid(row=row, column=2)
            setattr(self, key, var)

    def create_result_panel(self, parent):
        """创建结果展示面板"""
        # 净值曲线图
        self.fig, self.ax = plt.subplots(figsize=(12, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 交易信号表格
        ttk.Label(parent, text="最近交易信号:").pack(anchor="w")
        self.signal_table = ttk.Treeview(parent, columns=('date', 'action', 'price'), 
                                       show='headings', height=8)
        
        # 配置表格列
        columns = [
            ('date', '日期', 120),
            ('action', '操作', 80),
            ('price', '价格', 100)
        ]
        for col, text, width in columns:
            self.signal_table.heading(col, text=text)
            self.signal_table.column(col, width=width, anchor='center')

        # 添加滚动条
        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.signal_table.yview)
        self.signal_table.configure(yscrollcommand=vsb.set)
        
        self.signal_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # 回测报告
        self.report_text = tk.Text(parent, height=10, font=('Consolas', 10), state=tk.DISABLED)
        self.report_text.pack(fill=tk.BOTH)

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
            self.code_label.config(text=f"{code} (加载中...)")
            self.add_task('load_data')

        else:
            self.status_var.set("请输入股票代码！")
            self.run_btn.config(state=tk.NORMAL)

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
            self.status_var.set("正在下载数据...")
            dtt = datetime.now().strftime("%Y%m%d")
            edtt=datetime.now().replace(year=datetime.now().year - 5)
            edtl=edtt.strftime("%Y%m%d")
            df = ak.stock_zh_a_hist(
                symbol=self.current_code,
                period="daily",
                start_date=edtl,
                end_date=dtt,
                adjust=""
            )
            df.to_csv(f'stock_{self.current_code}.csv', index=False, encoding='utf_8_sig')
            self.master.after(0, self.on_data_loaded_success)
        except Exception as e:
            self.show_error(f"数据加载失败: {str(e)}")
            self.master.after(0, self.init_data_loading)

    def on_data_loaded_success(self):
        """数据加载成功处理"""
        self.code_label.config(text=f"{self.current_code} (已加载)")
        self.status_var.set("数据加载完成")
        self.run_btn.config(state=tk.NORMAL)
        if self.current_code not in self.history:
            self.history.append(self.current_code)

    def execute_strategy(self):
        """执行策略任务"""
        try:
            self.run_btn.config(state=tk.DISABLED, text="执行中...")
            self.status_var.set("正在执行策略...")
            
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
            #self.hcbg(result_df)
            
        except Exception as e:
            self.show_error(f"策略执行错误: {str(e)}")
        finally:
            self.master.after(0, lambda: self.run_btn.config(state=tk.NORMAL, text="执行策略"))
            self.status_var.set("策略执行完成")

    def wilder_smooth(self, series, period):
        """Wilder平滑法计算ADX"""
        return series.ewm(alpha=1/period, adjust=False).mean()

    def calculate_technical_indicators(self, df):
        """计算技术指标"""
        df = df.copy()
        
        # EMA指标
        for period in self.SETTINGS['ema_periods']:
            df[f'ema{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        
        # MACD指标
        df['macd_fast'] = df['close'].ewm(span=self.SETTINGS['macd_fast'], adjust=False).mean()
        df['macd_slow'] = df['close'].ewm(span=self.SETTINGS['macd_slow'], adjust=False).mean()
        df['macd_diff'] = df['macd_fast'] - df['macd_slow']
        df['macd_dea'] = df['macd_diff'].ewm(span=self.SETTINGS['macd_signal'], adjust=False).mean()
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
        """生成交易信号"""
        df = df.copy()
        df['buy'] = 0
        df['sell'] = 0
        position = False
        entry_price = 0.0
        
        for i in range(55, len(df)):
            # 趋势过滤条件
            trend_cond = (df['adx'].iloc[i] > 12) & \
                        (df['ema21'].iloc[i] > df['ema21'].iloc[i-5])
            
            # 买入条件
            price_cond = (df['close'].iloc[i] > df['ema13'].iloc[i]) & \
                        (df['ema5'].iloc[i] > df['ema21'].iloc[i])
            
            volume_cond = (df['vol_ratio'].iloc[i] > self.SETTINGS['volume_ratio_threshold'])
            
            momentum_cond = (df['macd_hist'].iloc[i] > 0) & \
                           (df['macd_hist'].iloc[i] > df['macd_hist'].iloc[i-1])
            
            if trend_cond & price_cond & volume_cond & momentum_cond & ~position:
                df.at[i, 'buy'] = 1
                position = True
                entry_price = df['close'].iloc[i]
            
            # 卖出条件
            if position:
                current_price = df['close'].iloc[i]
                stop_loss = min(self.SETTINGS['max_stop_loss'], df['std20'].iloc[i] * 1.5)
                
                # 动态止损
                if current_price < entry_price * (1 - stop_loss):
                    df.at[i, 'sell'] = 1
                    position = False
                    continue
                    
                # 趋势反转或超卖
                trend_reverse = (df['close'].iloc[i] < df['ema13'].iloc[i]) & \
                               (df['macd_diff'].iloc[i] < 0) & \
                               (df['adx'].iloc[i] < 22)
                
                overbought = df['rsi'].iloc[i] > self.SETTINGS['rsi_overbought']
                
                if trend_reverse | overbought:
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
                price = df['open'].iloc[i] * (1 - self.SETTINGS['slippage_rate'])
                fee = price * shares * self.SETTINGS['commission_rate']
                cash += shares * price - fee
                shares = 0
                df.at[i, 'position'] = 0
            
            # 更新净值
            df.at[i, 'equity'] = cash + shares * df['close'].iloc[i]
        
        # 计算绩效指标
        df['returns'] = df['equity'].pct_change()
        df['cumulative'] = (1 + df['returns']).cumprod()
        df['max_drawdown'] = df['cumulative'].cummax() - df['cumulative']
        
        return df

    def display_results(self, df):
        global gpn
        """显示策略结果"""
        plt.rcParams['font.sans-serif'] = ['SimHei']
        self.ax.clear()

    
        df['date'] = pd.to_datetime(df['date'])

      
        temp_df = df.set_index('date')
        monthly_returns = temp_df['equity'].resample('M').last().pct_change() * 100
        monthly_dates = monthly_returns.index + pd.offsets.MonthBegin(-1) + pd.DateOffset(days=14)

        # ==== 使用原 date 列绘图 ====
        self.ax.plot(df['date'], df['equity'], label='策略净值', color='#619ac3')
        self.ax.plot(df['date'], df['close']/df['close'].iloc[0]*10000, 
                    label=gpn, color='#ea7293')

        # ==== 绘制月度收益 ====
        ax2 = self.ax.twinx()
        colors = ['#d62728' if x > 0 else '#2ca02c' for x in monthly_returns]
        ax2.bar(monthly_dates, monthly_returns, 
                width=20, alpha=0.3, color=colors, 
                label='月度收益')

        # ==== 图表装饰 ====
        self.ax.set_title('策略净值曲线', fontsize=10)
        self.ax.legend()
        self.canvas.draw()

        # ==== 更新交易信号 ====
        self.signal_table.delete(*self.signal_table.get_children())
        signals = df[(df['buy'] > 0) | (df['sell'] > 0)].tail(10)
        for _, row in signals.iterrows():
            action = '买入' if row['buy'] > 0 else '卖出'
            self.signal_table.insert('', 'end', values=(
                row['date'].strftime('%Y-%m-%d'),
                action,
                f"{row['close']:.2f}"
            ))
        
        # ==== 更新回测报告 ====
        self.report_text.config(state=tk.NORMAL)
        self.report_text.delete(1.0, tk.END)
        report = f"""策略净值: {df['equity'].iloc[-1]:,.2f}
    累计收益率: {(df['equity'].iloc[-1]/10000-1)*100:.2f}%
    最大回撤率: {df['max_drawdown'].max()*100:.2f}%
    总交易次数: {df['buy'].sum()}"""
        self.report_text.insert(tk.END, report)
        self.report_text.config(state=tk.DISABLED)
    def execute_change_code(self):
        """执行更换代码"""
        self.run_btn.config(state=tk.DISABLED)
        # self.init_data_loading()
        self.master.after(0, self.init_data_loading)

    def update_setting(self, key, value):
        """更新参数设置"""
        self.SETTINGS[key] = value

    def update_risk_param(self, key, value):
        """更新风险参数"""
        self.SETTINGS[key] = value / 100 if key == 'max_stop_loss' else value

    def reset_parameters(self):
        """重置参数到默认值"""
        defaults = {
            'ema_periods': [5, 13, 21],
            'macd_fast': 9,
            'macd_slow': 21,
            'macd_signal': 6,
            'volume_ratio_threshold': 1.2,
            'max_stop_loss': 0.05
        }
        for key, value in defaults.items():
            var = getattr(self, key, None)
            if var:
                var.set(value if not isinstance(value, list) else value[0])
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
    root = tk.Tk()
    try:
        app = StockStrategyApp(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("致命错误", f"程序崩溃: {str(e)}")
        sys.exit(1)