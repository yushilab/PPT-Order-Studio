param([switch]$Dev, [switch]$CoreOnly)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$basePython = Get-Command python -ErrorAction SilentlyContinue
if (-not $basePython) { throw 'Install Python 3.10+ from python.org and enable PATH, then rerun.' }
& $basePython.Source -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ required'"
if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ required.' }
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    & $basePython.Source -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create .venv' }
}
$venvPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed; check network/index configuration.' }
$spec = if ($Dev) { '.[extract,dev]' } elseif ($CoreOnly) { '.' } else { '.[extract]' }
& $venvPython -m pip install -e $spec
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $venvPython -m pptstudio doctor
if ($LASTEXITCODE -ne 0) { throw 'Core environment check failed.' }
Write-Output 'Ready. Run: .\.venv\Scripts\python.exe -m pptstudio demo orders\demo'
