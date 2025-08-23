"""
LangGraph-based LLM Analyzer

Advanced message analysis using LangGraph for sophisticated preference extraction,
sentiment analysis, and conversational understanding.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, TypedDict, Annotated
from datetime import datetime

from langchain.schema import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MessageAnalysisState(TypedDict):
    """State for LangGraph message analysis workflow."""
    messages: Annotated[List[BaseMessage], add_messages]
    user_context: Dict[str, Any]
    raw_message: str
    analysis_results: Dict[str, Any]
    confidence_scores: Dict[str, float]
    extracted_preferences: List[Dict[str, Any]]
    sentiment_analysis: Dict[str, Any]
    restaurant_mentions: List[Dict[str, Any]]
    dietary_mentions: List[str]
    cuisine_preferences: List[str]
    price_sensitivity: Optional[str]
    group_dynamics: Dict[str, Any]
    next_action: str


@tool
def preference_extractor(text: str) -> Dict[str, Any]:
    """Extract generic food-related keywords and preferences from text using LLM-driven approach."""
    
    # Initialize generic keyword storage
    extracted_keywords = {
        "food_keywords": [],        # Any food-related terms
        "cuisine_keywords": [],     # Cuisine types or dishes
        "taste_keywords": [],       # Taste/flavor descriptors
        "price_keywords": [],       # Price-related terms
        "atmosphere_keywords": [],  # Ambiance/setting preferences
        "dietary_keywords": [],     # Dietary needs/restrictions
        "location_keywords": [],    # Location/proximity terms
        "time_keywords": [],        # Time-related preferences
        "quantity_keywords": [],    # Group size, portion mentions
        "quality_keywords": [],     # Quality/rating descriptors
        "service_keywords": [],     # Service expectations
        "misc_keywords": []         # Other relevant terms
    }
    
    import re
    
    # Use regex and natural language processing to extract keywords
    text_lower = text.lower()
    words = re.findall(r'\b\w+(?:\s+\w+)*\b', text_lower)
    
    # Food-related indicators - cast wider net
    food_indicators = [
        "food", "eat", "eating", "meal", "dish", "cuisine", "restaurant", "place", 
        "spot", "joint", "cafe", "diner", "kitchen", "grill", "bar", "bistro",
        "lunch", "dinner", "breakfast", "brunch", "snack", "appetizer", "dessert",
        "taste", "flavor", "delicious", "tasty", "yummy", "mouth", "hungry", "craving",
        "cook", "cooking", "chef", "recipe", "ingredient", "sauce", "soup", "salad",
        "meat", "chicken", "beef", "pork", "fish", "seafood", "vegetable", "fruit"
    ]
    
    # Extract any food-related terms
    for word_phrase in words:
        if any(indicator in word_phrase for indicator in food_indicators):
            extracted_keywords["food_keywords"].append(word_phrase)
    
    # Cuisine/dish extraction - look for proper nouns and food terms
    cuisine_patterns = [
        r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',  # Proper nouns (restaurant names, cuisines)
        r'\b\w*(?:curry|pasta|pizza|sushi|taco|burger|noodle|rice|bread|soup)\w*\b',
        r'\b\w*(?:spicy|sweet|sour|salty|bitter|savory|mild|hot|cold)\b'
    ]
    
    for pattern in cuisine_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if len(match.strip()) > 2:  # Avoid single letters
                extracted_keywords["cuisine_keywords"].append(match.lower())
    
    # Price extraction - look for any price-related terms
    price_patterns = [
        r'\$\d+',  # Dollar amounts
        r'\b\d+\s*(?:dollar|buck|rupee|pound|euro)\b',
        r'\b(?:budget|cheap|expensive|costly|affordable|pricey|deal|discount|sale)\b',
        r'\bunder\s*\d+\b', r'\bover\s*\d+\b', r'\babove\s*\d+\b', r'\bbelow\s*\d+\b'
    ]
    
    for pattern in price_patterns:
        matches = re.findall(pattern, text_lower)
        extracted_keywords["price_keywords"].extend(matches)
    
    # Taste descriptors - any adjectives that could describe food
    taste_pattern = r'\b(?:spicy|mild|hot|sweet|sour|bitter|salty|savory|tangy|rich|light|heavy|fresh|crispy|crunchy|soft|tender|juicy|dry|wet|smooth|rough|creamy|chunky)\b'
    taste_matches = re.findall(taste_pattern, text_lower)
    extracted_keywords["taste_keywords"].extend(taste_matches)
    
    # Atmosphere/ambiance terms
    atmosphere_pattern = r'\b(?:casual|formal|fancy|upscale|cozy|romantic|family|quiet|loud|busy|calm|outdoor|indoor|rooftop|waterfront|downtown|suburban)\b'
    atmosphere_matches = re.findall(atmosphere_pattern, text_lower)
    extracted_keywords["atmosphere_keywords"].extend(atmosphere_matches)
    
    # Dietary terms
    dietary_pattern = r'\b(?:vegetarian|vegan|gluten.free|halal|kosher|keto|paleo|organic|healthy|diet|low.fat|low.carb|sugar.free|dairy.free)\b'
    dietary_matches = re.findall(dietary_pattern, text_lower)
    extracted_keywords["dietary_keywords"].extend(dietary_matches)
    
    # Location terms
    location_pattern = r'\b(?:near|close|nearby|walking|driving|far|distance|delivery|takeout|pickup|dine.in)\b'
    location_matches = re.findall(location_pattern, text_lower)
    extracted_keywords["location_keywords"].extend(location_matches)
    
    # Time-related terms
    time_pattern = r'\b(?:now|soon|later|tonight|today|tomorrow|weekend|morning|afternoon|evening|quick|fast|slow|rush|time|hour|minute)\b'
    time_matches = re.findall(time_pattern, text_lower)
    extracted_keywords["time_keywords"].extend(time_matches)
    
    # Quality descriptors
    quality_pattern = r'\b(?:good|great|excellent|amazing|awesome|terrible|bad|awful|best|worst|favorite|recommended|popular|famous|new|old)\b'
    quality_matches = re.findall(quality_pattern, text_lower)
    extracted_keywords["quality_keywords"].extend(quality_matches)
    
    # Service terms
    service_pattern = r'\b(?:service|staff|waiter|waitress|server|friendly|rude|fast|slow|attentive|helpful)\b'
    service_matches = re.findall(service_pattern, text_lower)
    extracted_keywords["service_keywords"].extend(service_matches)
    
    # Clean up and deduplicate
    for key in extracted_keywords:
        extracted_keywords[key] = list(set([kw.strip() for kw in extracted_keywords[key] if len(kw.strip()) > 2]))
    
    # Add relevance score based on keyword density
    total_keywords = sum(len(keywords) for keywords in extracted_keywords.values())
    word_count = len(text.split())
    relevance_score = min(1.0, total_keywords / max(1, word_count) * 5)  # Scale to 0-1
    
    return {
        "keywords": extracted_keywords,
        "relevance_score": relevance_score,
        "total_keywords_found": total_keywords,
        "message_length": word_count,
        "extraction_timestamp": datetime.utcnow().isoformat()
    }


@tool
def sentiment_analyzer(text: str) -> Dict[str, Any]:
    """Analyze sentiment, emotions, and satisfaction levels in dining conversations."""
    text_lower = text.lower()
    
    positive_words = ["love", "amazing", "delicious", "great", "awesome", "perfect", "craving", "excited"]
    negative_words = ["hate", "terrible", "awful", "bad", "horrible", "disappointed"]
    enthusiasm_words = ["!!", "omg", "definitely", "must try"]
    agreement_words = ["everyone", "we all", "agreed"]
    disagreement_words = ["but", "however", "disagree"]
    
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    enthusiasm_count = sum(1 for phrase in enthusiasm_words if phrase in text_lower)
    
    sentiment = "positive" if positive_count > negative_count else "negative" if negative_count > positive_count else "neutral"
    confidence = min(0.9, 0.5 + abs(positive_count - negative_count) * 0.1)
    enthusiasm = "high" if enthusiasm_count > 1 else "medium" if enthusiasm_count > 0 else "low"
    agreement = "high" if any(word in text_lower for word in agreement_words) else "low" if any(word in text_lower for word in disagreement_words) else "unknown"
    
    return {
        "overall_sentiment": sentiment,
        "confidence": confidence,
        "enthusiasm_level": enthusiasm,
        "group_agreement": agreement
    }


@tool
def restaurant_mention_detector(text: str) -> List[Dict[str, Any]]:
    """Detect specific restaurant mentions, recommendations, and experiences."""
    mentions = []
    text_lower = text.lower()
    words = text.split()
    
    restaurant_indicators = ["restaurant", "place", "spot", "cafe", "bar"]
    experience_words = {"visited": ["went to", "tried"], "recommended": ["recommend", "suggest"]}
    
    for i, word in enumerate(words):
        if word.lower() in restaurant_indicators and i > 0:
            name = words[i-1]
            context = "unknown"
            for ctx, ctx_words in experience_words.items():
                if any(w in text_lower for w in ctx_words):
                    context = ctx
                    break
            mentions.append({"name": name, "context": context, "confidence": 0.7})
    
    return mentions


class LangGraphAnalyzer:
    """Advanced message analyzer using LangGraph workflow."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4.1-nano",
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for message analysis."""
        workflow = StateGraph(MessageAnalysisState)
        
        # Add nodes
        workflow.add_node("initial_analysis", self._initial_analysis)
        workflow.add_node("preference_extraction", self._extract_preferences)
        workflow.add_node("sentiment_analysis", self._analyze_sentiment)
        workflow.add_node("restaurant_detection", self._detect_restaurants)
        workflow.add_node("context_integration", self._integrate_context)
        workflow.add_node("confidence_scoring", self._score_confidence)
        workflow.add_node("final_synthesis", self._synthesize_results)
        
        # Define the flow
        workflow.set_entry_point("initial_analysis")
        
        workflow.add_edge("initial_analysis", "preference_extraction")
        workflow.add_edge("preference_extraction", "sentiment_analysis")
        workflow.add_edge("sentiment_analysis", "restaurant_detection")
        workflow.add_edge("restaurant_detection", "context_integration")
        workflow.add_edge("context_integration", "confidence_scoring")
        workflow.add_edge("confidence_scoring", "final_synthesis")
        workflow.add_edge("final_synthesis", END)
        
        return workflow.compile()
    
    async def _initial_analysis(self, state: MessageAnalysisState) -> MessageAnalysisState:
        state["analysis_results"] = {"message_type": "dining_related", "relevance_score": 0.8}
        state["next_action"] = "preference_extraction"
        return state
    
    async def _extract_preferences(self, state: MessageAnalysisState) -> MessageAnalysisState:
        extraction_result = preference_extractor.invoke(state["raw_message"])
        state["extracted_preferences"] = [extraction_result]
        state["next_action"] = "sentiment_analysis"
        return state
    
    async def _analyze_sentiment(self, state: MessageAnalysisState) -> MessageAnalysisState:
        sentiment = sentiment_analyzer.invoke(state["raw_message"])
        state["sentiment_analysis"] = sentiment
        state["next_action"] = "restaurant_detection"
        return state
    
    async def _detect_restaurants(self, state: MessageAnalysisState) -> MessageAnalysisState:
        mentions = restaurant_mention_detector.invoke(state["raw_message"])
        state["restaurant_mentions"] = mentions
        state["next_action"] = "context_integration"
        return state
    
    async def _integrate_context(self, state: MessageAnalysisState) -> MessageAnalysisState:
        sentiment = state["sentiment_analysis"]
        message_lower = state["raw_message"].lower()
        
        leadership_phrases = ["let's", "how about", "i suggest"]
        leadership_found = [p for p in leadership_phrases if p in message_lower]
        
        state["group_dynamics"] = {
            "influence_level": "high" if leadership_found else "medium",
            "consensus_building": sentiment.get("group_agreement", "unknown")
        }
        state["next_action"] = "confidence_scoring"
        return state
    
    async def _score_confidence(self, state: MessageAnalysisState) -> MessageAnalysisState:
        extraction_result = state["extracted_preferences"][0] if state["extracted_preferences"] else {}
        keywords = extraction_result.get("keywords", {})
        base_relevance = extraction_result.get("relevance_score", 0.0)
        
        relevance_factors = [base_relevance]
        
        non_empty_categories = sum(1 for kw in keywords.values() if kw)
        if non_empty_categories > 0:
            relevance_factors.append(min(1.0, non_empty_categories / 6.0))
        
        if keywords.get("food_keywords") or keywords.get("cuisine_keywords"):
            relevance_factors.append(0.8)
        if keywords.get("taste_keywords") or keywords.get("price_keywords"):
            relevance_factors.append(0.7)
        if state["restaurant_mentions"]:
            relevance_factors.append(0.9)
        
        overall_relevance = sum(relevance_factors) / len(relevance_factors) if relevance_factors else 0.1
        
        state["confidence_scores"] = {
            "overall_relevance": overall_relevance,
            "keyword_density": min(1.0, extraction_result.get("total_keywords_found", 0) / 15.0)
        }
        state["next_action"] = "final_synthesis"
        return state
    
    async def _synthesize_results(self, state: MessageAnalysisState) -> MessageAnalysisState:
        """Synthesize all analysis results into final output."""
        
        extraction_result = state["extracted_preferences"][0] if state["extracted_preferences"] else {}
        keywords = extraction_result.get("keywords", {})
        
        # Create comprehensive analysis result
        final_result = {
            "message_id": state["user_context"].get("message_id"),
            "user_id": state["user_context"].get("user_id"),
            "group_id": state["user_context"].get("group_id"),
            "timestamp": datetime.utcnow().isoformat(),
            
            # Core analysis - NEW generic keyword structure
            "extracted_keywords": keywords,
            "keyword_extraction_metadata": {
                "relevance_score": extraction_result.get("relevance_score", 0.0),
                "total_keywords_found": extraction_result.get("total_keywords_found", 0),
                "message_length": extraction_result.get("message_length", 0),
                "extraction_timestamp": extraction_result.get("extraction_timestamp")
            },
            "sentiment": state["sentiment_analysis"],
            "restaurant_mentions": state["restaurant_mentions"],
            "group_dynamics": state["group_dynamics"],
            
            # Confidence and relevance
            "confidence_scores": state["confidence_scores"],
            "overall_relevance": state["confidence_scores"]["overall_relevance"],
            
            # Actionable insights
            "should_update_preferences": state["confidence_scores"]["overall_relevance"] > 0.5,  # Lower threshold for generic approach
            "requires_follow_up": state["sentiment_analysis"].get("enthusiasm_level") == "high",
            "consensus_indicator": state["group_dynamics"]["consensus_building"],
            
            # Recommendation keywords - flatten all relevant keywords for API calls
            "recommendation_keywords": self._flatten_keywords_for_recommendations(keywords),
            
            # Metadata
            "analysis_version": "langgraph_generic_v2.0",
            "processing_time": datetime.utcnow().isoformat()
        }
        
        state["analysis_results"] = final_result
        
        return state
    
    def _flatten_keywords_for_recommendations(self, keywords: Dict[str, List[str]]) -> List[str]:
        """Flatten and prioritize keywords for restaurant recommendations."""
        flattened = []
        
        # Prioritize keywords by relevance for restaurant search
        priority_order = [
            "cuisine_keywords",    # Most important for restaurant search
            "food_keywords",       # General food terms
            "taste_keywords",      # Flavor preferences
            "dietary_keywords",    # Dietary restrictions
            "price_keywords",      # Price considerations
            "atmosphere_keywords", # Ambiance preferences
            "quality_keywords",    # Quality indicators
            "location_keywords",   # Location preferences
            "time_keywords",       # Timing preferences
            "service_keywords",    # Service expectations
        ]
        
        for category in priority_order:
            if category in keywords and keywords[category]:
                flattened.extend(keywords[category])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for keyword in flattened:
            if keyword.lower() not in seen:
                seen.add(keyword.lower())
                unique_keywords.append(keyword)
        
        # Limit to top 20 keywords for API efficiency
        return unique_keywords[:20]
    
    async def analyze_message(
        self, 
        message_text: str, 
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze a message using the LangGraph workflow.
        
        Args:
            message_text: The message to analyze
            user_context: Context about the user and group
            
        Returns:
            Comprehensive analysis results
        """
        try:
            # Initialize state
            initial_state = MessageAnalysisState(
                messages=[],
                user_context=user_context,
                raw_message=message_text,
                analysis_results={},
                confidence_scores={},
                extracted_preferences=[],
                sentiment_analysis={},
                restaurant_mentions=[],
                dietary_mentions=[],
                cuisine_preferences=[],
                price_sensitivity=None,
                group_dynamics={},
                next_action="initial_analysis"
            )
            
            # Run the workflow
            final_state = await self.workflow.ainvoke(initial_state)
            
            logger.info(f"Message analysis completed with relevance: {final_state['confidence_scores']['overall_relevance']}")
            
            return final_state["analysis_results"]
            
        except Exception as e:
            logger.error(f"Error in LangGraph message analysis: {str(e)}")
            
            # Return fallback analysis
            return {
                "error": str(e),
                "message_id": user_context.get("message_id"),
                "user_id": user_context.get("user_id"),
                "group_id": user_context.get("group_id"),
                "overall_relevance": 0.0,
                "should_update_preferences": False,
                "analysis_version": "fallback_v1.0"
            }
    
    async def batch_analyze_messages(
        self, 
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple messages in batch.
        
        Args:
            messages: List of message dictionaries with 'text' and 'context'
            
        Returns:
            List of analysis results
        """
        results = []
        
        for message_data in messages:
            try:
                result = await self.analyze_message(
                    message_data["text"],
                    message_data["context"]
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Error analyzing message in batch: {str(e)}")
                results.append({
                    "error": str(e),
                    "overall_relevance": 0.0
                })
        
        return results


# Global analyzer instance
langgraph_analyzer = LangGraphAnalyzer()