# Monitor FFmpeg Service - Documentação

## Visão Geral

O script `monitor_ffmpeg_service.sh` é uma ferramenta de diagnóstico abrangente desenvolvida para monitorar e diagnosticar travamentos de processos FFmpeg em sistemas Raspberry Pi 4B. O script foi projetado especificamente para trabalhar com duas câmeras USB (video0 e video2) e coletar dados detalhados sobre o sistema durante a execução dos processos FFmpeg.

## Autor

**Alex Bauruel** - Desenvolvido para Raspberry Pi 4B

## Propósito

Este script foi criado para diagnosticar problemas de travamento em subprocessos FFmpeg que são executados via Python, fornecendo logs detalhados e métricas do sistema para análise posterior.

## Funcionalidades Principais

### 1. Coleta de Estado Inicial
- **Configuração das câmeras**: Coleta informações detalhadas de `/dev/video0` e `/dev/video2` usando `v4l2-ctl`
- **Informações USB**: Lista todos os dispositivos USB conectados com detalhes (`lsusb -v`)
- **Espaço em disco**: Verifica o espaço disponível em disco (`df -h`)
- **Temperatura inicial**: Registra a temperatura do sistema no início do monitoramento

### 2. Monitoramento Contínuo do Sistema
- **Logs do kernel**: Monitora mensagens do kernel em tempo real (`dmesg -wT`)
- **I/O do sistema**: Rastreia operações de entrada/saída com `iotop`
- **Uso de recursos**: Monitora CPU, memória e processos com `top`
- **Temperatura**: Coleta dados de temperatura a cada 10 segundos

### 3. Detecção Inteligente e Monitoramento Contínuo de Processos FFmpeg
- **Detecção multi-tentativa**: Tenta localizar processos FFmpeg até 6 vezes com intervalos de 10 segundos
- **Padrões flexíveis**: Busca por diferentes padrões (`ffmpeg`, `video[02]`)
- **Modo adaptativo**: Continua monitoramento mesmo sem FFmpeg inicial
- **🆕 Instrumentação automática**: Detecta e instrumenta automaticamente novos processos FFmpeg a cada 5 segundos
- **🆕 Rastreamento de ciclo de vida**: Monitora quando processos FFmpeg iniciam e terminam
- **🆕 Controle de duplicação**: Evita instrumentar o mesmo processo múltiplas vezes
- **Detecção de processos relacionados**: Identifica processos Python (Gunicorn, capture3, etc.)

### 4. Rastreamento Detalhado de Processos
- **Instrumentação completa**: Para cada processo FFmpeg (inicial e novos):
  - Rastreamento de chamadas de sistema (`strace`)
  - Lista de arquivos abertos (`lsof`)
  - Informações de processo (PID, PPID, comando, uso de CPU/memória)
- **🆕 Logs de descoberta**: Registro detalhado de quando cada processo foi detectado
- **🆕 Status contínuo**: Log de status a cada minuto durante o monitoramento
- **Detecção de problemas**: Identifica processos zumbi do FFmpeg

### Configurações

### Variáveis Configuráveis

```bash
MONITOR_DURATION=300   # Duração do monitoramento em segundos (padrão: 5 minutos)
DEVICES=("/dev/video0" "/dev/video2")   # Dispositivos de câmera a monitorar
MAX_ATTEMPTS=6         # Número máximo de tentativas para encontrar processos FFmpeg
```

### Modos de Operação

O script opera em diferentes modos dependendo da detecção de processos FFmpeg:

- **`ffmpeg_found`**: Processos FFmpeg detectados no início - monitoramento completo
- **`system_only`**: Nenhum FFmpeg detectado - monitora apenas sistema e aguarda processos
- **`ffmpeg_detected_later`**: FFmpeg detectado durante a execução - registra aparição

### Diretório de Logs

Os logs são armazenados em:
```
/tmp/ffmpeg_diag_python_YYYYMMDD_HHMMSS/
```

Onde `YYYYMMDD_HHMMSS` representa a data e hora de início do monitoramento.

## Estrutura de Logs Gerados

### Logs de Estado Inicial
- `video0_before.log` - Estado inicial da câmera video0
- `video2_before.log` - Estado inicial da câmera video2
- `lsusb.log` - Lista detalhada de dispositivos USB
- `df.log` - Informações de espaço em disco
- `temp_start.log` - Temperatura inicial do sistema

### Logs de Monitoramento Contínuo
- `dmesg_live.log` - Mensagens do kernel em tempo real
- `iotop.log` - Monitoramento de I/O do sistema
- `top.log` - Monitoramento de processos e recursos
- `temp.log` - Log contínuo de temperatura (a cada 10 segundos)

