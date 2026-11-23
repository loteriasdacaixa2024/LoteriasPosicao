$ErrorActionPreference = 'Continue'
$pids = @(10872,10800,12076,12280,11552,11472,11776,11712,12108,12056,11392,11396,11940,11620,11604,11684,796,11232)
$lines = New-Object System.Collections.Generic.List[string]
foreach ($p in $pids) {
    $out = & taskkill /F /PID $p 2>&1 | Out-String
    $lines.Add(("PID {0}: {1}" -f $p, $out.Trim()))
}
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$lines -join "`r`n" | Set-Content -Encoding UTF8 (Join-Path $dir 'kill-old-servers.txt')
