/* ==========================================================================
   大学生竞赛成果管理系统 —— 移动端逻辑（复刻桌面版 PyQt5 全部功能）
   登录 / 五表 CRUD / 多条件联合查询 / 统计分析图表 / 报表导出
   ========================================================================== */
'use strict';

var state = {
  username: '',
  metaList: [],
  metaMap: {},          // key -> meta
  currentTable: 'depart',
  currentRows: [],      // 当前表格数据
  selectedRow: -1,      // 选中的行索引
  formTable: 'depart',  // 表单对应表
  editing: false,       // 表单是否编辑模式
  editingRecord: null   // 编辑时的原始记录
};

var formOptionsCache = {};  // 下拉选项缓存: depart/student/competition/award

/* ==========================================================================
   服务器地址配置
   - 浏览器直接访问后端(http://IP:5000)：API_BASE 为空，同源访问
   - APK 内嵌页面(file://)：首次启动弹出配置框，地址保存在 localStorage
   助手地址 HELPER_BASE(5001)：用于"启动电脑服务"，从配置自动推导
   ========================================================================== */
var API_BASE = '';
var HELPER_BASE = '';
(function () {
  var saved = '';
  try { saved = localStorage.getItem('api_base') || ''; } catch (e) {}
  /* 用户自定义地址优先；未设置时使用打包内置的默认地址(config.js) */
  if (!saved && window.__API_BASE__) saved = window.__API_BASE__;
  API_BASE = saved.replace(/\/+$/, '');
  /* 助手地址：优先内置，否则从 API 地址推导端口 5000->5001 */
  var hp = (window.__HELPER_BASE__ || '').replace(/\/+$/, '');
  if (!hp && API_BASE) hp = API_BASE.replace(/:\d+$/, ':5001');
  HELPER_BASE = hp;
})();

function $(id) { return document.getElementById(id); }

/* 网络异常时统一转为可读错误，前端各处只需判断 res.ok */
function api(url, options) {
  return fetch(API_BASE + url, options).then(function (r) { return r.json(); })
    .catch(function () { return { ok: false, msg: '无法连接服务器，请确认后端已启动！' }; });
}

function apiRaw(base, url, timeoutMs) {
  /* 直连指定地址（如助手 5001），带超时（兼容旧版 WebView，不用 finally） */
  /* 部分旧 WebView 不支持 AbortController，此时退化为无超时请求 */
  var ctrl = (typeof AbortController !== 'undefined') ? new AbortController() : null;
  var timer = setTimeout(function () { if (ctrl) ctrl.abort(); }, timeoutMs || 6000);
  var opts = ctrl ? { signal: ctrl.signal } : {};
  return fetch(base + url, opts)
    .then(function (r) { clearTimeout(timer); return r.json(); })
    .then(function (j) { return j; })
    .catch(function () { clearTimeout(timer); return { ok: false }; });
}

