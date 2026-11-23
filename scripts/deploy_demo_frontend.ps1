<#
Build the static demo frontend and publish it to AWS Amplify Hosting by direct upload.
No GitHub connection or server is required. The demo serves stored dossiers only.

Usage:  powershell -File scripts/deploy_demo_frontend.ps1
Teardown: aws amplify delete-app --app-id <appId> --region us-east-1
#>
$ErrorActionPreference = "Stop"
$region = "us-east-1"
$appName = "nyxalensai-demo"
$branch = "main"
$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root "frontend"

Set-Location $frontend
if (-not $env:SKIP_BUILD) {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend build failed." }
}

$zip = Join-Path $frontend "out.zip"
# Python writes clean forward-slash entries; Windows tar/Compress-Archive produce paths Amplify mis-extracts.
python (Join-Path $PSScriptRoot "zip_site.py") (Join-Path $frontend "out") $zip
if (-not (Test-Path $zip)) { throw "Could not create zip." }

$appId = aws amplify list-apps --region $region --query "apps[?name=='$appName'].appId | [0]" --output text
if (-not $appId -or $appId -eq "None") {
    $appId = aws amplify create-app --name $appName --platform WEB --region $region --query "app.appId" --output text
    aws amplify create-branch --app-id $appId --branch-name $branch --stage PRODUCTION --region $region | Out-Null
} else {
    $existing = aws amplify list-branches --app-id $appId --region $region --query "branches[?branchName=='$branch'].branchName | [0]" --output text
    if ($existing -eq "None") { aws amplify create-branch --app-id $appId --branch-name $branch --stage PRODUCTION --region $region | Out-Null }
}

$deployment = aws amplify create-deployment --app-id $appId --branch-name $branch --region $region | ConvertFrom-Json
curl.exe -s -T $zip $deployment.zipUploadUrl
aws amplify start-deployment --app-id $appId --branch-name $branch --job-id $deployment.jobId --region $region | Out-Null

for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 5
    $status = aws amplify get-job --app-id $appId --branch-name $branch --job-id $deployment.jobId --region $region --query "job.summary.status" --output text
    if ($status -in @("SUCCEED", "FAILED", "CANCELLED")) { break }
}
Remove-Item $zip -Force -ErrorAction SilentlyContinue
Write-Output "STATUS=$status"
Write-Output "APP_ID=$appId"
Write-Output "URL=https://$branch.$appId.amplifyapp.com"
