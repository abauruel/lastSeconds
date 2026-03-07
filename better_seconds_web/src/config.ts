// Configuração centralizada para URLs do servidor
// Use variáveis de ambiente ou detecção automática do hostname

// Obtém o hostname do servidor - usa variável de ambiente ou detecta automaticamente
const getServerHost = (): string => {
  // Primeira opção: usa variável de ambiente se configurada
  const envHost = import.meta.env.VITE_SERVER_HOST;
  if (envHost && envHost !== 'bettersecond.local') {
    return envHost;
  }

  // Segunda opção: usa o hostname atual (útil quando servidor e frontend estão na mesma máquina)
  // ATIVADO: Detecta automaticamente o hostname do navegador
  return window.location.hostname;

  // Terceira opção: fallback para bettersecond.local (comentado)
  // return 'bettersecond.local';
};

export const SERVER_HOST = getServerHost();
export const MEDIAMTX_PORT = import.meta.env.VITE_MEDIAMTX_PORT || '8888';
export const BACKEND_PORT = import.meta.env.VITE_BACKEND_PORT || '5000';
export const FILES_PORT = import.meta.env.VITE_FILES_PORT || '3333';

// URLs construídas
export const MEDIAMTX_URL = `http://${SERVER_HOST}:${MEDIAMTX_PORT}`;
export const BACKEND_URL = `http://${SERVER_HOST}:${BACKEND_PORT}`;
export const FILES_URL = `http://${SERVER_HOST}:${FILES_PORT}`;


// URLs dos streams HLS servidos pelo MediaMTX
// O MediaMTX converte RTSP -> HLS automaticamente nos paths configurados
export const STREAM1_URL = `${MEDIAMTX_URL}/stream1/index.m3u8`;
export const STREAM2_URL = `${MEDIAMTX_URL}/stream2/index.m3u8`;
