# QZStock - 股票策略分析工具

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

QZStock 是一个基于 Python 和 Tkinter 的股票策略分析工具，提供技术指标计算、策略回测和可视化功能。

## **<font color="red">重要说明：该软件不构成任何投资建议，并且该策略胜率较低，仅作娱乐使用！</font>**

## 功能特点

1. 多指标分析：支持EMA、MACD、ADX、RSI等多种技术指标
2. 策略回测：内置趋势跟踪策略，可自定义参数
3. 可视化界面：直观展示净值曲线和交易信号
4. 实时更新：支持动态调整参数并立即查看效果
5. 数据管理：自动下载并缓存股票历史数据

## 技术栈 

* GUI框架: Tkinter
* 数据分析: Pandas, NumPy
* 可视化: Matplotlib
* 数据源: AKShare
* 多线程处理: threading, queue

## 安装与使用

1. 安装依赖库：
pip install akshare pandas numpy matplotlib

2. 运行程序：
python stock_strategy_app.py

## 主要功能 

- 股票代码输入与切换
- 技术指标参数动态调整
- 策略回测与绩效评估
- 交易信号展示
- 净值曲线可视化

