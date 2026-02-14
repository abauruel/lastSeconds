# 📑 ÍNDICE: Investigação da Câmera 2 - Referência Rápida

## 🎯 Você é...

### 👤 Operador/Suporte (5-10 minutos)
Precisa resolver o problema ou entender o que aconteceu?

**Leia nesta ordem:**
1. [README_CAMERA_FIX.md](README_CAMERA_FIX.md) - Resumo visual (2 min)
2. [CAMERA_DETECTION_FIX.md](CAMERA_DETECTION_FIX.md) - Procedimento prático (5 min)
3. Execute: `bash test_camera_detection.sh` - Testar (2 min)

**Para troubleshooting:**
- Seção "Troubleshooting" em [CAMERA_DETECTION_FIX.md](CAMERA_DETECTION_FIX.md)

---

### 👨‍💼 Product Owner/Tech Lead (10-15 minutos)
Precisa entender o problema e o impacto?

**Leia nesta ordem:**
1. [README_CAMERA_FIX.md](README_CAMERA_FIX.md) - TL;DR (2 min)
2. [SOLUCAO_FINAL.md](SOLUCAO_FINAL.md) - Visão completa (10 min)
3. [CHECKLIST_INVESTIGACAO.md](CHECKLIST_INVESTIGACAO.md) - Status (3 min)

**Para apresentações:**
- Use [README_CAMERA_FIX.md](README_CAMERA_FIX.md) como base
- Gráficos em "Comparação Visual" e "O Que Aconteceu"

---

### 👨‍💻 Desenvolvedor (20-30 minutos)
Precisa entender o código e como foi resolvido?

**Leia nesta ordem:**
1. [INVESTIGACAO_SUMARIO.md](INVESTIGACAO_SUMARIO.md) - Resumo técnico (5 min)
2. [docs/CAMERA_DEVICE_ENUMERATION.md](docs/CAMERA_DEVICE_ENUMERATION.md) - Análise profunda (15 min)
3. [SOLUCAO_FINAL.md](SOLUCAO_FINAL.md) - Implementação (10 min)

