"""产业链图谱几何自检：验证大类分组条与环节节点无重叠、节点不越界。

用法：python backend/scripts/diag_graph_layout.py
"""
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

BACKEND = r'H:\项目1\backend'
FRONTEND = r'H:\项目1\frontend'
PY = r'G:\123\python.exe'
NODE = r'C:\Program Files\nodejs\node.exe'
BACKEND_PORT = 15095
FRONTEND_PORT = 15094


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

    dbfile = os.path.join(tempfile.gettempdir(), 'chain_graph.db')
    if os.path.exists(dbfile):
        os.remove(dbfile)
    dburl = 'sqlite:///' + dbfile.replace('\\', '/')
    env = dict(os.environ)
    env['DATABASE_URL'] = dburl
    env['FLASK_ENV'] = 'development'
    tmp = tempfile.gettempdir()
    blog = open(os.path.join(tmp, 'g_backend.log'), 'w', encoding='utf-8')
    plog = open(os.path.join(tmp, 'g_frontend.log'), 'w', encoding='utf-8')

    backend = subprocess.Popen(
        [PY, '-c',
         'import os,sys;sys.path.insert(0,r"%s");'
         'os.environ["DATABASE_URL"]="%s";'
         'from app import create_app;'
         'app=create_app("development");'
         'app.run(host="127.0.0.1",port=%d,debug=False,use_reloader=False)' % (BACKEND, dburl, BACKEND_PORT)],
        cwd=BACKEND, env=env, stdout=blog, stderr=subprocess.STDOUT)
    if not wait_http(f'http://127.0.0.1:{BACKEND_PORT}/api/chain/overview', 90):
        print('后端启动失败'); backend.kill(); return 1

    vc = os.path.join(FRONTEND, 'vite.graph.config.js')
    with open(vc, 'w', encoding='utf-8') as f:
        f.write("""import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  preview: { port: %d, host: '127.0.0.1',
    proxy: { '/api': { target: 'http://127.0.0.1:%d', changeOrigin: true } } }
})
""" % (FRONTEND_PORT, BACKEND_PORT))

    preview = subprocess.Popen(
        [NODE, 'node_modules/vite/bin/vite.js', 'preview', '--config', 'vite.graph.config.js',
         '--port', str(FRONTEND_PORT), '--strictPort', '--host', '127.0.0.1'],
        cwd=FRONTEND, stdout=plog, stderr=subprocess.STDOUT)
    if not wait_http(f'http://127.0.0.1:{FRONTEND_PORT}/', 60):
        print('前端启动失败'); backend.kill(); preview.kill(); return 1

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', args=['--no-sandbox'])
            ctx = browser.new_context(viewport={'width': 1600, 'height': 1000})
            page = ctx.new_page()
            base = f'http://127.0.0.1:{FRONTEND_PORT}'
            page.goto(base + '/', wait_until='networkidle')
            page.evaluate("""async (base) => {
                await fetch(base + '/api/auth/login', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    credentials: 'include',
                    body: JSON.stringify({username: 'demo', password: 'demo123'})});
            }""", base)
            page.goto(base + '/chain', wait_until='networkidle')
            page.wait_for_timeout(2500)

            res = page.evaluate("""() => {
                const svg = document.querySelector('.chain-svg');
                if (!svg) return {err: 'no svg'};
                const bars = [...svg.querySelectorAll('.group-bar-text')].map(t => {
                    const r = t.getBoundingClientRect();
                    return {name: t.textContent.trim(), x: r.x, y: r.y, w: r.width, h: r.height};
                });
                // 分组条矩形（标题条的 rect 是每个 group 里的第一个 rect）
                const barRects = [...svg.querySelectorAll('g')].filter(g => g.querySelector('.group-bar-text')).map(g => {
                    const rect = g.querySelector('rect');
                    const r = rect.getBoundingClientRect();
                    return {x: r.x, y: r.y, w: r.width, h: r.height};
                });
                const nodes = [...svg.querySelectorAll('.node-group')].map(g => {
                    const rect = g.querySelector('rect');
                    const r = rect.getBoundingClientRect();
                    const name = g.querySelector('.node-name')?.textContent.trim() || '';
                    return {name, x: r.x, y: r.y, w: r.width, h: r.height};
                });
                const overlaps = [];
                for (const b of barRects) {
                    for (const n of nodes) {
                        if (b.x < n.x + n.w && b.x + b.w > n.x && b.y < n.y + n.h && b.y + b.h > n.y) {
                            overlaps.push([Math.round(b.x), Math.round(b.y), n.name]);
                        }
                    }
                }
                // 节点之间互相重叠
                const nodeOverlaps = [];
                for (let i = 0; i < nodes.length; i++) {
                    for (let j = i + 1; j < nodes.length; j++) {
                        const a = nodes[i], b = nodes[j];
                        if (a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y) {
                            nodeOverlaps.push([a.name, b.name]);
                        }
                    }
                }
                const svgRect = svg.getBoundingClientRect();
                const outside = nodes.filter(n => n.x < svgRect.x - 1 || n.x + n.w > svgRect.x + svgRect.width + 1);
                return {
                    barCount: bars.length, nodeCount: nodes.length,
                    overlaps, nodeOverlaps,
                    outside: outside.map(n => n.name),
                    svgH: Math.round(svgRect.height),
                    bars: bars.map(b => b.name),
                };
            }""")
            print('图谱几何:', {k: v for k, v in res.items() if k != 'bars'})
            print('分组条:', res['bars'])
            assert res['barCount'] == 9, f'分组条应为 9：{res["barCount"]}'
            assert not res['overlaps'], f'分组条与节点重叠：{res["overlaps"]}'
            assert not res['nodeOverlaps'], f'节点之间重叠：{res["nodeOverlaps"]}'
            assert not res['outside'], f'节点越出画布：{res["outside"]}'
            print('✓ 分组条 / 节点无重叠、无越界')

            browser.close()
    finally:
        for proc in (backend, preview):
            try:
                proc.terminate()
            except Exception:
                pass
        try:
            if os.path.exists(vc):
                os.remove(vc)
        except Exception:
            pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
