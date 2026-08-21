# -*- coding: utf-8 -*-
"""后端控制菜单 - 启动/关闭/查看状态"""
import os
import subprocess
import sys
import time
import socket

# 跟随控制台代码页输出，避免中文乱码（bat 已 chcp 65001）
if sys.platform == 'win32':
    try:
        import ctypes
        cp = ctypes.windll.kernel32.GetConsoleOutputCP()
        sys.stdout.reconfigure(encoding='utf-8' if cp == 65001 else 'gbk', errors='replace')
        sys.stdin.reconfigure(encoding='utf-8' if cp == 65001 else 'gbk', errors='replace')
    except Exception:
        pass

PYTHON = r'D:\python\python.exe'
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_PY = os.path.join(SCRIPT_DIR, 'server.py')
PORT = 5000


def is_port_listening(port):
    """检测端口是否在监听"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect(('127.0.0.1', port))
        s.close()
        return True
    except Exception:
        s.close()
        return False


def get_pid_on_port(port):
    """获取监听该端口的进程 PID"""
    try:
        r = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             '(Get-NetTCPConnection -LocalPort %d -State Listen -ErrorAction SilentlyContinue).OwningProcess' % port],
            capture_output=True, text=True, timeout=5)
        pids = [p.strip() for p in r.stdout.strip().split('\n') if p.strip()]
        return pids
    except Exception:
        return []


def is_mysql_running():
    """检测 MySQL80 服务是否在运行"""
    try:
        r = subprocess.run(['sc', 'query', 'MySQL80'], capture_output=True, text=True, timeout=5)
        return 'RUNNING' in r.stdout.upper()
    except Exception:
        return False


def kill_pids(pids):
    """结束指定 PID 的进程"""
    for pid in pids:
        try:
            r = subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True, text=True, timeout=5)
            print('  [调试] taskkill PID %s -> exit=%d out=%s' % (pid, r.returncode, r.stdout.strip()))
            if r.returncode != 0:
                print('  [调试] taskkill stderr=%s' % r.stderr.strip())
        except Exception as e:
            print('  [调试] taskkill exception: %s' % e)


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def pause():
    input('\n按回车键返回菜单...')


def show_menu():
    clear()
    print('=' * 35)
    print('       管理系统后端控制')
    print('=' * 35)
    print('   [1] 启动后端')
    print('   [2] 关闭后端')
    print('   [3] 查看状态')
    print('   [0] 退出')
    print('=' * 35)


def do_start():
    if is_port_listening(PORT):
        print('\n  [提示] 后端已在运行，无需重复启动')
        pause()
        return
    if is_mysql_running():
        print('\n  [提示] MySQL 已启动')
    else:
        print('\n  [提示] MySQL 未启动，请先在服务里启动 MySQL80')
    print('  [提示] 正在启动后端...')
    # 用新窗口启动，保持后端运行
    subprocess.Popen(
        [PYTHON, SERVER_PY],
        cwd=SCRIPT_DIR,
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
    )
    time.sleep(2)
    if is_port_listening(PORT):
        print('  [完成] 后端已启动')
    else:
        print('  [警告] 后端可能启动失败，请查看新窗口的报错信息')
    pause()


def do_stop():
    print('\n  [提示] 正在关闭后端(端口%d)...' % PORT)
    for attempt in range(3):
        pids = get_pid_on_port(PORT)
        if not pids:
            print('  [完成] 后端已关闭')
            pause()
            return
        print('  [调试] 找到进程 PID: %s' % ', '.join(pids))
        kill_pids(pids)
        time.sleep(2)
        if not is_port_listening(PORT):
            print('  [完成] 后端已关闭')
            pause()
            return
        print('  [调试] 第%d次尝试后端口仍占用，重试...' % (attempt + 1))
    print('  [警告] 关闭失败，请手动在任务管理器结束 python.exe 进程')
    pause()


def do_status():
    if is_port_listening(PORT):
        print('\n  [状态] 后端运行中')
    else:
        print('\n  [状态] 后端未运行')
    if is_mysql_running():
        print('  [状态] MySQL 已启动')
    else:
        print('  [状态] MySQL 未启动')
    pause()


def main():
    while True:
        show_menu()
        choice = input('  请选择数字后回车: ').strip()
        if choice == '1':
            do_start()
        elif choice == '2':
            do_stop()
        elif choice == '3':
            do_status()
        elif choice == '0':
            break
        else:
            print('\n  输入无效，请重试')
            time.sleep(1)


if __name__ == '__main__':
    main()
