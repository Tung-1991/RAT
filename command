Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\ratvenv\Scripts\Activate.ps1



###
@echo off
:: Di chuyển vào thư mục dự án
cd /d "C:\Users\Administrator\Downloads\RAT"

:: Xoá thư mục data nếu tồn tại
if exist "data" rd /s /q "data"

:: Quét và xoá toàn bộ thư mục __pycache__ (trong root, core, signals...)
echo [INFO] Dang don dep cac thu muc __pycache__...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

:: Cập nhật code từ Git
echo [INFO] Dang kiem tra va cap nhat code tu Git...
git fetch origin
git reset --hard origin/main

:: Kích hoạt môi trường ảo (Dùng lệnh 'call' để script tiếp tục chạy sau khi activate)
echo [INFO] Dang kich hoat moi truong ao...
call ratvenv\Scripts\activate.bat

:: Khởi chạy file Python
echo [INFO] Bot dang khoi chay...
python main.py

:: Giữ cửa sổ CMD không bị tắt ngay lập tức nếu code Python bị lỗi hoặc dừng
pause