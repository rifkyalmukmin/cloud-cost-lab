from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
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
    project_id = Column(String(100), unique=True, nullable=False)
    project_name = Column(String(200), nullable=False)
    environment = Column(String(50), nullable=False)
    team = Column(String(100))
    owner = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True)
    service_id = Column(String(100), unique=True, nullable=False)
    service_name = Column(String(200), nullable=False)
    category = Column(String(100))


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True)
    resource_id = Column(String(200), unique=True, nullable=False)
    resource_name = Column(String(200), nullable=False)
    resource_type = Column(String(100), nullable=False)
    service_id = Column(String(100), nullable=False)
    project_id = Column(String(100), nullable=False)
    region = Column(String(100))
    zone = Column(String(100))
    environment = Column(String(50))
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
    resource_id = Column(String(200), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    cpu_utilization = Column(Float)
    memory_utilization = Column(Float)
    disk_utilization = Column(Float)
    network_in = Column(Float)
    network_out = Column(Float)
    request_count = Column(Integer)


class CostRecord(Base):
    __tablename__ = "cost_records"

    id = Column(Integer, primary_key=True)
    project_id = Column(String(100), nullable=False)
    project_name = Column(String(200))
    service_id = Column(String(100), nullable=False)
    service_name = Column(String(200))
    sku = Column(String(200))
    region = Column(String(100))
    resource_id = Column(String(200))
    usage_date = Column(Date, nullable=False)
    usage_amount = Column(Float)
    usage_unit = Column(String(50))
    cost = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    credits = Column(Float, default=0.0)
    net_cost = Column(Float, nullable=False)
    environment = Column(String(50))
    team = Column(String(100))
    application = Column(String(100))
    labels = Column(Text)


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
