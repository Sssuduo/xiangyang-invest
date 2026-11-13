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

        # 抽屉详情
        tabs.nth(2).click()
        page.wait_for_timeout(1200)
        btn = page.locator('.el-table__fixed-right button, td:last-child button').first
        try:
            btn.click()
            page.wait_for_timeout(1500)
            page.screenshot(path=os.path.join(OUT, 'prod-chain-05-drawer.png'))
            print('✓ 详情抽屉')
        except Exception as e:
            print('抽屉截图跳过:', e)

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
