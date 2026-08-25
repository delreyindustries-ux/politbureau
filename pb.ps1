# Llancador: evita haver de recordar la ruta de Python i el PYTHONPATH.
$py = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
$env:PYTHONPATH = "$PSScriptRoot\src"
& $py -m politbureau @args
