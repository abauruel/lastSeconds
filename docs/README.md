# 📚 Documentação - Better Seconds Record

Documentação completa do sistema de gravação por eventos.

## ⚠️ IMPORTANTE - Mudança na v1.1 (29/03/2026)

**Inicialização Manual de Gravações**: A partir da versão 1.1, a aplicação **NÃO inicia gravações automaticamente**. É necessário chamar `POST /start` após o serviço estar rodando.

```bash
# Workflow atualizado:
curl http://localhost:5000/status          # Verificar se está rodando
curl -X POST http://localhost:5000/start   # Iniciar gravações
```

Consulte a [documentação da API](API_INTEGRATION.md) para mais detalhes.

---

## 📖 Guias Principais

### 🚀 Instalação e Configuração
- **[Quick Start](QUICK_START.md)** - ⭐ **COMECE AQUI** - Guia completo de instalação do zero
- **[Guia de Gravação em RAM](RAM_RECORDING_GUIDE.md)** - Sistema de buffer em tmpfs e sincronização automática
- **[Inicialização Automática](AUTO_START_INFO.md)** - Configuração de auto-start após reboot

### 📊 Operação e Monitoramento
- **[Monitoramento](MONITORING.md)** - Ferramentas de monitoramento e health checks
- **[Processamento de Timestamps](PROCESS_TIMESTAMPS_USAGE.md)** - Como processar eventos registrados
- **[Comandos](command.md)** - Referência de comandos úteis

### 📹 Streaming e Câmeras
- **[Guia de Streaming](STREAMING_GUIDE.md)** - Como visualizar câmeras ao vivo (HLS/RTMP)
- **[Acesso às Câmeras](ACESSO_CAMERAS.md)** - Informações de acesso às câmeras
- **[Diagnóstico de Streams](DIAGNOSTICO_STREAMS.md)** - Troubleshooting de streaming
- **[Streaming Health Fix](STREAMING_HEALTH_FIX.md)** - Correções de problemas de streaming
- **[Configuração DHCP](DHCP_CONFIGURATION.md)** - Servidor DHCP para câmeras IP

### 💻 Desenvolvimento
- **[Exemplos de API](API_EXAMPLES.md)** - Exemplos de uso da API REST
- **[Processamento de Timestamps](PROCESS_TIMESTAMPS_USAGE.md)** - Como processar eventos registrados
- **[Comandos](command.md)** - Referência de comandos úteis

### 🔧 Manutenção e Troubleshooting
- **[Correção de Arquivos Corrompidos](CORRUPTED_FILES_FIX.md)** - Como lidar com arquivos corrompidos
- **[Video Uploader](video_uploader.md)** - Sistema de upload de vídeos
- **[Skills](SKILLS.md)** - Habilidades e capacidades do sistema

## 🏠 Voltar

[← Voltar para README principal](../README.md)

---

**Estrutura do projeto:**
```
/home/pi/app/
├── README.md           # Documentação principal
├── docs/               # Esta pasta
│   ├── README.md       # Este arquivo
│   ├── *.md            # Documentação detalhada
├── capture3.py         # Aplicação principal
├── ffmpeg_manager.py   # Gerenciador FFmpeg
└── ...                 # Demais arquivos do projeto
```
