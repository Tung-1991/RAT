Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\ratvenv\Scripts\Activate.ps1



###
@echo off
setlocal enabledelayedexpansion

:: Di chuyển vào thư mục dự án
cd /d "C:\Users\Administrator\Downloads\RAT"

:: --- QUY TRÌNH RESET SESSION & DỌN DẸP THÔNG MINH ---
if exist "data" (
    echo [INFO] Dang tu dong Reset Session cho tat ca cac Account...
    
    :: Quét qua từng thư mục ID Account
    for /d %%d in ("data\*") do (
        set "dirname=%%~nxd"
        
        :: Bỏ qua thư mục hệ thống
        if /i "!dirname!" neq "logs" if /i "!dirname!" neq "templates" (
            pushd "%%d"
            
            :: 1. XOÁ CÁC FILE TRẠNG THÁI (Để Reset Safeguard/Daily Stats)
            if exist "bot_state.json" del /q "bot_state.json"
            if exist "live_signals.json" del /q "live_signals.json"
            if exist "current_signal_state.json" del /q "current_signal_state.json"
            
            :: 2. XOÁ CÁC FILE TẠM (.tmp, .bak, .log)
            del /q *.tmp >nul 2>&1
            del /q *.bak >nul 2>&1
            
            :: 3. GIỮ LẠI (Bằng cách không xoá): 
            :: - brain_settings.json (Cấu hình Mẹ)
            :: - symbol_overrides.json (Cấu hình Con)
            :: - *.csv (Lịch sử giao dịch)
            
            popd
            echo [SUCCESS] Da Reset trang thai cho Account: !dirname!
        )
    )
)

:: Quét và xoá __pycache__
echo [INFO] Dang don dep cac thu muc __pycache__...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

:: Cập nhật code từ Git
echo [INFO] Dang kiem tra va cap nhat code tu Git...
git fetch origin
git reset --hard origin/main

:: Khởi chạy Bot
echo [INFO] Dang khoi chay Bot...
call ratvenv\Scripts\activate.bat
python main.py

pause
