# -*- coding: utf-8 -*-
"""
============================================================================
 大学生竞赛成果管理系统 —— 手机 APP 后端 API 服务 (server.py)
---------------------------------------------------------------------------
 功能模块（与桌面版 main.py 一一对应）：
   1. 登录接口（账号密码验证，默认 admin / admin123）
   2. 五张表完整 CRUD 接口（depart/student/competition/award/record）
   3. 多条件联合查询接口（字段 × 运算符(= / 包含) × 值，条件为 AND 关系）
   4. 数据统计接口（各院系获奖人数 / 历年参赛人数）
   5. 统计报表导出接口（txt 格式文本）
   6. 托管移动端界面（app/ 目录）

 运行方式：
   pip install flask pymysql
   python server.py
   手机与电脑同一局域网，手机浏览器访问 http://电脑IP:5000

 依赖：flask / pymysql（数据库逻辑复用 db.py、database.sql）
============================================================================
"""
import datetime
import secrets
import socket

from flask import Flask, jsonify, request, send_from_directory

from db import Database, DatabaseError

app = Flask(__name__, static_folder='app', static_url_path='')

# ---------------------------------------------------------------------------
# 全局配置（与桌面版一致）
# ---------------------------------------------------------------------------
LOGIN_USER = 'admin'
LOGIN_PASS = 'admin123'
APP_VERSION = 'v1.1.9'  # 当前版本号（发布新版本时同步更新）
MIN_YEAR, MAX_YEAR = 2000, datetime.date.today().year + 1

# ---------------------------------------------------------------------------
# API 鉴权：内存级 token 校验，登录成功后发放，注销或重启服务后失效
# ---------------------------------------------------------------------------
ACTIVE_TOKENS = set()
PUBLIC_PATHS = {'/api/login', '/api/logout', '/api/health', '/'}


def _check_auth():
    """检查请求是否携带有效 token，未携带返回 None，携带且有效返回 True"""
    path = request.path
    # 公开接口 + 静态资源（css/js/图片等非 /api/ 路径）无需鉴权，仅 /api/ 接口需要 token
    if path in PUBLIC_PATHS or not path.startswith('/api/'):
        return True
    if request.method == 'OPTIONS':
        return True
    token = request.headers.get('X-Auth-Token', '') or request.args.get('token', '')
    if token and token in ACTIVE_TOKENS:
        return True
    return None


@app.before_request
def auth_middleware():
    result = _check_auth()
    if result is None:
        return jsonify({'ok': False, 'msg': '登录已过期，请重新登录！'}), 401

DB = Database()  # 单例


# ---------------------------------------------------------------------------
# 一、数据表元信息配置（与桌面版 main.py 完全一致）
# ---------------------------------------------------------------------------
TABLE_META = {
    'depart': {
        'title': '院系表 (depart)',
        'columns': ['depart_id', 'depart_name'],
        'headers': ['院系编号', '院系名称'],
        'query_sql': 'SELECT * FROM depart ORDER BY depart_id',
        'pk': 'depart_id',
        'form_fields': [('depart_name', '院系名称', 'str')],
    },
    'student': {
        'title': '学生表 (student)',
        'columns': ['stu_id', 'name', 'gender', 'depart_id', 'phone'],
        'headers': ['学号', '姓名', '性别', '所属院系', '联系电话'],
        'query_sql': """SELECT s.stu_id, s.name, s.gender, d.depart_name AS depart_name,
                               s.depart_id, s.phone
                        FROM student s JOIN depart d ON s.depart_id = d.depart_id
                        ORDER BY s.stu_id""",
        'pk': 'stu_id',
        'form_fields': [
            ('stu_id', '学号(10位数字)', 'stuid'),
            ('name', '姓名', 'str'),
            ('gender', '性别', 'gender'),
            ('depart_id', '所属院系', 'depart'),
            ('phone', '联系电话', 'phone'),
        ],
    },
    'competition': {
        'title': '竞赛表 (competition)',
        'columns': ['com_id', 'com_name', 'level', 'hold_year'],
        'headers': ['竞赛编号', '竞赛名称', '竞赛级别', '举办年份'],
        'query_sql': 'SELECT * FROM competition ORDER BY com_id',
        'pk': 'com_id',
        'form_fields': [
            ('com_name', '竞赛名称', 'str'),
            ('level', '竞赛级别', 'level'),
            ('hold_year', '举办年份', 'year'),
        ],
    },
    'award': {
        'title': '奖项表 (award)',
        'columns': ['award_id', 'award_name', 'rank'],
        'headers': ['奖项编号', '奖项名称', '获奖等级'],
        'query_sql': 'SELECT * FROM award ORDER BY award_id',
        'pk': 'award_id',
        'form_fields': [
            ('award_name', '奖项名称', 'str'),
            ('rank', '获奖等级', 'rank'),
        ],
    },
    'record': {
        'title': '参赛记录表 (record)',
        'columns': ['rec_id', 'stu_id', 'stu_name', 'com_name', 'com_level',
                    'award_name', 'award_rank', 'teacher', 'join_year'],
        'headers': ['记录编号', '学号', '姓名', '竞赛名称', '竞赛级别', '奖项名称', '获奖等级', '指导教师', '参赛年份'],
        'query_sql': """SELECT r.rec_id, r.stu_id, s.name AS stu_name,
                               c.com_name, c.level AS com_level,
                               a.award_name, a.`rank` AS award_rank,
                               r.teacher, r.join_year
                        FROM record r
                        JOIN student s     ON r.stu_id   = s.stu_id
                        JOIN competition c ON r.com_id   = c.com_id
                        JOIN award a       ON r.award_id = a.award_id
                        ORDER BY r.rec_id""",
        'pk': 'rec_id',
        'form_fields': [
            ('stu_id', '学号', 'stuid_select'),
            ('com_id', '竞赛', 'com_select'),
            ('award_id', '奖项', 'award_select'),
            ('teacher', '指导教师', 'str'),
            ('join_year', '参赛年份', 'year'),
        ],
    },
}

