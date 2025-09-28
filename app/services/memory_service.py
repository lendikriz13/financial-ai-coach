# app/services/memory_service.py
# COMPLETE FILE - Replace entire contents

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
        """Build direct, no-fluff prompt for business mentor"""
        
        # Minimal context
        context_parts = [
            f"You are {user.first_name}'s business mentor."
        ]
        
        # Business context if available
        if user.business_type:
            context_parts.append(f"Business: {user.business_type}.")
        
        # Minimal recent context
        if recent_conversations and len(recent_conversations) > 0:
            last_exchange = recent_conversations[0]
            context_parts.append(f"Last discussed: {last_exchange.user_message[:40]}...")
        
        # Current message and strict instructions
        context_parts.extend([
            f"\nCurrent: \"{current_message}\"",
            
            "\nResponse rules:",
            "• Maximum 2 sentences, 30-60 words total",
            "• No introductory phrases like 'That's great' or 'Good question'", 
            "• No closing pleasantries or offers to help further",
            "• Ask specific questions when you need details",
            "• Be direct about problems without softening",
            "• Get straight to the point",
            
            "\nDirect response:"
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
        print(f"DEBUG: update_user_context called with user_id: {user.id}")
        
        # Update last interaction time
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
            user.business_context = f"Initial context: {user_message[:200]}..."
            print(f"✅ Stored initial business context")
        
        # Commit changes
        try:
            db.commit()
            print(f"✅ User context updated successfully")
        except Exception as e:
            print(f"❌ Error committing user context: {e}")
            db.rollback()
            raise
    
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
        
        if len(recent_convs) >= 3:
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

# Test the class can be imported
if __name__ == "__main__":
    print("MemoryService class defined successfully")
    print("Available methods:")
    for method_name in dir(MemoryService):
        if not method_name.startswith('_'):
            print(f"  - {method_name}")