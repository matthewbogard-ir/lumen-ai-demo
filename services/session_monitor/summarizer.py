"""Azure OpenAI-powered conversation summarizer for Longines watch consultation analytics.

Focus: Luxury watch customer insights, collection preferences, purchase signals,
and newsletter interest for lead follow-up.
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional, List

from openai import AzureOpenAI

from .config import (
    BRAND_NAME, AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_VERSION, secrets
)
from .napster_client import SessionTranscript

logger = logging.getLogger(__name__)

# Longines-focused summarization prompt
SUMMARY_PROMPT = """You are a luxury watch retail analytics specialist helping {brand_name} understand customer consultation behavior and collection preferences through AI brand consultant conversations.

Analyze this conversation between a customer and the Longines AI brand consultant. Focus on CUSTOMER INSIGHTS, COLLECTION INTEREST, and PURCHASE SIGNALS that help the sales team follow up effectively.

Longines collections for reference: Master Collection (dress/complications), Heritage (vintage reissues), Spirit (aviation/adventure, COSC-certified), Conquest/HydroConquest (sport/dive), Elegance (DolceVita, La Grande Classique, PrimaLuna).

Provide a structured analysis in JSON format:

{{
    "summary": "2-3 sentence summary: what the customer was looking for, which collections/watches interested them, and their overall engagement with the consultation",

    "engagement_level": "HIGH" | "MEDIUM" | "LOW" | "BOUNCE",
    "engagement_reason": "Brief explanation of the engagement level",

    "customer_intent": ["List the customer's goals - gift, personal purchase, exploring collections, specific complication interest, etc."],
    "satisfaction_signals": ["Positive indicators: excitement about a watch, comparison interest, asking about availability, pricing questions"],
    "friction_points": ["Pain points: confusion about collections, price concerns, missing features, unmet needs"],

    "customer_profile": {{
        "buyer_type": "Collector | Gift buyer | First luxury watch | Upgrader | Enthusiast | Browser | Unknown",
        "style_preference": "Classic/Dress | Sporty/Dive | Heritage/Vintage | Elegant/Jewelry | Multiple | Unknown",
        "watch_knowledge": "Expert (knows calibres, complications) | Intermediate (knows brands, basic specs) | Beginner (new to watches) | Unknown",
        "budget_range": "Under $1,500 | $1,500-$2,500 | $2,500-$3,500 | $3,500+ | Not discussed | Unknown"
    }},

    "product_interests": {{
        "collections": ["Which Longines collections interested them"],
        "specific_watches": ["Exact watch models mentioned or shown"],
        "complications_interested": ["Moon phase, chronograph, GMT, flyback, annual calendar, etc."],
        "features_valued": ["Water resistance, power reserve, COSC certification, ceramic bezel, silicon balance spring, etc."],
        "features_missing": ["Features they wanted but couldn't find in the catalog"]
    }},

    "watches_discussed": ["List of specific Longines watches discussed or compared"],
    "customer_reactions": ["How did they react to watches shown? What did they like/dislike?"],

    "purchase_likelihood": "High (ready to buy) | Medium (considering) | Low (just browsing) | Unknown",
    "purchase_barriers": ["What stopped them from deciding? Price, need to see in person, comparing brands, gift timing, etc."],

    "customer_contact": "Email if provided, or null",
    "newsletter_interest": true or false,

    "product_improvement_insights": [
        "Actionable insights for the brand",
        "e.g., 'Customer wanted a green dial option in the Master Collection'",
        "e.g., 'Customer confused about difference between Spirit and HydroConquest for daily wear'",
        "e.g., 'Customer wished for more size options in La Grande Classique'"
    ],

    "recommended_followup": [
        "Suggested follow-up actions for the sales team",
        "e.g., 'Send comparison of Heritage Diver 1967 vs Legend Diver with boutique availability'",
        "e.g., 'Invite to upcoming Longines event or trunk show'",
        "e.g., 'Follow up with Spirit collection brochure for the aviation enthusiast'"
    ],

    "conversation_quality": {{
        "assistant_helpfulness": "Excellent | Good | Adequate | Poor",
        "information_completeness": "Did the assistant provide all needed info? Yes | Partially | No",
        "improvement_suggestions": ["How could the AI consultant do better next time?"]
    }}
}}

CONVERSATION:
{conversation}

