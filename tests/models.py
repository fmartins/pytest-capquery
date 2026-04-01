from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class AlarmPanel(Base):
    __tablename__ = 'alarm_panels'

    id = Column(Integer, primary_key=True)
    mac_address = Column(String(255), nullable=False, unique=True)
    is_online = Column(Boolean, default=False)

    sensors = relationship("Sensor", back_populates="panel", cascade="all, delete-orphan")

class Sensor(Base):
    __tablename__ = 'sensors'

    id = Column(Integer, primary_key=True)
    panel_id = Column(Integer, ForeignKey('alarm_panels.id'), nullable=False)
    name = Column(String(255), nullable=False)
    sensor_type = Column(String(255), nullable=False)

    panel = relationship("AlarmPanel", back_populates="sensors")
