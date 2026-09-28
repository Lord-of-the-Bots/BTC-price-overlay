$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    if (-not (Test-Path '.venv\Scripts\python.exe')) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the build environment.' }
    }
    $python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    & $python -m pip install -r requirements.txt 'pyinstaller==6.22.3'
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    & $python -m PyInstaller --noconfirm --clean --onefile --windowed --name BTC-price-overlay --hidden-import socks BTC_overlay.pyw
    if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
    $digest = (Get-FileHash 'dist\BTC-price-overlay.exe' -Algorithm SHA256).Hash.ToLowerInvariant()
    "$digest  BTC-price-overlay.exe" | Set-Content 'dist\SHA256SUMS.txt' -Encoding ascii
} finally {
    Pop-Location
}
