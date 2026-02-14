# Simuladores de Acionamento

Esta pasta contém scripts para simular os acionamentos do dispositivo baseado no padrão temporal observado no arquivo `analise.txt`.

## Arquivos Criados

### 1. `simulate_device_triggers.sh`
Script bash detalhado que reproduz exatamente a sequência temporal observada.

**Características:**
- Reproduz todos os acionamentos com intervalos reais
- Log detalhado de cada chamada
- Tratamento de erros HTTP
- Tempo total: ~85 minutos

**Uso:**
```bash
./simulate_device_triggers.sh
```

### 2. `simulate_triggers_compact.sh`
Script bash compacto e configurável.

**Características:**
- Configuração via variáveis de ambiente
- Multiplicador de velocidade
- Array de intervalos baseado no padrão real
- Interface mais limpa

**Uso básico:**
```bash
./simulate_triggers_compact.sh
```

**Uso com configurações:**
```bash
# Executar 10x mais rápido
SPEED_MULTIPLIER=0.1 ./simulate_triggers_compact.sh

# URL customizada
BASE_URL="http://192.168.1.100:8080/api/device/trigger" ./simulate_triggers_compact.sh

# Método customizado (se necessário)
CURL_METHOD="GET" ./simulate_triggers_compact.sh
```

### 3. `trigger_simulator.py`
Script Python avançado com análise automática do arquivo.

**Características:**
- Análise automática do `analise.txt`
- Extração de timestamps via regex
- Cálculo automático de intervalos
- Múltiplas opções de configuração
- Relatório detalhado de execução
- Modo dry-run para teste

**Uso básico:**
```bash
python3 trigger_simulator.py
```

**Opções avançadas:**
```bash
# URL customizada
python3 trigger_simulator.py --url "http://192.168.1.100:8080/api/trigger"

# Executar 5x mais rápido (intervalos em segundos são divididos por 5)
python3 trigger_simulator.py --speed 0.2

# Modo dry-run (apenas mostrar o que seria executado)
python3 trigger_simulator.py --dry-run

# Executar sem confirmação
python3 trigger_simulator.py --non-interactive

# Timeout customizado
python3 trigger_simulator.py --timeout 60

# Arquivo analise.txt customizado
python3 trigger_simulator.py --analise-file "/path/to/custom/analise.txt"
```

## Padrão Temporal Observado

Baseado na análise do arquivo `analise.txt`, o dispositivo foi acionado com os seguintes intervalos **precisos em segundos**:

- **06:58:14** - Primeiro acionamento (stream2)
- **07:00:06** - 112 segundos depois (stream1)
- **07:03:40** - 214 segundos depois (stream1)
- **07:08:03** - 263 segundos depois (stream1)
- **07:10:43** - 160 segundos depois (stream1)
- **07:16:48** - 365 segundos depois (stream1)
- E assim por diante...

**Estatísticas:**
- Total de acionamentos: **54**
- Período observado: **06:58:14 às 08:30:32** (5.538 segundos / 92m18s)
- Precisão: **Intervalos calculados em segundos**
- Menor intervalo: **2 segundos**
- Maior intervalo: **420 segundos (7 minutos)**

## Configuração dos Endpoints

Os scripts agora fazem chamadas POST simples (sem body) para endpoints diferentes baseado no tipo de stream:

- **stream1** → `/cam1`
- **stream2** → `/cam2`

### Para scripts bash:
```bash
export BASE_URL="http://seu-servidor:porta/api/trigger"
```

### Para script Python:
```bash
python3 trigger_simulator.py --url "http://seu-servidor:porta/api/trigger"
```

## URLs Geradas Automaticamente

- **stream1**: `{BASE_URL}/cam1`
- **stream2**: `{BASE_URL}/cam2`

Por exemplo, se `BASE_URL="http://localhost:8080/api/trigger"`:
- **stream1**: `http://localhost:8080/api/trigger/cam1`
- **stream2**: `http://localhost:8080/api/trigger/cam2`

## Estrutura das Requisições

### Método HTTP:
- **POST** (sem body/payload)
- **Headers**: Apenas `User-Agent` para identificação

### Exemplo de chamada:
```bash
curl -X POST http://localhost:8080/api/trigger/cam1
curl -X POST http://localhost:8080/api/trigger/cam2
```

## Logs

Todos os scripts geram logs detalhados:
- **Bash**: `simulation_log_YYYYMMDD_HHMMSS.txt`
- **Python**: `simulation_YYYYMMDD_HHMMSS.log`

## Exemplos de Uso por Cenário

### Teste rápido (intervalos reduzidos para 10% do tempo original):
```bash
SPEED_MULTIPLIER=0.1 ./simulate_triggers_compact.sh
```

### Simulação realística com precisão em segundos:
```bash
python3 trigger_simulator.py --speed 1.0 --url "http://localhost:8080/api/device/trigger"
```

### Desenvolvimento/Debug:
```bash
python3 trigger_simulator.py --dry-run
```

### Produção:
```bash
python3 trigger_simulator.py --non-interactive --url "http://production-server/api/triggers" --timeout 30
```

## Dependências

### Scripts Bash:
- `curl`
- `bc` (opcional, para cálculos de velocidade)

### Script Python:
- Python 3.6+
- `requests`

Para instalar dependências Python:
```bash
pip3 install requests
```

## Monitoramento

Todos os scripts fornecem:
- ✅ Indicadores de sucesso/falha
- ⏳ Tempo de espera atual
- 📊 Progresso da execução
- 📝 Logs detalhados para análise posterior