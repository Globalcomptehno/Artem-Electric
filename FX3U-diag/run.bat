@echo off
chcp 65001 >nul
echo Diagnostika FX3U (tolko chtenie)
echo Zakroyte GX Works2 pered zapuskom!
echo.
python -m pip install --quiet pyserial
mode | find "COM"
echo.
set /p PORT=Vvedite COM-port kabelya (naprimer COM3): 
python "%~dp0fx_diag.py" %PORT% > "%~dp0result.txt" 2>&1
type "%~dp0result.txt"
echo.
echo Rezultat sohranen v result.txt - prishlite ego.
pause
