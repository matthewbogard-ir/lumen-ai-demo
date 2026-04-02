"""Email notification sender for Longines watch consultation analytics.

Sends branded lead summary emails with customer insights, collection interest,
and a newsletter signup CTA unique to the Longines demo.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List

from .config import (
    SMTP_HOST, SMTP_PORT, SENDER_EMAIL, SMTP_USERNAME,
    RECIPIENT_EMAIL, BRAND_NAME, secrets
)
from .summarizer import ConversationSummary

logger = logging.getLogger(__name__)


def get_dynamic_recipient_email() -> str:
    if RECIPIENT_EMAIL:
        return RECIPIENT_EMAIL
    try:
        from .api import get_primary_email
        primary = get_primary_email()
        if primary:
            logger.info(f"Using dynamically registered recipient: {primary}")
            return primary
    except Exception as e:
        logger.warning(f"Failed to get dynamic recipient email: {e}")
    return ""


class EmailSender:
    """Sends email notifications with Longines consultation analytics."""

    def __init__(self, smtp_host=SMTP_HOST, smtp_port=SMTP_PORT,
                 sender_email=SENDER_EMAIL, smtp_username=SMTP_USERNAME,
                 sender_password=None, recipient_email=None):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.smtp_username = smtp_username if smtp_username else sender_email
        self.sender_password = sender_password if sender_password else secrets.SENDER_APP_PASSWORD
        self.recipient_email = recipient_email if recipient_email else get_dynamic_recipient_email()

        if not all([self.smtp_username, self.sender_password, self.recipient_email]):
            logger.warning("Email configuration incomplete - emails will not be sent")

    def _build_summary_html(self, summary: ConversationSummary) -> str:
        """Build HTML for a single consultation summary card."""

        def is_meaningful(value):
            if not value:
                return False
            return str(value).lower().strip() not in ('unknown', 'not specified', 'none', 'n/a', 'null', '')

        # Engagement level colors
        level_colors = {"HIGH": "#2e7d32", "MEDIUM": "#ef6c00", "LOW": "#1565c0", "BOUNCE": "#757575"}
        level_color = level_colors.get(summary.engagement_level, "#757575")

        # Purchase likelihood colors
        purchase_colors = {"High (ready to buy)": "#2e7d32", "Medium (considering)": "#ef6c00", "Low (just browsing)": "#1565c0"}
        purchase_color = "#757575"
        for key, color in purchase_colors.items():
            if key.lower() in summary.purchase_likelihood.lower():
                purchase_color = color
                break

        # Build sections
        intent_html = "".join(f"<li>{i}</li>" for i in summary.customer_intent) or "<li>Not identified</li>"
        satisfaction_html = "".join(f"<li style='color: #2e7d32;'>{s}</li>" for s in summary.satisfaction_signals)
        friction_html = "".join(f"<li style='color: #c62828;'>{f}</li>" for f in summary.friction_points)
        watches_html = "".join(f"<li>{w}</li>" for w in summary.watches_discussed) or "<li>None discussed</li>"
        reactions_html = "".join(f"<li>{r}</li>" for r in summary.customer_reactions) or "<li>No specific feedback</li>"
        insights_html = "".join(f"<li>{i}</li>" for i in summary.product_improvement_insights)
        followup_html = "".join(f"<li>{f}</li>" for f in summary.recommended_followup) or "<li>No specific follow-up needed</li>"
        barriers_html = "".join(f"<li>{b}</li>" for b in summary.purchase_barriers)
        features_valued_html = "".join(f"<li>{f}</li>" for f in summary.features_valued)
        features_missing_html = "".join(f"<li style='color: #c62828;'>{f}</li>" for f in summary.features_missing)
        suggestions_html = "".join(f"<li>{s}</li>" for s in summary.improvement_suggestions)
        collections_html = "".join(f"<li>{c}</li>" for c in summary.collections_interested)
        complications_html = "".join(f"<li>{c}</li>" for c in summary.complications_interested)

        # Customer profile section
        profile_rows = []
        if is_meaningful(summary.buyer_type):
            profile_rows.append(f'<tr><td style="padding: 6px 0; color: #666; width: 40%;">Buyer Type:</td><td style="padding: 6px 0;"><strong>{summary.buyer_type}</strong></td></tr>')
        if is_meaningful(summary.style_preference):
            profile_rows.append(f'<tr><td style="padding: 6px 0; color: #666;">Style Preference:</td><td style="padding: 6px 0;">{summary.style_preference}</td></tr>')
        if is_meaningful(summary.watch_knowledge):
            profile_rows.append(f'<tr><td style="padding: 6px 0; color: #666;">Watch Knowledge:</td><td style="padding: 6px 0;">{summary.watch_knowledge}</td></tr>')
        if is_meaningful(summary.budget_range):
            profile_rows.append(f'<tr><td style="padding: 6px 0; color: #666;">Budget Range:</td><td style="padding: 6px 0;">{summary.budget_range}</td></tr>')

        profile_section = ""
        if profile_rows:
            profile_section = f"""
                <div style="margin-top: 15px;">
                    <h4 style="margin: 0 0 8px 0; color: #002B5C; border-bottom: 2px solid #002B5C; padding-bottom: 4px;">Customer Profile</h4>
                    <table style="width: 100%; font-size: 14px;">{''.join(profile_rows)}</table>
                </div>
            """

        # Collections & complications section
        interests_section = ""
        if collections_html or complications_html:
            collections_block = f'<div style="margin-top: 8px;"><strong style="font-size: 13px; color: #002B5C;">Collections:</strong><ul style="margin: 4px 0; padding-left: 20px; font-size: 14px;">{collections_html}</ul></div>' if collections_html else ""
            complications_block = f'<div style="margin-top: 8px;"><strong style="font-size: 13px; color: #002B5C;">Complications:</strong><ul style="margin: 4px 0; padding-left: 20px; font-size: 14px;">{complications_html}</ul></div>' if complications_html else ""
            interests_section = f"""
                <div style="margin-top: 15px;">
                    <h4 style="margin: 0 0 8px 0; color: #002B5C; border-bottom: 2px solid #002B5C; padding-bottom: 4px;">Collection & Complication Interest</h4>
                    {collections_block}{complications_block}
                </div>
            """

        # Features section
        features_section = ""
        if features_valued_html or features_missing_html:
            valued_block = f'<div style="margin-top: 8px;"><strong style="font-size: 13px; color: #2e7d32;">Valued:</strong><ul style="margin: 4px 0; padding-left: 20px; font-size: 14px;">{features_valued_html}</ul></div>' if features_valued_html else ""
            missing_block = f'<div style="margin-top: 8px;"><strong style="font-size: 13px; color: #c62828;">Missing/Wanted:</strong><ul style="margin: 4px 0; padding-left: 20px; font-size: 14px;">{features_missing_html}</ul></div>' if features_missing_html else ""
            features_section = f"""
                <div style="margin-top: 15px;">
                    <h4 style="margin: 0 0 8px 0; color: #002B5C; border-bottom: 2px solid #002B5C; padding-bottom: 4px;">Feature Preferences</h4>
                    {valued_block}{missing_block}
                </div>
            """

        # Friction section
        friction_section = ""
        if friction_html:
            friction_section = f"""
                <div style="background: #ffebee; padding: 12px; border-radius: 8px; margin-top: 15px;">
                    <h4 style="margin: 0 0 8px 0; color: #c62828;">Friction Points</h4>
                    <ul style="margin: 0; padding-left: 20px; font-size: 14px;">{friction_html}</ul>
                </div>
            """

        # Purchase barriers section
        barriers_section = ""
        if barriers_html:
            barriers_section = f"""
                <div style="background: #fff3e0; padding: 12px; border-radius: 8px; margin-top: 15px;">
                    <h4 style="margin: 0 0 8px 0; color: #e65100;">Purchase Barriers</h4>
                    <ul style="margin: 0; padding-left: 20px; font-size: 14px;">{barriers_html}</ul>
                </div>
            """

        # Product insights section
        insights_section = ""
        if insights_html:
            insights_section = f"""
                <div style="background: #e8eaf6; padding: 12px; border-radius: 8px; margin-top: 15px; border-left: 4px solid #002B5C;">
                    <h4 style="margin: 0 0 8px 0; color: #002B5C;">Product Improvement Insights</h4>
                    <ul style="margin: 0; padding-left: 20px; font-size: 14px;">{insights_html}</ul>
                </div>
            """

        # AI quality section
        quality_section = ""
        if suggestions_html:
            quality_section = f"""
                <div style="background: #f3e5f5; padding: 12px; border-radius: 8px; margin-top: 15px;">
                    <h4 style="margin: 0 0 8px 0; color: #7b1fa2;">AI Consultant Feedback</h4>
                    <div style="font-size: 14px; margin-bottom: 8px;">Helpfulness: <strong>{summary.assistant_helpfulness}</strong> | Info Completeness: <strong>{summary.information_completeness}</strong></div>
                    <ul style="margin: 0; padding-left: 20px; font-size: 14px;">{suggestions_html}</ul>
                </div>
            """

        satisfaction_section_html = ""
        if satisfaction_html:
            satisfaction_section_html = '<div style="background: #e8f5e9; padding: 12px; border-radius: 8px; margin-top: 15px;"><h4 style="margin: 0 0 8px 0; color: #2e7d32;">Satisfaction Signals</h4><ul style="margin: 0; padding-left: 20px; font-size: 14px;">' + satisfaction_html + '</ul></div>'

        # Newsletter CTA section
        newsletter_section = ""
        if summary.newsletter_interest or summary.engagement_level == "HIGH":
            newsletter_reason = "Customer expressed interest in staying updated" if summary.newsletter_interest else "High-engagement customer — strong newsletter candidate"
            newsletter_section = f"""
                <div style="background: linear-gradient(135deg, #f5f0e6 0%, #faf7f0 100%); padding: 16px; border-radius: 8px; margin-top: 15px; border: 2px solid #C4A35A;">
                    <h4 style="margin: 0 0 8px 0; color: #002B5C; font-size: 15px;">NEWSLETTER SIGNUP OPPORTUNITY</h4>
                    <p style="margin: 0 0 12px 0; font-size: 14px; color: #333;">{newsletter_reason}</p>
                    <a href="https://www.longines.com/en-us/newsletter" style="display: inline-block; background: #002B5C; color: white; padding: 10px 24px; border-radius: 4px; text-decoration: none; font-size: 14px; font-weight: bold;">Add to Longines Newsletter</a>
                </div>
            """

        return f"""
        <div style="border: 1px solid #ddd; border-radius: 12px; padding: 0; margin: 20px 0; background: #fff; overflow: hidden;">
            <div style="background: {level_color}; color: white; padding: 12px 20px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 18px; font-weight: bold;">{summary.engagement_level} ENGAGEMENT</div>
                    <div style="font-size: 13px; opacity: 0.9; margin-top: 3px;">Purchase Likelihood: {summary.purchase_likelihood}</div>
                </div>
            </div>

            <div style="padding: 20px;">
                <p style="font-size: 15px; color: #333; line-height: 1.6; margin: 0 0 15px 0; padding: 12px; background: #f8f9fa; border-radius: 8px;">
                    {summary.summary}
                </p>
                <p style="font-size: 13px; color: #666; margin: 0 0 15px 0;">
                    <em>Engagement:</em> {summary.engagement_reason}
                </p>

                <div style="margin-bottom: 15px;">
                    <h4 style="margin: 0 0 8px 0; color: #002B5C;">Customer Intent</h4>
                    <ul style="margin: 0; padding-left: 20px; font-size: 14px;">{intent_html}</ul>
                </div>

                {profile_section}

                <div style="margin-top: 15px;">
                    <h4 style="margin: 0 0 8px 0; color: #333;">Watches Discussed</h4>
                    <ul style="margin: 0; padding-left: 20px; font-size: 14px;">{watches_html}</ul>
                    <div style="margin-top: 8px;">
                        <strong style="font-size: 13px; color: #666;">Customer Reactions:</strong>
                        <ul style="margin: 4px 0; padding-left: 20px; font-size: 14px; color: #555;">{reactions_html}</ul>
                    </div>
                </div>

                {interests_section}
                {features_section}
                {friction_section}
                {barriers_section}
                {insights_section}

                {satisfaction_section_html}

                <div style="background: #f5f5f5; padding: 12px; border-radius: 8px; margin-top: 15px; border-left: 4px solid #002B5C;">
                    <h4 style="margin: 0 0 8px 0; color: #002B5C;">RECOMMENDED FOLLOW-UP</h4>
                    <ol style="margin: 0; padding-left: 20px; font-size: 14px;">{followup_html}</ol>
                </div>

                {newsletter_section}

                {quality_section}
            </div>
        </div>
        """

    def _build_email_html(self, summaries: List[ConversationSummary]) -> str:
        """Build complete email HTML."""
        now = datetime.now().strftime("%B %d, %Y at %I:%M %p")

        total = len(summaries)
        high_engagement = sum(1 for s in summaries if s.engagement_level == "HIGH")
        medium_engagement = sum(1 for s in summaries if s.engagement_level == "MEDIUM")
        likely_buyers = sum(1 for s in summaries if "high" in s.purchase_likelihood.lower())
        newsletter_interested = sum(1 for s in summaries if s.newsletter_interest)

        summaries_html = "".join(self._build_summary_html(s) for s in summaries)

        # Aggregate product insights across all sessions
        all_insights = []
        for s in summaries:
            all_insights.extend(s.product_improvement_insights)
        insights_aggregate = ""
        if all_insights:
            insights_list = "".join(f"<li>{i}</li>" for i in all_insights[:10])
            insights_aggregate = f"""
                <div style="background: #e8eaf6; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #002B5C;">
                    <h3 style="margin: 0 0 10px 0; color: #002B5C;">Collection & Experience Insights (Aggregated)</h3>
                    <ul style="margin: 0; padding-left: 20px; font-size: 14px;">{insights_list}</ul>
                </div>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 10px; background: #f5f5f5;">
            <div style="background: linear-gradient(135deg, #002B5C 0%, #001a3a 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0 0 5px 0; font-size: 22px; color: white;">{BRAND_NAME} AI Brand Consultant Report</h1>
                <p style="margin: 0; opacity: 0.7; font-size: 13px;">Customer Insights &amp; Collection Interest</p>
                <p style="margin: 5px 0 0 0; opacity: 0.9; font-size: 14px;">{now}</p>
            </div>

            <div style="background: white; padding: 15px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #002B5C;">
                    <h2 style="margin: 0 0 15px 0; color: #002B5C; font-size: 18px;">Session Overview</h2>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; text-align: center;">
                        <div style="background: white; padding: 12px; border-radius: 5px;">
                            <div style="font-size: 22px; font-weight: bold; color: #333;">{total}</div>
                            <div style="font-size: 11px; color: #666;">Total Sessions</div>
                        </div>
                        <div style="background: white; padding: 12px; border-radius: 5px;">
                            <div style="font-size: 22px; font-weight: bold; color: #2e7d32;">{high_engagement}</div>
                            <div style="font-size: 11px; color: #666;">High Engagement</div>
                        </div>
                        <div style="background: white; padding: 12px; border-radius: 5px;">
                            <div style="font-size: 22px; font-weight: bold; color: #ef6c00;">{medium_engagement}</div>
                            <div style="font-size: 11px; color: #666;">Medium Engagement</div>
                        </div>
                        <div style="background: white; padding: 12px; border-radius: 5px;">
                            <div style="font-size: 22px; font-weight: bold; color: #C4A35A;">{newsletter_interested}</div>
                            <div style="font-size: 11px; color: #666;">Newsletter Interest</div>
                        </div>
                    </div>
                </div>

                {insights_aggregate}

                <h2 style="color: #333; border-bottom: 2px solid #002B5C; padding-bottom: 10px; font-size: 18px;">
                    Session Details ({total} consultation{"s" if total != 1 else ""})
                </h2>

                {summaries_html}

                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666; font-size: 12px;">
                    <p>This report was automatically generated by the {BRAND_NAME} AI Brand Consultant</p>
                    <p>For help: <a href="https://www.longines.com/en-us/contact" style="color: #002B5C;">longines.com/contact</a></p>
                </div>
            </div>
        </body>
        </html>
        """

    def send_notification(self, summaries: List[ConversationSummary], recipient_email: str = None) -> bool:
        if not summaries:
            logger.info("No summaries to send")
            return True

        to_email = recipient_email or self.recipient_email

        if not all([self.smtp_username, self.sender_password, to_email]):
            logger.error("Email configuration incomplete - cannot send email")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = self._build_subject(summaries)
            msg["From"] = self.sender_email
            msg["To"] = to_email

            html_content = self._build_email_html(summaries)
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.sender_password)
                server.sendmail(self.sender_email, to_email, msg.as_string())

            logger.info(f"Sent notification email with {len(summaries)} summaries to {to_email}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _build_subject(self, summaries: List[ConversationSummary]) -> str:
        count = len(summaries)
        high = sum(1 for s in summaries if s.engagement_level == "HIGH")
        newsletter = sum(1 for s in summaries if s.newsletter_interest)

        if high > 0:
            return f"Longines AI Report \u2014 {high} High-Engagement Session{'s' if high > 1 else ''} ({count} total)"
        elif newsletter > 0:
            return f"Longines AI Report \u2014 {newsletter} Newsletter Interest{'s' if newsletter > 1 else ''} ({count} session{'s' if count > 1 else ''})"
        else:
            return f"Longines AI Report \u2014 {count} New Session{'s' if count > 1 else ''}"