# 联合查询可检索字段（字段表达式 -> 显示名）
SEARCH_FIELDS = {
    'depart': [
        ('depart_id', '院系编号'),
        ('depart_name', '院系名称'),
    ],
    'student': [
        ('s.stu_id', '学号'),
        ('s.name', '姓名'),
        ('s.gender', '性别'),
        ('d.depart_name', '所属院系'),
        ('s.phone', '联系电话'),
    ],
    'competition': [
        ('com_id', '竞赛编号'),
        ('com_name', '竞赛名称'),
        ('level', '竞赛级别'),
        ('hold_year', '举办年份'),
    ],
    'award': [
        ('award_id', '奖项编号'),
        ('award_name', '奖项名称'),
        ('`rank`', '获奖等级'),
    ],
    'record': [
        ('r.stu_id', '学号'),
        ('s.name', '姓名'),
        ('c.com_name', '竞赛名称'),
        ('c.level', '竞赛级别'),
        ('a.`rank`', '获奖等级'),
        ('r.teacher', '指导教师'),
        ('r.join_year', '参赛年份'),
    ],
}

# 各表查询 SQL 的基础部分（用于联合查询拼接 WHERE）
SEARCH_BASE_SQL = {
    'depart': 'SELECT * FROM depart',
    'student': """SELECT s.stu_id, s.name, s.gender, d.depart_name AS depart_name, s.phone
                  FROM student s JOIN depart d ON s.depart_id = d.depart_id""",
    'competition': 'SELECT * FROM competition',
    'award': 'SELECT * FROM award',
    'record': """SELECT r.rec_id, r.stu_id, s.name AS stu_name,
                        c.com_name, c.level AS com_level,
                        a.award_name, a.`rank` AS award_rank,
                        r.teacher, r.join_year
                 FROM record r
                 JOIN student s     ON r.stu_id   = s.stu_id
                 JOIN competition c ON r.com_id   = c.com_id
                 JOIN award a       ON r.award_id = a.award_id""",
}


# ---------------------------------------------------------------------------
# 二、输入验证工具函数（与桌面版一致）
# ---------------------------------------------------------------------------
def validate_stuid(value):
    """校验学号：必须为10位数字"""
    value = value.strip()
    if not value.isdigit() or len(value) != 10:
        return False, '学号必须为10位数字！'
    return True, ''


def validate_phone(value):
    """校验联系电话：可选，若填写必须为11位数字"""
    value = value.strip()
    if value and (not value.isdigit() or len(value) != 11):
        return False, '联系电话必须为11位数字！'
    return True, ''


def validate_not_empty(value, label='该字段'):
    """通用非空校验"""
    if not value.strip():
        return False, '{}不能为空！'.format(label)
    return True, ''


