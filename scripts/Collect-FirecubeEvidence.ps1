param([string]$Device = '192.168.50.39:5555')
$ErrorActionPreference = 'Stop'
$adb = Join-Path $PSScriptRoot '..\adb.exe'
if (-not (Test-Path $adb)) { $adb = Join-Path (Get-Location) 'adb.exe' }
if (-not (Test-Path $adb)) { throw 'Run this from your platform-tools folder.' }
$report = [ordered]@{ captured_at = (Get-Date).ToUniversalTime().ToString('o'); device = $Device; read_only = $true; evidence = @() }
$commands = @(
    @('getprop', 'ro.build.fingerprint'),
    @('pm', 'help'),
    @('pm', 'list', 'users'),
    @('pm', 'resolve-activity', '--brief', '-a', 'android.intent.action.MAIN', '-c', 'android.intent.category.HOME'),
    @('dumpsys', 'package', 'com.amazon.tv.launcher'),
    @('dumpsys', 'package', 'com.amazon.vizzini'),
    @('dumpsys', 'package', 'com.amazon.alexa.datastore.app'),
    @('dumpsys', 'package', 'com.amazon.alexa.externalmediaplayer.fireos'),
    @('dumpsys', 'package', 'com.amazon.alexamediaplayer.runtime.ftv'),
    @('dumpsys', 'package', 'com.amazon.alexashopping'),
    @('dumpsys', 'package', 'com.amazon.tv.alexaalerts'),
    @('dumpsys', 'package', 'com.amazon.tv.alexanotifications'),
    @('dumpsys', 'package', 'com.ivona.orchestrator'),
    @('dumpsys', 'package', 'com.ivona.tts.oem')
)
foreach ($command in $commands) {
    $text = & $adb -s $Device shell @command 2>&1
    $report.evidence += [ordered]@{ command = $command; exit_code = $LASTEXITCODE; output = ($text | Out-String) }
}
$filename = Join-Path (Get-Location) ('firecube-evidence-' + (Get-Date -Format 'yyyyMMdd-HHmmss-ffff') + '.json')
$json = $report | ConvertTo-Json -Depth 8
$stream = [System.IO.File]::Open($filename, 'CreateNew', 'Write')
try {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    $stream.Write($bytes, 0, $bytes.Length)
} finally { $stream.Dispose() }
Write-Output "Saved read-only evidence: $filename"
