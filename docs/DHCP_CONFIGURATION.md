# Configuração DHCP para Câmeras IP

## 📋 Sumário

Este documento descreve a configuração do servidor DHCP dedicado para a interface cabeada `end0`, utilizado para gerenciar endereços IP das câmeras IP conectadas ao sistema.

## 🎯 Objetivo

Fornecer endereços IP dinâmicos e reservas estáticas para câmeras IP conectadas via switch na rede 192.168.0.0/24, garantindo conectividade confiável e IPs fixos para cada câmera.

## 🔍 Problema Inicial

### Cenário
- **Câmera 1**: IP 10.10.0.210 - Conectividade OK ✅
- **Câmera 2**: IP 10.10.0.209 - Sem conectividade ❌
- **Raspberry Pi**: Interface end0 com IP 10.10.0.10
- **Infraestrutura**: Ambas câmeras e Raspberry conectados via switch com link físico UP

### Diagnóstico
Após reset de fábrica da câmera 2, foi identificado que:
- A câmera voltou para configuração de fábrica na rede 192.168.0.x
- A câmera estava configurada para obter IP via DHCP
- Não havia servidor DHCP disponível na rede 192.168.0.x
- O Raspberry Pi já possuía um servidor DHCP ativo para o hotspot WiFi (rede 10.42.0.x)

## 🏗️ Solução Implementada

### 1. Configuração de IP Secundário

Adicionado IP secundário na interface `end0` para permitir comunicação com câmeras em diferentes redes:

```bash
# IP secundário temporário
sudo ip addr add 192.168.0.100/24 dev end0

# Verificar configuração
ip addr show end0
```

**Resultado:**
```
inet 10.10.0.10/24 brd 10.10.0.255 scope global end0
inet 192.168.0.100/24 scope global end0
```

### 2. Servidor DHCP Dedicado

Configurado servidor DHCP usando `dnsmasq` isolado para a interface `end0`, sem conflitar com o servidor DHCP existente do hotspot WiFi.

#### Arquivo de Configuração: `/etc/dnsmasq.d/end0.conf`

```bash
# Configuração DHCP para interface end0 (câmeras IP)
# Serviço dedicado para a rede cabeada 192.168.0.0/24

# Interface específica
interface=end0
bind-interfaces

# Não atuar como servidor DNS, apenas DHCP
port=0

# Configuração DHCP
dhcp-range=192.168.0.50,192.168.0.150,12h
dhcp-option=option:router,192.168.0.100
dhcp-option=option:dns-server,8.8.8.8,8.8.4.4

# Reservas DHCP (IPs fixos por MAC)
dhcp-host=5a:5a:00:c6:7e:e9,192.168.0.209,IPCAM-2,infinite
dhcp-host=f0:00:06:0b:27:47,192.168.0.210,IPCAM-1,infinite

# Lease file
dhcp-leasefile=/var/lib/dnsmasq/dnsmasq-end0.leases

# Log
log-dhcp
log-facility=/var/log/dnsmasq-end0.log

# Configurações adicionais
dhcp-authoritative
```

### 3. Serviço Systemd

Criado serviço systemd para inicialização automática do servidor DHCP.

#### Arquivo: `/etc/systemd/system/dnsmasq-end0.service`

```ini
[Unit]
Description=DHCP server for end0 interface (IP Cameras)
After=network.target
Wants=network.target

[Service]
Type=forking
PIDFile=/var/run/dnsmasq-end0.pid
ExecStartPre=/bin/sleep 5
ExecStart=/usr/sbin/dnsmasq --conf-file=/etc/dnsmasq.d/end0.conf --pid-file=/var/run/dnsmasq-end0.pid
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## 📊 Configuração da Rede

### Arquitetura de Rede

```
┌─────────────────────────────────────────┐
│         Raspberry Pi 4                  │
│                                         │
│  end0: 10.10.0.10/24                   │
│        192.168.0.100/24                │
│                                         │
│  wlan0: 10.42.0.1/24 (Hotspot)        │
└──────────────┬──────────────────────────┘
               │
               │ Ethernet
               │
        ┌──────┴──────┐
        │   Switch    │
        └──────┬──────┘
               │
        ┌──────┴──────────┐
        │                 │
   ┌────┴────┐      ┌────┴────┐
   │ Câmera 1│      │ Câmera 2│
   │192.168  │      │192.168  │
   │ 0.210   │      │ 0.209   │
   └─────────┘      └─────────┘