function postJSON(url, data) {
  return api(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
}

/* ==========================================================================
   消息弹窗
   ========================================================================== */
function showMsg(title, content, cb) {
  $('msg-title').textContent = title;
  $('msg-content').textContent = content;
  $('msg-cancel').style.display = 'none';
  $('msg-ok').textContent = '确 定';
  $('msg-mask').style.display = 'flex';
  $('msg-ok').onclick = function () {
    $('msg-mask').style.display = 'none';
    if (cb) cb();
  };
}

function showConfirm(title, content, onYes) {
  $('msg-title').textContent = title;
  $('msg-content').textContent = content;
  $('msg-cancel').style.display = '';
  $('msg-ok').textContent = '确 定';
  $('msg-mask').style.display = 'flex';
  $('msg-cancel').onclick = function () { $('msg-mask').style.display = 'none'; };
  $('msg-ok').onclick = function () {
    $('msg-mask').style.display = 'none';
    if (onYes) onYes();
  };
}

/* ==========================================================================
   登录
   ========================================================================== */
$('login-btn').addEventListener('click', doLogin);
$('login-user').addEventListener('keydown', function (e) { if (e.key === 'Enter') doLogin(); });
$('login-pass').addEventListener('keydown', function (e) { if (e.key === 'Enter') doLogin(); });

function doLogin() {
  var u = $('login-user').value.trim();
  var p = $('login-pass').value;
  $('login-msg').textContent = '';
  $('start-service-status').style.display = 'none';
  if (!u || !p) { $('login-msg').textContent = '用户名和密码不能为空！'; return; }
  postJSON('/api/login', { username: u, password: p }).then(function (res) {
    if (res.ok) {
      state.username = u;
      checkHealthAndEnter();
    } else if (res.msg && res.msg.indexOf('无法连接服务器') === 0) {
      $('login-msg').textContent = '无法连接后端，请先点下方"启动电脑服务"（需电脑开机且与手机同一Wi-Fi）';
    } else {
      $('login-msg').textContent = res.msg;
      $('login-pass').value = '';
      $('login-pass').focus();
    }
  });
}

/* 登录后先检测数据库是否可用，避免进入界面后才发现连接失败 */
function checkHealthAndEnter() {
  api('/api/health').then(function (res) {
    if (res.db) {
      enterMain();
      return;
    }
    var reason = (res.msg && res.msg.indexOf('无法连接服务器') !== 0) ? res.msg
               : 'MySQL 未启动或数据库未初始化';
    showMsg('数据库连接失败',
      reason + '\n\n请点击下方"启动电脑服务"尝试自动修复；\n若仍失败，请在电脑上检查 MySQL 是否已启动。',
      function () {
        showStartServiceStatus('数据库连接失败：' + reason, '#e74c3c');
      });
  });
}

/* ==========================================================================
   启动电脑服务：请求电脑上的助手(5001) 拉起 MySQL + 后端
   ========================================================================== */
function showStartServiceStatus(text, color) {
  var el = $('start-service-status');
  el.textContent = text;
  el.style.color = color || '#28b463';
  el.style.display = 'block';
}

function startComputerService(onDone) {
  if (!HELPER_BASE) {
    $('login-msg').textContent = '未配置助手地址，请先进入"服务器设置"填写后端地址。';
    return;
  }
  showStartServiceStatus('正在请求电脑启动服务...', '#1a6fb5');
  apiRaw(HELPER_BASE, '/start', 10000).then(function (res) {
    /* /start 返回 202 + {ok:true}；res 可能无 ok（低版本助手），按已提交处理 */
    if (res.ok === false) {
      showStartServiceStatus('请求失败：无法连接电脑助手(' + HELPER_BASE + ')，请确认电脑已开机且助手在运行。', '#e74c3c');
      if (onDone) onDone(false);
      return;
    }
    /* 轮询等待全部就绪：后端 + MySQL + 数据库可连（最多 40 秒） */
    var tries = 0;
    var timer = setInterval(function () {
      apiRaw(HELPER_BASE, '/status', 5000).then(function (st) {
        /* 请求失败（如 CORS/网络不通）时立即提示，避免空等 40 秒 */
        if (!st || st.ok === false) {
          clearInterval(timer);
          showStartServiceStatus('无法连接电脑助手，请确认电脑已开机、助手已启动，且手机与电脑在同一Wi-Fi。', '#e74c3c');
          if (onDone) onDone(false);
          return;
        }
        var mysqlOk = st.mysql === true;
        var backendOk = st.backend === true;
        var dbOk = st.db === true;
        if (backendOk && mysqlOk && dbOk) {
          clearInterval(timer);
          showStartServiceStatus('启动成功！正在重新登录...', '#28b463');
          if (onDone) onDone(true);
        } else if (++tries >= 20) {
          clearInterval(timer);
          var reason = st.db_msg || '';
          showStartServiceStatus(
            '等待超时。当前状态：后端' + (backendOk ? '正常' : '未就绪') +
            '，MySQL' + (mysqlOk ? '正常' : '未就绪') +
            '，数据库' + (dbOk ? '正常' : '失败' + (reason ? '（' + reason + '）' : '')) +
            '。请到电脑上检查。', '#e74c3c');
          if (onDone) onDone(false);
        }
      });
    }, 2000);
  });
}

/* 登录页"启动电脑服务"与设置弹窗按钮统一绑定 */
function bindStartService() {
  var run = function () {
    $('config-mask').style.display = 'none';
    startComputerService(function (ok) {
      if (ok) doLogin();
    });
  };
  $('btn-start-service').addEventListener('click', run);
  $('btn-config-start').addEventListener('click', run);
}

/* 服务器地址配置弹窗 */
function openServerConfig() {
  $('server-input').value = API_BASE || '';
  $('config-mask').style.display = 'flex';
}

function saveServerConfig() {
  var v = $('server-input').value.trim().replace(/\/+$/, '');
  if (!v) { showMsg('提示', '请输入服务器地址！'); return; }
  /* 缺省 http:// 前缀时自动补全 */
  if (!/^https?:\/\//.test(v)) v = 'http://' + v;
  /* 缺省端口时自动补 5000（后端默认端口） */
  if (!/:\d+(\/|$)/.test(v)) v = v + ':5000';
  API_BASE = v;
  /* 同步助手地址（端口 5000->5001） */
  if (!window.__HELPER_BASE__) HELPER_BASE = v.replace(/:\d+$/, ':5001');
  try { localStorage.setItem('api_base', v); } catch (e) {}
  $('config-mask').style.display = 'none';
  showMsg('已保存', '服务器地址已保存：' + v);
}

function enterMain() {
  $('topbar').textContent = '👤 当前用户：' + state.username + '　|　欢迎使用大学生竞赛成果管理系统';
  $('login-screen').style.display = 'none';
  $('main-screen').style.display = 'flex';
  initMeta();
}

/* ==========================================================================
   初始化：加载表元信息 + 下拉选项
   ========================================================================== */
function initMeta() {
  api('/api/meta').then(function (res) {
    if (!res.ok) { showMsg('错误', res.msg); return; }
    state.metaList = res.meta;
    state.metaList.forEach(function (m) { state.metaMap[m.key] = m; });

    var sel = $('table-select');
    sel.innerHTML = '';
    state.metaList.forEach(function (m) {
      var o = document.createElement('option');
      o.value = m.key;
      o.textContent = m.title;
      sel.appendChild(o);
    });

    preloadOptions();
    buildSearchRows();
    sel.onchange = onTableChange;
    $('btn-refresh').onclick = loadData;
    $('btn-add').onclick = function () { openForm(null); };
    $('btn-edit').onclick = editRecord;
    $('btn-del').onclick = deleteRecord;
    $('btn-search').onclick = doSearch;
    $('btn-clear').onclick = resetSearch;
    $('btn-draw').onclick = drawChart;
    $('btn-export').onclick = exportReport;
    $('btn-save').onclick = saveForm;
    $('btn-cancel').onclick = function () { $('form-mask').style.display = 'none'; };
    $('btn-export-close').onclick = function () { $('export-mask').style.display = 'none'; };
    $('btn-copy').onclick = copyReport;
    $('btn-download').onclick = downloadReport;
    $('chart-select').onchange = clearChart;
    document.querySelectorAll('.tabbar-item').forEach(function (el) {
      el.onclick = function () { switchTab(el.dataset.tab); };
    });

    loadData();
  }).catch(function () { showMsg('错误', '无法获取数据表信息'); });
}

function preloadOptions() {
  ['depart', 'student', 'competition', 'award'].forEach(function (t) {
    api('/api/options?type=' + t).then(function (res) {
      if (res.ok) formOptionsCache[t] = res.options;
    });
  });
}

/* ==========================================================================
   底部导航切换
   ========================================================================== */
function switchTab(tab) {
  document.querySelectorAll('.tabbar-item').forEach(function (e) {
    e.classList.toggle('active', e.dataset.tab === tab);
  });
  $('tab-data').style.display = tab === 'data' ? '' : 'none';
  $('tab-stat').style.display = tab === 'stat' ? '' : 'none';
  if (tab === 'stat') clearChart();
}

/* ==========================================================================
   数据管理：切换表 / 加载 / 填充
   ========================================================================== */
function onTableChange() {
  state.currentTable = $('table-select').value;
  state.selectedRow = -1;
  refreshSearchFieldOptions();
  loadData();
}

function loadData() {
  api('/api/data?table=' + encodeURIComponent(state.currentTable)).then(function (res) {
    if (!res.ok) { showMsg('错误', res.msg); return; }
    state.currentRows = res.rows;
    state.selectedRow = -1;
    fillTable(res.rows);
    $('table-tip').textContent = '共 ' + res.rows.length + ' 条记录';
  });
}

function fillTable(rows) {
  var meta = state.metaMap[state.currentTable];
  var thead = $('data-table').querySelector('thead');
  var tbody = $('data-table').querySelector('tbody');

  var htr = document.createElement('tr');
  meta.headers.forEach(function (h) {
    var th = document.createElement('th');
    th.textContent = h;
    htr.appendChild(th);
  });
  thead.innerHTML = '';
  thead.appendChild(htr);

  tbody.innerHTML = '';
  rows.forEach(function (row, idx) {
    var tr = document.createElement('tr');
    tr.dataset.idx = idx;
    meta.columns.forEach(function (col) {
      var td = document.createElement('td');
      var v = row[col];
      td.textContent = (v === null || v === undefined) ? '' : String(v);
      tr.appendChild(td);
    });
    tr.addEventListener('click', (function (i) {
      return function () { selectRow(i); };
    })(idx));
    tbody.appendChild(tr);
  });
}

function selectRow(idx) {
  state.selectedRow = idx;
  var trs = $('data-table').querySelectorAll('tbody tr');
  trs.forEach(function (tr) {
    tr.classList.toggle('selected', parseInt(tr.dataset.idx, 10) === idx);
  });
}

function getSelectedRecord() {
  if (state.selectedRow < 0 || !state.currentRows[state.selectedRow]) return null;
  return state.currentRows[state.selectedRow];
}

/* ==========================================================================
   多条件联合查询
   ========================================================================== */
function buildSearchRows() {
  var wrap = $('search-rows');
  wrap.innerHTML = '';
  for (var i = 0; i < 3; i++) {
    var row = document.createElement('div');
    row.className = 'search-row';
    var fieldSel = document.createElement('select');
    var opSel = document.createElement('select');
    opSel.className = 'op';
    ['=', '包含'].forEach(function (op) {
      var o = document.createElement('option');
      o.textContent = op;
      opSel.appendChild(o);
    });
    var valInput = document.createElement('input');
    valInput.placeholder = '条件值';
    row.appendChild(fieldSel);
    row.appendChild(opSel);
    row.appendChild(valInput);
    wrap.appendChild(row);
  }
  refreshSearchFieldOptions();
}

function refreshSearchFieldOptions() {
  var meta = state.metaMap[state.currentTable];
  var rows = $('search-rows').children;
  for (var i = 0; i < rows.length; i++) {
    var sel = rows[i].children[0];
    sel.innerHTML = '';
    var opt = document.createElement('option');
    opt.value = '';
    opt.textContent = '(不使用)';
    sel.appendChild(opt);
    (meta.search_fields || []).forEach(function (f) {
      var o = document.createElement('option');
      o.value = f.expr;
      o.textContent = f.name;
      sel.appendChild(o);
    });
    rows[i].children[1].selectedIndex = 0;
    rows[i].children[2].value = '';
  }
}

function doSearch() {
  var conds = [];
  var rows = $('search-rows').children;
  for (var i = 0; i < rows.length; i++) {
    var expr = rows[i].children[0].value;
    var op = rows[i].children[1].value;
    var v = rows[i].children[2].value.trim();
    if (expr && v) conds.push({ expr: expr, op: op, value: v });
  }
  postJSON('/api/search', { table: state.currentTable, conds: conds }).then(function (res) {
    if (!res.ok) { showMsg('查询失败', res.msg); return; }
    state.currentRows = res.rows;
    state.selectedRow = -1;
    fillTable(res.rows);
    $('table-tip').textContent = '查询到 ' + res.rows.length + ' 条记录';
  });
}

function resetSearch() {
  var rows = $('search-rows').children;
  for (var i = 0; i < rows.length; i++) {
    rows[i].children[0].selectedIndex = 0;
    rows[i].children[1].selectedIndex = 0;
    rows[i].children[2].value = '';
  }
  loadData();
}

/* ==========================================================================
   新增 / 修改 / 删除
   ========================================================================== */
function editRecord() {
  var row = getSelectedRecord();
  if (!row) { showMsg('提示', '请先在表格中选择一条记录！'); return; }
  if (state.currentTable === 'record') {
    /* 联查展示的是可读字段，编辑时按主键取原始记录回填外键 */
    api('/api/data/record/' + row.rec_id).then(function (res) {
      if (res.ok) openForm(res.record);
      else showMsg('错误', res.msg);
    });
  } else {
    openForm(row);
  }
}

function deleteRecord() {
  var row = getSelectedRecord();
  if (!row) { showMsg('提示', '请先在表格中选择一条记录！'); return; }
  var meta = state.metaMap[state.currentTable];
  var pkValue = row[meta.pk];
  showConfirm('确认删除', '确定要删除该条记录吗？\n此操作不可恢复！', function () {
    api('/api/data/' + state.currentTable + '/' + encodeURIComponent(pkValue),
      { method: 'DELETE' }).then(function (res) {
      if (res.ok) showMsg('成功', '删除成功！', loadData);
      else showMsg('删除失败', res.msg);
    });
  });
}

/* ==========================================================================
   记录编辑表单
   ========================================================================== */
function makeSelect(options) {
  var s = document.createElement('select');
  options.forEach(function (pair) {
    var o = document.createElement('option');
    o.value = pair[1];
    o.textContent = pair[0];
    s.appendChild(o);
  });
  return s;
}

function makeCombo(otype) {
  /* 下拉 + 手动输入 二合一控件（对应桌面版可编辑下拉框） */
  var wrap = document.createElement('div');
  wrap.className = 'combo-wrap';
  var sel = document.createElement('select');
  (formOptionsCache[otype] || []).forEach(function (o) {
    var op = document.createElement('option');
    op.value = String(o.id);
    op.textContent = otype === 'student' ? (o.id + ' - ' + o.name) : o.name;
    sel.appendChild(op);
  });
  var input = document.createElement('input');
  input.type = 'text';
  input.style.display = 'none';
  var btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'combo-toggle';
  btn.textContent = '手动输入';
  btn.onclick = function () {
    var usingInput = input.style.display !== 'none';
    if (usingInput) {
      input.style.display = 'none';
      sel.style.display = '';
      btn.textContent = '手动输入';
    } else {
      input.style.display = '';
      sel.style.display = 'none';
      btn.textContent = '下拉选择';
    }
  };
  wrap.appendChild(sel);
  wrap.appendChild(input);
  wrap.appendChild(btn);
  wrap.__sel = sel;
  wrap.__input = input;
  wrap.__btn = btn;
  return wrap;
}

function openForm(record) {
  state.formTable = state.currentTable;
  state.editing = record !== null && record !== undefined;
  state.editingRecord = state.editing ? record : null;

  var meta = state.metaMap[state.formTable];
  $('form-title').textContent = (state.editing ? '修改记录 - ' : '新增记录 - ') + meta.title;

  /* 先加载所需下拉选项，再渲染表单 */
  var needed = {};
  meta.form_fields.forEach(function (ff) {
    if (ff.type === 'depart') needed.depart = 1;
    if (ff.type === 'stuid_select') needed.student = 1;
    if (ff.type === 'com_select') needed.competition = 1;
    if (ff.type === 'award_select') needed.award = 1;
  });
  var tasks = Object.keys(needed).map(function (t) {
    return api('/api/options?type=' + t).then(function (res) {
      if (res.ok) formOptionsCache[t] = res.options;
    });
  });
  Promise.all(tasks).then(function () { renderForm(record); });
}

function renderForm(record) {
  var meta = state.metaMap[state.formTable];
  var body = $('form-body');
  body.innerHTML = '';

  meta.form_fields.forEach(function (ff) {
    var wrapper = document.createElement('div');
    wrapper.className = 'form-item';
    var lab = document.createElement('label');
    lab.textContent = ff.label + ':';
    wrapper.appendChild(lab);
    wrapper.appendChild(createControl(meta, ff, record));
    body.appendChild(wrapper);
  });

  $('form-mask').style.display = 'flex';
}

function createControl(meta, ff, record) {
  var c;
  switch (ff.type) {
    case 'gender':
      c = makeSelect([['男', '男'], ['女', '女']]);
      break;
    case 'level':
      c = makeSelect([['国家级', '国家级'], ['省级', '省级'], ['校级', '校级']]);
      break;
    case 'rank':
      c = makeSelect([['一等奖', '1'], ['二等奖', '2'], ['三等奖', '3']]);
      break;
    case 'year':
      c = document.createElement('input');
      c.type = 'number';
      c.min = 2000;
      c.max = new Date().getFullYear() + 1;
      break;
    case 'depart':
      c = makeSelect((formOptionsCache.depart || []).map(function (o) {
        return [o.name, String(o.id)];
      }));
      break;
    case 'stuid_select':
      c = makeCombo('student');
      break;
    case 'com_select':
      c = makeCombo('competition');
      break;
    case 'award_select':
      c = makeCombo('award');
      break;
    default:
      c = document.createElement('input');
      c.type = 'text';
      if (ff.type === 'phone' || ff.type === 'stuid') c.inputmode = 'numeric';
  }
  c.dataset.field = ff.field;
  c.dataset.ftype = ff.type;

  /* 回填数据 */
  if (record) {
    var val = record[ff.field];
    if (val !== null && val !== undefined) {
      if (c.tagName === 'SELECT') {
        c.value = String(val);
      } else if (c.classList.contains('combo-wrap')) {
        c.__sel.value = String(val);
        if (c.__sel.selectedIndex < 0) {
          /* 值不在下拉列表中 -> 自动切到手动输入并回填 */
          c.__input.value = String(val);
          c.__input.style.display = '';
          c.__sel.style.display = 'none';
          c.__btn.textContent = '下拉选择';
        }
      } else {
        c.value = String(val);
      }
    }
  } else if (ff.type === 'year') {
    c.value = '2024';
  }

  /* 编辑时主键只读 */
  if (record && ff.field === meta.pk) c.disabled = true;
  return c;
}

function collectForm() {
  var meta = state.metaMap[state.formTable];
  var data = {};
  var items = $('form-body').querySelectorAll('.form-item');
  for (var i = 0; i < items.length; i++) {
    var ff = meta.form_fields[i];
    if (!ff) continue;
    var control = items[i].querySelector('[data-field]');
    var val = null;

    if (control.tagName === 'SELECT') {
      val = control.value;
    } else if (control.classList.contains('combo-wrap')) {
      if (control.__input.style.display !== 'none') val = control.__input.value.trim();
      else val = control.__sel.value;
    } else {
      val = control.value.trim();
    }

    /* 输入校验（与桌面版一致） */
    var label = ff.label;
    if (ff.type === 'stuid' || ff.type === 'stuid_select') {
      if (!/^\d{10}$/.test(val)) { showMsg('输入错误', '学号必须为10位数字！'); return null; }
    } else if (ff.type === 'phone') {
      if (val && !/^\d{11}$/.test(val)) { showMsg('输入错误', '联系电话必须为11位数字！'); return null; }
    } else if (ff.type === 'year') {
      var y = parseInt(val, 10);
      if (isNaN(y) || y < 2000 || y > new Date().getFullYear() + 1) { showMsg('输入错误', label + '年份超出有效范围！'); return null; }
    } else if (ff.type === 'gender' || ff.type === 'level' || ff.type === 'rank' ||
               ff.type === 'depart' || ff.type === 'com_select' ||
               ff.type === 'award_select') {
      if (!val) { showMsg('输入错误', '请选择' + label + '！'); return null; }
    } else {
      if (!val) { showMsg('输入错误', label + '不能为空！'); return null; }
      if (val.length > 100) { showMsg('输入错误', label + '长度不能超过100个字符！'); return null; }
    }

    if (ff.field !== meta.pk) data[ff.field] = val;
  }
  return data;
}

function saveForm() {
  var data = collectForm();
  if (!data) return;

  var url = '/api/data';
  var method = 'POST';
  if (state.editing) {
    var pk = state.metaMap[state.formTable].pk;
    var pkValue = state.editingRecord[pk];
    url = '/api/data/' + state.formTable + '/' + encodeURIComponent(pkValue);
    method = 'PUT';
  }
  api(url, {
    method: method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ table: state.formTable, data: data })
  }).then(function (res) {
    if (res.ok) {
      $('form-mask').style.display = 'none';
      showMsg('成功', '保存成功！', loadData);
    } else {
      showMsg('数据库错误', res.msg);
    }
  });
}