def _validate_and_collect(table_key, data, is_insert):
    """
    收集并校验表单数据（与桌面版 RecordDialog._collect_data 逻辑一致）
    :return: (data_dict, error_msg)；error_msg 为空表示校验通过
    """
    meta = TABLE_META[table_key]
    out = {}
    for field, label, ftype in meta['form_fields']:
        raw = data.get(field)

        if ftype == 'stuid':
            s = str(raw or '').strip()
            ok, msg = validate_stuid(s)
            if not ok:
                return None, msg
            out[field] = s

        elif ftype == 'phone':
            s = str(raw or '').strip()
            ok, msg = validate_phone(s)
            if not ok:
                return None, msg
            out[field] = s if s else None

        elif ftype == 'year':
            try:
                v = int(raw)
            except (TypeError, ValueError):
                return None, '{}必须为数字！'.format(label)
            if not (MIN_YEAR <= v <= MAX_YEAR):
                return None, '{}必须在{}~{}之间！'.format(label, MIN_YEAR, MAX_YEAR)
            out[field] = v

        elif ftype == 'gender':
            s = str(raw or '').strip()
            if s not in ('男', '女'):
                return None, '请选择{}！'.format(label)
            out[field] = s

        elif ftype == 'level':
            s = str(raw or '').strip()
            if s not in ('国家级', '省级', '校级'):
                return None, '请选择{}！'.format(label)
            out[field] = s

        elif ftype == 'rank':
            try:
                v = int(raw)
            except (TypeError, ValueError):
                return None, '{}必须为数字！'.format(label)
            if v not in (1, 2, 3):
                return None, '{}仅允许1/2/3！'.format(label)
            out[field] = v

        elif ftype in ('depart', 'com_select', 'award_select', 'stuid_select'):
            s = str(raw or '').strip()
            if not s:
                return None, '{}不能为空！'.format(label)
            if ftype == 'stuid_select':
                if not s.isdigit() or len(s) != 10:
                    return None, '学号必须为10位数字！'
                out[field] = s
            elif ftype == 'depart':
                if not s.isdigit():
                    return None, '请选择{}！'.format(label)
                out[field] = int(s)
            else:  # com_select / award_select：允许名称或编号，不存在则报错
                tname = 'competition' if ftype == 'com_select' else 'award'
                fname = 'com_name' if ftype == 'com_select' else 'award_name'
                fkey = 'com_id' if ftype == 'com_select' else 'award_id'
                row = None
                if s.isdigit():
                    row = DB.query_one(
                        'SELECT `{}` AS v FROM `{}` WHERE `{}` = %s'.format(fkey, tname, fkey), (s,))
                if row is None:
                    row = DB.query_one(
                        'SELECT `{}` AS v FROM `{}` WHERE `{}` = %s'.format(fkey, tname, fname), (s,))
                if row is None:
                    return None, '所选{}不存在，请先添加该记录！'.format(label)
                out[field] = row['v']

        else:  # str 通用非空
            s = str(raw or '').strip()
            ok, msg = validate_not_empty(s, label)
            if not ok:
                return None, msg
            if len(s) > 100:
                return None, '{}长度不能超过100个字符！'.format(label)
            out[field] = s

    # 编辑时不更新主键
    if not is_insert:
        out.pop(meta['pk'], None)

    return out, ''


# ===========================================================================
# 三、API 接口
# ===========================================================================
# ---------------------------------------------------------------------------
# 1. 登录
# ---------------------------------------------------------------------------
@app.route('/api/login', methods=['POST'])
def api_login():
    body = request.get_json(silent=True) or {}
    username = str(body.get('username') or '').strip()
    password = str(body.get('password') or '')

    if not username or not password:
        return jsonify({'ok': False, 'msg': '用户名和密码不能为空！'})
    if username == LOGIN_USER and password == LOGIN_PASS:
        token = secrets.token_hex(16)
        ACTIVE_TOKENS.add(token)
        return jsonify({'ok': True, 'username': username, 'token': token})
    return jsonify({'ok': False, 'msg': '用户名或密码错误，请重新输入！'})


