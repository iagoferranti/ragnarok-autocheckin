@echo off
cd /d "C:\Users\Iago\Documents\Python\Ragnarok Login Diário"

pyinstaller --noconfirm --onefile --console ^
 --name "RagnarokMasterTool" ^
 --icon "icon.ico" ^
 --clean ^
 --hidden-import "fabricador" ^
 --hidden-import "checkin_bot_v2" ^
 --add-data "version.txt;." ^
 master.py

cd dist
certutil -hashfile RagnarokMasterTool.exe SHA256 > RagnarokMasterTool.exe.sha256

echo.
echo ✔ Build + SHA256 gerados em dist\
pause
