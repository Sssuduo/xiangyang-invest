"""产业链招商前端视觉自检：本地起后端 + 前端 preview，Playwright 截图。

用法：python scripts/visual_check_chain.py
截图输出：G:/123/2026-11-13-16-05-00/outputs/shots/
"""
import os
import subprocess
import sys
import time
import shutil
import urllib.request

BACKEND = r'H:\项目1\backend'
FRONTEND = r'H:\项目1\frontend'
OUT = r'G:\123\2026-11-13-16-05-00\outputs\shots'
PY = r'G:\123\python.exe'
NODE = r'C:\Program Files\nodejs\node.exe'

os.makedirs(OUT, exist_ok=True)

BACKEND_PORT = 15099
FRONTEND_PORT = 15098


def wait_http(url, timeout=60, expect_json_ok=False):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if r.status < 500:
                    if not expect_json_ok:
                        return True
        except urllib.error.HTTPError as e:
            if e.code == 401 and expect_json_ok:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def main():
    import playwright
    from playwright.sync_api import sync_playwright

    # ---- 启动后端（独立测试库，放临时目录避免中文路径问题）----
    import tempfile
    dbfile = os.path.join(tempfile.gettempdir(), 'chain_vc.db')
    if os.path.exists(dbfile):
        os.remove(dbfile)
    dburl = 'sqlite:///' + dbfile.replace('\\', '/')
    env = dict(os.environ)
    env['DATABASE_URL'] = dburl
    env['FLASK_ENV'] = 'development'

    import tempfile
    log_dir = tempfile.gettempdir()
    backend_log = open(os.path.join(log_dir, 'vc_backend.log'), 'w', encoding='utf-8')
    preview_log = open(os.path.join(log_dir, 'vc_frontend.log'), 'w', encoding='utf-8')

    backend = subprocess.Popen(
        [PY, '-c',
         'import os,sys;sys.path.insert(0,r"%s");'
         'os.environ["DATABASE_URL"]="%s";'
         'from app import create_app;'
         'app=create_app("development");'
         'app.run(host="127.0.0.1",port=%d,debug=False,use_reloader=False)' % (BACKEND, dburl, BACKEND_PORT)],
        cwd=BACKEND, env=env,
        stdout=backend_log, stderr=subprocess.STDOUT)

    if not wait_http(f'http://127.0.0.1:{BACKEND_PORT}/api/chain/overview', 90, expect_json_ok=True):
        print('后端启动失败：')
        backend_log.flush()
        with open(os.path.join(log_dir, 'vc_backend.log'), encoding='utf-8', errors='ignore') as f:
            print(f.read()[-3000:])
        backend.kill()
        return 1
    print('后端已启动 :%d' % BACKEND_PORT)

    # ---- 启动前端 preview（代理到后端）----
    # 预览模式需要把 /api 代理到本地测试后端：运行时生成一份临时 vite 配置
    vc_config = os.path.join(FRONTEND, 'vite.vc.config.js')
    with open(vc_config, 'w', encoding='utf-8') as f:
        f.write("""import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  preview: {
    port: %d,
    host: '127.0.0.1',
    proxy: {
      '/api': { target: 'http://127.0.0.1:%d', changeOrigin: true },
      '/static': { target: 'http://127.0.0.1:%d', changeOrigin: true }
    }
  }
})
""" % (FRONTEND_PORT, BACKEND_PORT, BACKEND_PORT))

    preview = subprocess.Popen(
        [NODE, 'node_modules/vite/bin/vite.js', 'preview', '--config', 'vite.vc.config.js',
         '--port', str(FRONTEND_PORT), '--strictPort', '--host', '127.0.0.1'],
        cwd=FRONTEND, stdout=preview_log, stderr=subprocess.STDOUT)
    if not wait_http(f'http://127.0.0.1:{FRONTEND_PORT}/', 60):
        print('前端启动失败：')
        preview_log.flush()
        with open(os.path.join(log_dir, 'vc_frontend.log'), encoding='utf-8', errors='ignore') as f:
            print(f.read()[-2000:])
        backend.kill()
        preview.kill()
        return 1
    print('前端已启动 :%d' % FRONTEND_PORT)

    shots = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', args=['--no-sandbox'])
            ctx = browser.new_context(viewport={'width': 1600, 'height': 1000},
                                      device_scale_factor=1.5)
            page = ctx.new_page()
            errors = []
            page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
            page.on('pageerror', lambda e: errors.append('PAGEERROR: ' + str(e)))

            # 登录：在页面上下文内发起，保证 cookie 写入浏览器会话
            base = f'http://127.0.0.1:{FRONTEND_PORT}'
            page.goto(base + '/', wait_until='networkidle')
            login = page.evaluate("""async (base) => {
                const r = await fetch(base + '/api/auth/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    credentials: 'include',
                    body: JSON.stringify({username: 'demo', password: 'demo123'})
                });
                return {status: r.status, text: (await r.text()).slice(0, 160)};
            }""", base)
            print('登录:', login)

            page.goto(base + '/chain', wait_until='networkidle')
            page.wait_for_timeout(2500)
            shots.append(('01-graph', OUT + '/chain-01-graph.png'))
            page.screenshot(path=shots[-1][1], full_page=True)

            # 图谱页：三级层级（大类分组条 + 大类面板 + 属地分布）
            graph_probe = page.evaluate("""() => {
                return {
                    groupBars: document.querySelectorAll('.group-bar-text').length,
                    groupCards: document.querySelectorAll('.group-card').length,
                    regionEnt: document.querySelectorAll('.region-ent-item').length,
                    statCards: document.querySelectorAll('.stat-card').length,
                    nodeCount: document.querySelectorAll('.node-group').length,
                };
            }""")
            print('图谱页探针:', graph_probe)
            assert graph_probe['groupBars'] >= 8, f'大类分组条偏少：{graph_probe["groupBars"]}'
            assert graph_probe['groupCards'] == 9, f'大类卡片应为 9：{graph_probe["groupCards"]}'
            assert graph_probe['regionEnt'] == 2, '属地分布应为 2 条'
            assert graph_probe['statCards'] == 12, f'统计卡片应为 12：{graph_probe["statCards"]}'

            # 页签二：缺口与优先级
            tabs = page.locator('.chain-tabs .el-tabs__item')
            print('页签数:', tabs.count())
            assert tabs.count() == 6, f'页签应为 6 个（更新日志、评判规则各自独立）：{tabs.count()}'
            tabs.nth(1).click()
            page.wait_for_timeout(2200)
            shots.append(('02-gap', OUT + '/chain-02-gap.png'))
            page.screenshot(path=shots[-1][1], full_page=True)

            # 缺口卡片：雷达图 + 布局 + 悬停提示 + 内嵌目标企业表格
            gap_probe = page.evaluate("""() => {
                const cards = document.querySelectorAll('.gap-card');
                const radars = document.querySelectorAll('.gap-radar');
                const canvases = document.querySelectorAll('.gap-radar canvas');
                // 默认单列：第 1、2 张卡片左边缘对齐且上下排列
                let oneCol = false;
                if (cards.length >= 2) {
                    const a = cards[0].getBoundingClientRect();
                    const b = cards[1].getBoundingClientRect();
                    oneCol = Math.abs(a.left - b.left) < 4 && (b.top - a.top) > 100;
                }
                const canvasSizes = [];
                canvases.forEach(c => canvasSizes.push({w: c.width, h: c.height}));
                // 雷达图与文字评述左右并排：评述区左边缘应落在雷达图右边缘之后
                const firstCard = cards[0];
                const radarBox = firstCard.querySelector('.gap-radar-box');
                const comment = firstCard.querySelector('.gap-comment');
                let sideBySide = false, commentRight = 0, radarRight = 0;
                if (radarBox && comment) {
                    const rb = radarBox.getBoundingClientRect();
                    const cb = comment.getBoundingClientRect();
                    radarRight = Math.round(rb.right);
                    commentRight = Math.round(cb.right);
                    sideBySide = cb.left >= rb.right - 2;
                }
                // 内嵌目标企业表格：默认收起（无 table 渲染），但每个卡片有折叠按钮
                const toggles = document.querySelectorAll('.gap-targets-toggle').length;
                const inlineTables = document.querySelectorAll('.gap-target-table').length;
                return {
                    cards: cards.length,
                    radars: radars.length,
                    canvases: canvases.length,
                    zeroCanvas: canvasSizes.filter(s => s.w === 0 || s.h === 0).length,
                    oneCol,
                    gridCols: getComputedStyle(document.querySelector('.gap-cards')).gridTemplateColumns,
                    factorRows: document.querySelectorAll('.gap-factor-row').length,
                    sideBySide,
                    commentRight,
                    radarRight,
                    toggles,
                    inlineTables,
                    hasRadioGroup: document.querySelectorAll('.gap-cards').length > 0
                        && !!document.querySelector('.el-radio-group'),
                };
            }""")
            print('缺口雷达图探针:', gap_probe)
            assert gap_probe['cards'] == 18, f'缺口卡片应为 18：{gap_probe["cards"]}'
            assert gap_probe['radars'] == 18, f'雷达图容器应为 18：{gap_probe["radars"]}'
            assert gap_probe['canvases'] >= 1, '雷达图 canvas 未初始化'
            assert gap_probe['zeroCanvas'] == 0, f'存在 0×0 雷达图 canvas：{gap_probe}'
            assert gap_probe['oneCol'], f'缺口卡片默认应为单列排布：{gap_probe["gridCols"]}'
            assert gap_probe['sideBySide'], (
                f'文字评述未移至雷达图右侧（radarRight={gap_probe["radarRight"]}, '
                f'commentRight={gap_probe["commentRight"]}）')
            assert gap_probe['toggles'] == 18, f'每张卡片应有目标企业折叠按钮：{gap_probe["toggles"]}'
            assert gap_probe['inlineTables'] == 0, '目标企业表格默认应为收起状态'
            assert gap_probe['hasRadioGroup'], '缺少每行一列/两列切换按钮'
            assert gap_probe['factorRows'] == 18 * 6, '六因子明细行数不对'

            # 悬停雷达图 → 自建信息层出现且含六因子
            radar_el = page.locator('.gap-radar').first
            radar_el.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            box = radar_el.bounding_box()
            # 雷达中心（center 50%/52%），往上偏移一点确保落在多边形内
            cx = box['x'] + box['width'] / 2
            cy = box['y'] + box['height'] * 0.52
            page.mouse.move(cx, cy)
            page.wait_for_timeout(400)
            page.mouse.move(cx + 2, cy - 6)
            page.wait_for_timeout(700)
            tip_probe = page.evaluate("""() => {
                const tip = document.querySelector('.gap-radar-tip');
                if (!tip) return null;
                const rows = [...tip.querySelectorAll('.gap-radar-tip-row')];
                return {
                    title: tip.querySelector('.gap-radar-tip-title')?.innerText || '',
                    rowCount: rows.length,
                    names: rows.map(r => r.querySelector('.gap-radar-tip-name')?.innerText || ''),
                    vals: rows.map(r => r.querySelector('.gap-radar-tip-val')?.innerText || ''),
                    activeCount: rows.filter(r => r.classList.contains('active')).length,
                };
            }""")
            print('雷达图悬浮信息层:', tip_probe)
            assert tip_probe, '雷达图悬停未显示信息层'
            assert tip_probe['rowCount'] == 6, f'信息层应有 6 个因子行：{tip_probe["rowCount"]}'
            assert '需求刚性' in tip_probe['names'], '信息层缺少「需求刚性」'
            assert any('/25' in v for v in tip_probe['vals']), '信息层未显示得分/满分'
            assert tip_probe['activeCount'] == 1, '悬停未高亮所指向的因子轴'
            shots.append(('02b-gap-radar', OUT + '/chain-02b-gap-radar.png'))
            page.screenshot(path=shots[-1][1], full_page=False)

            # ---- 内嵌目标企业表格：单独展开 → 全部展开 → 全部收起 ----
            page.locator('.gap-targets-toggle').first.click()
            page.wait_for_timeout(600)
            single_probe = page.evaluate("""() => {
                const tables = document.querySelectorAll('.gap-target-table');
                const first = tables[0];
                const allBtns = [...document.querySelectorAll('.gap-target-table .el-button')];
                return {
                    tables: tables.length,
                    rows: first ? first.querySelectorAll('tbody tr').length : 0,
                    headers: first ? [...first.querySelectorAll('thead th')].map(h => h.innerText.trim()) : [],
                    exportBtns: document.querySelectorAll('.gap-targets-export').length,
                    detailBtns: first ? first.querySelectorAll('tbody .el-button').length : 0,
                    statusSelects: first ? first.querySelectorAll('tbody .el-select').length : 0,
                    convertBtns: allBtns.filter(b => b.innerText.includes('转为线索')).length,
                };
            }""")
            print('单张展开探针:', single_probe)
            assert single_probe['tables'] == 1, f'单独展开应只渲染 1 张表格：{single_probe["tables"]}'
            assert single_probe['rows'] == 20, f'缺口 1 应有 20 行目标企业：{single_probe["rows"]}'
            assert any('目标企业' in h for h in single_probe['headers']), '表格缺少目标企业列'
            assert any('符合状态' in h for h in single_probe['headers']), '表格缺少符合状态列'
            assert any('操作' in h for h in single_probe['headers']), '表格缺少操作列'
            assert single_probe['exportBtns'] == 18, \
                f'导出按钮应每张卡片一个：{single_probe["exportBtns"]}'
            assert single_probe['detailBtns'] == 20, \
                f'每行应有 1 个详情按钮：{single_probe["detailBtns"]}'
            assert single_probe['statusSelects'] == 20, \
                f'每行应有 1 个符合状态下拉：{single_probe["statusSelects"]}'
            assert single_probe['convertBtns'] == 0, '内嵌表格不应出现「转为线索」按钮'
            shots.append(('02c-gap-targets-single', OUT + '/chain-02c-gap-targets-single.png'))
            page.screenshot(path=shots[-1][1], full_page=False)

            # ---- 缺口卡片内嵌表格：点击目标企业名称打开详情抽屉 ----
            page.locator('.gap-target-name').first.click()
            page.wait_for_timeout(2000)
            gap_drawer_probe = page.evaluate("""() => {
                const drawer = document.querySelector('.chain-drawer');
                const body = document.querySelector('.chain-drawer .el-drawer__body');
                if (!body) return null;
                return {
                    open: !!drawer,
                    text: body.innerText.slice(0, 400),
                    hasSixFactor: body.innerText.includes('六因子匹配得分'),
                    hasStrength: body.innerText.includes('企业实力'),
                    hasSources: body.innerText.includes('来源'),
                    sourceCount: document.querySelectorAll('.chain-drawer .source-item').length,
                };
            }""")
            print('缺口卡片详情抽屉探针:', gap_drawer_probe)
            assert gap_drawer_probe, '点击目标企业名称未打开详情抽屉'
            assert gap_drawer_probe['hasSixFactor'], '缺口抽屉缺六因子得分区块'
            assert gap_drawer_probe['hasStrength'], '缺口抽屉缺企业实力区块'
            assert gap_drawer_probe['sourceCount'] >= 3, \
                f'缺口抽屉来源链接应多条（≥3）：{gap_drawer_probe["sourceCount"]}'
            shots.append(('02c2-gap-detail', OUT + '/chain-02c2-gap-detail.png'))
            page.screenshot(path=shots[-1][1], full_page=False)
            page.keyboard.press('Escape')
            page.wait_for_timeout(900)

            # ---- 缺口卡片表格右上角导出（九列口径）----
            with page.expect_download(timeout=30000) as dl_info:
                page.locator('.gap-targets-export').first.click()
            _dl = dl_info.value
            _csv = _dl.path()
            with open(_csv, 'rb') as f:
                _txt = f.read().decode('utf-8-sig')
            _lines = [x for x in _txt.split('\r\n') if x.strip()]
            _hdr = _lines[2] if len(_lines) > 2 else ''
            for _h in ('目标企业', '产业类别', '产业环节', '对应缺口', '地址',
                       '可对接本地链主', '注册资本(万元)', '近三年营收', '规模资质'):
                assert _h in _hdr, f'导出表头缺「{_h}」：{_hdr}'
            assert len(_lines) == 20 + 3, \
                f'缺口 1 导出应为 20 家 + 3 行表头，实际 {len(_lines)} 行'
            print(f'[导出] 缺口卡片下载成功：{_dl.suggested_filename}（{len(_lines)} 行）✓')

            # 全部展开
            btn_exp = page.locator('.section-header .el-button', has_text='全部展开目标企业').first
            btn_exp.scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            btn_exp.click()
            page.wait_for_timeout(900)
            all_probe = page.evaluate("""() => {
                const tables = document.querySelectorAll('.gap-target-table');
                let rows = 0;
                tables.forEach(t => { rows += t.querySelectorAll('tbody tr').length; });
                return { tables: tables.length, rows };
            }""")
            print('全部展开探针:', all_probe)
            assert all_probe['tables'] == 18, f'全部展开应渲染 18 张表格：{all_probe["tables"]}'
            assert all_probe['rows'] == 183, f'全部展开应共 183 行：{all_probe["rows"]}'
            shots.append(('02d-gap-targets-all', OUT + '/chain-02d-gap-targets-all.png'))
            page.screenshot(path=shots[-1][1], full_page=False)

            # 全部收起
            btn_col = page.locator('.section-header .el-button', has_text='全部收起目标企业').first
            btn_col.scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            btn_col.click()
            page.wait_for_timeout(700)
            collapsed_probe = page.evaluate("""() => ({
                tables: document.querySelectorAll('.gap-target-table').length
            })""")
            print('全部收起探针:', collapsed_probe)
            assert collapsed_probe['tables'] == 0, '全部收起后仍渲染表格'

            # 切换为每行两列
            page.locator('.el-radio-button__inner', has_text='每行两列').first.click()
            page.wait_for_timeout(700)
            two_col_probe = page.evaluate("""() => {
                const cards = document.querySelectorAll('.gap-card');
                const a = cards[0].getBoundingClientRect();
                const b = cards[1].getBoundingClientRect();
                return {
                    sameTop: Math.abs(a.top - b.top) < 4,
                    dx: Math.round(b.left - a.left),
                    cols: getComputedStyle(document.querySelector('.gap-cards')).gridTemplateColumns,
                };
            }""")
            print('两列布局探针:', two_col_probe)
            assert two_col_probe['sameTop'] and two_col_probe['dx'] > 200, \
                f'切换后未成两列：{two_col_probe}'
            shots.append(('02e-gap-twocol', OUT + '/chain-02e-gap-twocol.png'))
            page.screenshot(path=shots[-1][1], full_page=False)
            # 还原为每行一列
            page.locator('.el-radio-button__inner', has_text='每行一列').first.click()
            page.wait_for_timeout(500)

            # 页签三：目标企业库
            tabs.nth(2).click()
            page.wait_for_timeout(1500)
            shots.append(('03-target', OUT + '/chain-03-target.png'))
            page.screenshot(path=shots[-1][1], full_page=True)

            # 目标企业库列结构：去掉省份/地域类型，所在地置于第二列，转为线索入口下线
            lib_probe = page.evaluate("""() => {
                const root = document.querySelector('.target-table');
                if (!root) return null;
                const headers = [...root.querySelectorAll('thead th')]
                    .map(h => h.innerText.trim()).filter(Boolean);
                const btns = [...root.querySelectorAll('.el-button')].map(b => b.innerText.trim());
                return {
                    headers,
                    firstCol: headers[0] || '',
                    secondCol: headers[1] || '',
                    hasProvince: headers.some(h => h.includes('省份')),
                    hasRegionType: headers.some(h => h.includes('地域类型')),
                    hasStatus: headers.some(h => h.includes('符合状态')),
                    convertBtns: btns.filter(b => b.includes('转为线索')).length,
                };
            }""")
            print('目标企业库列结构探针:', lib_probe)
            assert lib_probe, '未找到目标企业库表格'
            assert lib_probe['firstCol'] == '目标企业', \
                f'首列应为「目标企业」：{lib_probe["firstCol"]}'
            assert lib_probe['secondCol'] == '所在地', \
                f'第二列应为「所在地」：{lib_probe["secondCol"]}'
            assert not lib_probe['hasProvince'], '「省份」列应已去掉'
            assert not lib_probe['hasRegionType'], '「地域类型」列应已去掉'
            assert lib_probe['hasStatus'], '缺少「符合状态」列'
            assert lib_probe['convertBtns'] == 0, '「转为线索」按钮应已下线'
            print('列序:', ' | '.join(lib_probe['headers']))

            # 目标企业库：点击「省外企业」快捷筛选（数量从概览接口动态取，避免硬编码随数据漂移）
            outprov_expect = page.evaluate("""async () => {
                const r = await fetch('/api/chain/overview', {credentials: 'include'});
                const j = await r.json();
                return (j.data && j.data.outprov_target_count) || 0;
            }""")
            page.locator('.quick-filters button', has_text='省外企业').first.click()
            page.wait_for_timeout(1500)
            shots.append(('03b-outprov', OUT + '/chain-03b-outprov.png'))
            page.screenshot(path=shots[-1][1], full_page=True)
            outprov_text = page.locator('.result-count').first.inner_text()
            print('省外筛选结果:', outprov_text, '（概览口径 %d 家）' % outprov_expect)
            assert f'{outprov_expect} 家' in outprov_text, \
                f'省外筛选数量与概览不一致: {outprov_text}'

            # 冻结首列：横向滚动后首列位置不变（限定目标企业库表格）
            freeze_probe = page.evaluate("""() => {
                const root = document.querySelector('.target-table');
                if (!root) return null;
                // Element Plus 表格的真实横向滚动容器是 el-scrollbar__wrap
                const wraps = [...root.querySelectorAll('.el-scrollbar__wrap')].filter(w => w.scrollWidth > w.clientWidth + 20);
                const wrap = wraps[0];
                const cell = root.querySelector('.el-table__row td .cell');
                if (!wrap || !cell) return {noScroll: true, wrapCount: wraps.length};
                const before = cell.getBoundingClientRect().left;
                wrap.scrollLeft = 400;
                const after = cell.getBoundingClientRect().left;
                const scrolled = wrap.scrollLeft;
                wrap.scrollLeft = 0;
                return {
                    before, after, scrolled,
                    maxScroll: wrap.scrollWidth - wrap.clientWidth,
                    scrollWidth: wrap.scrollWidth, clientWidth: wrap.clientWidth,
                    fixedCells: root.querySelectorAll('.el-table-fixed-column--left').length,
                };
            }""")
            print('冻结首列探针:', freeze_probe)
            assert freeze_probe and not freeze_probe.get('noScroll'), '未找到可横向滚动的表格容器'
            assert freeze_probe['maxScroll'] > 100, \
                f'目标企业表横向可滚动距离过小：{freeze_probe["maxScroll"]}'
            assert freeze_probe['scrolled'] > 100, '横向滚动未生效'
            assert abs(freeze_probe['before'] - freeze_probe['after']) < 2, \
                f'首列未冻结（滚动前后位置变化 {freeze_probe["before"]} → {freeze_probe["after"]}）'
            assert freeze_probe['fixedCells'] > 0, '首列未渲染为固定列'

            # 目标企业库：打开详情抽屉
            page.locator('.target-table .el-table__row .el-button', has_text='详情').first.click()
            page.wait_for_timeout(2000)
            shots.append(('03c-detail', OUT + '/chain-03c-detail.png'))
            page.screenshot(path=shots[-1][1], full_page=True)
            drawer_probe = page.evaluate("""() => {
                const d = document.querySelector('.chain-drawer .el-drawer__body');
                const drawer = document.querySelector('.chain-drawer');
                if (!d) return null;
                const items = [...document.querySelectorAll('.chain-drawer .source-item')];
                return {
                    hasStrength: d.innerText.includes('企业实力'),
                    hasRole: d.innerText.includes('链作用'),
                    hasFit: d.innerText.includes('投资可行性'),
                    hasSixFactor: d.innerText.includes('六因子匹配得分'),
                    hasGroup: d.innerText.includes('所属环节') || d.innerText.includes('大类'),
                    scrollH: d.scrollHeight,
                    drawerWidth: drawer ? Math.round(drawer.getBoundingClientRect().width) : 0,
                    bodyWidth: Math.round(d.getBoundingClientRect().width),
                    sourceCount: items.length,
                    sourceTitles: items.slice(0, 3).map(i => i.querySelector('.source-title')?.innerText || ''),
                    sourceHasUrl: items.every(i => !!(i.querySelector('.source-url') || {}).innerText),
                };
            }""")
            print('详情抽屉探针:', drawer_probe)
            assert drawer_probe and drawer_probe['hasStrength'], '详情抽屉缺少企业实力区块'
            assert drawer_probe and drawer_probe['hasSixFactor'], '详情抽屉缺少六因子得分'
            assert drawer_probe and drawer_probe['drawerWidth'] >= 700, \
                f'详情抽屉未加宽：{drawer_probe["drawerWidth"]}px'
            assert drawer_probe and drawer_probe['sourceCount'] >= 3, \
                f'来源链接应多条（≥3）：{drawer_probe["sourceCount"]}'
            assert drawer_probe and drawer_probe['sourceHasUrl'], '来源链接缺 URL'
            print('来源链接小标题:', drawer_probe['sourceTitles'])
            page.keyboard.press('Escape')
            page.wait_for_timeout(800)

            # 复位筛选
            page.locator('.quick-filters button', has_text='重置').first.click()
            page.wait_for_timeout(1200)

            # 页签四：招商建议
            tabs.nth(3).click()
            page.wait_for_timeout(1800)
            shots.append(('04-advice', OUT + '/chain-04-advice.png'))
            page.screenshot(path=shots[-1][1], full_page=True)

            # 建议排版探针：段落数 / 加粗数 / 列表项 / 文本占宽比（防大片空白）
            advice_probe = page.evaluate("""() => {
                const paras = document.querySelectorAll('.advice-para');
                const strongs = document.querySelectorAll('.advice-content strong');
                const items = document.querySelectorAll('.advice-ul li');
                // 样式命中探针：v-html 注入的节点不带 scoped 属性，
                // 样式若未写 :deep() 则完全不生效（段落不分行 / 列表无缩进）
                const firstPara = paras[0];
                const firstLine = document.querySelector('.advice-line');
                const firstUl = document.querySelector('.advice-ul');
                const firstLi = document.querySelector('.advice-ul li');
                const lineCS = firstLine ? getComputedStyle(firstLine) : null;
                const ulCS = firstUl ? getComputedStyle(firstUl) : null;
                const liBefore = firstLi ? getComputedStyle(firstLi, '::before').content : '';
                // 文本实际占宽比：用 Range 量每段真实文本宽度 vs 段落宽度
                let ratioSum = 0, ratioN = 0;
                const paras2 = [...document.querySelectorAll('.advice-para')].filter(p => {
                    const t = (p.innerText || '').trim();
                    return t.length > 60 && !p.querySelector('.advice-ul');
                });
                for (const p of paras2) {
                    const r = p.getBoundingClientRect();
                    const rg = document.createRange();
                    rg.selectNodeContents(p);
                    const tw = rg.getBoundingClientRect().width;
                    if (r.width > 0) { ratioSum += tw / r.width; ratioN++; }
                }
                return {
                    paras: paras.length,
                    strongs: strongs.length,
                    items: items.length,
                    avgRatio: ratioN ? ratioSum / ratioN : 1,
                    sampled: ratioN,
                    lineDisplay: lineCS ? lineCS.display : null,
                    ulDisplay: ulCS ? ulCS.display : null,
                    ulPadding: ulCS ? ulCS.paddingLeft : null,
                    liBefore: liBefore,
                };
            }""")
            print('建议页探针:', advice_probe)
            assert advice_probe['paras'] >= 5, '建议未按段落拆分'
            assert advice_probe['strongs'] >= 3, '建议关键句未加粗'
            assert advice_probe['items'] >= 20, '建议列表项渲染异常'
            # 样式命中断言（:deep() 漏写会静默失效）
            assert advice_probe['lineDisplay'] == 'block', (
                f'.advice-line 未生效（display={advice_probe["lineDisplay"]}），样式可能缺 :deep()')
            assert advice_probe['ulDisplay'] == 'block' and advice_probe['ulPadding'] != '0px', (
                f'.advice-ul 未生效（display={advice_probe["ulDisplay"]} padding={advice_probe["ulPadding"]}）')
            assert advice_probe['liBefore'] not in ('none', ''), '列表圆点未生效（::before 缺 :deep()）'
            # 散文段文本应基本占满行宽（占宽比 < 0.75 说明仍在硬折行、右侧大片空白）
            assert advice_probe['sampled'] >= 3, '可用于测量的长段落太少'
            assert advice_probe['avgRatio'] > 0.75, (
                f'建议正文占宽比仅 {advice_probe["avgRatio"]:.2f}，仍有硬折行导致右侧空白')

            # 页签五：更新日志（独立页签）
            tabs.nth(4).click()
            page.wait_for_timeout(1500)
            shots.append(('05-changelog', OUT + '/chain-05-changelog.png'))
            page.screenshot(path=shots[-1][1], full_page=True)

            log_probe = page.evaluate("""() => {
                const logs = document.querySelectorAll('.changelog-card');
                const risk = document.querySelectorAll('.changelog-block.risk li');
                const next = document.querySelectorAll('.changelog-block.next li');
                // 更新日志页签内的日志卡片数必须独立于建议页
                const inPane = document.querySelectorAll('.el-tab-pane[aria-hidden="false"] .changelog-card').length;
                return {
                    logs: logs.length,
                    inPane: inPane,
                    version: (document.querySelector('.changelog-head .el-tag') || {}).innerText || '',
                    riskItems: risk.length,
                    nextItems: next.length,
                    changeItems: document.querySelectorAll('.changelog-block:not(.risk):not(.next) li').length,
                    adviceInPane: document.querySelectorAll('.el-tab-pane[aria-hidden="false"] .advice-card').length,
                };
            }""")
            print('更新日志页探针:', log_probe)
            assert log_probe['logs'] >= 1, '缺少更新日志卡片'
            assert log_probe['inPane'] >= 1, '更新日志未独立成页签'
            assert log_probe['changeItems'] >= 5, '更新日志修改内容条目偏少'
            assert log_probe['riskItems'] >= 1, '更新日志缺少风险提示'
            assert log_probe['nextItems'] >= 1, '更新日志缺少下一步工作'
            assert log_probe['adviceInPane'] == 0, '更新日志页签不应混入招商建议卡片'

            # 页签六：评判规则（独立页签）
            tabs.nth(5).click()
            page.wait_for_timeout(1500)
            shots.append(('06-rules', OUT + '/chain-06-rules.png'))
            page.screenshot(path=shots[-1][1], full_page=True)

            rules_probe = page.evaluate("""() => {
                const pane = document.querySelector('.el-tab-pane[aria-hidden="false"]');
                if (!pane) return null;
                const txt = pane.innerText;
                return {
                    factorCards: pane.querySelectorAll('.rf-card').length,
                    formulaCards: pane.querySelectorAll('.formula-item').length,
                    strengthCards: pane.querySelectorAll('.st-card').length,
                    distRows: pane.querySelectorAll('.st-dist-row').length,
                    roleBlocks: pane.querySelectorAll('.role-block').length,
                    roleItems: pane.querySelectorAll('.rule-item-detail').length,
                    basisLabels: pane.querySelectorAll('.rf-basis-label').length,
                    impactRows: pane.querySelectorAll('.rf-impact').length,
                    scoreTableRows: pane.querySelectorAll('.target-score-table tbody tr').length,
                    hasVeto: txt.includes('否决规则'),
                    hasLevels: txt.includes('总分 ≥ 80'),
                    hasTargetScore: txt.includes('目标企业匹配总分'),
                    hasGapScore: txt.includes('缺口优先级总分'),
                    adviceInPane: document.querySelectorAll('.el-tab-pane[aria-hidden="false"] .advice-card').length,
                    overflow: [...pane.querySelectorAll('.rf-card, .st-card, .formula-item, .role-block')]
                        .filter(el => el.scrollWidth > el.clientWidth + 2).length,
                };
            }""")
            print('评判规则页探针:', rules_probe)
            assert rules_probe, '评判规则页签未激活'
            assert rules_probe['factorCards'] == 6, f'六因子卡片应为 6 个：{rules_probe["factorCards"]}'
            assert rules_probe['formulaCards'] == 2, f'总分公式应为 2 套：{rules_probe["formulaCards"]}'
            assert rules_probe['strengthCards'] == 5, f'企业实力五维卡片应为 5 个：{rules_probe["strengthCards"]}'
            assert rules_probe['roleBlocks'] == 2, f'链作用/可行性分块应为 2 个：{rules_probe["roleBlocks"]}'
            assert rules_probe['roleItems'] == 6, \
                f'链作用 3 类 + 可行性 3 档应各 3 条：{rules_probe["roleItems"]}'
            assert rules_probe['basisLabels'] == 17, \
                f'判定依据标签应为 6+5+3+3=17 个：{rules_probe["basisLabels"]}'
            assert rules_probe['impactRows'] == 6, \
                f'匹配分影响说明应为 6 条：{rules_probe["impactRows"]}'
            assert rules_probe['distRows'] >= 10, '五维实际取值分布行数偏少'
            assert rules_probe['scoreTableRows'] == 6, \
                f'目标企业六因子口径表应为 6 行：{rules_probe["scoreTableRows"]}'
            assert rules_probe['hasVeto'], '缺少否决规则'
            assert rules_probe['hasLevels'], '缺少优先级分档'
            assert rules_probe['hasTargetScore'] and rules_probe['hasGapScore'], '缺少两套总分公式说明'
            assert rules_probe['adviceInPane'] == 0, '评判规则页签不应混入招商建议卡片'
            assert rules_probe['overflow'] == 0, f'评判规则卡片存在横向溢出：{rules_probe["overflow"]}'
            print('✓ 评判规则页签')

            # 关键几何探针
            probe = page.evaluate("""() => {
                const out = {};
                out.scrollWidth = document.documentElement.scrollWidth;
                out.clientWidth = document.documentElement.clientWidth;
                const svg = document.querySelector('.chain-svg');
                if (svg) {
                    const r = svg.getBoundingClientRect();
                    out.svg = { w: Math.round(r.width), h: Math.round(r.height) };
                    out.nodeCount = document.querySelectorAll('.node-group').length;
                    const over = [];
                    document.querySelectorAll('.node-name').forEach(t => {
                        const b = t.getBBox();
                        const parent = t.parentNode.querySelector('rect');
                        const pb = parent.getBBox();
                        if (b.x + b.width > pb.x + pb.width) over.push(t.textContent);
                    });
                    out.textOverflow = over;
                }
                const radar = document.querySelector('.chart-box canvas');
                out.radarCanvas = radar ? { w: radar.width, h: radar.height } : null;
                // 新增面板的溢出检查
                const panels = ['.strength-panel', '.role-fit-panel', '.region-panel', '.quick-filters',
                                '.group-panel', '.region-ent-panel', '.changelog-blocks', '.gap-cards',
                                '.rules-intro', '.rule-factor-grid', '.strength-grid'];
                out.panels = {};
                panels.forEach(sel => {
                    const el = document.querySelector(sel);
                    if (!el) { out.panels[sel] = null; return; }
                    const r = el.getBoundingClientRect();
                    out.panels[sel] = { w: Math.round(r.width), h: Math.round(r.height),
                                        overflowX: el.scrollWidth > el.clientWidth + 2 };
                });
                // 表格横向溢出
                const wrap = document.querySelector('.el-table__body-wrapper');
                out.tableOverflow = wrap ? wrap.scrollWidth > wrap.clientWidth + 2 : null;
                return out;
            }""")
            print('几何探针:', probe)

            if errors:
                print('!! 控制台错误:')
                for e in errors[:15]:
                    print('   ', e[:220])
            else:
                print('控制台无错误 ✓')

            browser.close()
    finally:
        for proc in (backend, preview):
            try:
                proc.terminate()
            except Exception:
                pass
        # 清理临时 vite 配置
        try:
            if os.path.exists(vc_config):
                os.remove(vc_config)
        except Exception:
            pass

    for name, path in shots:
        print('截图:', name, os.path.exists(path) and str(os.path.getsize(path)) + ' bytes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
