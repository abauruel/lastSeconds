# 🔄 Configuração de Inicialização Automática

## ✅ Após Reboot - TOTALMENTE AUTOMÁTICO

Nenhuma configuração manual necessária! O sistema está 100% automatizado.

### O que acontece automaticamente ao reiniciar:

#### 1. **Serviço better_seconds_record.service**
- ✅ **Status:** `enabled` (inicia automaticamente)
- ✅ **Recria diretórios RAM:** `/dev/shm/bts/stream1` e `/dev/shm/bts/stream2`
- ✅ **Carrega variáveis de ambiente:** `.env.ram`
- ✅ **Inicia FFmpeg:** Gravação em RAM automaticamente

```bash
# Verificar status
sudo systemctl status better_seconds_record.service

# Ver logs
sudo journalctl -u better_seconds_record.service -f
```

#### 2. **Sincronização RAM → Pendrive (Cron)**
- ✅ **Frequência:** A cada 1 minuto
- ✅ **Usuário:** pi (cron do usuário, persiste após reboot)
- ✅ **Move arquivos:** Com mais de 1 minuto para o pendrive

```bash
# Ver cron configurado
crontab -l

# Monitorar sincronização
tail -f /home/pi/app/logs/sync_ram.log
```

#### 3. **Variáveis de Ambiente (.env.ram)**
- ✅ **BTS_STREAM1_DIR:** `/dev/shm/bts/stream1`
- ✅ **BTS_STREAM2_DIR:** `/dev/shm/bts/stream2`
- ✅ **BTS_USE_RAM:** `1`

### Ordem de Inicialização:

```
1. Sistema inicia
   ↓
2. Systemd carrega better_seconds_record.service
   ↓
3. ExecStartPre: Cria /dev/shm/bts/stream1 e stream2
   ↓
4. EnvironmentFile: Carrega .env.ram
   ↓
5. ExecStart: Inicia Gunicorn + Capture3
   ↓
6. Capture3 inicia 2 processos FFmpeg (gravando em RAM)
   ↓
7. Cron (1 min depois): Sincroniza arquivos antigos para pendrive
```

### 🛠️ Comandos Úteis:

```bash
# Status completo do sistema
./monitor_ram.sh

# Verificar gravação em RAM
ls -lht /dev/shm/bts/stream1/ | head -5

# Ver uso de RAM
du -sh /dev/shm/bts

# Testar sincronização manual
/home/pi/app/sync_ram_to_pendrive.sh

# Reiniciar serviço (se necessário)
sudo systemctl restart better_seconds_record.service
```

### ⚠️ Importante:

- **Após reboot:** Primeiros arquivos aparecem em ~60-120 segundos
- **RAM sempre limpa:** Sincronização roda a cada 1 minuto
- **Sem perda de dados:** Janela de risco máxima de ~2 minutos
- **Logs persistentes:** `/home/pi/app/logs/` (não em RAM)

### 🔍 Validação Pós-Reboot:

```bash
# 1. Verificar serviço ativo
sudo systemctl is-active better_seconds_record.service
# Deve retornar: active

# 2. Verificar diretórios criados
ls -la /dev/shm/bts/
# Deve mostrar: stream1/ stream2/

# 3. Aguardar 65s e verificar gravação
sleep 65 && ls /dev/shm/bts/stream1/
# Deve mostrar arquivos .ts

# 4. Verificar cron funcionando
tail -5 /home/pi/app/logs/sync_ram.log
# Deve mostrar sincronizações recentes
```

### 📊 Configuração Atual:

| Parâmetro | Valor | Descrição |
|-----------|-------|-----------|
| Buffer RAM | 100 MB | ~5 minutos de vídeo |
| Retenção RAM | 1 minuto | Arquivos movidos após 1 min |
| Sincronização | 1 minuto | Cron executa a cada 1 min |
| Janela de risco | ~2 minutos | Perda máxima em caso de queda |
| Auto-start | ✅ Sim | Systemd enabled |

---

**Última atualização:** 2026-02-14  
**Status:** 🟢 Produção - Totalmente Automatizado
