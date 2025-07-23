# Dockerfile para rodar Ollama com o modelo qwen2.5:0.5b já instalado
FROM ollama/ollama:latest

# Exponha a porta padrão do Ollama
EXPOSE 11434

# Baixa o modelo qwen2.5:0.5b na inicialização, se não existir
CMD ollama serve & sleep 5 && ollama pull qwen2.5:0.5b && fg
