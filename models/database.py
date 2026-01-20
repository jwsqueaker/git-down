"""Database models and schema."""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Date, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config.settings import DATABASE_URL

Base = declarative_base()


class PortfolioPosition(Base):
    """Portfolio position model."""
    __tablename__ = 'portfolio_positions'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False)
    shares = Column(Float, nullable=False)
    purchase_date = Column(Date, nullable=False)
    purchase_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PortfolioMetrics(Base):
    """Historical portfolio metrics."""
    __tablename__ = 'portfolio_metrics'

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, unique=True)
    total_value = Column(Float, nullable=False)
    total_return = Column(Float)
    daily_return = Column(Float)
    sharpe_ratio = Column(Float)
    sortino_ratio = Column(Float)
    max_drawdown = Column(Float)
    volatility = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class MacroIndicator(Base):
    """Macro economic indicators."""
    __tablename__ = 'macro_indicators'

    id = Column(Integer, primary_key=True)
    indicator_name = Column(String(100), nullable=False)
    date = Column(Date, nullable=False)
    value = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class LTCMAData(Base):
    """JP Morgan LTCMA data."""
    __tablename__ = 'ltcma_data'

    id = Column(Integer, primary_key=True)
    asset_class = Column(String(100), nullable=False)
    expected_return = Column(Float)
    volatility = Column(Float)
    correlation_matrix = Column(Text)  # JSON string
    year = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class BenchmarkData(Base):
    """Benchmark performance data."""
    __tablename__ = 'benchmark_data'

    id = Column(Integer, primary_key=True)
    benchmark_name = Column(String(50), nullable=False)
    date = Column(Date, nullable=False)
    close_price = Column(Float, nullable=False)
    daily_return = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


# Database initialization
def init_db():
    """Initialize the database."""
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    return engine


def get_session():
    """Get database session."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()
