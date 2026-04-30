Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\ratvenv\Scripts\Activate.ps1



###
@echo off
:: Di chuyển vào thư mục dự án
cd /d "C:\Users\Administrator\Downloads\RAT"

:: Xử lý thư mục data: Giữ lại file và các thư mục chỉ định
if exist "data" (
    echo [INFO] Dang bao ton du lieu, logs va templates...
    if exist "temp_hold" rd /s /q "temp_hold"
    mkdir "temp_hold"
    
    :: Di chuyển các file lẻ
    if exist "data\brain_settings.json" move "data\brain_settings.json" "temp_hold\" >nul
    if exist "data\trade_history_master.csv" move "data\trade_history_master.csv" "temp_hold\" >nul
    
    :: Di chuyển các thư mục (logs và templates)
    if exist "data\logs" move "data\logs" "temp_hold\" >nul
    if exist "data\templates" move "data\templates" "temp_hold\" >nul
    
    :: Xoá sạch các file/thư mục rác còn lại trong data
    rd /s /q "data"
    
    :: Khôi phục lại cấu trúc ban đầu
    mkdir "data"
    move "temp_hold\*" "data\" >nul
    
    :: Dọn dẹp thư mục tạm
    rd /s /q "temp_hold"
)

:: Quét và xoá toàn bộ thư mục __pycache__
echo [INFO] Dang don dep cac thu muc __pycache__...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

:: Cập nhật code từ Git
echo [INFO] Dang kiem tra va cap nhat code tu Git...
git fetch origin
git reset --hard origin/main

:: Kích hoạt môi trường ảo
echo [INFO] Dang kich hoat moi truong ao...
call ratvenv\Scripts\activate.bat

:: Khởi chạy file Python
echo [INFO] Bot dang khoi chay...
python main.py

:: Giữ cửa sổ CMD
pause