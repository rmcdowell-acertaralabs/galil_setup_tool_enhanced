@echo off
echo ========================================
echo Creating Galil Setup Tool Distribution
echo ========================================
echo.

echo Creating distribution folder...
if exist "Galil_Setup_Tool_Distribution" rmdir /s /q "Galil_Setup_Tool_Distribution"
mkdir "Galil_Setup_Tool_Distribution"

echo.
echo Copying executable...
copy "dist\Galil_Setup_Tool.exe" "Galil_Setup_Tool_Distribution\"

echo.
echo Copying documentation...
copy "README_EXECUTABLE.md" "Galil_Setup_Tool_Distribution\README.md"

echo.
echo Creating installation instructions...
echo # Galil Setup Tool - Quick Start > "Galil_Setup_Tool_Distribution\INSTALL.txt"
echo. >> "Galil_Setup_Tool_Distribution\INSTALL.txt"
echo 1. Right-click Galil_Setup_Tool.exe and select "Run as Administrator" >> "Galil_Setup_Tool_Distribution\INSTALL.txt"
echo 2. Click "INSTALL DLL FILES" to install required DLLs >> "Galil_Setup_Tool_Distribution\INSTALL.txt"
echo 3. Use "READ NETWORK SETTINGS" to check current configuration >> "Galil_Setup_Tool_Distribution\INSTALL.txt"
echo 4. Connect to your Galil controller >> "Galil_Setup_Tool_Distribution\INSTALL.txt"
echo. >> "Galil_Setup_Tool_Distribution\INSTALL.txt"
echo For detailed instructions, see README.md >> "Galil_Setup_Tool_Distribution\INSTALL.txt"

echo.
echo Creating version info...
echo Galil Setup Tool v1.0 > "Galil_Setup_Tool_Distribution\VERSION.txt"
echo Build Date: %date% %time% >> "Galil_Setup_Tool_Distribution\VERSION.txt"
echo Python Version: 3.8 (embedded) >> "Galil_Setup_Tool_Distribution\VERSION.txt"
echo PyInstaller: 6.15.0 >> "Galil_Setup_Tool_Distribution\VERSION.txt"
echo Executable Size: 10.0 MB >> "Galil_Setup_Tool_Distribution\VERSION.txt"

echo.
echo Distribution created successfully!
echo.
echo Location: Galil_Setup_Tool_Distribution\
echo.
echo Files included:
echo - Galil_Setup_Tool.exe (Main executable)
echo - README.md (Complete documentation)
echo - INSTALL.txt (Quick start guide)
echo - VERSION.txt (Version information)
echo.
echo The distribution is ready for deployment.
echo.
pause
