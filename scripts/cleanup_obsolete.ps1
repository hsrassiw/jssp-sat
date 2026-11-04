$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
# Only obsolete project files; never remove environments, bounds or experiment results.
foreach ($relative in @('BOUNDS_CACHE.md', 'WEEK1.md', 'report/main.pdf', 'setup.sh', 'infra/ec2-jssp.yaml', 'requirements-lam.txt', 'requirements-experiments.txt')) {
    $target = Join-Path $repoRoot $relative
    if (Test-Path -LiteralPath $target -PathType Leaf) {
        Remove-Item -LiteralPath $target
        Write-Output "Removed $relative"
    }
}
