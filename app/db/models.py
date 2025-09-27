from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, BigInteger, Date, JSON, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    business_name = Column(String(200))
    business_type = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(DECIMAL(10, 2), nullable=False)  # Changed from Decimal to DECIMAL
    type = Column(String(20), nullable=False)
    category = Column(String(100), nullable=False)
    description = Column(Text)
    transaction_date = Column(Date, nullable=False)
    is_business = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

class Goal(Base):
    __tablename__ = "goals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    goal_type = Column(String(50))
    target_amount = Column(DECIMAL(10, 2))  # Changed from Decimal to DECIMAL
    current_amount = Column(DECIMAL(10, 2), default=0)  # Changed from Decimal to DECIMAL
    target_date = Column(Date)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

class ConversationContext(Base):
    __tablename__ = "conversation_context"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    context_data = Column(JSON)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())