```

### Tabela de Endereços IP

| Dispositivo | Interface | IP Principal | IP Secundário | Rede |
|-------------|-----------|--------------|---------------|------|
| Raspberry Pi | end0 | 10.10.0.10/24 | 192.168.0.100/24 | Câmeras |
| Raspberry Pi | wlan0 | 10.42.0.1/24 | - | Hotspot WiFi |
| Câmera 1 | eth0 | 192.168.0.210/24 | - | DHCP Reservado |
| Câmera 2 | eth0 | 192.168.0.209/24 | - | DHCP Reservado |

### Configuração DHCP

| Parâmetro | Valor |
|-----------|-------|
| Rede | 192.168.0.0/24 |
| Faixa DHCP | 192.168.0.50 - 192.168.0.150 |
| Gateway | 192.168.0.100 |
| DNS | 8.8.8.8, 8.8.4.4 |
| Lease Time | 12 horas |
| Interface | end0 |

### Reservas DHCP (IPs Fixos)

| Câmera | MAC Address | IP Reservado | Hostname | Lease |
|--------|-------------|--------------|----------|-------|
| Câmera 1 | f0:00:06:0b:27:47 | 192.168.0.210 | IPCAM-1 | Infinito |
| Câmera 2 | 5a:5a:00:c6:7e:e9 | 192.168.0.209 | IPCAM-2 | Infinito |

## 🚀 Instalação e Configuração

### Passo 1: Adicionar IP Secundário na Interface

```bash
# Adicionar IP secundário (temporário)
sudo ip addr add 192.168.0.100/24 dev end0

# Verificar
ip addr show end0
```

### Passo 2: Criar Arquivo de Configuração DHCP

```bash
# Criar diretório se não existir
sudo mkdir -p /etc/dnsmasq.d
sudo mkdir -p /var/lib/dnsmasq

# Criar arquivo de configuração
sudo nano /etc/dnsmasq.d/end0.conf
```

Cole a configuração mostrada na seção 2 acima.

### Passo 3: Criar Serviço Systemd

```bash
# Criar arquivo do serviço
sudo nano /etc/systemd/system/dnsmasq-end0.service
```

Cole a configuração do serviço mostrada na seção 3 acima.

### Passo 4: Habilitar e Iniciar o Serviço

```bash
# Recarregar daemon do systemd
sudo systemctl daemon-reload

# Habilitar serviço para iniciar no boot
sudo systemctl enable dnsmasq-end0.service

# Iniciar serviço
sudo systemctl start dnsmasq-end0.service

# Verificar status
sudo systemctl status dnsmasq-end0.service
```

### Passo 5: Iniciar Servidor DHCP Manualmente (Alternativa)

```bash
# Iniciar dnsmasq manualmente
sudo dnsmasq --conf-file=/etc/dnsmasq.d/end0.conf --pid-file=/var/run/dnsmasq-end0.pid

# Verificar processo
ps aux | grep dnsmasq | grep end0
```

## 🔧 Comandos Úteis

### Gerenciamento do Serviço

```bash
# Verificar status
sudo systemctl status dnsmasq-end0.service

# Iniciar serviço
sudo systemctl start dnsmasq-end0.service

# Parar serviço
sudo systemctl stop dnsmasq-end0.service

# Reiniciar serviço
sudo systemctl restart dnsmasq-end0.service

# Recarregar configuração sem derrubar conexões
sudo kill -HUP $(cat /var/run/dnsmasq-end0.pid)

# Verificar logs do serviço
sudo journalctl -u dnsmasq-end0.service -f
```

### Monitoramento

```bash
# Ver processos DHCP rodando
ps aux | grep dnsmasq

# Ver leases DHCP ativos
cat /var/lib/dnsmasq/dnsmasq-end0.leases

# Monitorar log DHCP em tempo real
sudo tail -f /var/log/dnsmasq-end0.log

# Ver últimos logs
sudo tail -50 /var/log/dnsmasq-end0.log

# Ver portas UDP em uso
sudo netstat -ulnp | grep dnsmasq
# ou
sudo ss -ulnp | grep dnsmasq

# Ver tabela ARP
ip neigh show

# Ver rotas
ip route show
```

### Teste de Conectividade

```bash
# Ping nas câmeras
ping -c 4 192.168.0.209
ping -c 4 192.168.0.210

# Verificar resolução ARP
ip neigh show | grep 192.168.0

# Scan de rede
sudo nmap -sn 192.168.0.0/24

# Testar configuração
sudo dnsmasq --conf-file=/etc/dnsmasq.d/end0.conf --test
```

### Limpeza e Reset

```bash
# Limpar cache ARP
sudo ip neigh flush dev end0

# Limpar leases DHCP
sudo rm /var/lib/dnsmasq/dnsmasq-end0.leases
sudo touch /var/lib/dnsmasq/dnsmasq-end0.leases
sudo kill -HUP $(cat /var/run/dnsmasq-end0.pid)

# Remover IP secundário
sudo ip addr del 192.168.0.100/24 dev end0
```

## 🔍 Troubleshooting

### Problema: Câmera não recebe IP

**Sintomas:**
- Câmera não aparece na rede
- Sem lease no arquivo de leases

**Soluções:**
```bash
# Verificar se o servidor DHCP está rodando
ps aux | grep dnsmasq | grep end0

# Verificar log para erros
sudo tail -50 /var/log/dnsmasq-end0.log

# Verificar configuração da interface
ip addr show end0

# Verificar se a porta DHCP está aberta
sudo ss -ulnp | grep :67

