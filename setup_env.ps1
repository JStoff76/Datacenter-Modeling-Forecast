<#
PowerShell helper to create and populate the env-dbt virtual environment.
Run in the project root with PowerShell (you can run commands individually if preferred).
#>

param(
    [string]$VenvName = 'env-dbt'
)

Write-Host "Creating virtual environment: $VenvName"
python -m venv $VenvName

$venvPython = Join-Path -Path $VenvName -ChildPath 'Scripts\python.exe'
if (!(Test-Path $venvPython)) {
    Write-Error "Could not find $venvPython. Make sure Python is on PATH and venv was created."
    exit 1
}

Write-Host "Upgrading pip inside venv..."
Start-Process -FilePath $venvPython -ArgumentList "-m pip install --upgrade pip" -NoNewWindow -Wait

if (Test-Path './requirements-dbt.txt') {
    Write-Host "Installing packages from requirements-dbt.txt"
    Start-Process -FilePath $venvPython -ArgumentList "-m pip install -r requirements-dbt.txt" -NoNewWindow -Wait
} else {
    Write-Warning "requirements-dbt.txt not found in current directory. Create it with required packages first."
}

Write-Host "Done. To activate the venv in this PowerShell session run:`n`n    .\\$VenvName\\Scripts\\Activate.ps1`n"