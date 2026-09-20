@echo off
chcp 65001 >nul
setlocal

echo [1/3] 安装依赖...
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
if errorlevel 1 goto fail

echo [2/3] 安装 PyInstaller...
py -m pip install --upgrade pyinstaller
if errorlevel 1 goto fail

echo [3/3] 打包 Windows 单文件 EXE...
py -m PyInstaller --noconfirm --clean --onefile --windowed --name ImageSizer ^
  --collect-all tkinterdnd2 ^
  --hidden-import=tkinterdnd2 ^
  ImageSizer.py
if errorlevel 1 goto fail

echo.
echo 完成！绿色版 EXE：
echo dist\ImageSizer.exe
pause
exit /b 0

:fail
echo.
echo 构建失败，请检查上面的错误信息。
pause
exit /b 1
