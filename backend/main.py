from fastapi import FastAPI
from database.connection import Base, engine
from routes.github_webhook import router as github_webhook
from routes.health import router as health_router
from routes.review_router import router as review_router


# Create database tables
Base.metadata.create_all(bind=engine)


app = FastAPI()

app.include_router(github_webhook)
app.include_router(health_router)
app.include_router(review_router)