param(
    [string]$CplexStudioDir = '',
    [string]$PythonExecutable = '',
    [switch]$CheckSolvers
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $Program" }
}
Push-Location $PSScriptRoot
try {
    $venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $venvPython)) {
        if (Test-Path -LiteralPath '.venv') {
            throw 'Existing .venv is not a usable Windows environment. Rename it before retrying.'
        }
        if ($PythonExecutable) {
            Invoke-Checked -Program $PythonExecutable -Arguments @('-m', 'venv', '.venv')
        } else {
            Invoke-Checked -Program 'py' -Arguments @('-3.12', '-m', 'venv', '.venv')
        }
    }
    Invoke-Checked -Program $venvPython -Arguments @('-c', 'import sys; assert sys.version_info >= (3,12) and sys.maxsize > 2**32')
    Invoke-Checked -Program $venvPython -Arguments @('-m', 'pip', 'install', '-r', 'requirements.txt')
    if ($CplexStudioDir) {
        $studio = (Resolve-Path -LiteralPath $CplexStudioDir).Path
        $cplexExe = Join-Path $studio 'cplex\bin\x64_win64\cplex.exe'
        $cpExe = Join-Path $studio 'cpoptimizer\bin\x64_win64\cpoptimizer.exe'
        if (-not (Test-Path -LiteralPath $cplexExe)) {
            throw 'CplexStudioDir must contain cplex\bin\x64_win64\cplex.exe.'
        }
        $docplex = Join-Path $PSScriptRoot '.venv\Scripts\docplex.exe'
        Invoke-Checked -Program $docplex -Arguments @('config', '--upgrade', $studio)
        Invoke-Checked -Program $venvPython -Arguments @('scripts/check_solvers.py', '--full', '--solvers', 'cplex')
        if (Test-Path -LiteralPath $cpExe) {
            $cpBin = Split-Path -Parent $cpExe
            $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
            if ($cpBin -notin ($userPath -split ';')) {
                [Environment]::SetEnvironmentVariable('Path', ($cpBin + ';' + $userPath), 'User')
            }
            $env:Path = $cpBin + ';' + $env:Path
            Write-Host 'CP Optimizer added to user PATH. Reopen VS Code/PowerShell for future sessions.'
        } else {
            Write-Warning 'CP Optimizer executable not found. CPLEX CP still requires the full CP Optimizer installation.'
        }
    } else {
        Write-Warning 'Dependencies installed only. Full CPLEX setup requires -CplexStudioDir.'
    }
    if ($CheckSolvers) {
        Invoke-Checked -Program $venvPython -Arguments @('scripts/check_solvers.py', '--full')
    }
    Write-Host 'Activate with: .\.venv\Scripts\Activate.ps1'
    Write-Host 'Gurobi: put gurobi.lic in your Windows user profile, outside this repository.'
} finally {
    Pop-Location
}
