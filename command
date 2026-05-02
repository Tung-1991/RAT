Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\ratvenv\Scripts\Activate.ps1



###
@echo off
setlocal enabledelayedexpansion

:: 1. Chuyển vào thư mục chứa chính file script này (đảm bảo đường dẫn tương đối đúng)
cd /d "%~dp0"

:: --- QUY TRÌNH RESET SESSION & DỌN DẸP THÔNG MINH ---
if exist "data" (
    echo [INFO] Dang tu dong Reset Session cho tat ca cac Account...
    
    :: Quét qua từng thư mục con trong data
    for /d %%d in ("data\*") do (
        set "dirpath=%%~fd"
        set "dirname=%%~nxd"
        
        :: Kiểm tra bỏ qua thư mục hệ thống (Dùng nhãn để chắc chắn)
        if /i "!dirname!"=="logs" goto :continue
        if /i "!dirname!"=="templates" goto :continue
        
        :: Thực hiện dọn dẹp cho Account ID
        pushd "!dirpath!" >nul 2>&1
        if !errorlevel! equ 0 (
            :: A. XOÁ CÁC FILE TRẠNG THÁI (Reset Safeguard)
            if exist "bot_state.json" del /q "bot_state.json"
            if exist "live_signals.json" del /q "live_signals.json"
            if exist "current_signal_state.json" del /q "current_signal_state.json"
            
            :: B. XOÁ FILE TẠM
            del /q *.tmp >nul 2>&1
            del /q *.bak >nul 2>&1
            
            popd
            echo [SUCCESS] Da Reset trang thai cho Account: !dirname!
        ) else (
            echo [ERROR] Khong the truy cap vao Account: !dirname!
        )

        :continue
        nop
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
:: [LƯU Ý] Nếu chạy trên CMD, dùng dòng dưới. Nếu chạy PowerShell thì bỏ .bat
call ratvenv\Scripts\activate.bat
python main.py

pause