# Reiniciar servidor DHCP
sudo kill $(cat /var/run/dnsmasq-end0.pid)
sudo dnsmasq --conf-file=/etc/dnsmasq.d/end0.conf --pid-file=/var/run/dnsmasq-end0.pid
```

### Problema: Conflito com outro servidor DHCP

**Sintomas:**
- Erro "address already in use"
- Múltiplos processos dnsmasq

**Soluções:**
```bash
# Verificar todos os processos dnsmasq
ps aux | grep dnsmasq

# Verificar serviço dnsmasq principal
sudo systemctl status dnsmasq

# Parar serviço principal se necessário
sudo systemctl stop dnsmasq
sudo systemctl disable dnsmasq

# Verificar portas em uso
sudo ss -ulnp | grep :67
```

### Problema: Câmera não pega IP reservado

**Sintomas:**
- Câmera recebe IP da faixa dinâmica
- Reserva não funciona

**Soluções:**
```bash
# Verificar MAC address correto
ip neigh show | grep 192.168.0

# Verificar configuração de reserva
sudo cat /etc/dnsmasq.d/end0.conf | grep dhcp-host

# Limpar leases antigos
sudo rm /var/lib/dnsmasq/dnsmasq-end0.leases
sudo touch /var/lib/dnsmasq/dnsmasq-end0.leases
sudo kill -HUP $(cat /var/run/dnsmasq-end0.pid)

# Reiniciar câmera para forçar novo DHCP request
```

### Problema: Servidor DHCP não inicia no boot

**Sintomas:**
- Serviço inativo após reboot
- Câmeras sem IP após reinicialização

**Soluções:**
```bash
# Verificar status do serviço
sudo systemctl status dnsmasq-end0.service

# Verificar se está habilitado
sudo systemctl is-enabled dnsmasq-end0.service

# Habilitar se necessário
sudo systemctl enable dnsmasq-end0.service

# Ver logs de inicialização
sudo journalctl -u dnsmasq-end0.service -b

# Verificar dependências
systemctl list-dependencies dnsmasq-end0.service
```

## 📝 Adicionando Novas Reservas DHCP

Para adicionar uma nova câmera com IP fixo:

### Passo 1: Descobrir MAC Address

```bash
# Aguardar câmera obter IP da faixa dinâmica
sudo tail -f /var/log/dnsmasq-end0.log

# Ou verificar leases
cat /var/lib/dnsmasq/dnsmasq-end0.leases

# Ou via ARP
ip neigh show | grep 192.168.0
```

### Passo 2: Editar Configuração

```bash
sudo nano /etc/dnsmasq.d/end0.conf
```

Adicionar linha na seção "Reservas DHCP":
```bash
dhcp-host=XX:XX:XX:XX:XX:XX,192.168.0.XXX,HOSTNAME,infinite
```

### Passo 3: Recarregar Configuração

```bash
# Recarregar sem derrubar conexões
sudo kill -HUP $(cat /var/run/dnsmasq-end0.pid)

# Ou reiniciar serviço
sudo systemctl restart dnsmasq-end0.service
```

### Passo 4: Forçar Renovação na Câmera

- Reiniciar câmera via interface web, ou
- Desligar/ligar câmera fisicamente

## 🔐 Segurança

### Considerações

1. **Isolamento de Rede**: O servidor DHCP está isolado na interface `end0`, não afetando outras interfaces
2. **DHCP Authoritative**: Configurado para responder rapidamente a requests, evitando conflitos
3. **Logs Habilitados**: Todos os eventos DHCP são registrados para auditoria
4. **Reservas Estáticas**: IPs fixos garantem previsibilidade e facilitam regras de firewall

### Recomendações

- Manter backup do arquivo de configuração `/etc/dnsmasq.d/end0.conf`
- Monitorar logs regularmente para detectar atividades suspeitas
- Documentar novos dispositivos adicionados à rede
- Revisar faixa DHCP periodicamente para evitar esgotamento de IPs

## 📚 Referências

- [dnsmasq Documentation](http://www.thekelleys.org.uk/dnsmasq/doc.html)
- [dnsmasq Man Page](https://linux.die.net/man/8/dnsmasq)
- [Raspberry Pi Network Configuration](https://www.raspberrypi.com/documentation/computers/configuration.html#networking)

### Documentação Relacionada

- [Detecção de Câmeras](CAMERA_DEVICE_ENUMERATION.md) - Como o sistema detecta câmeras conectadas
- [Acesso às Câmeras](ACESSO_CAMERAS.md) - Informações de acesso às câmeras via rede
- [Diagnóstico de Streams](DIAGNOSTICO_STREAMS.md) - Troubleshooting de problemas de streaming

## 📄 Histórico de Alterações

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-03-20 | 1.0 | Configuração inicial do servidor DHCP para câmeras IP |
| 2026-03-20 | 1.1 | Adicionadas reservas para câmera 1 (192.168.0.210) e câmera 2 (192.168.0.209) |

---

**Autor:** Configuração do Sistema lastSeconds  
**Data:** 20 de Março de 2026  
**Versão:** 1.1
