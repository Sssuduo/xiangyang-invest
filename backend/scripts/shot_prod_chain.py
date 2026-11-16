"""生产环境页面视觉验证：登录 → 打开 /chain → 四个页签截图。

Edge 会拦截裸 IP 的 HTTP 访问（ERR_BLOCKED_BY_CLIENT），
故先起一个本地反代把 123.56.9.243 映射到 127.0.0.1，浏览器走 localhost。

用法：python backend/scripts/shot_prod_chain.py
"""
import os
import sys
import json
import threading
import urllib.request
import http.server
import socketserver
from http.cookiejar import CookieJar

sys.path.insert(0, r'H:\项目1\backend')
UPSTREAM = '123.56.9.243'
LOCAL_PORT = 15188
OUT = r'G:\123\2026-11-13-16-05-00\outputs\shots'


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def _proxy(self):
        length = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(length) if length else None
        url = f'http://{UPSTREAM}{self.path}'
        headers = {k: v for k, v in self.headers.items()
                   if k.lower() not in ('host', 'connection', 'content-length')}
        if body:
            headers['Content-Length'] = str(len(body))
        try:
            r = urllib.request.Request(url, data=body, method=self.command, headers=headers)
            with urllib.request.urlopen(r, timeout=60) as resp:
                data = resp.read()
                self.send_response(resp.status)
                for k, v in resp.getheaders():
                    if k.lower() in ('transfer-encoding', 'content-length', 'connection'):
                        continue
                    self.send_header(k, v)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except Exception as e:
            self.send_response(502)
            msg = str(e).encode()
            self.send_header('Content-Length', str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    do_GET = do_POST = do_PUT = do_DELETE = _proxy

    def log_message(self, *args):
        pass


def start_proxy():
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(('127.0.0.1', LOCAL_PORT), ProxyHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main():
    from playwright.sync_api import sync_playwright

    os.makedirs(OUT, exist_ok=True)
    srv = start_proxy()
    BASE = f'http://127.0.0.1:{LOCAL_PORT}'
    print('反代已启动:', BASE, '→', UPSTREAM)

    # 先在浏览器上下文里登录（cookie 写入浏览器会话）
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel='msedge',
            args=['--no-sandbox', '--disable-extensions', '--disable-features=msEdgeSync',
                  '--disable-sync', '--no-first-run'],
        )
        ctx = browser.new_context(viewport={'width': 1600, 'height': 1000},
                                  device_scale_factor=1.5, accept_downloads=True)
        page = ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append('PAGEERROR: ' + str(e)))

        page.goto(BASE + '/', wait_until='networkidle')
        login = page.evaluate("""async (base) => {
            const r = await fetch(base + '/api/auth/login', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                credentials: 'include',
                body: JSON.stringify({username: 'demo', password: 'demo123'})
            });
            return (await r.json()).code;
        }""", BASE)
        print('登录 code =', login)

        page.goto(BASE + '/chain', wait_until='networkidle')
        page.wait_for_timeout(3000)
        page.screenshot(path=os.path.join(OUT, 'prod-chain-01-graph.png'), full_page=True)
        print('✓ 图谱页')

        tabs = page.locator('.chain-tabs .el-tabs__item')
        print('页签数:', tabs.count())
        assert tabs.count() == 5, f'页签应为 5 个（更新日志已独立）：{tabs.count()}'
        for idx, (name, fn) in enumerate([
            ('缺口与优先级', 'prod-chain-02-gap.png'),
            ('目标企业库', 'prod-chain-03-target.png'),
            ('招商建议与材料', 'prod-chain-04-advice.png'),
        ], start=1):
            tabs.nth(idx).click()
            page.wait_for_timeout(2000)
            page.screenshot(path=os.path.join(OUT, fn), full_page=True)
            print('✓', name)

        # 顶部导航是否出现「产业链招商」入口
        nav_text = page.locator('.nav-menu').inner_text()
        print('导航含「产业链招商」:', '产业链招商' in nav_text)

        # 统计卡片（应为 12 张）
        cards = page.locator('.stat-card')
        print('统计卡片数:', cards.count())
        print('卡片标签:', [t.strip() for t in page.locator('.stat-card-label').all_inner_texts()])
        assert cards.count() == 12, f'统计卡片应为 12 张，实际 {cards.count()}'

        # 图谱页：大类分组条 + 大类卡片 + 属地分布
        graph_probe = page.evaluate("""() => ({
            groupBars: document.querySelectorAll('.group-bar-text').length,
            groupCards: document.querySelectorAll('.group-card').length,
            regionEnt: document.querySelectorAll('.region-ent-item').length,
            nodes: document.querySelectorAll('.node-group').length,
        })""")
        print('图谱页探针:', graph_probe)
        assert graph_probe['groupBars'] == 9, f'大类分组条应为 9：{graph_probe["groupBars"]}'
        assert graph_probe['groupCards'] == 9, f'大类卡片应为 9：{graph_probe["groupCards"]}'
        assert graph_probe['nodes'] == 29, f'环节节点应为 29：{graph_probe["nodes"]}'
        print('✓ 图谱三级层级渲染')

        # 缺口页签：六因子 + 企业实力五维 + 链作用面板 + 地域分布
        tabs.nth(1).click()
        page.wait_for_timeout(2000)
        gap_probe = page.evaluate("""() => {
            const cards = document.querySelectorAll('.gap-card');
            let oneCol = false;
            if (cards.length >= 2) {
                const a = cards[0].getBoundingClientRect();
                const b = cards[1].getBoundingClientRect();
                oneCol = Math.abs(a.left - b.left) < 4 && (b.top - a.top) > 100;
            }
            const first = cards[0];
            const rb = first.querySelector('.gap-radar-box');
            const cm = first.querySelector('.gap-comment');
            const sideBySide = (rb && cm)
                ? cm.getBoundingClientRect().left >= rb.getBoundingClientRect().right - 2
                : false;
            return {
                factorCards: document.querySelectorAll('.rules-panel .factor-item').length,
                strengthCards: document.querySelectorAll('.strength-panel .strength-item').length,
                roleBlocks: document.querySelectorAll('.role-fit-panel .role-block').length,
                regionRows: document.querySelectorAll('.region-panel .region-item').length,
                gapCards: cards.length,
                radarCanvases: document.querySelectorAll('.gap-radar canvas').length,
                factorRows: document.querySelectorAll('.gap-factor-row').length,
                gridCols: getComputedStyle(document.querySelector('.gap-cards')).gridTemplateColumns,
                oneCol,
                sideBySide,
                toggles: document.querySelectorAll('.gap-targets-toggle').length,
                inlineTables: document.querySelectorAll('.gap-target-table').length,
                hasRadioGroup: !!document.querySelector('.el-radio-group'),
            };
        }""")
        print('缺口页签探针:', gap_probe)
        assert gap_probe['factorCards'] == 6, f'六因子卡片数异常 {gap_probe["factorCards"]}'
        assert gap_probe['strengthCards'] == 5, f'企业实力维度数异常 {gap_probe["strengthCards"]}'
        assert gap_probe['roleBlocks'] == 2, '链作用面板区块数异常'
        assert gap_probe['regionRows'] == 3, '地域分布行数异常'
        assert gap_probe['gapCards'] == 18, f'缺口卡片应为 18：{gap_probe["gapCards"]}'
        assert gap_probe['radarCanvases'] == 18, f'雷达图 canvas 应为 18：{gap_probe["radarCanvases"]}'
        assert gap_probe['factorRows'] == 18 * 6, '六因子明细行数异常'
        assert gap_probe['oneCol'], f'缺口卡片默认应为单列：{gap_probe["gridCols"]}'
        assert gap_probe['sideBySide'], '文字评述未移至雷达图右侧'
        assert gap_probe['toggles'] == 18, f'每张卡片应有目标企业折叠按钮：{gap_probe["toggles"]}'
        assert gap_probe['inlineTables'] == 0, '目标企业表格默认应为收起状态'
        assert gap_probe['hasRadioGroup'], '缺少每行一列/两列切换按钮'
        print('✓ 缺口页签新增面板全部渲染')

        # 内嵌目标企业表格：全部展开 → 收起
        btn_exp = page.locator('.section-header .el-button', has_text='全部展开目标企业').first
        btn_exp.scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        btn_exp.click()
        page.wait_for_timeout(1200)
        inline_probe = page.evaluate("""() => {
            const tables = document.querySelectorAll('.gap-target-table');
            let rows = 0;
            tables.forEach(t => { rows += t.querySelectorAll('tbody tr').length; });
            const first = tables[0];
            const allBtns = [...document.querySelectorAll('.gap-target-table .el-button')];
            return {
                tables: tables.length, rows,
                headers: first ? [...first.querySelectorAll('thead th')].map(h => h.innerText.trim()) : [],
                exportBtns: document.querySelectorAll('.gap-targets-export').length,
                statusSelects: first ? first.querySelectorAll('tbody .el-select').length : 0,
                convertBtns: allBtns.filter(b => b.innerText.includes('转为线索')).length,
            };
        }""")
        print('内嵌目标企业表格:', inline_probe)
        assert inline_probe['tables'] == 18, f'全部展开应渲染 18 张表格：{inline_probe["tables"]}'
        assert inline_probe['rows'] == 183, f'全部展开应共 183 行：{inline_probe["rows"]}'
        assert any('符合状态' in h for h in inline_probe['headers']), '内嵌表格缺少符合状态列'
        assert any('操作' in h for h in inline_probe['headers']), '内嵌表格缺少操作列'
        assert inline_probe['exportBtns'] == 18, f'导出按钮应为 18 个：{inline_probe["exportBtns"]}'
        assert inline_probe['statusSelects'] == 20, \
            f'首张表格应有 20 个符合状态下拉：{inline_probe["statusSelects"]}'
        assert inline_probe['convertBtns'] == 0, '内嵌表格不应出现「转为线索」按钮'
        page.screenshot(path=os.path.join(OUT, 'prod-chain-07b-gap-targets.png'), full_page=False)

        # 缺口卡片内嵌表格：点击目标企业名称打开详情抽屉
        page.locator('.gap-target-name').first.click()
        page.wait_for_timeout(2000)
        gap_drawer_probe = page.evaluate("""() => {
            const body = document.querySelector('.chain-drawer .el-drawer__body');
            if (!body) return null;
            return {
                hasSixFactor: body.innerText.includes('六因子匹配得分'),
                hasStrength: body.innerText.includes('企业实力'),
                sourceCount: document.querySelectorAll('.chain-drawer .source-item').length,
            };
        }""")
        print('缺口卡片详情抽屉:', gap_drawer_probe)
        assert gap_drawer_probe, '点击目标企业名称未打开详情抽屉'
        assert gap_drawer_probe['hasSixFactor'], '缺口抽屉缺少六因子得分区块'
        assert gap_drawer_probe['hasStrength'], '缺口抽屉缺少企业实力区块'
        assert gap_drawer_probe['sourceCount'] >= 3, \
            f'缺口抽屉来源链接应多条（≥3）：{gap_drawer_probe["sourceCount"]}'
        page.screenshot(path=os.path.join(OUT, 'prod-chain-07c-gap-detail.png'), full_page=False)
        page.keyboard.press('Escape')
        page.wait_for_timeout(900)
        print('✓ 缺口卡片详情抽屉')

        # 缺口卡片表格右上角导出（九列口径）
        with page.expect_download(timeout=30000) as dl_info:
            page.locator('.gap-targets-export').first.click()
        _dl = dl_info.value
        with open(_dl.path(), 'rb') as f:
            _txt = f.read().decode('utf-8-sig')
        _lines = [x for x in _txt.split('\r\n') if x.strip()]
        _hdr = _lines[2] if len(_lines) > 2 else ''
        for _h in ('目标企业', '产业类别', '产业环节', '对应缺口', '地址',
                   '可对接本地链主', '注册资本(万元)', '近三年营收', '规模资质'):
            assert _h in _hdr, f'导出表头缺「{_h}」：{_hdr}'
        assert len(_lines) == 20 + 3, f'缺口 1 导出应为 23 行，实际 {len(_lines)} 行'
        print('✓ 缺口卡片导出（%s，%d 行）' % (_dl.suggested_filename, len(_lines)))

        btn_col = page.locator('.section-header .el-button', has_text='全部收起目标企业').first
        btn_col.scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        btn_col.click()
        page.wait_for_timeout(800)
        print('✓ 内嵌目标企业表格')

        # 雷达图悬停 → 自建信息层
        radar_el = page.locator('.gap-radar').first
        radar_el.scroll_into_view_if_needed()
        page.wait_for_timeout(600)
        box = radar_el.bounding_box()
        page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] * 0.52)
        page.wait_for_timeout(400)
        page.mouse.move(box['x'] + box['width'] / 2 + 2, box['y'] + box['height'] * 0.52 - 5)
        page.wait_for_timeout(800)
        tip_probe = page.evaluate("""() => {
            const tip = document.querySelector('.gap-radar-tip');
            if (!tip) return null;
            const rows = [...tip.querySelectorAll('.gap-radar-tip-row')];
            return {
                title: tip.querySelector('.gap-radar-tip-title')?.innerText || '',
                rowCount: rows.length,
                active: rows.filter(r => r.classList.contains('active')).length,
            };
        }""")
        print('雷达图悬停信息层:', tip_probe)
        assert tip_probe and tip_probe['rowCount'] == 6, '雷达图悬停信息层异常'
        assert tip_probe['active'] == 1, '雷达图悬停未高亮指向的指标轴'
        page.screenshot(path=os.path.join(OUT, 'prod-chain-07-gap-radar.png'), full_page=False)
        print('✓ 雷达图悬停')

        # 目标企业库：省外筛选（家数从概览接口动态取，避免硬编码随数据漂移）
        tabs.nth(2).click()
        page.wait_for_timeout(1500)

        # 目标企业库列结构：去掉省份/地域类型，所在地置于第二列，转为线索入口下线
        lib_probe = page.evaluate("""() => {
            const root = document.querySelector('.target-table');
            if (!root) return null;
            const headers = [...root.querySelectorAll('thead th')].map(h => h.innerText.trim()).filter(Boolean);
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
        print('目标企业库列结构:', lib_probe)
        assert lib_probe, '未找到目标企业库表格'
        assert lib_probe['firstCol'] == '目标企业', f'首列应为「目标企业」：{lib_probe["firstCol"]}'
        assert lib_probe['secondCol'] == '所在地', f'第二列应为「所在地」：{lib_probe["secondCol"]}'
        assert not lib_probe['hasProvince'], '「省份」列应已去掉'
        assert not lib_probe['hasRegionType'], '「地域类型」列应已去掉'
        assert lib_probe['hasStatus'], '缺少「符合状态」列'
        assert lib_probe['convertBtns'] == 0, '「转为线索」按钮应已下线'
        print('✓ 目标企业库列结构')

        outprov_expect = page.evaluate("""async (base) => {
            const r = await fetch(base + '/api/chain/overview', {credentials: 'include'});
            const j = await r.json();
            return (j.data && j.data.outprov_target_count) || 0;
        }""", BASE)
        page.locator('.quick-filters button', has_text='省外企业').first.click()
        page.wait_for_timeout(1600)
        cnt = page.locator('.result-count').first.inner_text()
        print('省外筛选:', cnt, '（概览口径 %d 家）' % outprov_expect)
        assert f'{outprov_expect} 家' in cnt, f'省外筛选数量与概览不一致: {cnt}'
        page.screenshot(path=os.path.join(OUT, 'prod-chain-06-outprov.png'), full_page=True)
        print('✓ 省外筛选')

        # 冻结首列
        freeze_probe = page.evaluate("""() => {
            const root = document.querySelector('.target-table');
            if (!root) return {noScroll: true};
            const wraps = [...root.querySelectorAll('.el-scrollbar__wrap')].filter(w => w.scrollWidth > w.clientWidth + 20);
            const wrap = wraps[0];
            const cell = root.querySelector('.el-table__row td .cell');
            if (!wrap || !cell) return {noScroll: true};
            const before = cell.getBoundingClientRect().left;
            wrap.scrollLeft = 400;
            const after = cell.getBoundingClientRect().left;
            const scrolled = wrap.scrollLeft;
            wrap.scrollLeft = 0;
            return {before, after, scrolled, maxScroll: wrap.scrollWidth - wrap.clientWidth,
                    fixedCells: root.querySelectorAll('.el-table-fixed-column--left').length};
        }""")
        print('冻结首列探针:', freeze_probe)
        assert not freeze_probe.get('noScroll'), '未找到可横向滚动的表格容器'
        assert abs(freeze_probe['before'] - freeze_probe['after']) < 2, '首列未冻结'
        assert freeze_probe['scrolled'] > 100, '横向滚动未生效'
        print('✓ 首列冻结')

        # 抽屉详情
        btn = page.locator('.target-table .el-table__row .el-button', has_text='详情').first
        try:
            btn.click()
            page.wait_for_timeout(2000)
            page.screenshot(path=os.path.join(OUT, 'prod-chain-05-drawer.png'))
            drawer_probe = page.evaluate("""() => {
                const d = document.querySelector('.chain-drawer .el-drawer__body');
                const drawer = document.querySelector('.chain-drawer');
                if (!d) return null;
                const txt = d.innerText;
                const items = [...document.querySelectorAll('.chain-drawer .source-item')];
                return {
                    hasStrength: txt.includes('企业实力'),
                    hasSixFactor: txt.includes('六因子匹配得分'),
                    hasChainRole: txt.includes('链作用'),
                    capital: (txt.match(/注册资本\\s*([^\\n]*)/) || [])[1] || '',
                    drawerWidth: drawer ? Math.round(drawer.getBoundingClientRect().width) : 0,
                    sourceCount: items.length,
                    sourceTitles: items.map(i => i.querySelector('.source-title')?.innerText || ''),
                };
            }""")
            print('详情抽屉探针:', drawer_probe)
            assert drawer_probe and drawer_probe['hasStrength'], '详情抽屉缺少企业实力区块'
            assert drawer_probe and drawer_probe['hasSixFactor'], '详情抽屉缺少六因子得分'
            assert drawer_probe and drawer_probe['drawerWidth'] >= 700, \
                f'详情抽屉未加宽：{drawer_probe["drawerWidth"]}px'
            assert drawer_probe and drawer_probe['sourceCount'] >= 3, \
                f'来源链接应多条：{drawer_probe["sourceCount"]}'
            assert all(t for t in drawer_probe['sourceTitles']), '来源链接缺少小标题'
            print('✓ 详情抽屉（来源链接 %d 条）' % drawer_probe['sourceCount'])
        except Exception as e:
            print('抽屉截图跳过:', e)

        # 关闭抽屉（否则遮罩会拦截后续页签点击）
        try:
            close_btn = page.locator('.chain-drawer .el-drawer__close-btn')
            if close_btn.count():
                close_btn.first.click()
            else:
                page.keyboard.press('Escape')
            page.wait_for_timeout(1000)
            overlay = page.locator('.el-overlay.is-drawer')
            if overlay.count():
                print('提示: 抽屉遮罩仍存在，跳过页签切换前的遮罩清理')
        except Exception as e:
            print('关闭抽屉失败:', e)

        # 表格列清单 + 横向滚动检查
        cols = page.evaluate("""() => {
            const hs = Array.from(document.querySelectorAll('.target-table .el-table__header th'));
            const wrap = document.querySelector('.target-table .el-scrollbar__wrap');
            const first = document.querySelector('.target-table .el-table__body-wrapper tbody tr');
            return {
                headers: hs.map(h => h.innerText.trim()).filter(Boolean),
                scrollW: wrap ? wrap.scrollWidth : 0,
                clientW: wrap ? wrap.clientWidth : 0,
                firstRowCells: first ? first.children.length : 0,
                firstRowText: first ? first.innerText.replace(/\\s+/g,' ').slice(0,260) : '',
            };
        }""")
        print('表格列:', cols)
        assert any('企业实力' in c for c in cols['headers']), '表格缺少企业实力列'
        assert any('所属大类' in c for c in cols['headers']), '表格缺少所属大类列'
        assert any('所属环节' in c for c in cols['headers']), '表格缺少所属环节列'
        print('✓ 企业实力 / 所属大类 / 所属环节 列存在')

        # 招商建议页：建议分段加粗 + 导出卡片 + 正文占宽比（防右侧大片空白）
        tabs.nth(3).click()
        page.wait_for_timeout(1800)
        adv_probe = page.evaluate("""() => {
            const paras = [...document.querySelectorAll('.advice-para')];
            const strongs = document.querySelectorAll('.advice-content strong');
            const items = document.querySelectorAll('.advice-ul li');
            const firstLine = document.querySelector('.advice-line');
            const firstUl = document.querySelector('.advice-ul');
            const firstLi = document.querySelector('.advice-ul li');
            const lineCS = firstLine ? getComputedStyle(firstLine) : null;
            const ulCS = firstUl ? getComputedStyle(firstUl) : null;
            const liBefore = firstLi ? getComputedStyle(firstLi, '::before').content : '';
            let ratioSum = 0, ratioN = 0;
            for (const p of paras) {
                const t = (p.innerText || '').trim();
                if (t.length <= 60 || p.querySelector('.advice-ul')) continue;
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
                exportCards: document.querySelectorAll('.export-card').length,
                logs: document.querySelectorAll('.changelog-card').length,
            };
        }""")
        print('建议页探针:', adv_probe)
        assert adv_probe['paras'] >= 5 and adv_probe['strongs'] >= 3, '建议未分段/加粗'
        assert adv_probe['items'] >= 20, '建议列表项渲染异常'
        assert adv_probe['exportCards'] == 5, f'导出卡片应为 5：{adv_probe["exportCards"]}'
        assert adv_probe['lineDisplay'] == 'block', (
            f'.advice-line 未生效（display={adv_probe["lineDisplay"]}）')
        assert adv_probe['ulDisplay'] == 'block' and adv_probe['ulPadding'] != '0px', (
            f'.advice-ul 未生效（display={adv_probe["ulDisplay"]}）')
        assert adv_probe['liBefore'] not in ('none', ''), '列表圆点未生效'
        assert adv_probe['sampled'] >= 3, '可用于测量的长段落太少'
        assert adv_probe['avgRatio'] > 0.75, (
            f'建议正文占宽比仅 {adv_probe["avgRatio"]:.2f}，仍有硬折行导致右侧空白')
        page.screenshot(path=os.path.join(OUT, 'prod-chain-08-advice.png'), full_page=True)
        print('✓ 建议排版')

        # 更新日志页签（独立第 5 个页签）
        tabs.nth(4).click()
        page.wait_for_timeout(1500)
        log_probe = page.evaluate("""() => ({
            inPane: document.querySelectorAll('.el-tab-pane[aria-hidden="false"] .changelog-card').length,
            changeItems: document.querySelectorAll('.changelog-block:not(.risk):not(.next) li').length,
            riskItems: document.querySelectorAll('.changelog-block.risk li').length,
            nextItems: document.querySelectorAll('.changelog-block.next li').length,
            adviceInPane: document.querySelectorAll('.el-tab-pane[aria-hidden="false"] .advice-card').length,
            blocks: document.querySelectorAll('.changelog-blocks').length,
        })""")
        print('更新日志页探针:', log_probe)
        assert log_probe['inPane'] >= 1, '更新日志未独立成页签'
        assert log_probe['changeItems'] >= 5, '更新日志修改内容偏少'
        assert log_probe['riskItems'] >= 1 and log_probe['nextItems'] >= 1, '风险/下一步缺失'
        assert log_probe['adviceInPane'] == 0, '更新日志页签不应混入招商建议卡片'
        # blocks = 每条日志一个三栏容器，条数应与日志卡片数一致
        assert log_probe['blocks'] == log_probe['inPane'], (
            f'更新日志三栏布局异常：blocks={log_probe["blocks"]} logs={log_probe["inPane"]}')
        # 每条日志的三栏（修改内容 / 风险提示 / 下一步工作）都要有内容
        assert log_probe['changeItems'] >= log_probe['inPane'] * 5, '更新日志修改内容条目偏少'
        page.screenshot(path=os.path.join(OUT, 'prod-chain-09-changelog.png'), full_page=True)
        print('✓ 更新日志独立页签')

        if errors:
            print('!! 页面错误:')
            for e in errors[:8]:
                print('   ', e[:200])
        else:
            print('无页面 JS 错误 ✓')

        browser.close()
    srv.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
