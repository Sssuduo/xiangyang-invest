"""雷达图悬停提示诊断脚本（对照实验）

目的：定位 ECharts 雷达图 tooltip 不出现的原因：
  A. 元素不在视口内（bounding_box 坐标无效）
  B. tooltip trigger 模式不适用于 radar
  C. tooltip DOM 结构与探针选择器不匹配

用法：python backend/scripts/diag_radar_tooltip.py
"""
import os
import subprocess
import sys
import time
import tempfile
import urllib.request

BACKEND = r'H:\项目1\backend'
FRONTEND = r'H:\项目1\frontend'
PY = r'G:\123\python.exe'
NODE = r'C:\Program Files\nodejs\node.exe'
BACKEND_PORT = 15097
FRONTEND_PORT = 15096


def wait_http(url, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if r.status < 500:
                    return True
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def main():
    from playwright.sync_api import sync_playwright

    dbfile = os.path.join(tempfile.gettempdir(), 'chain_diag.db')
    if os.path.exists(dbfile):
        os.remove(dbfile)
    dburl = 'sqlite:///' + dbfile.replace('\\', '/')
    env = dict(os.environ)
    env['DATABASE_URL'] = dburl
    env['FLASK_ENV'] = 'development'

    tmp = tempfile.gettempdir()
    blog = open(os.path.join(tmp, 'diag_backend.log'), 'w', encoding='utf-8')
    plog = open(os.path.join(tmp, 'diag_frontend.log'), 'w', encoding='utf-8')

    backend = subprocess.Popen(
        [PY, '-c',
         'import os,sys;sys.path.insert(0,r"%s");'
         'os.environ["DATABASE_URL"]="%s";'
         'from app import create_app;'
         'app=create_app("development");'
         'app.run(host="127.0.0.1",port=%d,debug=False,use_reloader=False)' % (BACKEND, dburl, BACKEND_PORT)],
        cwd=BACKEND, env=env, stdout=blog, stderr=subprocess.STDOUT)
    if not wait_http(f'http://127.0.0.1:{BACKEND_PORT}/api/chain/overview', 90):
        print('后端启动失败')
        backend.kill()
        return 1

    vc_config = os.path.join(FRONTEND, 'vite.diag.config.js')
    with open(vc_config, 'w', encoding='utf-8') as f:
        f.write("""import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  preview: {
    port: %d, host: '127.0.0.1',
    proxy: {
      '/api': { target: 'http://127.0.0.1:%d', changeOrigin: true },
      '/static': { target: 'http://127.0.0.1:%d', changeOrigin: true }
    }
  }
})
""" % (FRONTEND_PORT, BACKEND_PORT, BACKEND_PORT))

    preview = subprocess.Popen(
        [NODE, 'node_modules/vite/bin/vite.js', 'preview', '--config', 'vite.diag.config.js',
         '--port', str(FRONTEND_PORT), '--strictPort', '--host', '127.0.0.1'],
        cwd=FRONTEND, stdout=plog, stderr=subprocess.STDOUT)
    if not wait_http(f'http://127.0.0.1:{FRONTEND_PORT}/', 60):
        print('前端启动失败')
        backend.kill(); preview.kill()
        return 1

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', args=['--no-sandbox'])
            ctx = browser.new_context(viewport={'width': 1600, 'height': 1000})
            page = ctx.new_page()
            errs = []
            page.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
            page.on('pageerror', lambda e: errs.append('PAGEERROR: ' + str(e)))

            base = f'http://127.0.0.1:{FRONTEND_PORT}'
            page.goto(base + '/', wait_until='networkidle')
            page.evaluate("""async (base) => {
                await fetch(base + '/api/auth/login', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    credentials: 'include',
                    body: JSON.stringify({username: 'demo', password: 'demo123'})
                });
            }""", base)
            page.goto(base + '/chain', wait_until='networkidle')
            page.wait_for_timeout(2000)
            page.locator('.chain-tabs .el-tabs__item').nth(1).click()
            page.wait_for_timeout(2500)

            # ---- A. 元素几何与可见性 ----
            geo = page.evaluate("""() => {
                const c = document.querySelector('.gap-radar canvas');
                if (!c) return null;
                const r = c.getBoundingClientRect();
                const card = c.closest('.gap-card');
                const cr = card.getBoundingClientRect();
                return {
                    canvas: {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)},
                    inViewport: r.top >= 0 && r.bottom <= window.innerHeight && r.left >= 0 && r.right <= window.innerWidth,
                    viewport: {w: window.innerWidth, h: window.innerHeight},
                    scrollY: window.scrollY,
                    cardTop: Math.round(cr.top),
                    parentPointerEvents: getComputedStyle(c.parentElement).pointerEvents,
                };
            }""")
            print('A. 几何:', geo)

            # ---- B. 用 ECharts dispatchAction 直接显示 tooltip（验证 formatter 内容） ----
            # 找到第一个 radar 实例：ECharts 把实例挂在 DOM 上，通过 __echarts_instance__ 属性
            disp = page.evaluate("""() => {
                const el = document.querySelector('.gap-radar');
                const key = el && el.getAttribute('_echarts_instance_');
                const all = Object.keys(window).filter(k => k.startsWith('__ECHART'));
                // ECharts 2.0+ 用 attr 存 id，全局缓存在 __ECHARTS__ 里不易取，改用 dispatchEvent 方案
                return {attr: key, glob: all};
            }""")
            print('B. 实例句柄:', disp)

            # ---- C. 真实鼠标移动 + 全 DOM 扫描 tooltip ----
            el = page.locator('.gap-radar canvas').first
            el.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            box = el.bounding_box()
            print('C. bounding_box:', box)
            # 扫一圈：中心 + 四个顶点方向
            pts = [
                (0.5, 0.5), (0.5, 0.35), (0.35, 0.5), (0.65, 0.5), (0.5, 0.65),
            ]
            found = None
            for fx, fy in pts:
                page.mouse.move(box['x'] + box['width'] * fx, box['y'] + box['height'] * fy)
                page.wait_for_timeout(700)
                res = page.evaluate("""() => {
                    const all = [...document.querySelectorAll('body *')].filter(d => {
                        const s = getComputedStyle(d);
                        return (s.position === 'absolute') && d.innerText &&
                               d.innerText.length > 10 && d.innerText.length < 600 &&
                               !d.className.toString().includes('el-');
                    });
                    return all.map(d => ({
                        cls: d.className.toString().slice(0, 60),
                        pos: getComputedStyle(d).position,
                        disp: getComputedStyle(d).display,
                        txt: d.innerText.replace(/\\s+/g, ' ').slice(0, 160)
                    }));
                }""")
                if res:
                    print(f'   悬停点 ({fx},{fy}) 命中绝对定位层:', res[:4])
                    found = res
                    break
            if not found:
                print('   所有悬停点均未出现绝对定位 tooltip 层')

            # ---- D. 检查 ECharts tooltip 配置是否生效 ----
            cfg = page.evaluate("""() => {
                const c = document.querySelector('.gap-radar canvas');
                const host = c.parentElement;
                const html = host.outerHTML.slice(0, 900);
                return {hostChildren: host.children.length, html};
            }""")
            print('D. 雷达容器 HTML 前缀:', cfg['hostChildren'], cfg['html'][:400])

            # ---- E. 用 mousemove 事件直接派发到 canvas 中心 ----
            e2 = page.evaluate("""() => {
                const c = document.querySelector('.gap-radar canvas');
                const r = c.getBoundingClientRect();
                const x = r.left + r.width / 2, y = r.top + r.height / 2;
                ['mousemove','mousemove','mouseover'].forEach(type => {
                    c.dispatchEvent(new MouseEvent(type, {
                        clientX: x, clientY: y, bubbles: true, cancelable: true, view: window
                    }));
                });
                return true;
            }""")
            page.wait_for_timeout(900)
            after = page.evaluate("""() => {
                const c = document.querySelector('.gap-radar canvas');
                const host = c.parentElement;
                const tips = [...host.querySelectorAll('div')].map(d => ({
                    cls: d.className.toString().slice(0,80),
                    txt: d.innerText.replace(/\\s+/g,' ').slice(0,180),
                    disp: getComputedStyle(d).display,
                    op: getComputedStyle(d).opacity
                }));
                return tips;
            }""")
            print('E. 派发事件后容器内 div:', after)

            if errs:
                print('控制台错误:', errs[:8])
            browser.close()
    finally:
        for proc in (backend, preview):
            try:
                proc.terminate()
            except Exception:
                pass
        try:
            if os.path.exists(vc_config):
                os.remove(vc_config)
        except Exception:
            pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
