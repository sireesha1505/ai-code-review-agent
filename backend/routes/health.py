from fastapi import APIRouter

router = APIRouter(tags = ["health"], prefix= "/health")

@router.get("")
def getHealthStatus():
    return {"message": "Healthy"}

