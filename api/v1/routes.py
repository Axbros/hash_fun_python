from fastapi import APIRouter, Depends, HTTPException,Request
from sqlalchemy.orm import Session
import logging
from services.transaction_service import transfer
from database import SessionLocal
router = APIRouter()

block_ip_list = []

# 创建依赖项
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/transactions/{transaction_id}")
def transfer_transaction(transaction_id: int,request:Request,db: Session = Depends(get_db)):
    client_ip = request.client.host
    if client_ip in block_ip_list:
        logging.warn("Block IP Request,IP address:"+client_ip)
        raise HTTPException(status_code=403, detail="Forbidden: Block IP")
    if client_ip not in ("127.0.0.1", "localhost", "::1"):
        block_ip_list.append(client_ip)
        logging.warn("Not localhost request,IP address:"+client_ip)
        raise HTTPException(status_code=403, detail="Forbidden: Only localhost allowed")
    return transfer(transaction_id,db)
