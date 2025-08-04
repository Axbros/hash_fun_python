from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from services.transaction_service import transfer
from database import SessionLocal
router = APIRouter()



# 创建依赖项
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/transactions/{transaction_id}")
def transfer_transaction(transaction_id: int, db: Session = Depends(get_db)):
    return transfer(transaction_id,db)
