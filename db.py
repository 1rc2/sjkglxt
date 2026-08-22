# -*- coding: utf-8 -*-
"""
============================================================================
 数据库工具类模块 (db.py)
---------------------------------------------------------------------------
 功能：
   1. 封装 pymysql 的数据库连接管理（单例模式）
   2. 提供统一的增删改查方法（query / execute）
   3. 提供自动执行 database.sql 初始化数据库的方法
   4. 统一的异常捕获与友好错误提示

 使用前请根据本机 MySQL 环境修改下方 DB_CONFIG 配置。
============================================================================
"""

import os
import pymysql
import pymysql.cursors


# ---------------------------------------------------------------------------
# 数据库连接配置（请根据实际环境修改）
# ---------------------------------------------------------------------------
DB_CONFIG = {
    'host': 'localhost',          # MySQL 主机地址
    'port': 3306,                 # MySQL 端口
    'user': 'root',               # 用户名
    'password': '041632qwe',      # 密码（已更新为用户实际密码）
    'database': 'competition_db', # 数据库名
    'charset': 'utf8mb4',         # 字符集
    'autocommit': True,           # 自动提交事务
}

# database.sql 脚本所在路径（与本文件同目录）
SQL_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.sql')


class DatabaseError(Exception):
    """自定义数据库异常，便于界面层统一捕获提示"""
    pass


class Database:
    """数据库操作封装类（单例模式：全程序共用同一个连接）"""

    _instance = None

    def __new__(cls):
        """单例：确保整个程序只存在一个 Database 实例"""
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._conn = None
            self._initialized = True

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------
    @property
    def conn(self):
        """懒加载获取数据库连接：首次访问时自动建立连接"""
        if self._conn is None or not self._ping():
            self._connect()
        return self._conn

    def _ping(self):
        """检测连接是否仍然有效"""
        try:
            self._conn.ping(reconnect=True)
            return True
        except Exception:
            return False

    def _connect(self):
        """建立数据库连接"""
        try:
            self._conn = pymysql.connect(
                host=DB_CONFIG['host'],
                port=DB_CONFIG['port'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                database=DB_CONFIG['database'],
                charset=DB_CONFIG['charset'],
                autocommit=DB_CONFIG['autocommit'],
                cursorclass=pymysql.cursors.DictCursor,  # 查询结果以字典形式返回
            )
        except pymysql.MySQLError as e:
            raise DatabaseError('数据库连接失败：{}\n\n请检查 MySQL 服务是否启动，'
                                '以及 db.py 中的 DB_CONFIG 配置是否正确。'.format(e))

    # ------------------------------------------------------------------
    # 通用增删改查方法
    # ------------------------------------------------------------------
    def query(self, sql, params=None):
        """
        执行查询语句，返回结果列表（每行是一个字典）
        :param sql:    SQL 查询语句
        :param params: 参数元组/列表，用于防 SQL 注入
        :return:       list[dict]
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except pymysql.MySQLError as e:
            raise DatabaseError('查询失败：{}'.format(e))

    def query_one(self, sql, params=None):
        """执行查询，仅返回第一条结果（字典）或 None"""
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql, params=None):
        """
        执行增、删、改语句
        :return: 受影响的行数
        """
        try:
            with self.conn.cursor() as cursor:
                affected = cursor.execute(sql, params)
                return affected
        except pymysql.MySQLError as e:
            raise DatabaseError('操作失败：{}'.format(e))

    def insert_return_id(self, sql, params=None):
        """
        执行插入语句，并返回自增主键值
        :return: 新记录的自增 id
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.lastrowid
        except pymysql.MySQLError as e:
            raise DatabaseError('插入失败：{}'.format(e))

    def fetch_fields(self, table):
        """
        获取指定表的字段信息（字段名、是否主键等）
        用于界面层动态生成表格列头
        """
        sql = """
            SELECT COLUMN_NAME AS name, COLUMN_KEY AS ckey, DATA_TYPE AS dtype
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, (DB_CONFIG['database'], table))
                return cursor.fetchall()
        except pymysql.MySQLError as e:
            raise DatabaseError('获取表结构失败：{}'.format(e))

    def close(self):
        """关闭数据库连接"""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    # ------------------------------------------------------------------
    # 数据库初始化（自动执行 database.sql）
    # ------------------------------------------------------------------
    def init_database(self):
        """
        自动读取 database.sql 脚本并执行，完成建库建表与测试数据导入。
        注意：pymysql 不支持一次执行多条语句，这里按 ';' 分割后逐条执行。
        """
        if not os.path.exists(SQL_SCRIPT_PATH):
            raise DatabaseError('未找到数据库脚本：{}'.format(SQL_SCRIPT_PATH))

        with open(SQL_SCRIPT_PATH, 'r', encoding='utf-8') as f:
            script = f.read()

        # 去掉注释行，并按分号分割为独立语句
        # 使用 \n; 分割以避免字段内含分号时误拆分
        statements = []
        for raw_line in script.replace('\r\n', '\n').split(';\n'):
            line = raw_line.strip()
            if not line:
                continue
            lines = [s for s in line.splitlines() if s.strip() and not s.strip().startswith('--')]
            if lines:
                statements.append('\n'.join(lines))

        # 使用无 database 的连接，先建库再切库
        config = dict(DB_CONFIG)
        config.pop('database', None)
        try:
            conn = pymysql.connect(
                host=config['host'], port=config['port'],
                user=config['user'], password=config['password'],
                charset=config['charset'], autocommit=True,
                cursorclass=pymysql.cursors.DictCursor,
            )
            with conn.cursor() as cursor:
                for stmt in statements:
                    cursor.execute(stmt)
            conn.close()
        except pymysql.MySQLError as e:
            raise DatabaseError('初始化数据库失败：{}'.format(e))
        finally:
            # 初始化后重建主连接
            if self._conn is not None:
                self._conn.close()
                self._conn = None


# ---------------------------------------------------------------------------
# 模块级便捷函数（供界面层直接调用）
# ---------------------------------------------------------------------------
def get_db():
    """获取数据库单例"""
    return Database()


def init_db():
    """初始化数据库（建库建表 + 测试数据）"""
    Database().init_database()


if __name__ == '__main__':
    # 独立运行本文件时，执行数据库初始化
    try:
        print('开始初始化数据库...')
        init_db()
        print('数据库初始化完成！')
    except DatabaseError as e:
        print('初始化失败：', e)
