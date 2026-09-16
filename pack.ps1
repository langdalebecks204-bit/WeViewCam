# ==============================================================================
# WeViewCam 一键打包脚本 (Windows PowerShell) - v0.1.0
# ==============================================================================

$version = "0.1.0"
$output = "weviewcam_ubuntu.tar.gz"
$versioned_output = "weviewcam_ubuntu_v$version.tar.gz"

Write-Host "正在打包发布包 $versioned_output 与 $output ..."

tar -czvf $output `
    --exclude="*.zip" `
    --exclude="HCNetSDKV6.1.11.30*" `
    --exclude="*.tar.gz" `
    --exclude="__pycache__" `
    --exclude=".pytest_cache" `
    --exclude=".venv" `
    --exclude="logs" `
    core adapters ui config sdk tests main.py scan_rtsp.py requirements.txt setup_env.sh run.sh install_desktop_shortcut.sh weviewcam.desktop icon.png README.md

Copy-Item $output $versioned_output -Force

$size = (Get-Item $output).Length / 1MB
Write-Host ("打包成功: {0} 及 {1} ({2:N2} MB)" -f $output, $versioned_output, $size) -ForegroundColor Green
