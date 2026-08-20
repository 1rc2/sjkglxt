# -*- coding: utf-8 -*-
"""
============================================================================
 手机远程启动助手 (start_helper.py)
---------------------------------------------------------------------------
 常驻本机 5001 端口，手机通过 HTTP 请求远程启动/停止服务：
   GET  http://电脑IP:5001/status          -> 查询 MySQL / 后端运行状态
   GET  http://电脑IP:5001/start           -> 启动 MySQL 服务 + 后端 server.py
   GET  http://电脑IP:5001/stop-backend    -> 停止后端 server.py

 说明：
   - 启动 MySQL 服务需要管理员权限。本助手内置 UAC 提权：
     非管理员启动时自动弹出 UAC 授权窗口，授权后重启用管理员权限运行。
   - 建议配合"开机自启"使用（见 README），电脑开机后助手自动常驻。
   - 手机与电脑需同一局域网；Windows 防火墙需放行 5001 端口。
============================================================================
"""
import ctypes
import os
import socket
import subprocess
import sys
import time
from threading import Thread

from flask import Flask, jsonify, request

MYSQL_PORT = 3306
BACKEND_PORT = 5000
HELPER_PORT = 5001
MYSQL_SERVICE = 'MySQL80'      # 本机 MySQL 服务名，可按实际修改
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_CMD = [sys.executable, os.path.join(BASE_DIR, 'server.py')]

app = Flask(__name__)

_backend_proc = None           # 后端进程句柄


# ---------------------------------------------------------------------------
# CORS 支持（APK 内页面通过 file:// 跨源访问本助手接口）
# ---------------------------------------------------------------------------
@app.after_request
def add_cors_headers(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return resp


@app.before_request
def handle_preflight():
    """处理浏览器/WebView 的 OPTIONS 预检请求"""
    if request.method == 'OPTIONS':
        return ('', 204)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def request_admin():
    """通过 UAC 提权，用管理员权限重启本脚本"""
    ctypes.windll.shell32.ShellExecuteW(
        None, 'runas', sys.executable,
        '"{}"'.format(os.path.abspath(__file__)), None, 1)


def port_open(port, host='127.0.0.1', timeout=1.5):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def start_mysql_service():
    """启动 MySQL 服务（需管理员权限），最多等待 30 秒"""
    if port_open(MYSQL_PORT):
        return True, 'MySQL 已在运行'
    if not is_admin():
        # 提示用户以管理员权限运行，避免提权后新旧进程争抢 5001 端口
        return False, '助手未以管理员权限运行，无法启动 MySQL。请右键"以管理员身份运行"start_helper.py'
    subprocess.run(['sc', 'start', MYSQL_SERVICE],
                   capture_output=True, shell=True)
    for _ in range(30):
        if port_open(MYSQL_PORT):
            return True, 'MySQL 启动成功'
        time.sleep(1)
    return False, 'MySQL 30秒内启动失败，请检查服务状态'


def start_backend():
    """启动后端 server.py（若未运行）"""
    global _backend_proc
    if port_open(BACKEND_PORT):
        return True, '后端已在运行'
    _backend_proc = subprocess.Popen(
        BACKEND_CMD, cwd=BASE_DIR,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(15):
        if port_open(BACKEND_PORT):
            return True, '后端启动成功'
        time.sleep(0.5)
    return False, '后端 15 秒内未就绪，请检查 server.py 是否报错'


def stop_backend():
    """停止后端进程（仅终止本助手启动的子进程，不误杀同端口其他程序）"""
    global _backend_proc
    killed = False
    if _backend_proc is not None and _backend_proc.poll() is None:
        _backend_proc.terminate()
        try:
            _backend_proc.wait(timeout=5)
        except Exception:
            _backend_proc.kill()
        killed = True
    _backend_proc = None
    return killed


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------
@app.route('/status')
def status():
    """状态检测：MySQL 端口 / 后端端口 / 数据库真实连接"""
    db_ok = False
    db_msg = ''
    try:
        if port_open(MYSQL_PORT):
            import sys as _sys
            if BASE_DIR not in _sys.path:
                _sys.path.insert(0, BASE_DIR)
            import db as dbmod
            try:
                db_ok = dbmod.Database().query_one('SELECT 1') is not None
                db_msg = '数据库连接正常' if db_ok else '数据库连接失败'
            except Exception as e:
                db_msg = '数据库连接失败：{}'.format(e)
        else:
            db_msg = 'MySQL 未运行'
    except Exception as e:
        db_msg = '数据库检测异常：{}'.format(e)
    return jsonify({
        'ok': True,
        'mysql': port_open(MYSQL_PORT),
        'backend': port_open(BACKEND_PORT),
        'db': db_ok,
        'db_msg': db_msg,
        'helper': True,
    })


@app.route('/start')
def start_all():
    # 后台线程执行，避免长时间阻塞 HTTP 响应
    def worker():
        mysql_ok, mysql_msg = start_mysql_service()
        time.sleep(1)
        backend_ok, backend_msg = start_backend()
        print('[助手]', mysql_msg, '|', backend_msg)
    Thread(target=worker, daemon=True).start()
    return jsonify({'ok': True, 'msg': '启动任务已提交，请稍候 10~30 秒后刷新'}), 202


@app.route('/stop-backend')
def stop_backend_api():
    stopped = stop_backend()
    return jsonify({'ok': stopped, 'msg': '后端已停止' if stopped else '后端未在运行'})


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


if __name__ == '__main__':
    if not is_admin():
        print('需要管理员权限才能启动 MySQL 服务，正在请求提权...')
        print('请在弹出的 UAC 窗口中点击"是"，脚本将自动以管理员权限重启。')
        request_admin()
        sys.exit(0)

    print('=' * 52)
    print('    手机远程启动助手 (端口 {})'.format(HELPER_PORT))
    print('=' * 52)

    # 启动后自动确保 MySQL 与后端处于运行状态（已运行则跳过）
    if not port_open(MYSQL_PORT):
        print('  检测到 MySQL 未运行，正在启动...')
        ok, msg = start_mysql_service()
        print(' ', msg)
    if not port_open(BACKEND_PORT):
        print('  检测到后端未运行，正在启动...')
        ok, msg = start_backend()
        print(' ', msg)

    print('  手机访问: http://{}:{}/status'.format(get_lan_ip(), HELPER_PORT))
    print('            http://{}:{}/start'.format(get_lan_ip(), HELPER_PORT))
    print('  MySQL 服务名: {}'.format(MYSQL_SERVICE))
    print('  提示: 建议配置为开机自启（见 README 说明）')
    print('=' * 52)
    app.run(host='0.0.0.0', port=HELPER_PORT, debug=False)
