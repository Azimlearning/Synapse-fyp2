# Stops every Synapse demo server started by start-synapse.ps1 (whatever listens on 8000, 3000, 8001, 3001).
foreach ($port in 8000, 3000, 8001, 3001) {
  $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  foreach ($c in $conns) {
    taskkill /PID $c.OwningProcess /T /F | Out-Null
    Write-Host "stopped port $port (pid $($c.OwningProcess))"
  }
}
