# 在 Elasticsearch 就绪后创建 rag_chunks 索引（幂等：已存在则跳过）
$ErrorActionPreference = "Stop"
$BaseUrl = if ($env:ES_URL) { $env:ES_URL.TrimEnd("/") } else { "http://127.0.0.1:9200" }
$IndexName = "rag_chunks"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$BodyPath = Join-Path $RepoRoot "database\es\rag_chunks.index.json"

Write-Host "Checking $BaseUrl/$IndexName ..."
try {
    $head = Invoke-WebRequest -Method Head -Uri "$BaseUrl/$IndexName" -SkipHttpErrorCheck
    if ($head.StatusCode -eq 200) {
        Write-Host "Index '$IndexName' already exists. Skip."
        exit 0
    }
} catch {
    # 404 etc. -> create
}

if (-not (Test-Path $BodyPath)) {
    Write-Error "Missing mapping file: $BodyPath"
    exit 1
}

$json = Get-Content -Raw -Path $BodyPath -Encoding UTF8
Write-Host "Creating index '$IndexName' ..."
Invoke-RestMethod -Method Put -Uri "$BaseUrl/$IndexName" -ContentType "application/json; charset=utf-8" -Body $json | ConvertTo-Json -Depth 10
Write-Host "Done."
