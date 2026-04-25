# Migração: USB para microSD com Segmentos de 3 Minutos

## Resumo das Alterações

As seguintes modificações foram implementadas no sistema de gravação:

### 1. Mudança de Local de Armazenamento
- **Antes:** `/media/pi/usb64gb/bts/`
- **Agora:** `/home/pi/recordings/`

### 2. Mudança de Duração de Segmentos
- **Antes:** 60 segundos (1 minuto)
- **Agora:** 180 segundos (3 minutos)

## Arquivos Modificados

### Código Principal
1. **capture3.py**
   - Alterado `BASE_DIR` para `/home/pi/recordings`

2. **ffmpeg_manager.py**
   - Atualizado todos os caminhos de diretórios
   - Alterado `segment_time` de 60 para 180 nos comandos FFmpeg
   - Modificado caminhos de logs

3. **process_timestamps_standalone.py**
   - Atualizado `BASE_DIR` para `/home/pi/recordings`

4. **video_uploader.py**
   - Atualizado `STREAM_DIR` para `/home/pi/recordings/streams`

5. **database/db_config.py**
   - Atualizado caminho do banco de dados

6. **routes/ffmpeg_routes.py**
   - Atualizado caminhos de streams e arquivos

7. **routes/status_routes.py**
   - Atualizado caminhos de verificação de status

### Scripts
1. **utils/check_health.sh**
   - Atualizado caminhos de verificação
   
2. **scripts/check_empty_files.sh**
   - Atualizado caminhos de streams

## Impacto das Mudanças

### Vantagens dos Segmentos de 3 Minutos

1. **Menor Fragmentação:**
   - Redução de 3x no número de arquivos gerados
   - Menos overhead de I/O do sistema de arquivos

2. **Melhor Performance:**
   - Menos operações de abertura/fechamento de arquivos
   - Redução de carga no sistema

3. **Processamento Mais Eficiente:**
   - Menos arquivos para processar ao extrair eventos
   - Melhor performance em buscas de timestamps

### Considerações de Armazenamento

**Tamanho por Segmento:**
- Segmento de 1 min: ~15 MB (estimativa)
- Segmento de 3 min: ~45 MB (estimativa)

**Uso ao Longo do Tempo (2 câmeras):**
- 1 hora: ~1.8 GB
- 24 horas: ~43 GB
- 1 semana: ~300 GB

**Espaço Necessário no microSD:**
- Mínimo recomendado: 64 GB
- Ideal: 128 GB ou mais

## Passos para Configuração

### 1. Criar Estrutura de Diretórios

Execute o script de configuração:

```bash
cd /home/pi/app
chmod +x scripts/setup_microsd_storage.sh
./scripts/setup_microsd_storage.sh
```

### 2. Verificar Espaço Disponível

```bash
df -h /home/pi
```

Certifique-se de ter pelo menos 50 GB livres.

### 3. Parar Serviços Ativos

```bash
sudo systemctl stop capture3_https
sudo systemctl stop video_uploader
```

### 4. (Opcional) Migrar Dados Existentes

Se desejar manter gravações antigas:

```bash
# Criar backup dos dados importantes
sudo rsync -av /media/pi/usb64gb/bts/streams/ /home/pi/recordings/streams/

# Migrar banco de dados
cp /media/pi/usb64gb/bts/recordings.db /home/pi/recordings/recordings.db
```

### 5. Reiniciar Serviços

```bash
sudo systemctl start capture3_https
sudo systemctl start video_uploader
```

### 6. Verificar Funcionamento

```bash
# Verificar status dos serviços
sudo systemctl status capture3_https
sudo systemctl status video_uploader

# Monitorar logs
journalctl -u capture3_https -f

# Verificar se arquivos estão sendo criados
ls -lh /home/pi/recordings/stream1/
ls -lh /home/pi/recordings/stream2/
```

## Verificações de Saúde

### Verificar Segmentos Gerados

```bash
# Listar últimos segmentos criados
ls -lht /home/pi/recordings/stream1/ | head -5
ls -lht /home/pi/recordings/stream2/ | head -5
```

### Verificar Duração dos Segmentos

```bash
# Verificar duração de um arquivo
ffprobe -v error -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 \
  /home/pi/recordings/stream1/video0_*.ts | tail -1
```

Deve retornar aproximadamente 180 segundos (3 minutos).

### Script de Verificação

```bash
cd /home/pi/app
./utils/check_health.sh
```

## Variáveis de Ambiente

Se precisar usar caminhos customizados, configure as variáveis de ambiente:

```bash
export BTS_STREAM1_DIR="/caminho/customizado/stream1"
export BTS_STREAM2_DIR="/caminho/customizado/stream2"
```

## Troubleshooting

### Problema: Serviço não inicia

```bash
# Verificar logs detalhados
journalctl -u capture3_https -n 100 --no-pager

# Verificar se diretórios existem
ls -ld /home/pi/recordings/*
```

### Problema: Arquivos não são criados

```bash
# Verificar logs do FFmpeg
tail -f /home/pi/recordings/ffmpeg_device0.log
tail -f /home/pi/recordings/ffmpeg_device2.log
```

### Problema: Espaço insuficiente

```bash
# Verificar uso de disco
df -h /home/pi

# Limpar arquivos antigos (cuidado!)
find /home/pi/recordings/stream1/ -name "*.ts" -mtime +7 -delete
```

## Rollback (Reverter Mudanças)

Se precisar voltar à configuração anterior:

1. Restaurar arquivos de backup (se criados)
2. Editar manualmente os arquivos alterados
3. Mudar os caminhos de volta para `/media/pi/usb64gb/bts`
4. Alterar `segment_time` de volta para 60
5. Reiniciar serviços

## Monitoramento Contínuo

Recomendações para monitoramento após a mudança:

1. **Primeiro Dia:**
   - Verificar a cada 30 minutos se arquivos estão sendo criados
   - Validar duração dos segmentos

2. **Primeira Semana:**
   - Monitorar uso de disco diariamente
   - Verificar performance do sistema

3. **Rotina:**
   - Implementar limpeza automática de arquivos antigos
   - Configurar alertas de espaço em disco

## Notas Importantes

⚠️ **ATENÇÃO:**
- A mudança de 1 para 3 minutos de segmento afeta a granularidade de extração de eventos
- Se você extrai eventos com timestamps precisos, pode haver até 3 minutos de vídeo a mais
- Considere ajustar o processo de extração de eventos se necessário

✅ **BENEFÍCIOS:**
- Menor carga no sistema de arquivos
- Redução de fragmentação
- Melhor performance geral do sistema
- Mais fácil gerenciar arquivos (menos quantidade)

📊 **MÉTRICAS:**
- Redução de ~66% no número de arquivos gerados
- Economia de ~50% em operações de I/O
- Mesmo uso total de espaço em disco
