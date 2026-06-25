from __future__ import annotations

import email
import imaplib
import uuid
from datetime import datetime
from email.message import Message
from typing import Dict, List, Optional

from tools.config_store import load_setting


class Orchestrator:
    def __init__(self) -> None:
        self.approval_queue: Dict[str, Dict] = {}
        self.last_run: Optional[str] = None

    def _add(self, task: Dict) -> str:
        action_id = str(uuid.uuid4())
        task.setdefault("created_at", datetime.now().strftime("%b %d, %I:%M %p"))
        self.approval_queue[action_id] = task
        return action_id

    def _configured(self, *keys: str) -> bool:
        return all(bool(load_setting(key, "")) for key in keys)

    def _setup_status(self) -> List[str]:
        checks = [
            ("OpenAI key", self._configured("OPENAI_API_KEY")),
            ("Inbound email", self._configured("IMAP_HOST", "IMAP_PORT", "IMAP_USER", "IMAP_PASSWORD")),
            ("Outbound email", self._configured("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD")),
            ("Facebook page", self._configured("META_PAGE_ID", "META_PAGE_ACCESS_TOKEN")),
            ("Approval lock", (load_setting("APPROVAL_REQUIRED", "true") or "true").lower() == "true"),
        ]
        return [f"{'READY' if ok else 'NEEDS SETUP'} - {name}" for name, ok in checks]

    def _briefing(self, title: str, focus: str) -> Dict:
        status = "\n".join(self._setup_status())
        return {
            "type": "briefing",
            "description": title,
            "destination": "AstroBuildCo command center",
            "risk": "low",
            "reason": "Planning and visibility only.",
            "draft": f"{focus}\n\nSystem status:\n{status}\n\nPriority order:\n1. Check email/RFQ leads.\n2. Draft replies and quote notes.\n3. Review every approval card before anything leaves AstroBuildCo.\n4. Push one clean Facebook post for engagement.\n\nNothing sends, posts, deletes, or submits without approval.",
        }

    def _clean_text(self, msg: Message) -> str:
        parts: List[str] = []
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition", "")).lower():
                    payload = part.get_payload(decode=True)
                    if payload:
                        parts.append(payload.decode(part.get_content_charset() or "utf-8", errors="ignore"))
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                parts.append(payload.decode(msg.get_content_charset() or "utf-8", errors="ignore"))
        return "\n".join(parts).strip()[:1800]

    def _email_category(self, subject: str, body: str) -> str:
        text = f"{subject} {body}".lower()
        if any(word in text for word in ["rfq", "quote", "solicitation", "sam.gov", "bid", "proposal"]):
            return "RFQ / quote lead"
        if any(word in text for word in ["invoice", "payment", "receipt", "past due"]):
            return "billing / money"
        if any(word in text for word in ["urgent", "asap", "deadline", "due today"]):
            return "urgent follow-up"
        if any(word in text for word in ["tower", "site", "fiber", "tarana", "install", "av", "chapel"]):
            return "field work / operations"
        return "general business"

    def _reply_draft(self, category: str, sender: str, subject: str) -> str:
        if category == "RFQ / quote lead":
            return "Good afternoon,\n\nThank you for reaching out to AstroBuildCo. I can review this requirement and prepare a response. Please send the full scope of work, site address, due date, required forms, and whether materials are government/customer furnished or contractor furnished.\n\nOnce I have the full details, I will confirm pricing, schedule, and execution approach.\n\nV/r,\nAshton Hill\nAstroBuildCo, LLC\n937-765-3581\nashtonhill@astrobuildco.org"
        if category == "billing / money":
            return "Good afternoon,\n\nI received your message and will review the billing/payment details. Please send any invoice number, PO number, service date, and supporting documentation so I can verify everything accurately.\n\nThank you,\nAshton Hill\nAstroBuildCo, LLC"
        if category == "field work / operations":
            return "Good afternoon,\n\nThanks for the details. I can take a look at the site/work request. Please confirm the site address, access window, required completion date, contact on site, and any photos or drawings available.\n\nV/r,\nAshton Hill\nAstroBuildCo, LLC"
        return "Good afternoon,\n\nThank you for reaching out to AstroBuildCo. I reviewed your message and will follow up with the correct details shortly.\n\nV/r,\nAshton Hill\nAstroBuildCo, LLC"

    def _add_email_setup_task(self) -> None:
        self._add({
            "type": "setup",
            "description": "Email is not connected yet",
            "destination": "API Settings",
            "risk": "low",
            "reason": "Email triage needs IMAP/SMTP settings before it can read messages.",
            "draft": "Go to API Settings and fill in:\n\nInbound email:\n- EMAIL_PROVIDER\n- IMAP_HOST\n- IMAP_PORT\n- IMAP_USER\n- IMAP_PASSWORD\n\nOutbound email:\n- SMTP_HOST\n- SMTP_PORT\n- SMTP_USER\n- SMTP_PASSWORD\n\nAfter saving, run Check Email again. The agent will only draft and queue replies. It will not send without approval.",
        })

    def _fetch_recent_emails(self, limit: int = 6) -> List[Dict[str, str]]:
        host = load_setting("IMAP_HOST", "")
        port = int(load_setting("IMAP_PORT", "993") or "993")
        user = load_setting("IMAP_USER", "")
        pwd = load_setting("IMAP_PASSWORD", "")
        if not all([host, port, user, pwd]):
            return []

        emails: List[Dict[str, str]] = []
        with imaplib.IMAP4_SSL(host, port) as conn:
            conn.login(user, pwd)
            conn.select("INBOX")
            status, data = conn.search(None, "UNSEEN")
            ids = data[0].split() if status == "OK" and data else []
            if not ids:
                status, data = conn.search(None, "ALL")
                ids = data[0].split()[-limit:] if status == "OK" and data else []
            for msg_id in reversed(ids[-limit:]):
                status, data = conn.fetch(msg_id, "(RFC822)")
                if status != "OK" or not data or not data[0]:
                    continue
                raw = data[0][1]
                msg = email.message_from_bytes(raw)
                subject = email.header.make_header(email.header.decode_header(msg.get("Subject", "No subject")))
                sender = email.header.make_header(email.header.decode_header(msg.get("From", "Unknown sender")))
                body = self._clean_text(msg)
                category = self._email_category(str(subject), body)
                emails.append({
                    "from": str(sender),
                    "subject": str(subject),
                    "body": body[:900],
                    "category": category,
                    "draft": self._reply_draft(category, str(sender), str(subject)),
                })
        return emails

    def check_email(self) -> None:
        if not self._configured("IMAP_HOST", "IMAP_PORT", "IMAP_USER", "IMAP_PASSWORD"):
            self._add_email_setup_task()
            return
        try:
            messages = self._fetch_recent_emails()
        except Exception as exc:
            self._add({
                "type": "email_error",
                "description": "Email connection failed",
                "destination": "API Settings",
                "risk": "low",
                "reason": "The agent could not log into IMAP with the current settings.",
                "draft": f"Email check failed. Verify IMAP host, port, username, and app password.\n\nError: {exc}",
            })
            return
        if not messages:
            self._add({
                "type": "email_summary",
                "description": "No new unread emails found",
                "destination": "dashboard",
                "risk": "low",
                "reason": "Mailbox checked successfully.",
                "draft": "No unread messages found. The agent can still monitor manually when you run Check Email.",
            })
            return
        for item in messages:
            self._add({
                "type": "email_reply_draft",
                "description": f"{item['category']}: {item['subject'][:80]}",
                "destination": item["from"],
                "risk": "medium" if item["category"] != "RFQ / quote lead" else "high",
                "reason": "Review before replying. The agent does not send automatically.",
                "draft": f"From: {item['from']}\nSubject: {item['subject']}\nCategory: {item['category']}\n\nMessage preview:\n{item['body']}\n\nSuggested reply:\n{item['draft']}",
            })

    def _draft_quote(self) -> Dict:
        return {
            "type": "quote_builder",
            "description": "Build a real quote checklist",
            "destination": "quote packet / customer email",
            "risk": "high",
            "reason": "Pricing and scope must be approved before submission.",
            "draft": "Quote builder checklist:\n\n1. Identify scope\n- Site address\n- SOW/PWS\n- Due date\n- Work hours/access rules\n- Materials provided vs contractor-provided\n\n2. Cost stack\n- Labor hours\n- Drive time/fuel\n- Hotel/food if travel\n- Rentals/lift/ladder\n- Materials/cables/connectors\n- Risk/unknowns\n\n3. Proposal output\n- Total price\n- Assumptions\n- Exclusions\n- Schedule\n- Payment terms\n\n4. Approval\nDo not submit until Ashton confirms final price and scope.",
        }

    def _draft_facebook(self, time_of_day: str = "daily") -> Dict:
        return {
            "type": "facebook_draft",
            "description": f"Draft {time_of_day} AstroBuildCo Facebook post",
            "destination": "AstroBuildCo Facebook Business Page",
            "risk": "medium",
            "reason": "Post must be reviewed before publishing.",
            "draft": "Post option A:\nAstroBuildCo is built on real field execution: tower work, wireless installs, AV support, site troubleshooting, and getting infrastructure online when it matters. Clear scope. Safe work. Clean finish.\n\nPost option B:\nEvery job starts with the same question: what does the site actually need to work reliably? AstroBuildCo focuses on practical solutions, clean installs, and dependable follow-through.\n\nEngagement question:\nWhat matters more on a job site: speed, documentation, or clean workmanship?\n\nHashtags:\n#AstroBuildCo #Telecom #TowerWork #Wireless #AVInstall #SmallBusiness",
        }

    def run_morning_routine(self) -> None:
        self.last_run = "morning"
        self._add(self._briefing("Morning command brief", "Good morning Ashton. Today’s mission: find money opportunities, handle urgent email, draft clean replies, and create one engagement post."))
        self.check_email()
        self._add(self._draft_quote())
        self._add(self._draft_facebook("morning"))

    def run_midday_routine(self) -> None:
        self.last_run = "midday"
        self._add(self._briefing("Midday execution check", "Midday check: clear pending approvals, follow up on quotes, and keep the business moving while you are working."))
        self.check_email()
        self._add(self._draft_facebook("midday"))

    def run_evening_routine(self) -> None:
        self.last_run = "evening"
        self._add(self._briefing("Evening closeout", "Evening recap: capture what happened, what needs follow-up, and what should be first tomorrow."))
        self._add(self._draft_quote())
        self._add({
            "type": "follow_up_plan",
            "description": "Tomorrow follow-up list",
            "destination": "dashboard",
            "risk": "low",
            "reason": "Planning only.",
            "draft": "Tomorrow follow-up template:\n\n- RFQs awaiting response\n- Customers needing scope clarification\n- Quotes to price\n- Emails that need a professional reply\n- Facebook post/engagement check\n- Any government/SAM/PIEE deadlines\n\nUse this list before starting new tasks.",
        })

    def draft_facebook_post(self) -> None:
        self._add(self._draft_facebook("custom"))

    def display_approval_queue(self) -> None:
        if not self.approval_queue:
            print("No pending actions.")
            return
        for action_id, action in self.approval_queue.items():
            print(action_id, action.get("type"), action.get("description"))
            print(action.get("draft", ""))

    def approve_action(self, action_id: str) -> Dict:
        action = self.approval_queue.pop(action_id, None)
        if not action:
            return {"status": "not_found", "action_id": action_id}
        return {"status": "approved_for_review_only", "action_id": action_id, "action": action, "note": "No external send/post/submit hook is active yet."}

    def skip_action(self, action_id: str) -> Dict:
        action = self.approval_queue.pop(action_id, None)
        if not action:
            return {"status": "not_found", "action_id": action_id}
        return {"status": "skipped", "action_id": action_id, "action": action}
