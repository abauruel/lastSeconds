// server.js
const express = require("express");
const fs = require("fs");
const path = require("path");
const cors = require("cors")

const app = express();


app.use(cors())

const videosDir = path.join(__dirname, "..", "output");

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
  const filename = req.params.filename
  console.log(`filename ${filename}`)
})

const PORT = 3333;
app.listen(PORT, () => console.log(`Servidor rodando na porta ${PORT}`));
