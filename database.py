import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import models  # 强制注册所有模型


engine = create_engine(os.getenv("DATABASE_URL"))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

Base.metadata.create_all(engine)
