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

# 开机自启动：Windows 启动文件夹 + 隐藏窗口的 VBS 启动脚本
STARTUP_DIR = os.path.join(
    os.environ.get('APPDATA', ''),
    r'Microsoft\Windows\Start Menu\Programs\Startup')
STARTUP_VBS = os.path.join(STARTUP_DIR, 'start_backend.vbs')


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
    """检测 MySQL 服务是否运行（自动识别 MySQL/MySQL80 等服务名，不写死）"""
    try:
        # 先枚举系统里所有 MySQL 相关服务
        r = subprocess.run(['sc', 'query', 'type=', 'service', 'state=', 'all'],
                           capture_output=True, text=True, timeout=8)
        svc_names = set()
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.upper().startswith('SERVICE_NAME:'):
                svc_names.add(line.split(':', 1)[1].strip())
        mysql_svcs = [s for s in svc_names if s.upper().startswith('MYSQL')]
        if not mysql_svcs:
            return False
        # 任一 MySQL 服务处于 RUNNING 即认为已启动
        for svc in mysql_svcs:
            rr = subprocess.run(['sc', 'query', svc], capture_output=True, text=True, timeout=5)
            if 'RUNNING' in rr.stdout.upper():
                return True
        return False
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
    print('   [4] 设置开机自启动')
    print('   [5] 取消开机自启动')
    print('   [0] 退出')
    print('=' * 35)


def setup_autostart():
    """设置开机自启动：启动文件夹放一个隐藏窗口的 VBS，开机自动运行后端"""
    if os.path.exists(STARTUP_VBS):
        print('\n  [提示] 开机自启动已设置，无需重复操作')
        pause()
        return
    # 隐藏窗口后台运行 python server.py（server.py 自带端口占用预检，重复启动安全）
    cmd = '"{}" "{}"'.format(PYTHON.replace('"', '""'), SERVER_PY.replace('"', '""'))
    vbs = 'Set ws = CreateObject("Wscript.Shell")\r\nws.Run "{}", 0, False\r\n'.format(cmd)
    try:
        os.makedirs(STARTUP_DIR, exist_ok=True)
        with open(STARTUP_VBS, 'w', encoding='gbk') as f:
            f.write(vbs)
        print('\n  [完成] 已设置开机自启动')
        print('        电脑开机后将自动后台运行后端（无窗口）')
        print('        文件位置: {}'.format(STARTUP_VBS))
    except Exception as e:
        print('\n  [失败] 设置开机自启动失败: {}'.format(e))
    pause()


def cancel_autostart():
    """取消开机自启动"""
    try:
        if os.path.exists(STARTUP_VBS):
            os.remove(STARTUP_VBS)
            print('\n  [完成] 已取消开机自启动')
        else:
            print('\n  [提示] 当前未设置开机自启动')
    except Exception as e:
        print('\n  [失败] 取消开机自启动失败: {}'.format(e))
    pause()


def do_start():
    if is_port_listening(PORT):
        print('\n  [提示] 后端已在运行，无需重复启动')
        pause()
        return
    mysql_ok = is_mysql_running()
    if mysql_ok:
        print('\n  [OK]  MySQL 已启动')
    else:
        print('\n  [警告] MySQL 未启动，请先在 Windows 服务中启动 MySQL 服务')
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
        # 显示日志尾部，便于直接排查失败原因
        try:
            with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as lf:
                tail = lf.read().strip().splitlines()[-6:]
            print('  ---- server.log 最后几行 ----')
            for ln in tail:
                print('  | ' + ln)
        except Exception:
            pass
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
        elif choice == '4':
            setup_autostart()
        elif choice == '5':
            cancel_autostart()
        elif choice == '0':
            break
        else:
            print('\n  输入无效，请重试')
            time.sleep(1)


if __name__ == '__main__':
    main()
