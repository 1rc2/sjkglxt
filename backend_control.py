# -*- coding: utf-8 -*-
"""后端控制菜单 - 启动/关闭/查看状态"""
import os
import subprocess
import sys
import time
import socket

if sys.platform == 'win32':
    try:
        import ctypes
        cp = ctypes.windll.kernel32.GetConsoleOutputCP()
        sys.stdout.reconfigure(encoding='utf-8' if cp == 65001 else 'gbk', errors='replace')
        sys.stdin.reconfigure(encoding='utf-8' if cp == 65001 else 'gbk', errors='replace')
    except Exception:
        pass

PYTHON = sys.executable if sys.executable else 'python'
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_PY = os.path.join(SCRIPT_DIR, 'server.py')
LOG_FILE = os.path.join(SCRIPT_DIR, 'server.log')
PORT = 5000


def is_port_listening(port):
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
    try:
        r = subprocess.run(['sc', 'query', 'MySQL80'], capture_output=True, text=True, timeout=5)
        return 'RUNNING' in r.stdout.upper()
    except Exception:
        return False


def kill_pids(pids):
    for pid in pids:
        try:
            subprocess.run(['taskkill', '/F', '/PID', pid],
                           capture_output=True, text=True, timeout=5)
        except Exception:
            pass


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
    mysql_ok = is_mysql_running()
    if mysql_ok:
        print('\n  [OK]  MySQL 已启动')
    else:
        print('\n  [警告] MySQL 未启动，请先在服务里启动 MySQL80')
    print('  [提示] 正在启动后端（后台运行）...')

    log_f = open(LOG_FILE, 'w', encoding='utf-8')
    creation_flags = 0
    if os.name == 'nt':
        DETACHED_PROCESS = 0x00000008
        creation_flags = DETACHED_PROCESS
    proc = subprocess.Popen(
        [PYTHON, SERVER_PY],
        cwd=SCRIPT_DIR,
        stdout=log_f,
        stderr=subprocess.STDOUT,
        creationflags=creation_flags if os.name == 'nt' else 0,
        close_fds=True if os.name != 'nt' else False
    )
    log_f.close()

    for i in range(10):
        time.sleep(0.5)
        if is_port_listening(PORT):
            break

    if is_port_listening(PORT):
        ip = get_lan_ip()
        print('  [完成] 后端已启动')
        if ip:
            print('  手机访问: http://%s:%d' % (ip, PORT))
    else:
        print('  [失败] 后端启动失败，请查看日志: %s' % LOG_FILE)
    pause()


def do_stop():
    print('\n  [提示] 正在关闭后端(端口%d)...' % PORT)
    for attempt in range(3):
        pids = get_pid_on_port(PORT)
        if not pids:
            print('  [完成] 后端已关闭')
            pause()
            return
        kill_pids(pids)
        time.sleep(1.5)
        if not is_port_listening(PORT):
            print('  [完成] 后端已关闭')
            pause()
            return
    print('  [失败] 关闭失败，请在任务管理器结束 python.exe 进程')
    pause()


def do_status():
    running = is_port_listening(PORT)
    mysql = is_mysql_running()
    print()
    if running:
        ip = get_lan_ip()
        print('  [状态] 后端运行中')
        if ip:
            print('         手机访问: http://%s:%d' % (ip, PORT))
    else:
        print('  [状态] 后端未运行')
    print('  [状态] MySQL %s' % ('已启动' if mysql else '未启动'))
    if not running and mysql:
        print('  [提示] 可按 [1] 启动后端')
    pause()


def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return ''


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
