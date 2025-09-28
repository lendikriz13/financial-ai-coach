from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    # Original fields
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    first_name = Column(String(100))
    username = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # NEW MEMORY SYSTEM FIELDS
    business_context = Column(Text, nullable=True)
    conversation_summary = Column(Text, nullable=True) 
    business_type = Column(String(100), nullable=True)
    last_interaction = Column(DateTime, nullable=True)
    
    # Relationships
    transactions = relationship("Transaction", back_populates="user")
    conversation_history = relationship("ConversationHistory", back_populates="user")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(String(50))
    description = Column(Text)
    category = Column(String(100))
    transaction_type = Column(String(20))  # income, expense
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="transactions")

class ConversationHistory(Base):
    __tablename__ = "conversation_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user_message = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    message_type = Column(String(50), nullable=True)  # question, expense, goal, analysis, etc.
    
    user = relationship("User", back_populates="conversation_history")

class Goal(Base):
    __tablename__ = "goals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(200), nullable=False)
    description = Column(Text)
    target_amount = Column(String(50))
    target_date = Column(DateTime)
    status = Column(String(50), default="active")  # active, completed, paused
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")