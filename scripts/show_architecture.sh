#!/bin/bash
# Visualização da arquitetura de gravação de 2 câmeras

cat << 'EOF'
╔══════════════════════════════════════════════════════════════════════════╗
║         ARQUITETURA DE GRAVAÇÃO SIMULTÂNEA - 2 CÂMERAS                  ║
╚══════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────┐
│                          SEPARAÇÃO DE RECURSOS                           │
└──────────────────────────────────────────────────────────────────────────┘

  CÂMERA 0                                      CÂMERA 1
  ════════                                      ════════
     │                                              │
     ├─ Processo FFmpeg PID: XXXX                  ├─ Processo FFmpeg PID: YYYY
     │                                              │
     ├─ Input: RTSP Stream 0                       ├─ Input: RTSP Stream 1
     │                                              │
     ├─ Diretório: /home/pi/recordings/stream1/    ├─ Diretório: /home/pi/recordings/stream2/
     │   │                                          │   │
     │   ├─ video0_20260404_070000.ts              │   ├─ video2_20260404_070000.ts
     │   ├─ video0_20260404_070300.ts              │   ├─ video2_20260404_070300.ts
     │   ├─ video0_20260404_070600.ts              │   ├─ video2_20260404_070600.ts
     │   └─ ...                                     │   └─ ...
     │                                              │
     ├─ Log: /home/pi/recordings/ffmpeg_device0.log
     │                                              ├─ Log: /home/pi/recordings/ffmpeg_device2.log
     │                                              │
     ├─ RTMP: rtmp://localhost/live/stream1        ├─ RTMP: rtmp://localhost/live/stream2
     │                                              │
     └─ Bitrate: ~2 Mbps (~0.25 MB/s)              └─ Bitrate: ~2 Mbps (~0.25 MB/s)


┌──────────────────────────────────────────────────────────────────────────┐
│                      RECURSOS COMPARTILHADOS                             │
└──────────────────────────────────────────────────────────────────────────┘

  📁 Banco de Dados (SQLite com WAL)
     └─ /home/pi/recordings/recordings.db
        ├─ Lock automático do SQLite
        └─ Proteção: Write-Ahead Logging (WAL)

  📝 Arquivo de Timestamps (Eventos)
     └─ /home/pi/recordings/streams/timestamps/YYYYMMDD.txt
        ├─ Proteção: threading.Lock() + fcntl.flock()
        └─ Escrita atômica com flush explícito

  💾 microSD (/home/pi/)
     ├─ Capacidade I/O: 26.6 MB/s
     ├─ Uso total: ~0.5 MB/s (2 câmeras)
     └─ Margem: 98% disponível


┌──────────────────────────────────────────────────────────────────────────┐
│                       FLUXO DE GRAVAÇÃO                                  │
└──────────────────────────────────────────────────────────────────────────┘

  CÂMERA 0                          microSD                        CÂMERA 1
  ┌────────┐                    ╔═══════════╗                    ┌────────┐
  │ RTSP   │─────┐             ║           ║             ┌───────│ RTSP   │
  │ Stream │     │             ║  Ext4 FS  ║             │       │ Stream │
  └────────┘     │             ║           ║             │       └────────┘
                 │             ║  26.6MB/s ║             │
                 ▼             ║           ║             ▼
         ┌──────────────┐     ║           ║     ┌──────────────┐
         │   FFmpeg 0   │────▶║  stream1/ ║◀────│   FFmpeg 1   │
         │   PID XXXX   │     ║  stream2/ ║     │   PID YYYY   │
         └──────────────┘     ║           ║     └──────────────┘
                 │             ║  logs/    ║             │
                 │             ║  streams/ ║             │
                 │             ║  db/      ║             │
                 │             ╚═══════════╝             │
                 │                                       │
                 ▼                                       ▼
         segmento 3 min                          segmento 3 min
         (0.25 MB/s)                             (0.25 MB/s)


┌──────────────────────────────────────────────────────────────────────────┐
│                   PROTEÇÕES CONTRA RACE CONDITIONS                       │
└──────────────────────────────────────────────────────────────────────────┘

  ✅ Arquivos de Vídeo
     • Prefixos diferentes: video0_ vs video2_
     • Diretórios separados: stream1/ vs stream2/
     • Processos independentes
     • Risco: NENHUM

  ✅ Logs FFmpeg
     • Arquivos separados: ffmpeg_device0.log vs ffmpeg_device2.log
     • Modo append atômico
     • Risco: NENHUM

  ✅ Arquivo de Timestamps
     • Thread Lock (threading.Lock)
     • File Lock (fcntl.flock LOCK_EX)
     • Flush explícito
     • Risco: PROTEGIDO

  ✅ Banco de Dados SQLite
     • WAL mode habilitado
     • Lock interno do SQLite
     • Transações ACID
     • Risco: PROTEGIDO

  ✅ Sistema de Arquivos
     • Ext4 suporta escrita concorrente
     • Kernel gerencia cache de I/O
     • Operações atômicas
     • Risco: NENHUM


