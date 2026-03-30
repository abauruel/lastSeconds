# API de Gravação - Exemplos de Uso

## ⚠️ IMPORTANTE - v1.1+

**Antes de registrar eventos, é necessário iniciar as gravações:**

```bash
# 1. Verificar se o serviço está rodando
curl http://localhost:5000/status

# 2. Iniciar as gravações
curl -X POST http://localhost:5000/start

# 3. Aguardar alguns segundos para FFmpeg iniciar
sleep 5

# 4. Agora você pode registrar eventos
```

---

## Registro de Eventos com Duração Dinâmica

### Padrão (10 segundos)
```bash
# Câmera 1
curl -X POST http://localhost:5000/record/cam1 \
  -H "Content-Type: application/json" \
  -d '{}'

# Câmera 2
curl -X POST http://localhost:5000/record/cam2 \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Com Duração Personalizada

```bash
# Vídeo de 15 segundos - Câmera 1
curl -X POST http://localhost:5000/record/cam1 \
  -H "Content-Type: application/json" \
  -d '{"duration": 15}'

# Vídeo de 18 segundos - Câmera 2
curl -X POST http://localhost:5000/record/cam2 \
  -H "Content-Type: application/json" \
  -d '{"duration": 18}'

# Vídeo de 20 segundos - Câmera 1
curl -X POST http://localhost:5000/record/cam1 \
  -H "Content-Type: application/json" \
  -d '{"duration": 20}'

# Vídeo de 30 segundos - Câmera 2
curl -X POST http://localhost:5000/record/cam2 \
  -H "Content-Type: application/json" \
  -d '{"duration": 30}'
```

### Processamento Manual

```bash
# Processar todos os eventos pendentes (últimos 3 dias)
curl -X POST http://localhost:5000/process_timestamps \
  -H "Content-Type: application/json" \
  -d '{}'

# Processar eventos de uma data específica
curl -X POST http://localhost:5000/process_timestamps \
  -H "Content-Type: application/json" \
  -d '{"date": "20260208"}'

# Processar eventos dos últimos 7 dias
curl -X POST http://localhost:5000/process_timestamps \
  -H "Content-Type: application/json" \
  -d '{"days_back": 7}'
```

## Resposta da API

### Sucesso no Registro
```json
{
  "status": "success",
  "message": "Evento cam1 registrado (duração: 15s)"
}
```

### Sucesso no Processamento
```json
{
  "status": "success",
  "dates": ["20260208"],
  "processed": 3,
  "failed": 0
}
```

## Funcionamento

1. **Registro**: O evento é registrado instantaneamente (<100ms) com o timestamp e duração
2. **Extração**: O vídeo é capturado com duração/2 ANTES e duração/2 DEPOIS do evento
   - 10s: 5s antes + 5s depois
   - 15s: 7.5s antes + 7.5s depois
   - 18s: 9s antes + 9s depois
3. **Localização**: `/home/pi/app/recordings/streams/YYYYMMDD/`

## Limitações

- **Duração máxima**: Limitada ao tamanho do segmento (60 segundos)
- **Tempo de espera**: Aguardar pelo menos 65-75 segundos após registro antes de processar
- **Variação**: Devido a keyframes H264, a duração pode ter variação de ±1-2 segundos
- **Segmentos**: Requer que o FFmpeg tenha gravado pelo menos 1 segmento completo

## Teste Rápido

```bash
# Registrar evento de 15 segundos
curl -X POST http://localhost:5000/record/cam1 \
  -H "Content-Type: application/json" \
  -d '{"duration": 15}'

# Aguardar 75 segundos
sleep 75

# Processar
curl -X POST http://localhost:5000/process_timestamps \
  -H "Content-Type: application/json" \
  -d '{}'

# Verificar resultado
ls -lh /home/pi/app/recordings/streams/$(date +%Y%m%d)/
```
