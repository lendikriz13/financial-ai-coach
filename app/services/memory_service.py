# app/services/memory_service.py
# COMPLETE FILE - Final Version with Comprehensive Seasoned Mentor Prompt

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
        """Build CONSTRAINED seasoned business mentor prompt - RESPONSE FORMAT FOCUSED"""
        
        # Minimal but essential context
        context_parts = [
            f"You are {user.first_name}'s experienced business mentor."
        ]
        
        if user.business_type:
            context_parts.append(f"Business: {user.business_type}.")
        
        # Recent context (minimal)
        if recent_conversations:
            last_conv = recent_conversations[0]
            context_parts.append(f"Last discussed: {last_conv.user_message[:50]}...")
        
        # Current message and STRICT FORMAT RULES
        context_parts.extend([
            f"\nCurrent: \"{current_message}\"",
            
            "\n*** CRITICAL RESPONSE CONSTRAINTS ***",
            "1. MAXIMUM 3 sentences (50-80 words total)",
            "2. NO introductory phrases like 'let's dig into', 'that's great', 'good question'",
            "3. NO closing offers like 'does this help?' or 'let me know'",
            "4. Get straight to your advice or questions",
            "5. Sound like an experienced mentor - confident but not verbose",
            
            "\nYour response style: Warm but direct. Natural but concise. Skip the fluff.",
            "\nRespond now in 3 sentences or less:"
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
                'clothing': ['clothing', 'clothes', 'fashion', 'apparel', 'boutique', 'fabric', 'garment', 'textile'],
                'restaurant': ['restaurant', 'food', 'cafe', 'diner', 'kitchen', 'menu', 'cooking', 'catering'],
                'retail': ['store', 'shop', 'retail', 'sales', 'customer', 'inventory', 'merchandise'],
                'service': ['service', 'consulting', 'freelance', 'client', 'contract', 'professional services'],
                'ecommerce': ['online', 'website', 'ecommerce', 'shipping', 'digital', 'amazon', 'shopify'],
                'construction': ['construction', 'contractor', 'building', 'renovation', 'project', 'job site'],
                'fitness': ['gym', 'fitness', 'training', 'workout', 'health', 'wellness', 'nutrition']
            }
            
            for business_type, keywords in business_keywords.items():
                if any(keyword in message_lower for keyword in keywords):
                    user.business_type = business_type
                    print(f"✅ Auto-detected business type: {business_type}")
                    break
        
        # Extract and store business context from substantial messages
        if len(user_message) > 60 and not user.business_context:
            user.business_context = f"Initial context: {user_message[:250]}..."
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
        
        if any(word in message_lower for word in ['spent', 'spend', 'cost', 'expense', 'bought', 'paid', 'purchase']):
            return 'expense'
        elif any(word in message_lower for word in ['goal', 'target', 'plan', 'want to', 'hoping', 'objective']):
            return 'goal'
        elif any(word in message_lower for word in ['profit', 'revenue', 'income', 'sales', 'earnings', 'made']):
            return 'revenue'
        elif any(word in message_lower for word in ['budget', 'planning', 'forecast', 'projection', 'cash flow']):
            return 'planning'
        elif any(word in message_lower for word in ['help', 'how', 'what', 'why', 'advice', 'should i']):
            return 'question'
        elif any(word in message_lower for word in ['problem', 'issue', 'struggling', 'difficult', 'challenge']):
            return 'problem'
        else:
            return 'general'
    
    @staticmethod
    def update_conversation_summary(db: Session, user: User):
        """Update rolling conversation summary (call periodically)"""
        recent_convs = MemoryService.get_recent_conversations(db, user.id, 20)
        
        if len(recent_convs) >= 5:
            # Analyze conversation patterns
            topic_counts = {}
            for conv in recent_convs:
                msg_type = MemoryService.categorize_message_type(conv.user_message)
                topic_counts[msg_type] = topic_counts.get(msg_type, 0) + 1
            
            # Build summary based on most common topics
            top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            topic_summary = ", ".join([f"{topic}({count})" for topic, count in top_topics])
            
            user.conversation_summary = f"Recent focus: {topic_summary}. Last active: {recent_convs[0].timestamp.strftime('%Y-%m-%d')}"
            db.commit()
            print(f"✅ Updated conversation summary: {user.conversation_summary}")
    
    @staticmethod
    def get_user_stats(db: Session, user_id: int) -> dict:
        """Get conversation statistics for the user"""
        total_conversations = db.query(ConversationHistory).filter(ConversationHistory.user_id == user_id).count()
        
        recent_conversations = db.query(ConversationHistory)\
                                .filter(ConversationHistory.user_id == user_id)\
                                .filter(ConversationHistory.timestamp >= datetime.utcnow() - timedelta(days=7))\
                                .count()
        
        # Get conversation type breakdown
        recent_convs = MemoryService.get_recent_conversations(db, user_id, 10)
        type_counts = {}
        for conv in recent_convs:
            msg_type = MemoryService.categorize_message_type(conv.user_message)
            type_counts[msg_type] = type_counts.get(msg_type, 0) + 1
        
        return {
            'total_conversations': total_conversations,
            'recent_conversations': recent_conversations,
            'conversation_types': type_counts,
            'user_id': user_id
        }

# Validation and testing
if __name__ == "__main__":
    print("MemoryService class with comprehensive seasoned mentor prompt loaded successfully")
    print("Available methods:")
    for method_name in dir(MemoryService):
        if not method_name.startswith('_'):
            print(f"  - {method_name}")