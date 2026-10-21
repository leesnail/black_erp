@echo off
:: natapp 快速启动脚本（随安装包自动生成）
:: 双击本文件即可启动 natapp
:: 首次使用请到 natapp 官网获取自己的 authtoken 并填入下方，
:: 或改为环境变量：set NATAPP_AUTHTOKEN=xxxx 然后下方使用 %NATAPP_AUTHTOKEN%
if "%NATAPP_AUTHTOKEN%"=="" (
  echo [WARN] 未设置 NATAPP_AUTHTOKEN 环境变量，使用占位符将无法连接
  set NATAPP_AUTHTOKEN=your-authtoken-here
)
"D:\code\black_erp\deploy\scripts\natapp.exe" -authtoken=%NATAPP_AUTHTOKEN%
pause