┌──────────────────────────────────────────────────────────────────────────┐
│                       CAPACIDADE vs DEMANDA                              │
└──────────────────────────────────────────────────────────────────────────┘

  Performance do microSD:
  ╔════════════════════════════════════════════════════════╗
  ║ Velocidade de escrita medida: 26.6 MB/s               ║
  ╚════════════════════════════════════════════════════════╝

  Demanda de gravação:
  ┌────────────────────────────────────────────────────────┐
  │ Câmera 0:  0.25 MB/s  ███░░░░░░░░░░░░░░░░░░░░  (0.9%) │
  │ Câmera 1:  0.25 MB/s  ███░░░░░░░░░░░░░░░░░░░░  (0.9%) │
  │ ─────────────────────────────────────────────────────  │
  │ Total:     0.50 MB/s  ██████░░░░░░░░░░░░░░░░  (1.9%) │
  │                                                        │
  │ Margem:   26.10 MB/s  ███████████████████████ (98.1%) │
  └────────────────────────────────────────────────────────┘

  Conclusão: ✅ CAPACIDADE MAIS QUE SUFICIENTE


┌──────────────────────────────────────────────────────────────────────────┐
│                          LINHA DO TEMPO                                  │
└──────────────────────────────────────────────────────────────────────────┘

  Tempo →  0s      30s     60s     90s     120s    150s    180s    210s
           │       │       │       │       │       │       │       │
  Cam 0:   ├───────────────────────────────────────────────┤       ├──...
           │     video0_070000.ts (3 min)          │   video0_070300.ts
           │                                       │
  Cam 1:   ├───────────────────────────────────────────────┤       ├──...
           │     video2_070000.ts (3 min)          │   video2_070300.ts

  • Segmentos sincronizados no tempo (segment_atclocktime=1)
  • Mas escritos em arquivos/diretórios diferentes
  • Sem sobreposição ou conflito


┌──────────────────────────────────────────────────────────────────────────┐
│                    RECOMENDAÇÕES DE HARDWARE                             │
└──────────────────────────────────────────────────────────────────────────┘

  microSD Recomendado:
  ✅ Classe: 10 ou superior
  ✅ UHS: U3 (30 MB/s mínimo)
  ✅ Application: A1 ou A2
  ✅ Capacidade: 64 GB ou maior
  ✅ Marcas: SanDisk Extreme, Samsung EVO Plus, Kingston Canvas

  Exemplos:
  • SanDisk Extreme 64GB (U3, A2, 160MB/s leitura, 60MB/s escrita)
  • Samsung EVO Plus 64GB (U3, A2, 130MB/s leitura, 60MB/s escrita)
  • Kingston Canvas Go Plus 64GB (U3, V30, A2, 170MB/s leitura, 70MB/s escrita)


┌──────────────────────────────────────────────────────────────────────────┐
│                         TESTES DISPONÍVEIS                               │
└──────────────────────────────────────────────────────────────────────────┘

  1. Teste completo de gravação simultânea (5 minutos):
     $ ./scripts/test_dual_camera_recording.sh

  2. Teste estendido (30 minutos):
     $ ./scripts/test_dual_camera_recording.sh 1800

  3. Verificação de saúde do sistema:
     $ ./utils/check_health.sh

  4. Setup inicial do microSD:
     $ ./scripts/setup_microsd_storage.sh


╔══════════════════════════════════════════════════════════════════════════╗
║                         CONCLUSÃO FINAL                                  ║
╚══════════════════════════════════════════════════════════════════════════╝

  Status: ✅ CONFIGURAÇÃO APROVADA

  • Nenhum risco de race condition direta
  • Capacidade de I/O mais que adequada (98% de margem)
  • Proteções implementadas em recursos compartilhados
  • Sistema de arquivos Ext4 robusto para escrita concorrente
  • Segmentos de 3 minutos otimizam performance

  O sistema está bem projetado para operar 2 câmeras simultaneamente
  gravando no microSD sem problemas de conflito ou corrupção de dados.

EOF