### Logs de Processos FFmpeg
Para cada processo FFmpeg detectado (PID específico):
- `ffmpeg_${PID}.log.strace` - Rastreamento de chamadas de sistema
- `ffmpeg_${PID}_lsof.log` - Lista de arquivos abertos pelo processo
- `ffmpeg_${PID}_start.log` - Informações iniciais do processo
- `ffmpeg_${PID}_final.log` - Estado final do processo (se ainda ativo)

### Logs Especiais
- `python_${PID}_info.log` - Informações sobre processos Python detectados (Gunicorn, etc.)
- **🆕** `new_ffmpeg_detailed.log` - Registro detalhado de novos processos FFmpeg descobertos durante execução
- **🆕** `ffmpeg_lifecycle.log` - Log do ciclo de vida dos processos (início/término)
- **🆕** `monitor_status.log` - Status do monitoramento a cada minuto
- **🆕** `ffmpeg_monitoring_summary.log` - Resumo completo de todos os processos monitorados
- **🆕** `final_active_ffmpeg.log` - Processos FFmpeg ainda ativos no final
- `zombie_ffmpeg.log` - Lista de processos FFmpeg zumbi encontrados

## Pré-requisitos

### Dependências do Sistema
- `v4l2-ctl` (part of v4l-utils)
- `iotop`
- `strace`
- `lsof`
- Acesso sudo para alguns comandos

### Instalação de Dependências (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install v4l-utils iotop strace lsof
```

### Permissões Necessárias
O script requer permissões sudo para:
- Executar `dmesg -wT`
- Executar `iotop`
- Executar `strace` em processos
- Executar `lsof` em processos

## Como Usar

### 1. Execução Básica
```bash
cd /home/pi/app/utils
chmod +x monitor_ffmpeg_service.sh
./monitor_ffmpeg_service.sh
```

### 2. Execução em Background
```bash
nohup ./monitor_ffmpeg_service.sh > monitor.out 2>&1 &
```

### 3. Teste com Processos FFmpeg Simulados
```bash
# Primeiro, iniciar processos FFmpeg de teste
./test_ffmpeg_processes.sh

# Em seguida, executar o monitoramento
./monitor_ffmpeg_service.sh
```

### 4. Monitoramento Sem FFmpeg Ativo
Se não houver processos FFmpeg ativos, o script continuará coletando logs do sistema e aguardará que processos FFmpeg sejam iniciados durante a execução.

### 5. Personalização da Duração
Para alterar a duração do monitoramento, edite a variável `MONITOR_DURATION` no início do script:
```bash
MONITOR_DURATION=1800   # 30 minutos
```

## Fluxo de Execução

1. **Inicialização**: Cria diretório de logs com timestamp único
2. **Coleta inicial**: Captura estado inicial das câmeras e sistema
3. **Início dos monitores**: Inicia processos de monitoramento em background
4. **Detecção inteligente**: Tenta localizar processos FFmpeg com múltiplas tentativas
5. **Instrumentação adaptativa**: 
   - Se FFmpeg encontrado: anexa ferramentas de debugging
   - Se não encontrado: continua monitoramento do sistema
6. **Monitoramento contínuo**: 
   - Executa por duração configurada
   - Monitora aparição de novos processos FFmpeg
7. **Coleta final**: Captura estado final e identifica processos zumbi
8. **Finalização**: Termina processos de monitoramento e compacta logs

## Situações Comuns e Soluções

### 1. "Nenhum processo FFmpeg encontrado"
**Causa**: Os processos FFmpeg ainda não foram iniciados ou têm nomes diferentes.

**Soluções**:
- Execute `./test_ffmpeg_processes.sh` para criar processos de teste
- Inicie sua aplicação que usa FFmpeg em outro terminal
- O script continuará monitorando e detectará FFmpeg quando aparecer
- Verifique se os processos existem: `ps aux | grep ffmpeg`

### 2. "Processos FFmpeg zumbi detectados"
**Causa**: Processos FFmpeg terminaram incorretamente, deixando processos zumbi.

**Soluções**:
- Verifique os logs `zombie_ffmpeg.log` para detalhes
- Analise `dmesg_live.log` para erros de sistema
- Considere reiniciar os serviços relacionados

### 3. "Permissão negada para sudo"
**Causa**: Script precisa de privilégios administrativos para algumas operações.

**Soluções**:
- Execute com sudo: `sudo ./monitor_ffmpeg_service.sh`
- Configure sudoers para permitir comandos específicos sem senha
- Algumas funcionalidades funcionarão sem sudo (logs reduzidos)

## Análise dos Logs

### Identificação de Problemas Comuns

1. **Travamentos de câmera**:
   - Verifique `video0_before.log` e `video2_before.log` para configurações
   - Analise `dmesg_live.log` para erros USB ou de driver

2. **Problemas de performance**:
   - Examine `top.log` para uso excessivo de CPU/memória
   - Analise `iotop.log` para gargalos de I/O

3. **Problemas térmicos**:
   - Monitore `temp.log` para throttling por temperatura

4. **Problemas específicos do FFmpeg**:
   - Use `ffmpeg_${PID}.log.strace` para chamadas de sistema problemáticas
   - Verifique `ffmpeg_${PID}_lsof.log` para recursos bloqueados

## Limitações Conhecidas

1. **Requer privilégios sudo**: Algumas funcionalidades precisam de permissões administrativas
2. **Pode gerar logs grandes**: Durante monitoramento prolongado em sistemas ocupados
3. **Dependente de ferramentas externas**: Requer v4l-utils, iotop, strace e lsof

## Melhorias Implementadas (v3.0)

1. ✅ **Detecção inteligente de FFmpeg**: Múltiplas tentativas e padrões flexíveis
2. ✅ **Modo adaptativo**: Continua funcionando mesmo sem FFmpeg
3. ✅ **🆕 Instrumentação automática**: Detecta e monitora novos processos automaticamente
4. ✅ **🆕 Monitoramento de ciclo de vida**: Rastreia início e término de processos
5. ✅ **🆕 Controle anti-duplicação**: Evita instrumentar o mesmo processo múltiplas vezes
6. ✅ **🆕 Logs detalhados de descoberta**: Registro completo de quando cada processo foi encontrado
7. ✅ **🆕 Status contínuo**: Relatórios de status durante toda a execução
8. ✅ **Detecção de processos relacionados**: Identifica Python/Gunicorn
9. ✅ **Detecção de problemas**: Identifica e registra processos zumbi
10. ✅ **Limpeza automática**: Termina processos de monitoramento corretamente
11. ✅ **Relatório detalhado**: Saída com resumo e instruções de análise
12. ✅ **Script de teste melhorado**: Simula múltiplas ondas de processos FFmpeg

## Melhorias Sugeridas (Futuras)

1. **Interface web**: Dashboard para visualizar logs em tempo real
2. **Alertas automáticos**: Notificações quando problemas são detectados
3. **Rotação de logs**: Evitar uso excessivo de disco em monitoramentos longos
4. **Configuração via arquivo**: Permitir personalização sem editar o script
5. **Integração com Grafana**: Visualização de métricas de performance
6. **Detecção de padrões**: Identificação automática de problemas recorrentes

## Arquivos Relacionados

- `monitor_ffmpeg_service.sh` - Script principal de monitoramento
- `test_ffmpeg_processes.sh` - Utilitário para criar processos FFmpeg de teste
- `README_monitor_ffmpeg_service.md` - Esta documentação

## Exemplo de Uso Completo (Demonstração da Nova Funcionalidade)

```bash
# 1. Preparar o ambiente
cd /home/pi/app/utils
chmod +x monitor_ffmpeg_service.sh test_ffmpeg_processes.sh

