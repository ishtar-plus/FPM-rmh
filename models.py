from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class ImageData(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    image_path = Column(String, index=True)
    logo_path = Column(String, index=True)
    text = Column(String, index=True)
    text_position_x = Column(Integer)
    text_position_y = Column(Integer)
    text_color = Column(String)
    font_size = Column(Integer)
    font_path = Column(String)
    logo_position_x = Column(Integer)
    logo_position_y = Column(Integer)

Base.metadata.create_all(bind=engine)
