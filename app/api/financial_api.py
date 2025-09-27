from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Transaction, User, Goal
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal

router = APIRouter()  # This line is critical

@router.get("/transactions/{user_id}")
async def get_transactions(user_id: int, db: Session = Depends(get_db)):
    """Get user transactions"""
    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()
    return {"transactions": transactions}

@router.get("/analysis/{user_id}")
async def get_financial_analysis(user_id: int, db: Session = Depends(get_db)):
    """Get financial analysis for user"""
    
    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()
    
    total_income = sum(t.amount for t in transactions if t.type == "income")
    total_expenses = sum(t.amount for t in transactions if t.type == "expense")
    net_position = total_income - total_expenses
    
    return {
        "user_id": user_id,
        "total_income": float(total_income),
        "total_expenses": float(total_expenses),
        "net_position": float(net_position),
        "transaction_count": len(transactions)
    }