# 2. Iniciar o monitoramento (agora detecta novos processos automaticamente!)
./monitor_ffmpeg_service.sh

# 3. Em outro terminal, criar múltiplas ondas de processos FFmpeg
./test_ffmpeg_processes.sh

# Isso criará processos FFmpeg em diferentes momentos:
# - T+5s:  Primeira onda (30s de duração) 
# - T+45s: Segunda onda (25s de duração)
# - T+85s: Terceira onda (20s de duração)

# 4. Observar o monitoramento em tempo real
tail -f /tmp/ffmpeg_diag_python_*/new_ffmpeg_detailed.log

# 5. Após conclusão, analisar resultados
tar -xzf /tmp/ffmpeg_diag_python_*/tar.gz
cd ffmpeg_diag_python_*

# Ver todos os processos monitorados
less ffmpeg_monitoring_summary.log

# Ver quando novos processos foram detectados
less new_ffmpeg_detailed.log

# Ver ciclo de vida dos processos
less ffmpeg_lifecycle.log

# Ver status do monitoramento
less monitor_status.log
```

## Suporte e Manutenção

Para problemas ou melhorias, consulte o desenvolvedor Alex Bauruel ou a documentação do projeto.

## Exemplo de Uso Típico

```bash
# 1. Executar o script (agora funciona mesmo sem FFmpeg ativo)
./monitor_ffmpeg_service.sh

# 2. Em outro terminal, iniciar a aplicação que usa FFmpeg
python3 /home/pi/app/capture3.py

# OU para teste rápido:
./test_ffmpeg_processes.sh

# 3. O script detectará automaticamente os processos FFmpeg
# e coletará todos os dados relevantes

# 4. Após o término, analisar os logs
tar -xzf /tmp/ffmpeg_diag_python_*/tar.gz
cd ffmpeg_diag_python_*
less dmesg_live.log    # Logs do kernel
less top.log           # Uso de recursos  
less new_ffmpeg.log    # FFmpeg detectados durante execução (se aplicável)
```

Este script é uma ferramenta valiosa para diagnóstico de problemas complexos em sistemas de captura de vídeo baseados em FFmpeg no Raspberry Pi, agora com capacidade de monitoramento adaptativo e detecção inteligente de processos.