/* ==========================================================================
   统计分析：柱状图 / 折线图（Canvas 绘制，无需图表库）
   ========================================================================== */
function truncate(s, n) { return s.length > n ? s.slice(0, n) + '…' : s; }

function clearChart() {
  var cv = $('chart-canvas');
  var dpr = window.devicePixelRatio || 1;
  var w = cv.clientWidth || 360, h = cv.clientHeight || 320;
  cv.width = w * dpr;
  cv.height = h * dpr;
  var ctx = cv.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  $('chart-empty').style.display = 'flex';
}

function drawBarChart(canvas, data, title, xlabel) {
  $('chart-empty').style.display = 'none';
  var dpr = window.devicePixelRatio || 1;
  var w = canvas.clientWidth || 360, h = canvas.clientHeight || 320;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  var ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);

  var padL = 46, padR = 14, padT = 34, padB = 46;
  var pw = w - padL - padR, ph = h - padT - padB;
  var maxV = 1;
  data.forEach(function (d) { if (d[1] > maxV) maxV = d[1]; });

  ctx.fillStyle = '#1a5276';
  ctx.font = 'bold 14px sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  ctx.fillText(title, w / 2, 8);

  ctx.font = '11px sans-serif';
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  for (var i = 0; i <= 4; i++) {
    var y = padT + ph - ph * i / 4;
    ctx.strokeStyle = '#e2e8f0';
    ctx.beginPath();
    ctx.moveTo(padL, y);
    ctx.lineTo(w - padR, y);
    ctx.stroke();
    ctx.fillStyle = '#7f8c8d';
    ctx.fillText(String(Math.round(maxV * i / 4)), padL - 6, y);
  }

  var n = data.length, slot = pw / n, bw = slot * 0.5;
  ctx.textAlign = 'center';
  data.forEach(function (d, idx) {
    var x = padL + slot * idx + (slot - bw) / 2;
    var bh = ph * d[1] / maxV;
    ctx.fillStyle = '#4e9acd';
    ctx.fillRect(x, padT + ph - bh, bw, bh);
    ctx.fillStyle = '#333';
    ctx.font = 'bold 11px sans-serif';
    ctx.textBaseline = 'bottom';
    ctx.fillText(String(d[1]), x + bw / 2, padT + ph - bh - 3);
    ctx.fillStyle = '#555';
    ctx.font = '11px sans-serif';
    ctx.textBaseline = 'top';
    ctx.fillText(truncate(String(d[0]), 6), x + bw / 2, padT + ph + 6);
  });

  ctx.fillStyle = '#7f8c8d';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  ctx.fillText(xlabel, w / 2, h - 12);
}

