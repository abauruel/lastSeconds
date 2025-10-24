from sqlalchemy import Column, Integer, String, DateTime, Enum
from datetime import datetime
import enum
from .db_config import Base

class VideoStatus(enum.Enum):
    PENDING = "pending"
    SENT = "sent"

class Video(Base):
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    path = Column(String, nullable=False)  # Caminho relativo do arquivo
    date = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(Enum(VideoStatus), nullable=False, default=VideoStatus.PENDING)

    def __repr__(self):
        return f"<Video(name={self.name}, path={self.path}, date={self.date}, status={self.status.value})>"