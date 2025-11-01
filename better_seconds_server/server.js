// server.js
const express = require("express");
const fs = require("fs");
const path = require("path");
const cors = require("cors")

const app = express();


app.use(cors())

// Ajusta para timezone -3 (horário de Brasília)
const now = new Date();
const brazilTime = new Date(now.getTime() - (3 * 60 * 60 * 1000));
const currentDate = brazilTime.toISOString().slice(0, 10).replace(/-/g, '');
console.log(currentDate)
const videosDir = path.join(__dirname, "..", "..", "app", "recordings", "streams", currentDate);


app.use("/thumbnails", express.static(videosDir));


// Rota para listar todos os vídeos
app.get("/api/videos", (req, res) => {
  fs.readdir(videosDir, (err, files) => {
    if (err) {
      return res.status(500).json({ error: "Erro ao ler o diretório" });
    }

    const videos = files
      .filter((file) => file.endsWith(".mp4")) // filtra apenas arquivos de vídeo
      .map((file) => (
        {
          name: file,
          thumbnail: `/thumbnails/${path.basename(file, ".mp4")}.mp4.jpeg`, // thumb precisa estar no formato <nome do video>.jpg
          url: `/api/download/${file}`,
        }))

    const extractDateFromFilename = (filename) => {
      const regex = /(\d{8}_\d{6})/;
      const match = filename.match(regex);
      return match ? match[1] : null;
    };

    const videosOrdered = videos.sort((a, b) => {
      const dateA = extractDateFromFilename(a.name);
      const dateB = extractDateFromFilename(b.name);
      return dateB.localeCompare(dateA);
    });

    res.json(videosOrdered);
  });
});

// Rota para download do vídeo
app.get("/api/download/:filename", (req, res) => {
  const filePath = path.join(videosDir, req.params.filename);
  res.download(filePath);
});

app.delete("/api/download/:filename", (req, res) => {
  const filename = req.params.filename;
  const filePath = path.join(videosDir, req.params.filename);
  const thumbnailPath = `${filePath}.jpeg`;

  // Verificar se o arquivo existe antes de tentar deletar
  fs.access(filePath, fs.constants.F_OK, (accessErr) => {
    if (accessErr) {
      console.error(`Arquivo ${filename} não encontrado:`, accessErr);
      return res.status(404).json({ error: "Arquivo não encontrado" });
    }

    // Deletar o arquivo de vídeo primeiro
    fs.unlink(filePath, (err) => {
      if (err) {
        console.error(`Erro ao deletar o arquivo ${filename}:`, err);
        if (err.code === 'EACCES') {
          return res.status(403).json({
            error: "Erro de permissão ao deletar o arquivo",
            details: "O servidor não tem permissão para deletar este arquivo. Verifique as permissões."
          });
        }
        return res.status(500).json({ error: "Erro ao deletar o arquivo" });
      }

      console.log(`Arquivo ${filename} deletado com sucesso.`);

      // Após deletar o vídeo, tentar deletar o thumbnail
      fs.unlink(thumbnailPath, (thumbnailErr) => {
        if (thumbnailErr) {
          console.error(`Erro ao deletar o thumbnail ${filename}.jpeg:`, thumbnailErr);
          console.log(`Aviso: Thumbnail ${filename}.jpeg não pôde ser deletado, mas o vídeo foi removido.`);
        } else {
          console.log(`Thumbnail ${filename}.jpeg deletado com sucesso.`);
        }

        // Enviar resposta de sucesso apenas uma vez
        res.status(200).json({
          message: `Arquivo ${filename} deletado com sucesso.`,
          thumbnailDeleted: !thumbnailErr,
          warning: thumbnailErr ? "Thumbnail não pôde ser deletado" : null
        });
      });
    });
  });
})

const PORT = 3333;
app.listen(PORT, () => console.log(`Servidor rodando na porta ${PORT}`));