@app.route('/api/logout', methods=['POST'])
def api_logout():
    """注销：清除当前会话 token"""
    body = request.get_json(silent=True) or {}
    token = body.get('token', '') or request.headers.get('X-Auth-Token', '')
    if token and token in ACTIVE_TOKENS:
        ACTIVE_TOKENS.discard(token)
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# 2. 数据表元信息（界面动态生成表格列头 / 表单 / 查询条件）
# ---------------------------------------------------------------------------
@app.route('/api/meta')
def api_meta():
    meta = []
    for key, m in TABLE_META.items():
        meta.append({
            'key': key,
            'title': m['title'],
            'columns': m['columns'],
            'headers': m['headers'],
            'pk': m['pk'],
            'form_fields': [{'field': f, 'label': l, 'type': t}
                            for f, l, t in m['form_fields']],
            'search_fields': [{'expr': e, 'name': n}
                              for e, n in SEARCH_FIELDS.get(key, [])],
        })
    return jsonify({'ok': True, 'meta': meta})


# ---------------------------------------------------------------------------
# 3. 下拉选项数据（院系 / 学生 / 竞赛 / 奖项）
# ---------------------------------------------------------------------------
@app.route('/api/options')
def api_options():
    t = request.args.get('type', '')
    sqls = {
        'depart': 'SELECT depart_id AS id, depart_name AS name FROM depart ORDER BY depart_id',
        'student': 'SELECT stu_id AS id, name FROM student ORDER BY stu_id',
        'competition': 'SELECT com_id AS id, com_name AS name FROM competition ORDER BY com_id',
        'award': 'SELECT award_id AS id, award_name AS name FROM award ORDER BY award_id',
    }
    if t not in sqls:
        return jsonify({'ok': False, 'msg': '未知选项类型：{}'.format(t)})
    try:
        rows = DB.query(sqls[t])
    except DatabaseError as e:
        return jsonify({'ok': False, 'msg': str(e)})
    return jsonify({'ok': True, 'options': rows})


# ---------------------------------------------------------------------------
# 4. 查询列表 / 单条原始记录
# ---------------------------------------------------------------------------
@app.route('/api/data')
def api_data():
    table = request.args.get('table', '')
    if table not in TABLE_META:
        return jsonify({'ok': False, 'msg': '未知数据表：{}'.format(table)})
    try:
        rows = DB.query(TABLE_META[table]['query_sql'])
    except DatabaseError as e:
        return jsonify({'ok': False, 'msg': str(e)})
    return jsonify({'ok': True, 'rows': rows})


@app.route('/api/data/<table>/<pk_value>', methods=['GET'])
def api_data_raw(table, pk_value):
    """按主键返回原始记录（record 表编辑时需要回填外键 id）"""
    if table not in TABLE_META:
        return jsonify({'ok': False, 'msg': '未知数据表：{}'.format(table)})
    pk = TABLE_META[table]['pk']
    try:
        row = DB.query_one('SELECT * FROM `{}` WHERE `{}` = %s'.format(table, pk), (pk_value,))
    except DatabaseError as e:
        return jsonify({'ok': False, 'msg': str(e)})
    return jsonify({'ok': row is not None, 'record': row})


# ---------------------------------------------------------------------------
# 5. 新增 / 修改 / 删除
# ---------------------------------------------------------------------------
@app.route('/api/data', methods=['POST'])
def api_add():
    body = request.get_json(silent=True) or {}
    table = body.get('table', '')
    data = body.get('data') or {}
    if table not in TABLE_META:
        return jsonify({'ok': False, 'msg': '未知数据表：{}'.format(table)})

    cleaned, err = _validate_and_collect(table, data, is_insert=True)
    if err:
        return jsonify({'ok': False, 'msg': err})

    fields = list(cleaned.keys())
    cols = ', '.join('`{}`'.format(f) for f in fields)
    marks = ', '.join(['%s'] * len(fields))
    sql = 'INSERT INTO `{}` ({}) VALUES ({})'.format(table, cols, marks)
    try:
        DB.execute(sql, tuple(cleaned.values()))
    except DatabaseError as e:
        return jsonify({'ok': False, 'msg': str(e)})
    return jsonify({'ok': True, 'msg': '保存成功！'})


@app.route('/api/data/<table>/<pk_value>', methods=['PUT'])
def api_update(table, pk_value):
    body = request.get_json(silent=True) or {}
    data = body.get('data') or {}
    if table not in TABLE_META:
        return jsonify({'ok': False, 'msg': '未知数据表：{}'.format(table)})

    cleaned, err = _validate_and_collect(table, data, is_insert=False)
    if err:
        return jsonify({'ok': False, 'msg': err})

    pk = TABLE_META[table]['pk']
    sets = ', '.join('`{}` = %s'.format(f) for f in cleaned)
    params = tuple(cleaned.values()) + (pk_value,)
    sql = 'UPDATE `{}` SET {} WHERE `{}` = %s'.format(table, sets, pk)
    try:
        DB.execute(sql, params)
    except DatabaseError as e:
        return jsonify({'ok': False, 'msg': str(e)})
    return jsonify({'ok': True, 'msg': '保存成功！'})


