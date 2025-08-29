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
def foursquare_parameter_extractor(text: str) -> Dict[str, Any]:
    """Extract Foursquare API parameters from text for direct API usage."""
    
    import re
    
    text_lower = text.lower()
    
    # Initialize Foursquare API parameters
    foursquare_params = {
        "query": None,           # Search query string
        "fsq_category_ids": [],  # Foursquare category IDs
        "min_price": None,       # 1-4 price range
        "max_price": None,       # 1-4 price range
        "open_now": None,        # Boolean for current availability
        "near": None,            # Location string
        "sort": None,            # relevance, rating, distance
    }
    
    # Extract query terms (food items, cuisine types, restaurant names, taste descriptors)
    query_patterns = [
        r'\b(?:pizza|burger|sushi|tacos?|pasta|chinese|italian|mexican|indian|thai|japanese|korean|vietnamese|american|french|mediterranean|bbq|seafood|steakhouse|cafe|coffee|breakfast|brunch|lunch|dinner)\b',
        r'\b(?:spicy|mild|hot|sweet|savory|tangy|crispy|fried|grilled|baked|roasted)\b',  # Taste/cooking descriptors
        r'\b(?:mcdonalds?|subway|starbucks|kfc|pizza\s*hut|dominos|chipotle|taco\s*bell)\b',
        r'\b(?:restaurant|place|spot|joint|bar|grill|bistro|diner|kitchen)\b'
    ]
    
    query_matches = []
    for pattern in query_patterns:
        matches = re.findall(pattern, text_lower)
        query_matches.extend(matches)
    
    # Clean and prioritize query matches
    if query_matches:
        # Remove generic terms and prioritize specific ones
        specific_queries = [q for q in query_matches if q not in ['restaurant', 'place', 'spot', 'joint', 'bar']]
        foursquare_params["query"] = specific_queries[0] if specific_queries else query_matches[0]
    
    # Extract Foursquare category mappings
    category_mapping = {
        # Main restaurant categories
        "restaurant": "13065",
        "fast food": "13145", 
        "cafe": "13032",
        "bar": "13003",
        
        # Cuisine-specific categories  
        "italian": "13236",
        "chinese": "13099", 
        "mexican": "13303",
        "indian": "13199",
        "japanese": "13263",
        "thai": "13352",
        "american": "13064",
        "french": "13148",
        "mediterranean": "13305",
        "korean": "13276",
        "vietnamese": "13360",
        "seafood": "13338",
        
        # Specific food types
        "pizza": "13064",
        "burger": "13064",
        "sushi": "13338",
        "bbq": "13061",
        "steakhouse": "13345",
        "breakfast": "13065",
        "coffee": "13032"
    }
    
    # Map detected cuisines/food types to category IDs
    detected_categories = []
    for cuisine_term in query_matches:
        if cuisine_term in category_mapping:
            detected_categories.append(category_mapping[cuisine_term])
    
    foursquare_params["fsq_category_ids"] = list(set(detected_categories))  # Remove duplicates
    
    # Extract price preferences
    price_patterns = {
        "cheap": (1, 2), "budget": (1, 2), "affordable": (1, 2),
        "expensive": (3, 4), "pricey": (3, 4), "upscale": (3, 4), "fine dining": (4, 4),
        "mid-range": (2, 3), "moderate": (2, 3)
    }
    
    for price_term, (min_p, max_p) in price_patterns.items():
        if price_term in text_lower:
            foursquare_params["min_price"] = min_p
            foursquare_params["max_price"] = max_p
            break
    
    # Extract specific dollar amounts and budget numbers
    dollar_matches = re.findall(r'\$(\d+)', text)
    budget_matches = re.findall(r'\b(?:budget|spend|under|around|about)\s+(?:of\s+)?(\d+)', text_lower)
    number_matches = re.findall(r'\b(\d{2,4})\b', text)  # 2-4 digit numbers (likely prices)
    
    amount = None
    if dollar_matches:
        amount = int(dollar_matches[0])
    elif budget_matches:
        amount = int(budget_matches[0])
    elif number_matches:
        # Only use if it looks like a reasonable price (50-5000)
        potential_amounts = [int(n) for n in number_matches if 50 <= int(n) <= 5000]
        if potential_amounts:
            amount = potential_amounts[0]
    
    if amount:
        # Map amount to Foursquare price levels (1=$ 2=$$ 3=$$$ 4=$$$$)
        if amount <= 20:
            foursquare_params["min_price"] = 1
            foursquare_params["max_price"] = 1
        elif amount <= 50:
            foursquare_params["min_price"] = 1
            foursquare_params["max_price"] = 2
        elif amount <= 150:
            foursquare_params["min_price"] = 2
            foursquare_params["max_price"] = 3
        elif amount <= 400:
            foursquare_params["min_price"] = 3
            foursquare_params["max_price"] = 4
        else:
            foursquare_params["min_price"] = 4
            foursquare_params["max_price"] = 4
    
    # Extract timing preferences
    timing_patterns = [
        r'\b(?:open now|right now|currently open)\b',
        r'\b(?:tonight|today|now)\b'
    ]
    
    for pattern in timing_patterns:
        if re.search(pattern, text_lower):
            foursquare_params["open_now"] = True
            break
    
    # Extract location mentions
    location_patterns = [
        r'\bnear\s+([A-Za-z\s]+)',
        r'\bin\s+([A-Za-z\s,]+)',
        r'\baround\s+([A-Za-z\s]+)',
        r'\bclose to\s+([A-Za-z\s]+)'
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, text)
        if match:
            location = match.group(1).strip()
            if len(location) > 3:  # Avoid short meaningless matches
                foursquare_params["near"] = location
                break
    
    # Extract sorting preferences
    sort_patterns = {
        "best rated": "rating",
        "highest rated": "rating", 
        "top rated": "rating",
        "closest": "distance",
        "nearby": "distance",
        "nearest": "distance"
    }
    
    for sort_term, sort_value in sort_patterns.items():
        if sort_term in text_lower:
            foursquare_params["sort"] = sort_value
            break
    
    # Calculate relevance score based on extracted parameters
    param_count = sum(1 for v in foursquare_params.values() if v is not None and v != [] and v != "")
    word_count = len(text.split())
    relevance_score = min(1.0, param_count / 4.0)  # Max score when 4+ params extracted
    
    # Clean up empty values
    cleaned_params = {}
    for key, value in foursquare_params.items():
        if value is not None and value != [] and value != "":
            cleaned_params[key] = value
    
    return {
        "foursquare_params": cleaned_params,
        "relevance_score": relevance_score,
        "parameters_extracted": param_count,
        "message_length": word_count,
        "extraction_timestamp": datetime.utcnow().isoformat(),
        "raw_query_matches": query_matches
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
        extraction_result = foursquare_parameter_extractor.invoke(state["raw_message"])
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
        foursquare_params = extraction_result.get("foursquare_params", {})
        base_relevance = extraction_result.get("relevance_score", 0.0)
        
        relevance_factors = [base_relevance]
        
        # Score based on Foursquare parameters extracted
        param_count = extraction_result.get("parameters_extracted", 0)
        if param_count > 0:
            relevance_factors.append(min(1.0, param_count / 4.0))  # Max when 4+ params
        
        # Higher confidence for specific query terms
        if foursquare_params.get("query"):
            relevance_factors.append(0.9)
        
        # Higher confidence for category matches
        if foursquare_params.get("fsq_category_ids"):
            relevance_factors.append(0.8)
        
        # Price and location preferences add confidence
        if foursquare_params.get("min_price") or foursquare_params.get("max_price"):
            relevance_factors.append(0.7)
        if foursquare_params.get("near"):
            relevance_factors.append(0.6)
        
        # Restaurant mentions still valuable
        if state["restaurant_mentions"]:
            relevance_factors.append(0.9)
        
        overall_relevance = sum(relevance_factors) / len(relevance_factors) if relevance_factors else 0.1
        
        state["confidence_scores"] = {
            "overall_relevance": overall_relevance,
            "parameter_density": min(1.0, param_count / 5.0),  # Based on parameter extraction
            "foursquare_compatibility": 1.0 if param_count > 0 else 0.0
        }
        state["next_action"] = "final_synthesis"
        return state
    
    async def _synthesize_results(self, state: MessageAnalysisState) -> MessageAnalysisState:
        """Synthesize all analysis results into final output."""
        
        extraction_result = state["extracted_preferences"][0] if state["extracted_preferences"] else {}
        foursquare_params = extraction_result.get("foursquare_params", {})
        
        # Create comprehensive analysis result
        final_result = {
            "message_id": state["user_context"].get("message_id"),
            "user_id": state["user_context"].get("user_id"),
            "group_id": state["user_context"].get("group_id"),
            "timestamp": datetime.utcnow().isoformat(),
            
            # Core analysis - NEW Foursquare-specific structure
            "foursquare_parameters": foursquare_params,
            "parameter_extraction_metadata": {
                "relevance_score": extraction_result.get("relevance_score", 0.0),
                "parameters_extracted": extraction_result.get("parameters_extracted", 0),
                "message_length": extraction_result.get("message_length", 0),
                "extraction_timestamp": extraction_result.get("extraction_timestamp"),
                "raw_query_matches": extraction_result.get("raw_query_matches", [])
            },
            "sentiment": state["sentiment_analysis"],
            "restaurant_mentions": state["restaurant_mentions"],
            "group_dynamics": state["group_dynamics"],
            
            # Confidence and relevance
            "confidence_scores": state["confidence_scores"],
            "overall_relevance": state["confidence_scores"]["overall_relevance"],
            
            # Actionable insights
            "should_update_preferences": state["confidence_scores"]["overall_relevance"] > 0.4,  # Lower threshold for API parameters
            "requires_follow_up": state["sentiment_analysis"].get("enthusiasm_level") == "high",
            "consensus_indicator": state["group_dynamics"]["consensus_building"],
            "api_ready": state["confidence_scores"]["foursquare_compatibility"] > 0.0,
            
            # Direct API parameters for recommendations
            "api_parameters": foursquare_params,
            
            # Metadata
            "analysis_version": "langgraph_foursquare_v3.0",
            "processing_time": datetime.utcnow().isoformat()
        }
        
        state["analysis_results"] = final_result
        
        return state
    
    
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