function drawLineChart(canvas, data, title, xlabel) {
  $('chart-empty').style.display = 'none';
  var dpr = window.devicePixelRatio || 1;
  var w = canvas.clientWidth || 360, h = canvas.clientHeight || 320;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  var ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);

  var padL = 46, padR = 14, padT = 34, padB = 46;
  var pw = w - padL - padR, ph = h - padT - padB;
  var maxV = 1;
  data.forEach(function (d) { if (d[1] > maxV) maxV = d[1]; });

  ctx.fillStyle = '#1a5276';
  ctx.font = 'bold 14px sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  ctx.fillText(title, w / 2, 8);

  ctx.font = '11px sans-serif';
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  for (var i = 0; i <= 4; i++) {
    var y = padT + ph - ph * i / 4;
    ctx.strokeStyle = '#e2e8f0';
    ctx.beginPath();
    ctx.moveTo(padL, y);
    ctx.lineTo(w - padR, y);
    ctx.stroke();
    ctx.fillStyle = '#7f8c8d';
    ctx.fillText(String(Math.round(maxV * i / 4)), padL - 6, y);
  }

  var n = data.length;
  var pts = data.map(function (d, idx) {
    return {
      x: n === 1 ? padL + pw / 2 : padL + pw * idx / (n - 1),
      y: padT + ph - ph * d[1] / maxV,
      v: d[1]
    };
  });

  ctx.strokeStyle = '#e67e22';
  ctx.lineWidth = 2;
  ctx.lineJoin = 'round';
  ctx.beginPath();
  pts.forEach(function (p, idx) {
    if (idx === 0) ctx.moveTo(p.x, p.y);
    else ctx.lineTo(p.x, p.y);
  });
  ctx.stroke();

  ctx.fillStyle = '#e67e22';
  pts.forEach(function (p) {
    ctx.beginPath();
    ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
    ctx.fill();
  });

  ctx.fillStyle = '#333';
  ctx.font = 'bold 11px sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'bottom';
  pts.forEach(function (p) { ctx.fillText(String(p.v), p.x, p.y - 8); });

  ctx.fillStyle = '#555';
  ctx.font = '11px sans-serif';
  ctx.textBaseline = 'top';
  pts.forEach(function (p, idx) { ctx.fillText(String(data[idx][0]), p.x, padT + ph + 6); });

  ctx.fillStyle = '#7f8c8d';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  ctx.fillText(xlabel, w / 2, h - 12);
}

