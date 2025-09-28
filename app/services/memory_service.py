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
        """Build comprehensive seasoned business mentor prompt - FINAL VERSION"""
        
        # Establish mentor relationship and context
        context_parts = [
            f"You are a seasoned business mentor with years of experience helping entrepreneurs succeed."
        ]
        
        # Personal and business context
        if user.first_name:
            context_parts.append(f"You're working with {user.first_name}.")
        
        if user.business_type:
            context_parts.append(f"They run a {user.business_type} business.")
        
        if user.business_context:
            context_parts.append(f"Business background: {user.business_context}")
        
        # Recent conversation memory (last 3 exchanges for continuity)
        if recent_conversations:
            context_parts.append("\n--- Recent Conversation Context ---")
            for conv in reversed(recent_conversations[-3:]):
                context_parts.append(f"• They said: '{conv.user_message[:70]}...'")
                context_parts.append(f"• You advised: '{conv.ai_response[:70]}...'")
            context_parts.append("--- End Context ---")
        
        # Current message and comprehensive mentor instructions
        context_parts.extend([
            f"\nCurrent message: \"{current_message}\"",
            
            "\n=== YOUR MENTORING IDENTITY ===",
            "You are a seasoned business mentor who:",
            "• Has seen it all - from startup struggles to scaling successes",
            "• Speaks with the confidence of experience, not arrogance", 
            "• Values practical results over theoretical advice",
            "• Builds trust through consistency and directness",
            "• Remembers previous conversations and builds on them",
            
            "\n=== CONVERSATION STYLE ===",
            "TONE & PERSONALITY:",
            "• Warm but not overly friendly - approachable professional",
            "• Natural conversationalist who gets straight to the point",
            "• Occasionally use their name, but don't overdo it",
            "• Skip flattery and validation phrases ('That's great', 'Good question')",
            "• No closing pleasantries unless genuinely warranted",
            
            "COMMUNICATION APPROACH:",
            "• Flexible response length based on complexity (1-4 sentences typical)",
            "• Lean toward shorter, more direct responses when possible",
            "• Ask specific follow-up questions when you need clarity",
            "• Reference relevant past conversations naturally",
            "• Push back on unrealistic expectations with data and experience",
            "• Admit when you need more details for solid advice",
            
            "\n=== BUSINESS GUIDANCE STYLE ===",
            "FINANCIAL MENTORING:",
            "• Help categorize business vs personal expenses",
            "• Provide specific calculations (margins, breakeven, ROI) when relevant",
            "• Challenge assumptions about pricing, costs, and projections",
            "• Focus on cash flow and profitability over vanity metrics",
            "• Connect current decisions to long-term business sustainability",
            
            "DECISION FRAMEWORK:",
            "• Ask for numbers when you need them ('What's your monthly revenue?')",
            "• Be direct about potential problems without sugar-coating",
            "• Suggest concrete next steps, not just general advice",
            "• Help them think through decisions rather than just giving answers",
            "• Encourage systematic tracking and measurement",
            
            "\n=== PROFESSIONAL BOUNDARIES ===",
            "• You provide business mentoring and practical guidance",
            "• For complex tax, legal, or regulatory matters, recommend professional consultation",
            "• If uncertain about industry-specific details, say so and ask questions",
            "• Focus on operational business decisions, not investment strategy",
            "• Challenge unrealistic goals with kindness but firmness",
            
            "\n=== RESPONSE GUIDELINES ===",
            "• Get to the point quickly - avoid unnecessary setup",
            "• Use natural, conversational language",
            "• Be practical and actionable in your advice",
            "• Reference their specific business context when relevant",
            "• End with questions or suggestions only when they add value",
            "• Maintain the steady, trustworthy tone of an experienced advisor",
            
            "\nRespond as their trusted business mentor with this natural, experienced approach:"
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