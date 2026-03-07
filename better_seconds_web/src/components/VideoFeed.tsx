import { useRef, useEffect, useState } from "react";
import videojs from "video.js";
import type Player from "video.js/dist/types/player";
import "video.js/dist/video-js.css";

interface VideoFeedProps {
  src: string;
}

const VideoFeed: React.FC<VideoFeedProps> = ({ src }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const playerRef = useRef<Player | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Garante que o elemento está no DOM antes de inicializar
    if (!videoRef.current) return;

    const videoElement = videoRef.current;

    // Adiciona um pequeno delay para garantir que o elemento está completamente renderizado
    const timer = setTimeout(() => {
      if (!playerRef.current && videoElement.parentElement) {
        try {
          const player = videojs(videoElement, {
            autoplay: true,
            controls: true,
            preload: "auto",
            responsive: true,
            fluid: false,
            liveui: true,
            muted: true, // Inicia mudo para permitir autoplay
            techOrder: ["html5"],
            html5: {
              vhs: {
                overrideNative: true,
                enableLowInitialPlaylist: true,
              },
              nativeVideoTracks: false,
              nativeAudioTracks: false,
              nativeTextTracks: false
            }
          });

          playerRef.current = player;

          player.ready(() => {
            console.log("player is ready");
            setIsReady(true);

            player.src({
              src: src,
              type: "application/x-mpegURL"
            });

            // Tratamento de erros
            player.on('error', () => {
              const playerError = player.error();
              console.error('Video.js error:', playerError);

              if (playerError) {
                // Erro de decodificação (geralmente codec não suportado)
                if (playerError.code === 3) {
                  setError('⚠️ Codec H265/HEVC não suportado neste navegador. Configure a câmera para usar H264.');
                  console.warn('HEVC não suportado. Configure a câmera para usar codec H264 para melhor compatibilidade.');
                }
                // Erro de rede
                else if (playerError.code === 2) {
                  setError('❌ Erro de rede. Verifique se o MediaMTX está rodando.');
                  // Tenta reconectar
                  setTimeout(() => {
                    setError(null);
                    player.src({
                      src: src,
                      type: "application/x-mpegURL"
                    });
                    player.load();
                  }, 3000);
                }
                // Erro de source não encontrada
                else if (playerError.code === 4) {
                  setError('❌ Stream não encontrado. Verifique a configuração do MediaMTX.');
                }
              }
            });

            // Quando o vídeo carregar com sucesso, limpa o erro
            player.on('loadeddata', () => {
              setError(null);
            });
          });
        } catch (error) {
          console.error('Erro ao inicializar Video.js:', error);
          setError('❌ Erro ao inicializar player');
        }
      }
    }, 100);

    return () => {
      clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    // Atualiza a source quando a URL mudar
    if (playerRef.current && isReady && src) {
      try {
        setError(null);
        playerRef.current.src({
          src: src,
          type: "application/x-mpegURL"
        });
      } catch (error) {
        console.error('Erro ao atualizar source:', error);
      }
    }
  }, [src, isReady]);

  useEffect(() => {
    return () => {
      if (playerRef.current) {
        try {
          playerRef.current.dispose();
        } catch (error) {
          console.error('Erro ao destruir player:', error);
        }
        playerRef.current = null;
      }
    };
  }, []);

  return (
    <div className="relative scale-x-100">
      <div data-vjs-player>
        <video
          className='video-js vjs-default-skin'
          ref={videoRef}
          width={384}
          height={"auto"}
        />
      </div>
      {error && (
        <div className="absolute top-0 left-0 right-0 bg-red-500/90 text-white text-xs p-2 rounded">
          {error}
        </div>
      )}
    </div>
  );
};

export default VideoFeed;