var currentChart = null;  // 当前图表 {type, data}，横屏切换时用于重绘

function renderChart() {
  if (!currentChart) return;
  if (currentChart.type === 'depart_bar') {
    drawBarChart($('chart-canvas'), currentChart.data, '各院系获奖人数统计', '院系');
  } else {
    drawLineChart($('chart-canvas'), currentChart.data, '历年参赛人数统计', '年份');
  }
}

function drawChart() {
  var type = $('chart-select').value;
  var url = type === 'depart_bar' ? '/api/stat/depart_award' : '/api/stat/year_join';
  api(url).then(function (res) {
    if (!res.ok) { showMsg('错误', res.msg); return; }
    if (!res.data || !res.data.length) {
      showMsg('提示', type === 'depart_bar' ? '暂无获奖记录数据！' : '暂无参赛记录数据！');
      currentChart = null;
      clearChart();
      return;
    }
    currentChart = { type: type, data: res.data };
    renderChart();
  });
}

/* 横竖屏切换 / 窗口尺寸变化时重绘图表 */
window.addEventListener('resize', function () {
  if (currentChart) renderChart();
});

/* ==========================================================================
   报表导出（txt）
   ========================================================================== */
function exportReport() {
  api('/api/export').then(function (res) {
    if (!res.ok) { showMsg('错误', res.msg); return; }
    $('export-content').value = res.content;
    $('export-mask').style.display = 'flex';
  });
}