Provide ONLY the JSON response. Focus on insights that help the Longines sales team follow up effectively and improve the consultation experience."""


@dataclass
class ConversationSummary:
    """Luxury watch consultation summary."""
    session_id: str
    summary: str

    # Engagement
    engagement_level: str  # HIGH, MEDIUM, LOW, BOUNCE
    engagement_reason: str
    customer_intent: List[str]
    satisfaction_signals: List[str]
    friction_points: List[str]

    # Customer profile
    buyer_type: str
    style_preference: str
    watch_knowledge: str
    budget_range: str

    # Product interests
    collections_interested: List[str]
    specific_watches: List[str]
    complications_interested: List[str]
    features_valued: List[str]
    features_missing: List[str]

    # Watches & reactions
    watches_discussed: List[str]
    customer_reactions: List[str]

    # Purchase
    purchase_likelihood: str
    purchase_barriers: List[str]

    # Contact & newsletter
    customer_contact: Optional[str]
    newsletter_interest: bool

    # Insights
    product_improvement_insights: List[str]
    recommended_followup: List[str]

    # Conversation quality
    assistant_helpfulness: str
    information_completeness: str
    improvement_suggestions: List[str]

    # Raw data
    raw_transcript: str
    transcript_start_time: Optional[int] = None


class AzureOpenAISummarizer:
    """Summarizes conversations using Azure OpenAI."""

    def __init__(self, api_key: str = None):
        if api_key is None:
            api_key = secrets.AZURE_OPENAI_API_KEY

        if not api_key:
            raise ValueError(
                "Azure OpenAI API key is required. "
                "Set AZURE_OPENAI_API_KEY env var or add azure-openai-api-key to Key Vault."
            )

        if not AZURE_OPENAI_ENDPOINT:
            raise ValueError(
                "Azure OpenAI endpoint is required. Set AZURE_OPENAI_ENDPOINT env var."
            )

        self.client = AzureOpenAI(
            api_key=api_key,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT
        )
        self.deployment = AZURE_OPENAI_DEPLOYMENT
        logger.info(f"Initialized Azure OpenAI summarizer (deployment: {self.deployment})")

    def _clean_contact(self, contact: Optional[str]) -> Optional[str]:
        if not contact:
            return None
        parts = [p.strip() for p in str(contact).split(",")]
        cleaned_parts = [p for p in parts if p and p.lower() not in ("null", "none")]
        return ", ".join(cleaned_parts) if cleaned_parts else None

    def summarize(self, transcript: SessionTranscript) -> Optional[ConversationSummary]:
        conversation_text = transcript.to_conversation_text()

        prompt = SUMMARY_PROMPT.format(
            brand_name=BRAND_NAME,
            conversation=conversation_text
        )

        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": "You are a luxury watch retail analytics specialist. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            response_text = response.choices[0].message.content.strip()
            data = json.loads(response_text)

            customer_profile = data.get("customer_profile", {})
            product_interests = data.get("product_interests", {})
            conv_quality = data.get("conversation_quality", {})

            summary = ConversationSummary(
                session_id=transcript.session_id,
                summary=data.get("summary", "No summary available"),

                engagement_level=data.get("engagement_level", "LOW"),
                engagement_reason=data.get("engagement_reason", ""),
                customer_intent=data.get("customer_intent", []),
                satisfaction_signals=data.get("satisfaction_signals", []),
                friction_points=data.get("friction_points", []),

                buyer_type=customer_profile.get("buyer_type", "Unknown"),
                style_preference=customer_profile.get("style_preference", "Unknown"),
                watch_knowledge=customer_profile.get("watch_knowledge", "Unknown"),
                budget_range=customer_profile.get("budget_range", "Unknown"),

                collections_interested=product_interests.get("collections", []),
                specific_watches=product_interests.get("specific_watches", []),
                complications_interested=product_interests.get("complications_interested", []),
                features_valued=product_interests.get("features_valued", []),
                features_missing=product_interests.get("features_missing", []),

                watches_discussed=data.get("watches_discussed", []),
                customer_reactions=data.get("customer_reactions", []),

                purchase_likelihood=data.get("purchase_likelihood", "Unknown"),
                purchase_barriers=data.get("purchase_barriers", []),

                customer_contact=self._clean_contact(data.get("customer_contact")),
                newsletter_interest=bool(data.get("newsletter_interest", False)),

                product_improvement_insights=data.get("product_improvement_insights", []),
                recommended_followup=data.get("recommended_followup", []),

                assistant_helpfulness=conv_quality.get("assistant_helpfulness", "Unknown"),
                information_completeness=conv_quality.get("information_completeness", "Unknown"),
                improvement_suggestions=conv_quality.get("improvement_suggestions", []),

                raw_transcript=conversation_text,
                transcript_start_time=transcript.get_first_timestamp()
            )

            logger.info(f"Generated summary for session {transcript.session_id[:20]}... "
                       f"(engagement: {summary.engagement_level}, purchase: {summary.purchase_likelihood})")
            return summary

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Azure OpenAI response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to summarize transcript: {e}")
            return None

    def summarize_multiple(self, transcripts: List[SessionTranscript]) -> List[ConversationSummary]:
        summaries = []
        for transcript in transcripts:
            summary = self.summarize(transcript)
            if summary:
                summaries.append(summary)
        return summaries
