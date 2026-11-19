
# ============================================================
# PAINEL DE ANALISE - DIA DE SORTE
# Dominio principal com alternativa automatica
# ============================================================

$dominios = @(
    "https://marciofernandomaia.com.br",
    "https://teste.marciofernandomaia.com.br"
)

$dominioAtivo = $null

foreach ($dominio in $dominios) {
    try {
        $resposta = Invoke-WebRequest `
            -Uri "$dominio/centralmodalidades/" `
            -Method Head `
            -TimeoutSec 8 `
            -UseBasicParsing

        if ($resposta.StatusCode -ge 200 -and $resposta.StatusCode -lt 400) {
            $dominioAtivo = $dominio
            break
        }
    }
    catch {
        Write-Host "Dominio indisponivel: $dominio" -ForegroundColor Yellow
    }
}

if (-not $dominioAtivo) {
    Write-Host "ERRO: Nenhum dominio esta acessivel." -ForegroundColor Red
    Read-Host "Pressione ENTER para sair"
    exit
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "       PAINEL DIA DE SORTE" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Dominio selecionado: $dominioAtivo" -ForegroundColor Green

$caminhos = @(
    "/centralmodalidades/"
    "/centralmodalidades/m/diadesorte/analise/resultados/"
    "/centralmodalidades/m/diadesorte/geradores-elite/estatisticas-ciclo/"
    "/centralmodalidades/m/diadesorte/geradores-elite/estatisticas-ciclo/?aba=2a1"
    "/centralmodalidades/m/diadesorte/analise/analises-inteligentes/"
    "/centralmodalidades/m/diadesorte/analise/escolha-visual/?aba=estatisticas&secao=2a"
    "/centralmodalidades/m/diadesorte/analise/escolha-visual/?aba=estatisticas&secao=2a1"
)

foreach ($caminho in $caminhos) {
    Start-Process "$dominioAtivo$caminho"
    Start-Sleep -Milliseconds 500
}

Write-Host "==========================================" -ForegroundColor Green
Write-Host "Todas as paginas foram abertas." -ForegroundColor Green
Write-Host "=========================================="
