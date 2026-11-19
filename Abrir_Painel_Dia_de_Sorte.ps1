$urls = @(
    "https://marciofernandomaia.com.br/centralmodalidades/"
    "https://marciofernandomaia.com.br/centralmodalidades/m/diadesorte/analise/resultados/"
    "https://marciofernandomaia.com.br/centralmodalidades/m/diadesorte/geradores-elite/estatisticas-ciclo/"
    "https://marciofernandomaia.com.br/centralmodalidades/m/diadesorte/geradores-elite/estatisticas-ciclo/?aba=2a1"
    "https://marciofernandomaia.com.br/centralmodalidades/m/diadesorte/analise/analises-inteligentes/"
    "https://marciofernandomaia.com.br/centralmodalidades/m/diadesorte/analise/escolha-visual/?aba=estatisticas&secao=2a"
    "https://marciofernandomaia.com.br/centralmodalidades/m/diadesorte/analise/escolha-visual/?aba=estatisticas&secao=2a1"
)

Write-Host "Abrindo Painel Dia de Sorte..." -ForegroundColor Cyan

foreach ($url in $urls) {
    Start-Process $url
    Start-Sleep -Milliseconds 500
}

Write-Host "Todas as paginas foram abertas." -ForegroundColor Green
