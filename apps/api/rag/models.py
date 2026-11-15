
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.app.database import Base


class RAGDocument(Base):
    __tablename__ = "rag_documents"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    owner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    chunks: Mapped[list["RAGChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class RAGChunk(Base):
    __tablename__ = "rag_chunks"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "rag_documents.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    embedding: Mapped[list[float]] = mapped_column(
        Vector(1536),
        nullable=False,
    )

    document: Mapped["RAGDocument"] = relationship(
        back_populates="chunks",
    )