@app.route('/api/data/<table>/<pk_value>', methods=['DELETE'])
def api_delete(table, pk_value):
    if table not in TABLE_META:
        return jsonify({'ok': False, 'msg': '未知数据表：{}'.format(table)})
    pk = TABLE_META[table]['pk']
    sql = 'DELETE FROM `{}` WHERE `{}` = %s'.format(table, pk)
    try:
        DB.execute(sql, (pk_value,))
    except DatabaseError as e:
        msg = str(e)
        # 外键约束错误：父表记录被引用时给出明确提示
        if '1451' in msg or 'foreign key' in msg.lower():
            return jsonify({'ok': False, 'msg':
                            '无法删除该记录：它正被其他表记录引用！\n'
                            '请先删除引用它的相关记录。\n\n详细信息：{}'.format(e)})
        return jsonify({'ok': False, 'msg': msg})
    return jsonify({'ok': True, 'msg': '删除成功！'})


# ---------------------------------------------------------------------------
# 6. 多条件联合查询
# ---------------------------------------------------------------------------
@app.route('/api/search', methods=['POST'])
def api_search():
    body = request.get_json(silent=True) or {}
    table = body.get('table', '')
    conds = body.get('conds') or []
    if table not in TABLE_META:
        return jsonify({'ok': False, 'msg': '未知数据表：{}'.format(table)})

    # 白名单：只允许 SEARCH_FIELDS 中定义的字段表达式，防止 SQL 注入
    valid_exprs = {e for e, _ in SEARCH_FIELDS.get(table, [])}
    conditions, params = [], []
    for c in conds:
        expr = str(c.get('expr') or '').strip()
        value = str(c.get('value') or '').strip()
        if not expr or not value:
            continue
        if expr not in valid_exprs:
            continue  # 非法字段名，直接跳过
        op = c.get('op') or '='
        if op == '=':
            conditions.append('{} = %s'.format(expr))
            params.append(value)
        else:  # 包含（模糊匹配）
            conditions.append('{} LIKE %s'.format(expr))
            params.append('%{}%'.format(value))

    base_sql = SEARCH_BASE_SQL[table]
    if conditions:
        sql = '{} WHERE {}'.format(base_sql, ' AND '.join(conditions))
    else:
        sql = base_sql
    # 统一按主键排序，保证结果顺序稳定
    order_by = {
        'depart': 'depart_id', 'student': 's.stu_id', 'competition': 'com_id',
        'award': 'award_id', 'record': 'r.rec_id',
    }[table]
    sql = '{} ORDER BY {}'.format(sql, order_by)
    try:
        rows = DB.query(sql, tuple(params))
    except DatabaseError as e:
        return jsonify({'ok': False, 'msg': '查询失败：{}'.format(e)})
    return jsonify({'ok': True, 'rows': rows})


# ---------------------------------------------------------------------------
# 7. 数据统计
# ---------------------------------------------------------------------------
@app.route('/api/stat/depart_award')
def api_stat_depart_award():
    """各院系获奖人数（按获奖记录数统计，降序）"""
    sql = """
        SELECT d.depart_name AS name, COUNT(r.rec_id) AS cnt
        FROM record r
        JOIN student s ON r.stu_id = s.stu_id
        JOIN depart d  ON s.depart_id = d.depart_id
        GROUP BY d.depart_name
        ORDER BY cnt DESC
    """
    try:
        rows = DB.query(sql)
    except DatabaseError as e:
        return jsonify({'ok': False, 'msg': str(e)})
    return jsonify({'ok': True, 'data': [[r['name'], r['cnt']] for r in rows]})


@app.route('/api/stat/year_join')
def api_stat_year_join():
    """历年参赛人数（按年份升序）"""
    sql = """
        SELECT join_year AS year, COUNT(*) AS cnt
        FROM record
        GROUP BY join_year
        ORDER BY join_year
    """
    try:
        rows = DB.query(sql)
    except DatabaseError as e:
        return jsonify({'ok': False, 'msg': str(e)})
    return jsonify({'ok': True, 'data': [[r['year'], r['cnt']] for r in rows]})


