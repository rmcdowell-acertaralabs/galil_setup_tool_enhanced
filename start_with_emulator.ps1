# Start Galil Setup Tool with Emulator
# This PowerShell script starts both the emulator server and the GUI application

Write-Host "Starting DMC-4143 Emulator Server..." -ForegroundColor Green
Start-Process python -ArgumentList "dmc4143_emulator.py --server" -WindowStyle Minimized -PassThru | Out-Null

# Wait a moment for the server to start
Start-Sleep -Seconds 2

Write-Host "Starting Galil Setup Tool GUI..." -ForegroundColor Green
python main.py

# When GUI closes, optionally stop the emulator server
# (Uncomment the line below if you want to stop the server when GUI closes)
# Get-Process python | Where-Object {$_.CommandLine -like "*dmc4143_emulator*"} | Stop-Process -Force

