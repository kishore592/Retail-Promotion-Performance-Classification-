from datetime import datetime

from sqlalchemy import (
    String,
    DateTime,
    Text,
    Float,
    JSON,
    Integer,
    Boolean,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config.settings import settings


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class Session(Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class Workflow(Base):
    __tablename__ = "workflows"

    workflow_id: Mapped[str] = mapped_column(
        String(64), primary_key=True
    )
    session_id: Mapped[str] = mapped_column(
        String(64), index=True
    )
    status: Mapped[str] = mapped_column(
        String(32), default="RUNNING"
    )
    risk_band: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )
    confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    state_json: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    workflow_id: Mapped[str] = mapped_column(
        String(64), index=True
    )
    agent: Mapped[str] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32))
    latency_ms: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    error: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    token_usage: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    workflow_id: Mapped[str] = mapped_column(
        String(64), index=True
    )
    agent: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    tool: Mapped[str] = mapped_column(String(128))
    arguments: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    result: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    status: Mapped[str] = mapped_column(String(32))
    latency_ms: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    source: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    document_id: Mapped[int] = mapped_column(
        Integer, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    workflow_id: Mapped[str] = mapped_column(
        String(64), index=True
    )
    decision: Mapped[str] = mapped_column(String(32))
    comment: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    approved_by: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    workflow_id: Mapped[str] = mapped_column(
        String(64), index=True
    )
    event: Mapped[str] = mapped_column(String(128))
    details: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    workflow_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    metric: Mapped[str] = mapped_column(String(128))
    score: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    details: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


# ------------------------------------------------------------------
# Async database configuration
# ------------------------------------------------------------------

DATABASE_URL = settings.database_url

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def close_db():
    await engine.dispose()
