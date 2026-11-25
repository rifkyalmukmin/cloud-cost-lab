from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.sql import func

from app.config import settings


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    project_id = Column(String(100), unique=True, nullable=False, index=True)
    project_name = Column(String(200), nullable=False)
    environment = Column(String(50), nullable=False, index=True)
    team = Column(String(100))
    owner = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True)
    service_id = Column(String(100), unique=True, nullable=False, index=True)
    service_name = Column(String(200), nullable=False)
    category = Column(String(100))


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True)
    resource_id = Column(String(200), unique=True, nullable=False, index=True)
    resource_name = Column(String(200), nullable=False)
    resource_type = Column(String(100), nullable=False)
    service_id = Column(String(100), ForeignKey("services.service_id"), nullable=False, index=True)
    project_id = Column(String(100), ForeignKey("projects.project_id"), nullable=False, index=True)
    region = Column(String(100))
    zone = Column(String(100))
    environment = Column(String(50), index=True)
    status = Column(String(50), default="active")
    owner = Column(String(100))
    team = Column(String(100))
    application = Column(String(100))
    labels = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    last_seen = Column(DateTime, server_default=func.now())


class ResourceUsage(Base):
    __tablename__ = "resource_usage"

    id = Column(Integer, primary_key=True)
    resource_id = Column(String(200), ForeignKey("resources.resource_id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    cpu_utilization = Column(Float)
    memory_utilization = Column(Float)
    disk_utilization = Column(Float)
    network_in = Column(Float)
    network_out = Column(Float)
    request_count = Column(Integer)


class CostRecord(Base):
    __tablename__ = "cost_records"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "service_id",
            "sku",
            "resource_id",
            "usage_date",
            name="uq_cost_records_line",
        ),
    )

    id = Column(Integer, primary_key=True)
    project_id = Column(String(100), ForeignKey("projects.project_id"), nullable=False, index=True)
    project_name = Column(String(200))
    service_id = Column(String(100), ForeignKey("services.service_id"), nullable=False, index=True)
    service_name = Column(String(200))
    sku = Column(String(200))
    region = Column(String(100))
    resource_id = Column(String(200), ForeignKey("resources.resource_id"), index=True)
    usage_date = Column(Date, nullable=False, index=True)
    usage_amount = Column(Numeric(18, 6))
    usage_unit = Column(String(50))
    cost = Column(Numeric(14, 4), nullable=False)
    currency = Column(String(10), default="USD")
    credits = Column(Numeric(14, 4), default=0)
    net_cost = Column(Numeric(14, 4), nullable=False)
    environment = Column(String(50), index=True)
    team = Column(String(100))
    application = Column(String(100))
    labels = Column(Text)


class CostDailyAggregate(Base):
    """Daily cost rolled up by project, service, and environment."""

    __tablename__ = "cost_daily_aggregates"
    __table_args__ = (
        UniqueConstraint(
            "usage_date",
            "project_id",
            "service_id",
            "environment",
            name="uq_cost_daily_aggregate",
        ),
    )

    id = Column(Integer, primary_key=True)
    usage_date = Column(Date, nullable=False, index=True)
    project_id = Column(String(100), ForeignKey("projects.project_id"), nullable=False, index=True)
    service_id = Column(String(100), ForeignKey("services.service_id"), nullable=False, index=True)
    project_name = Column(String(200), nullable=False)
    service_name = Column(String(200), nullable=False)
    environment = Column(String(50), nullable=False, index=True)
    cost = Column(Numeric(14, 4), nullable=False)
    net_cost = Column(Numeric(14, 4), nullable=False)
    currency = Column(String(10), nullable=False, default="USD")


class RecommendationStateRow(Base):
    __tablename__ = "recommendation_states"

    recommendation_id = Column(String(64), primary_key=True)
    resource_id = Column(String(200), ForeignKey("resources.resource_id"), nullable=False, index=True)
    status = Column(String(32), nullable=False, index=True)
    potential_savings = Column(Numeric(14, 4), nullable=False)
    current_cost = Column(Numeric(14, 4), nullable=False)
    cost_before = Column(Numeric(14, 4))
    cost_after = Column(Numeric(14, 4))
    realized_savings = Column(Numeric(14, 4))
    approved_by = Column(String(100))
    approved_at = Column(String(40))
    implemented_by = Column(String(100))
    implemented_at = Column(String(40))
    verified_at = Column(String(40))
    rejected_by = Column(String(100))
    rejected_at = Column(String(40))
    rejection_reason = Column(String(500))
    payload = Column(Text, nullable=False)


class AuditLogRow(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    recommendation_id = Column(
        String(64),
        ForeignKey("recommendation_states.recommendation_id"),
        nullable=False,
        index=True,
    )
    timestamp = Column(String(40), nullable=False)
    action = Column(String(32), nullable=False)
    actor = Column(String(100), nullable=False)
    reason = Column(String(500))
    cost_before = Column(Numeric(14, 4))
    cost_after = Column(Numeric(14, 4))
    realized_savings = Column(Numeric(14, 4))


engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