function copyReport() {
  var ta = $('export-content');
  var done = function () { showMsg('复制成功', '报表内容已复制到剪贴板'); };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(ta.value).then(done).catch(function () { done(); });
  } else {
    ta.select();
    document.execCommand('copy');
    done();
  }
}

function downloadReport() {
  var blob = new Blob([$('export-content').value], { type: 'text/plain;charset=utf-8' });
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = '竞赛成果统计报表.txt';
  a.click();
}

/* ==========================================================================
   初始化：配置弹窗绑定 + 首次启动检测
   ========================================================================== */
$('btn-server-set').addEventListener('click', openServerConfig);
$('btn-config-cancel').addEventListener('click', function () {
  $('config-mask').style.display = 'none';
});
$('btn-config-save').addEventListener('click', saveServerConfig);
$('btn-config-default').addEventListener('click', function () {
  var d = window.__API_BASE__ || '';
  if (!d) { showMsg('提示', '本安装包未内置默认地址，请手动输入'); return; }
  $('server-input').value = d;
});
$('server-input').addEventListener('keydown', function (e) {
  if (e.key === 'Enter') saveServerConfig();
});

/* 绑定"启动电脑服务"按钮 */
bindStartService();

/* APK 内嵌模式（file://）且未配置过服务器地址时，弹出配置框 */
window.addEventListener('load', function () {
  if (!API_BASE && location.protocol === 'file:') {
    openServerConfig();
  }
});
