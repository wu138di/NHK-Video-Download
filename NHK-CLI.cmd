@echo off
chcp 65001 >nul
cd /d "%~dp0"
"%~dp0NHK-CLI-V2.0.exe" %*
cmd /k
