# ASR 隧道自动启动配置

## 文件清单

| 文件 | 作用 |
|------|------|
| `scripts/asr_start.bat` | 首次启动（检查 ASR API + 建立隧道） |
| `scripts/asr_watchdog.ps1` | **看门狗 hook（推荐）**：每 30 分钟巡检，断线重启服务并重建隧道，支持 agent 在线门控 |
| `scripts/asr_monitor.ps1` | 旧版监控脚本（每 30 秒轮询），已被 `asr_watchdog.ps1` 取代，**勿与看门狗同时运行** |
| `scripts/asr_task.xml` | Windows 任务计划程序配置（登录/解锁触发），已指向 `asr_watchdog.ps1` |

## 安装步骤

### 1. 确认 SSH 密钥

确保 `~/.ssh/id_ed25519` 已添加到生产服务器 `authorized_keys`：

```bash
# 在笔记本上执行
cat ~/.ssh/id_ed25519.pub
# 将内容添加到生产服务器 /root/.ssh/authorized_keys
```

### 2. 注册任务计划

以管理员身份打开 PowerShell，执行：

```powershell
# 导入任务（登录时 + 解锁时自动启动 ASR 隧道）
Register-ScheduledTask -Xml (Get-Content "h:\项目1\scripts\asr_task.xml" | Out-String) -TaskName "ASR Tunnel Monitor" -Force
```

### 3. 验证

```powershell
# 查看任务状态
Get-ScheduledTask -TaskName "ASR Tunnel Monitor" | Get-ScheduledTaskInfo

# 手动启动测试
Start-ScheduledTask -TaskName "ASR Tunnel Monitor"

# 查看监控日志
Get-Content "h:\项目1\scripts\asr_monitor.log" -Tail 20
```

## 触发场景

| 场景 | 触发条件 | 行为 |
|------|----------|------|
| 开机后登录 | LogonTrigger | 启动监控脚本 |
| 休眠/睡眠后解锁 | SessionUnlock | 重新启动 ASR 隧道 |
| 隧道断线 | 监控脚本检测 | 每 30 秒自动重连 |
| ASR API 崩溃 | 本地健康检查失败 | 自动重启 `asr_api.py` |

## 卸载

```powershell
Unregister-ScheduledTask -TaskName "ASR Tunnel Monitor" -Confirm:$false
```
