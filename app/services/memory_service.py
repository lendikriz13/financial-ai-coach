# Create this file: app/services/memory_service.py

from sqlalchemy.orm import Session
from app.db.models import User, ConversationHistory
from datetime import datetime, timedelta
from typing import List, Optional

class MemoryService:
    
    @staticmethod
    def get_recent_conversations(db: Session, user_id: int, limit: int = 10) -> List[ConversationHistory]:
        """Get recent conversation history for context building"""
        return db.query(ConversationHistory)\
                 .filter(ConversationHistory.user_id == user_id)\
                 .order_by(ConversationHistory.timestamp.desc())\
                 .limit(limit)\
                 .all()
    
    @staticmethod
    def build_context_prompt(user: User, recent_conversations: List[ConversationHistory], current_message: str) -> str:
        """Build context-aware prompt including business info and conversation history"""
        
        # Base context
        context_parts = [
            "You are a helpful financial coach and business advisor."
        ]
        
        # Add user's name for personalization
        if user.first_name:
            context_parts.append(f"You are helping {user.first_name}.")
        
        # Add business context if available
        if user.business_type:
            context_parts.append(f"They own a {user.business_type}.")
        
        if user.business_context:
            context_parts.append(f"Business background: {user.business_context}")
        
        if user.conversation_summary:
            context_parts.append(f"Previous discussion summary: {user.conversation_summary}")
        
        # Add recent conversation history
        if recent_conversations:
            context_parts.append("\nRecent conversation history:")
            # Show last 5 exchanges in chronological order
            for conv in reversed(recent_conversations[-5:]):
                context_parts.append(f"User: {conv.user_message}")
                context_parts.append(f"Coach: {conv.ai_response}")
        
        # Add current message and instructions
        context_parts.extend([
            f"\nCurrent user message: \"{current_message}\"",
            "\nInstructions:",
            "- Reference previous conversations when relevant",
            "- Provide helpful, encouraging financial advice", 
            "- Help track expenses and categorize them as business or personal",
            "- Assist with business calculations (breakeven, profit margins, inventory)",
            "- Keep responses conversational, supportive, and under 200 words",
            "- Act like a knowledgeable financial mentor who understands small business challenges",
            "\nResponse:"
        ])
        
        return "\n".join(context_parts)
    
    @staticmethod
    def store_conversation(db: Session, user_id: int, user_message: str, ai_response: str, message_type: str = "general"):
        """Store conversation exchange in history"""
        conversation = ConversationHistory(
            user_id=user_id,
            user_message=user_message,
            ai_response=ai_response,
            message_type=message_type,
            timestamp=datetime.utcnow()
        )
        db.add(conversation)
        db.commit()
        return conversation
    
    @staticmethod
    def update_user_context(db: Session, user: User, user_message: str):
        """Update user's business context and interaction timestamp"""
        user.last_interaction = datetime.utcnow()
        
        # Auto-detect business type from early messages
        if not user.business_type:
            message_lower = user_message.lower()
            business_keywords = {
                'clothing': ['clothing', 'clothes', 'fashion', 'apparel', 'boutique', 'fabric', 'garment'],
                'restaurant': ['restaurant', 'food', 'cafe', 'diner', 'kitchen', 'menu', 'cooking'],
                'retail': ['store', 'shop', 'retail', 'sales', 'customer', 'inventory'],
                'service': ['service', 'consulting', 'freelance', 'client', 'contract'],
                'ecommerce': ['online', 'website', 'ecommerce', 'shipping', 'digital']
            }
            
            for business_type, keywords in business_keywords.items():
                if any(keyword in message_lower for keyword in keywords):
                    user.business_type = business_type
                    print(f"✅ Auto-detected business type: {business_type}")
                    break
        
        # Extract and store business context from detailed messages
        if len(user_message) > 50 and not user.business_context:
            # Store first substantial message as initial business context
            user.business_context = f"Initial context: {user_message[:200]}..."
        
        db.commit()
    
    @staticmethod
    def categorize_message_type(user_message: str) -> str:
        """Categorize the type of message for better organization"""
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ['spent', 'spend', 'cost', 'expense', 'bought', 'paid']):
            return 'expense'
        elif any(word in message_lower for word in ['goal', 'target', 'plan', 'want to', 'hoping']):
            return 'goal'
        elif any(word in message_lower for word in ['profit', 'revenue', 'income', 'sales', 'earnings']):
            return 'revenue'
        elif any(word in message_lower for word in ['budget', 'planning', 'forecast', 'projection']):
            return 'planning'
        elif any(word in message_lower for word in ['help', 'how', 'what', 'why', 'advice']):
            return 'question'
        else:
            return 'general'
    
    @staticmethod
    def update_conversation_summary(db: Session, user: User):
        """Update rolling conversation summary (call periodically)"""
        recent_convs = MemoryService.get_recent_conversations(db, user.id, 15)
        
        if len(recent_convs) >= 3:  # Only summarize if there's meaningful conversation
            # Analyze conversation patterns
            topic_counts = {}
            for conv in recent_convs:
                msg_type = MemoryService.categorize_message_type(conv.user_message)
                topic_counts[msg_type] = topic_counts.get(msg_type, 0) + 1
            
            # Build summary based on most common topics
            top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            topic_summary = ", ".join([f"{topic}({count})" for topic, count in top_topics])
            
            user.conversation_summary = f"Recent focus: {topic_summary}. Last interaction: {recent_convs[0].timestamp.strftime('%Y-%m-%d')}"
            db.commit()
    
    @staticmethod
    def get_user_stats(db: Session, user_id: int) -> dict:
        """Get conversation statistics for the user"""
        total_conversations = db.query(ConversationHistory).filter(ConversationHistory.user_id == user_id).count()
        
        recent_conversations = db.query(ConversationHistory)\
                                .filter(ConversationHistory.user_id == user_id)\
                                .filter(ConversationHistory.timestamp >= datetime.utcnow() - timedelta(days=7))\
                                .count()
        
        return {
            'total_conversations': total_conversations,
            'recent_conversations': recent_conversations,
            'user_id': user_id
        }