**Arquivos de código modificados:**
- [ffmpeg_manager.py](ffmpeg_manager.py#L48-L115) - Função `detect_usb_cameras()`
- [routes/status_routes.py](routes/status_routes.py#L145-L189) - Rota `/health`

**Para código review:**
- Foco em linhas 48-115 em `ffmpeg_manager.py`
- Foco em linhas 145-189 em `routes/status_routes.py`

---

### 🔧 Engenheiro DevOps/SRE (15-20 minutos)
Precisa validar a solução antes de deploy?

**Leia nesta ordem:**
1. [CHECKLIST_INVESTIGACAO.md](CHECKLIST_INVESTIGACAO.md) - Status (5 min)
2. [CAMERA_DETECTION_FIX.md](CAMERA_DETECTION_FIX.md) - Procedimento (5 min)

**Scripts para executar:**
```bash
# Teste rápido
bash test_camera_detection.sh

# Diagnóstico completo
python3 diagnose_camera_detection.py

# Validação com hotplug
# 1. Desconecte câmera
# 2. Aguarde 10s
# 3. Reconecte câmera
# 4. Execute novamente os testes
```

**Checklist pré-deploy:**
- [ ] Ambas câmeras detectadas: `curl http://localhost:5000/health | jq '.cameras.count'`
- [ ] Retorna `2`
- [ ] Teste com hotplug conforme acima

---

## 📚 Arquivos por Tipo

### 📖 Documentação Principal

| Arquivo | Tamanho | Público-Alvo | Tempo |
|---------|---------|--------------|-------|
| [README_CAMERA_FIX.md](README_CAMERA_FIX.md) | 7.9K | Todos | 5 min |
| [SOLUCAO_FINAL.md](SOLUCAO_FINAL.md) | 8.6K | Técnico | 10 min |
| [CAMERA_DETECTION_FIX.md](CAMERA_DETECTION_FIX.md) | 7.3K | Operacional | 8 min |
| [INVESTIGACAO_SUMARIO.md](INVESTIGACAO_SUMARIO.md) | 6.3K | Técnico | 8 min |
| [CHECKLIST_INVESTIGACAO.md](CHECKLIST_INVESTIGACAO.md) | 8.6K | Gestor | 5 min |
| [docs/CAMERA_DEVICE_ENUMERATION.md](docs/CAMERA_DEVICE_ENUMERATION.md) | ? | Técnico/Arquitetura | 20 min |

### 🔧 Scripts de Teste

| Script | Tipo | Uso |
|--------|------|-----|
| [test_camera_detection.sh](test_camera_detection.sh) | bash | Testes rápidos |
| [diagnose_camera_detection.py](diagnose_camera_detection.py) | python3 | Diagnóstico completo |

### ✏️ Código Modificado

| Arquivo | Linha | O Que Mudou |
|---------|-------|-----------|
| [ffmpeg_manager.py](ffmpeg_manager.py#L48) | 48-115 | `detect_usb_cameras()` reescrita |
| [routes/status_routes.py](routes/status_routes.py#L145) | 145-189 | Verificação de câmeras atualizada |
| [README.md](README.md) | ~35 | Links adicionados |

---

## 🚀 Começar Agora

### ⚡ Super Rápido (2 minutos)
```bash
# Ler o resumo
cat README_CAMERA_FIX.md

# Testar
bash test_camera_detection.sh
```

### ⏱️ Rápido (5 minutos)
```bash
# Ler o resumo executivo
cat README_CAMERA_FIX.md

# Ler o procedimento
cat CAMERA_DETECTION_FIX.md

# Testar
python3 diagnose_camera_detection.py
```

### 📖 Completo (20+ minutos)
```bash
# Ler tudo em ordem
cat README_CAMERA_FIX.md
cat INVESTIGACAO_SUMARIO.md
cat SOLUCAO_FINAL.md
cat docs/CAMERA_DEVICE_ENUMERATION.md

# Executar testes
bash test_camera_detection.sh
python3 diagnose_camera_detection.py

# Review do código
less ffmpeg_manager.py  # Linha 48-115
less routes/status_routes.py  # Linha 145-189
```

---

## 🎯 Perguntas Frequentes

### ❓ "Qual arquivo devo ler primeiro?"
**Resposta:** [README_CAMERA_FIX.md](README_CAMERA_FIX.md) (2 minutos)

### ❓ "Como testar se a solução funciona?"
**Resposta:** 
```bash
bash test_camera_detection.sh
```

### ❓ "Por que a câmera 2 sumiu?"
**Resposta:** Linux enumera dispositivos dinamicamente. Leia [CAMERA_DETECTION_FIX.md](CAMERA_DETECTION_FIX.md)#Diagnóstico

### ❓ "O que foi mudado no código?"
**Resposta:** Veja [SOLUCAO_FINAL.md](SOLUCAO_FINAL.md)#Solução Implementada

### ❓ "Preciso fazer algo?"
**Resposta:** 
- Se é **operador**: Execute `test_camera_detection.sh`
- Se é **desenvolvedor**: Review em `ffmpeg_manager.py` linha 48-115
- Se é **SRE**: Execute checklist em [CHECKLIST_INVESTIGACAO.md](CHECKLIST_INVESTIGACAO.md)

---

## 📊 Estatísticas da Investigação

```
Documentos criados:        6
Exemplos de código:        4
Scripts criados:           2
Linhas de código mudadas:  ~150
Tempo de investigação:     Completo
Status:                    ✅ RESOLVIDO
```

---

## 🔗 Links Rápidos

### Ler Documentação
- [Resumo Executivo](README_CAMERA_FIX.md)
- [Guia Prático](CAMERA_DETECTION_FIX.md)
- [Análise Técnica](docs/CAMERA_DEVICE_ENUMERATION.md)
- [Solução Implementada](SOLUCAO_FINAL.md)

### Testar
```bash
bash test_camera_detection.sh
python3 diagnose_camera_detection.py
```

### Ver Código
- [ffmpeg_manager.py](ffmpeg_manager.py#L48)
- [routes/status_routes.py](routes/status_routes.py#L145)

---

## ✨ Próximas Ações

- [ ] Ler documentação apropriada para sua função
- [ ] Executar `test_camera_detection.sh` ou `diagnose_camera_detection.py`
- [ ] Se for dev: review do código
- [ ] Se for SRE: validar checklist
- [ ] Se for suporte: guardar [CAMERA_DETECTION_FIX.md](CAMERA_DETECTION_FIX.md) para referência

---

**Última atualização:** 14 de Fevereiro de 2026  
**Status:** ✅ PRONTO PARA USAR  
**Versão:** 1.0
