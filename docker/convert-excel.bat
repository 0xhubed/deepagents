@echo off
REM Excel to CSV Converter
REM Converts all .xlsx files in the input folder to CSV

SETLOCAL EnableDelayedExpansion

SET WORKSPACE=C:\agent-workspace

echo.
echo  ====================================
echo   Excel to CSV Converter
echo  ====================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

REM Check for Excel files
IF NOT EXIST "%WORKSPACE%\input\*.xlsx" (
    echo No Excel files found in %WORKSPACE%\input\
    echo Place .xlsx files there and run this again.
    pause
    exit /b 0
)

echo Found Excel files in %WORKSPACE%\input\
echo Converting to CSV...
echo.

REM Create output directory
IF NOT EXIST "%WORKSPACE%\input\converted" mkdir "%WORKSPACE%\input\converted"

REM Run conversion
docker run --rm ^
    -v "%WORKSPACE%:/workspace" ^
    deepagents-cli:latest ^
    python -c "
import pandas as pd
from pathlib import Path

input_dir = Path('/workspace/input')
output_dir = Path('/workspace/input/converted')
output_dir.mkdir(exist_ok=True)

for excel_file in input_dir.glob('*.xlsx'):
    print(f'Converting {excel_file.name}...')
    try:
        excel = pd.ExcelFile(excel_file)
        for sheet in excel.sheet_names:
            df = pd.read_excel(excel, sheet_name=sheet)
            if len(excel.sheet_names) > 1:
                csv_name = f'{excel_file.stem}_{sheet}.csv'
            else:
                csv_name = f'{excel_file.stem}.csv'
            df.to_csv(output_dir / csv_name, index=False)
            print(f'  -> {csv_name}')
    except Exception as e:
        print(f'  ERROR: {e}')

print()
print('Conversion complete!')
print(f'CSV files saved to: /workspace/input/converted/')
"

echo.
echo ----------------------------------------
echo CSV files are in: %WORKSPACE%\input\converted\
echo.
pause
