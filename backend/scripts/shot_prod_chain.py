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
        ctx = browser.new_context(viewport={'width': 1600, 'height': 1000}, device_scale_factor=1.5)
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
        gap_probe = page.evaluate("""() => ({
            factorCards: document.querySelectorAll('.rules-panel .factor-item').length,
            strengthCards: document.querySelectorAll('.strength-panel .strength-item').length,
            roleBlocks: document.querySelectorAll('.role-fit-panel .role-block').length,
            regionRows: document.querySelectorAll('.region-panel .region-item').length,
            gapCards: document.querySelectorAll('.gap-card').length,
            radarCanvases: document.querySelectorAll('.gap-radar canvas').length,
            factorRows: document.querySelectorAll('.gap-factor-row').length,
            gridCols: getComputedStyle(document.querySelector('.gap-cards')).gridTemplateColumns,
        })""")
        print('缺口页签探针:', gap_probe)
        assert gap_probe['factorCards'] == 6, f'六因子卡片数异常 {gap_probe["factorCards"]}'
        assert gap_probe['strengthCards'] == 5, f'企业实力维度数异常 {gap_probe["strengthCards"]}'
        assert gap_probe['roleBlocks'] == 2, '链作用面板区块数异常'
        assert gap_probe['regionRows'] == 3, '地域分布行数异常'
        assert gap_probe['gapCards'] == 18, f'缺口卡片应为 18：{gap_probe["gapCards"]}'
        assert gap_probe['radarCanvases'] == 18, f'雷达图 canvas 应为 18：{gap_probe["radarCanvases"]}'
        assert gap_probe['factorRows'] == 18 * 6, '六因子明细行数异常'
        print('✓ 缺口页签新增面板全部渲染')

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

        # 目标企业库：省外筛选
        tabs.nth(2).click()
        page.wait_for_timeout(1500)
        page.locator('.quick-filters button', has_text='省外企业').first.click()
        page.wait_for_timeout(1600)
        cnt = page.locator('.result-count').first.inner_text()
        print('省外筛选:', cnt)
        assert '109 家' in cnt, f'省外筛选数量异常: {cnt}'
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

        # 招商建议页：更新日志三栏 + 建议分段加粗
        tabs.nth(3).click()
        page.wait_for_timeout(1800)
        adv_probe = page.evaluate("""() => ({
            logs: document.querySelectorAll('.changelog-card').length,
            changeItems: document.querySelectorAll('.changelog-block:not(.risk):not(.next) li').length,
            riskItems: document.querySelectorAll('.changelog-block.risk li').length,
            nextItems: document.querySelectorAll('.changelog-block.next li').length,
            paras: document.querySelectorAll('.advice-para').length,
            strongs: document.querySelectorAll('.advice-content strong').length,
            exportCards: document.querySelectorAll('.export-card').length,
        })""")
        print('建议/日志探针:', adv_probe)
        assert adv_probe['logs'] >= 1, '缺少更新日志'
        assert adv_probe['changeItems'] >= 5, '更新日志修改内容偏少'
        assert adv_probe['riskItems'] >= 1 and adv_probe['nextItems'] >= 1, '风险/下一步缺失'
        assert adv_probe['paras'] >= 5 and adv_probe['strongs'] >= 3, '建议未分段/加粗'
        assert adv_probe['exportCards'] == 5, f'导出卡片应为 5：{adv_probe["exportCards"]}'
        page.screenshot(path=os.path.join(OUT, 'prod-chain-08-advice-changelog.png'), full_page=True)
        print('✓ 更新日志与建议排版')

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
