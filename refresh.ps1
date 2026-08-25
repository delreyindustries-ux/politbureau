# Actualitzacio diaria: enquestes noves -> mitjanes -> projeccions.
# Es idempotent: si es torna a executar no duplica res.
$ErrorActionPreference = "Stop"
$py  = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
$env:PYTHONPATH = "$PSScriptRoot\src"
$log = Join-Path $PSScriptRoot "data\refresh.log"

"=== $(Get-Date -Format 'yyyy-MM-dd HH:mm') ===" | Out-File $log -Append -Encoding utf8
& $py -m politbureau ingest 2>&1 | Tee-Object -FilePath $log -Append
& $py -m politbureau build  2>&1 | Tee-Object -FilePath $log -Append
"" | Out-File $log -Append -Encoding utf8