# ---------------------------------------------------------------------------
# 8. 统计报表导出（txt 格式，与桌面版完全一致）
# ---------------------------------------------------------------------------
@app.route('/api/export')
def api_export():
    try:
        depart_data = DB.query("""
            SELECT d.depart_name AS name, COUNT(r.rec_id) AS cnt
            FROM record r
            JOIN student s ON r.stu_id = s.stu_id
            JOIN depart d  ON s.depart_id = d.depart_id
            GROUP BY d.depart_name
            ORDER BY cnt DESC
        """)
        year_data = DB.query("""
            SELECT join_year AS year, COUNT(*) AS cnt
            FROM record
            GROUP BY join_year
            ORDER BY join_year
        """)
    except DatabaseError as e:
        return jsonify({'ok': False, 'msg': str(e)})

    lines = []
    lines.append('=' * 50)
    lines.append('        大学生竞赛成果管理系统 - 统计报表')
    lines.append('=' * 50)
    lines.append('')
    lines.append('一、各院系获奖人数统计')
    lines.append('-' * 50)
    lines.append('{:<20}{:>10}'.format('院系名称', '获奖人数'))
    for r in depart_data:
        lines.append('{:<20}{:>10}'.format(r['name'], r['cnt']))
    if not depart_data:
        lines.append('（暂无数据）')
    lines.append('')
    lines.append('二、历年参赛人数统计')
    lines.append('-' * 50)
    lines.append('{:<20}{:>10}'.format('年份', '参赛人数'))
    for r in year_data:
        lines.append('{:<20}{:>10}'.format(str(r['year']), r['cnt']))
    if not year_data:
        lines.append('（暂无数据）')
    lines.append('')
    lines.append('统计时间：{}'.format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    lines.append('=' * 50)

    return jsonify({'ok': True, 'content': '\n'.join(lines)})


# ---------------------------------------------------------------------------
# 9. 健康检查
# ---------------------------------------------------------------------------
@app.route('/api/health')
def api_health():
    try:
        DB.query_one('SELECT 1')
        return jsonify({'ok': True, 'db': True, 'version': APP_VERSION})
    except DatabaseError:
        # 数据库不可用时 ok=False，语义与 ok 字段一致，前端仍通过 db 字段判断
        return jsonify({'ok': False, 'db': False, 'version': APP_VERSION,
                        'msg': '数据库连接失败，请检查 MySQL 是否启动、db.py 配置是否正确，'
                               '并先执行 python db.py 完成建库初始化'})


# ---------------------------------------------------------------------------
# 10. CORS 支持（APK 内嵌页面通过 file:// 跨源访问本 API）
# ---------------------------------------------------------------------------
@app.after_request
def add_cors_headers(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Auth-Token'
    return resp


@app.before_request
def handle_preflight():
    """处理浏览器/WebView 的 OPTIONS 预检请求"""
    if request.method == 'OPTIONS':
        return ('', 204)


# ---------------------------------------------------------------------------
# 11. 移动端界面入口
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    return send_from_directory('app', 'index.html')


def get_lan_ip():
    """获取本机局域网 IP（手机通过该地址访问）"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


# ===========================================================================
# 程序入口
# ===========================================================================
if __name__ == '__main__':
    print('=' * 52)
    print('    大学生竞赛成果管理系统 - 手机 APP 后端')
    print('=' * 52)
    lan_ip = get_lan_ip()
    print('  手机访问地址: http://{}:5000'.format(lan_ip))
    print('  本机访问地址: http://127.0.0.1:5000')
    print('  默认账号: admin / admin123')
    try:
        DB.query_one('SELECT 1')
        print('  数据库连接: OK (competition_db)')
    except DatabaseError as e:
        print('  数据库连接: 失败')
        print('    请先启动 MySQL，并执行 python db.py 完成建库初始化')
        print('    {}'.format(e))
    print('=' * 52)
    # 启动前检查端口占用，避免静默失败（进程存在但未监听）
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(('0.0.0.0', 5000))
        probe.close()
    except OSError:
        print('  [错误] 端口 5000 已被其他程序占用！')
        print('         请先关闭占用程序，或运行「后端控制.bat」选 [2] 关闭后端后重试')
        raise SystemExit(1)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=False)
