from common.logger import logger
from database.connection import engine, Base
from database.models import CodeReview

Base.metadata.create_all(bind=engine)

logger.info("Database tables created successfully.")