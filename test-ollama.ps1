# Script PowerShell para testar o modelo qwen2.5:0.5b no Ollama
$prompt = "Qual a capital do Brasil?"

try {

    $body = @{
        model = "qwen2.5:0.5b"
        prompt = $prompt
        stream = $false
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/generate" -Method Post -Body $body -ContentType "application/json"

    if ($null -eq $response -or $null -eq $response.response -or $response.response -eq "") {
        Write-Host "Nenhuma resposta recebida. Verifique se o modelo 'qwen2.5:0.5b' está disponível e pronto para uso."
    } else {
        Write-Host "Resposta do modelo: $($response.response)"
    }
} catch {
    Write-Host "Erro ao conectar ou processar a resposta do Ollama: $_"
}
