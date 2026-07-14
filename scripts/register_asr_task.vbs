' VBScript to register ASR Tunnel scheduled task with UAS elevation
' Double-click this file to run

Set Shell = CreateObject("Shell.Application")
psCmd = "powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File h:\项目1\scripts\asr_monitor.ps1"
schArgs = "/Create /TN ""ASR_Tunnel""" & _
          " /TR """ & psCmd & """" & _
          " /SC ONLOGON /RL HIGHEST /DELAY 0000:10 /F"

Shell.ShellExecute "schtasks.exe", schArgs, "", "runas", 1

WScript.Sleep 2000

Set Shell2 = CreateObject("Shell.Application")
Shell2.ShellExecute "schtasks.exe", "/Run /TN ""ASR_Tunnel""", "", "runas", 1

WScript.Echo "ASR Tunnel task registered and started"
