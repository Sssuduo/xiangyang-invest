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

            # 页签二：缺口与优先级
            tabs = page.locator('.chain-tabs .el-tabs__item')
            print('页签数:', tabs.count())
            tabs.nth(1).click()
            page.wait_for_timeout(1800)
            shots.append(('02-gap', OUT + '/chain-02-gap.png'))
            page.screenshot(path=shots[-1][1], full_page=True)

            # 页签三：目标企业库
            tabs.nth(2).click()
            page.wait_for_timeout(1500)
            shots.append(('03-target', OUT + '/chain-03-target.png'))
            page.screenshot(path=shots[-1][1], full_page=True)

            # 目标企业库：点击「省外企业」快捷筛选
            page.locator('.quick-filters button', has_text='省外企业').first.click()
            page.wait_for_timeout(1500)
            shots.append(('03b-outprov', OUT + '/chain-03b-outprov.png'))
            page.screenshot(path=shots[-1][1], full_page=True)
            outprov_text = page.locator('.result-count').first.inner_text()
            print('省外筛选结果:', outprov_text)
            assert '80 家' in outprov_text, f'省外筛选数量异常: {outprov_text}'

            # 目标企业库：打开详情抽屉
            page.locator('.el-table__row .el-button', has_text='详情').first.click()
            page.wait_for_timeout(1600)
            shots.append(('03c-detail', OUT + '/chain-03c-detail.png'))
            page.screenshot(path=shots[-1][1], full_page=True)
            drawer_probe = page.evaluate("""() => {
                const d = document.querySelector('.el-drawer__body');
                if (!d) return null;
                return {
                    hasStrength: d.innerText.includes('企业实力'),
                    hasRole: d.innerText.includes('链作用'),
                    hasFit: d.innerText.includes('投资可行性'),
                    hasSixFactor: d.innerText.includes('六因子匹配得分'),
                    scrollH: d.scrollHeight,
                };
            }""")
            print('详情抽屉探针:', drawer_probe)
            assert drawer_probe and drawer_probe['hasStrength'], '详情抽屉缺少企业实力区块'
            assert drawer_probe and drawer_probe['hasSixFactor'], '详情抽屉缺少六因子得分'
            page.keyboard.press('Escape')
            page.wait_for_timeout(800)

            # 复位筛选
            page.locator('.quick-filters button', has_text='重置').first.click()
            page.wait_for_timeout(1200)

            # 页签四：招商建议
            tabs.nth(3).click()
            page.wait_for_timeout(1500)
            shots.append(('04-advice', OUT + '/chain-04-advice.png'))
            page.screenshot(path=shots[-1][1], full_page=True)

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
                const panels = ['.strength-panel', '.role-fit-panel', '.region-panel', '.quick-filters'];
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
