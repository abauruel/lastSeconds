# Processamento de Timestamps - Scripts Standalone

Scripts para processar timestamps sem necessidade do serviço web rodando.

## Scripts Disponíveis

### 1. `process_timestamps_standalone.py`
Script Python completo com todas as opções.

### 2. `process_timestamps.sh`
Wrapper bash para facilitar o uso.

## Uso

### Processar últimos 3 dias (padrão)
```bash
cd /home/pi/app
./process_timestamps.sh
```

### Processar dia específico
```bash
./process_timestamps.sh --date 20260214
```

### Processar últimos N dias
```bash
./process_timestamps.sh --days 7
```

### Processar apenas pendentes (ignora failed)
```bash
./process_timestamps.sh --pending-only
```

### Modo verbose (debug detalhado)
```bash
./process_timestamps.sh --verbose
```

### Combinar opções
```bash
./process_timestamps.sh --date 20260214 --verbose
./process_timestamps.sh --days 5 --pending-only
```

## Vantagens vs Rota HTTP

1. **Não depende do serviço**: Pode rodar mesmo com serviço parado
2. **Timeout ilimitado**: Não tem limite de tempo do Gunicorn
3. **Melhor para debugging**: Vê os logs em tempo real no terminal
4. **Agendamento fácil**: Pode usar cron para horários específicos
5. **Controle manual**: Ideal para reprocessar falhas

## Agendar via Cron

### Processar todos os dias às 3h da manhã
```bash
# Editar crontab
crontab -e

# Adicionar linha:
0 3 * * * /home/pi/app/process_timestamps.sh --days 1 >> /home/pi/app/logs/cron_process.log 2>&1
```

### Processar a cada 6 horas
```bash
0 */6 * * * /home/pi/app/process_timestamps.sh --pending-only >> /home/pi/app/logs/cron_process.log 2>&1
```

## Exemplo de Saída

```
======================================================================
PROCESSAMENTO STANDALONE DE TIMESTAMPS
======================================================================
Iniciado em: 2026-02-14 15:35:00

Inicializando FFMpegManager...
Modo standalone - processos FFmpeg não serão iniciados

Processando últimos 3 dias
Modo: todos os timestamps 'pending' e 'failed'
----------------------------------------------------------------------

[Background] Iniciando processamento de timestamps...
[Background] Processando timestamps de 20260214...
DEBUG: Iniciando _extract_video_from_timestamp
  timestamp_epoch: 1771091109
  cam_id: 0
  duration: 20s
...

======================================================================
RESULTADO DO PROCESSAMENTO
======================================================================
Status: success
Processados com sucesso: 2
Falharam: 1
Datas processadas: 20260214, 20260213

Finalizado em: 2026-02-14 15:37:45
======================================================================
```

## Notas

- O script **não inicia** processos FFmpeg de gravação (modo standalone)
- Usa o mesmo código do FFMpegManager, garantindo consistência
- Exit code 0 = sucesso, 1 = erro, 130 = interrompido pelo usuário
- Logs aparecem em tempo real no terminal
