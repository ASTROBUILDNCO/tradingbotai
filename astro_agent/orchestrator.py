from __future__ import annotations

import email
import imaplib
import uuid
from datetime import datetime
from email.header import decode_header, make_header
from email.message import Message
from typing import Dict, List, Optional

from tools.config_store import load_setting
from tools.discord_notify import dashboard_url, discord_configured, send_discord_message


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
            ("No-setup tools", True),
            ("Inbound email", self._configured("IMAP_HOST", "IMAP_PORT", "IMAP_USER", "IMAP_PASSWORD")),
            ("Outbound email", self._configured("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD")),
            ("Discord Jarvis voice", discord_configured()),
            ("Facebook page", self._configured("META_PAGE_ID", "META_PAGE_ACCESS_TOKEN")),
            ("Approval lock", (load_setting("APPROVAL_REQUIRED", "true") or "true").lower() == "true"),
        ]
        return [f"{'READY' if ok else 'OPTIONAL'} - {name}" for name, ok in checks]

    def _briefing(self, title: str, focus: str) -> Dict:
        status = "\n".join(self._setup_status())
        return {
            "type": "briefing",
            "description": title,
            "destination": "AstroBuildCo command center",
            "risk": "low",
            "reason": "Planning and visibility only.",
            "draft": f"{focus}\n\nSystem status:\n{status}\n\nJarvis operating rules:\n1. Find and organize work aggressively.\n2. Draft replies, quote notes, lead lists, and posts.\n3. Put anything external into the approval queue.\n4. Never send, post, submit, spend, delete, or modify business records without Ashton approving it.\n\nNo-setup tools still work: paste an email/RFQ, run quick quote math, and review every approval card before using it.",
        }

    def _email_category(self, subject: str, body: str) -> str:
        text = f"{subject} {body}".lower()
        if any(word in text for word in ["rfq", "quote", "solicitation", "sam.gov", "bid", "proposal", "sow", "pws"]):
            return "RFQ / quote lead"
        if any(word in text for word in ["invoice", "payment", "receipt", "past due"]):
            return "billing / money"
        if any(word in text for word in ["urgent", "asap", "deadline", "due today", "close of business"]):
            return "urgent follow-up"
        if any(word in text for word in ["tower", "site", "fiber", "tarana", "install", "av", "chapel", "wireless"]):
            return "field work / operations"
        return "general business"

    def _reply_draft(self, category: str, sender: str = "", subject: str = "") -> str:
        if category == "RFQ / quote lead":
            return "Good afternoon,\n\nThank you for reaching out to AstroBuildCo. I can review this requirement and prepare a response. Please send the full scope of work, site address, due date, required forms, and whether materials are customer/government furnished or contractor furnished.\n\nOnce I have the full details, I will confirm pricing, schedule, and execution approach.\n\nV/r,\nAshton Hill\nAstroBuildCo, LLC\n937-765-3581\nashtonhill@astrobuildco.org"
        if category == "billing / money":
            return "Good afternoon,\n\nI received your message and will review the billing/payment details. Please send any invoice number, PO number, service date, and supporting documentation so I can verify everything accurately.\n\nThank you,\nAshton Hill\nAstroBuildCo, LLC"
        if category == "field work / operations":
            return "Good afternoon,\n\nThanks for the details. I can take a look at the site/work request. Please confirm the site address, access window, required completion date, contact on site, and any photos, drawings, or scope documents available.\n\nV/r,\nAshton Hill\nAstroBuildCo, LLC"
        return "Good afternoon,\n\nThank you for reaching out to AstroBuildCo. I reviewed your message and will follow up with the correct details shortly.\n\nV/r,\nAshton Hill\nAstroBuildCo, LLC"

    def analyze_pasted_message(self, raw_text: str) -> None:
        text = (raw_text or "").strip()
        if not text:
            self._add({
                "type": "manual_tool",
                "description": "Paste tool needs content",
                "destination": "dashboard",
                "risk": "low",
                "reason": "No message was provided.",
                "draft": "Paste an email, RFQ, solicitation note, or customer message into the quick draft box and run it again.",
            })
            return
        category = self._email_category("", text)
        questions = [
            "Exact site address / location",
            "Required completion date or response deadline",
            "Full scope of work / drawings / photos",
            "Materials provided vs contractor-provided",
            "Access rules, work hours, lift/ladder requirements",
        ]
        self._add({
            "type": "quick_reply",
            "description": f"Quick draft from pasted message: {category}",
            "destination": "copy/paste reply",
            "risk": "high" if category == "RFQ / quote lead" else "medium",
            "reason": "This was generated from pasted text and should be reviewed before sending.",
            "draft": f"Detected type: {category}\n\nOriginal preview:\n{text[:1200]}\n\nSuggested reply:\n{self._reply_draft(category)}\n\nInfo to verify before committing:\n- " + "\n- ".join(questions),
        })

    def build_quick_quote(self, job_name: str, labor_hours: str, labor_rate: str, materials: str, travel: str, rental: str, margin: str) -> None:
        def money(value: str, default: float = 0.0) -> float:
            try:
                return float(str(value).replace("$", "").replace(",", "").strip() or default)
            except Exception:
                return default

        hours = money(labor_hours)
        rate = money(labor_rate, 75.0)
        mat = money(materials)
        trav = money(travel)
        rent = money(rental)
        margin_pct = money(margin, 20.0)
        cost = (hours * rate) + mat + trav + rent
        price = cost / (1 - (margin_pct / 100)) if margin_pct < 95 else cost * 1.25
        profit = price - cost
        name = (job_name or "Quick job").strip()
        self._add({
            "type": "quick_quote",
            "description": f"Quick quote math: {name}",
            "destination": "quote review",
            "risk": "high",
            "reason": "Price math is a working draft, not a final bid/submission.",
            "draft": f"{name}\n\nCost build:\n- Labor: {hours:.1f} hrs x ${rate:.2f}/hr = ${hours * rate:,.2f}\n- Materials: ${mat:,.2f}\n- Travel / fuel / food: ${trav:,.2f}\n- Rental / lift / tools: ${rent:,.2f}\n\nEstimated cost: ${cost:,.2f}\nTarget margin: {margin_pct:.1f}%\nSuggested sell price: ${price:,.2f}\nExpected gross profit: ${profit:,.2f}\n\nProposal wording:\nAstroBuildCo can complete the requested work for a total price of ${price:,.2f}, based on the current scope and assumptions. Price includes labor, standard tools, travel allowance, and listed materials/rentals. Final pricing is subject to confirmation of site access, completion deadline, materials provided, and any lift or special access requirements.",
        })

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

    def _add_email_setup_task(self) -> None:
        self._add({
            "type": "optional_setup",
            "description": "Auto email is optional",
            "destination": "API Settings",
            "risk": "low",
            "reason": "The no-setup paste tool works now; auto email needs IMAP later.",
            "draft": "You do not need email setup to use this app. Use Paste Email/RFQ for immediate value.\n\nAuto email is optional later. To enable it, add IMAP_HOST, IMAP_PORT, IMAP_USER, and IMAP_PASSWORD in Settings.",
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
                subject = make_header(decode_header(msg.get("Subject", "No subject")))
                sender = make_header(decode_header(msg.get("From", "Unknown sender")))
                body = self._clean_text(msg)
                category = self._email_category(str(subject), body)
                emails.append({"from": str(sender), "subject": str(subject), "body": body[:900], "category": category, "draft": self._reply_draft(category, str(sender), str(subject))})
        return emails

    def check_email(self) -> None:
        if not self._configured("IMAP_HOST", "IMAP_PORT", "IMAP_USER", "IMAP_PASSWORD"):
            self._add_email_setup_task()
            return
        try:
            messages = self._fetch_recent_emails()
        except Exception as exc:
            self._add({"type": "email_error", "description": "Email connection failed", "destination": "API Settings", "risk": "low", "reason": "The agent could not log into IMAP with the current settings.", "draft": f"Email check failed. Verify IMAP host, port, username, and app password.\n\nError: {exc}"})
            return
        if not messages:
            self._add({"type": "email_summary", "description": "No new unread emails found", "destination": "dashboard", "risk": "low", "reason": "Mailbox checked successfully.", "draft": "No unread messages found. The paste tool still works for any message you copy in manually."})
            return
        for item in messages:
            self._add({"type": "email_reply_draft", "description": f"{item['category']}: {item['subject'][:80]}", "destination": item["from"], "risk": "medium" if item["category"] != "RFQ / quote lead" else "high", "reason": "Review before replying. The agent does not send automatically.", "draft": f"From: {item['from']}\nSubject: {item['subject']}\nCategory: {item['category']}\n\nMessage preview:\n{item['body']}\n\nSuggested reply:\n{item['draft']}"})

    def _draft_quote(self) -> Dict:
        return {
            "type": "quote_builder",
            "description": "Quote checklist",
            "destination": "quote review",
            "risk": "high",
            "reason": "Pricing and scope must be approved before submission.",
            "draft": "Use Quick Quote for immediate math. Then verify: exact site address, scope/SOW, deadline, materials provided, access, lift/rental, travel, and payment terms.\n\nJarvis quote focus:\n- Push small jobs under $10k when they fit AstroBuildCo.\n- Flag anything near Dayton first.\n- Favor low-voltage, AV, Cat6, wireless, tower-adjacent, camera, and service-call work.\n- Do not submit anything without Ashton approval.",
        }

    def _draft_facebook(self, time_of_day: str = "daily") -> Dict:
        return {"type": "facebook_draft", "description": f"Draft {time_of_day} AstroBuildCo Facebook post", "destination": "copy/paste Facebook", "risk": "medium", "reason": "Post must be reviewed before publishing.", "draft": "Post option A:\nAstroBuildCo is built on real field execution: tower work, wireless installs, AV support, site troubleshooting, and getting infrastructure online when it matters. Clear scope. Safe work. Clean finish.\n\nPost option B:\nEvery job starts with the same question: what does the site actually need to work reliably? AstroBuildCo focuses on practical solutions, clean installs, and dependable follow-through.\n\nEngagement question:\nWhat matters more on a job site: speed, documentation, or clean workmanship?\n\n#AstroBuildCo #Telecom #TowerWork #Wireless #AVInstall #SmallBusiness"}

    def _lead_radar(self) -> Dict:
        terms = load_setting("LEAD_SEARCH_TERMS", "")
        if not terms:
            terms = "low voltage, AV install, sound system, projector, Cat6, network wiring, wireless install, tower, Tarana, camera install, small construction, site service"
        local = load_setting("LOCAL_LEAD_MARKET", "Dayton, Troy, Wright-Patterson AFB, Miami Valley, Ohio")
        return {
            "type": "lead_radar",
            "description": "Jarvis lead radar targets",
            "destination": "lead finder",
            "risk": "medium",
            "reason": "This prepares lead-search targets. Review each lead before contacting anyone or bidding.",
            "draft": f"Lead search mission:\nFind small, winnable jobs Ashton can execute or coordinate with high leverage.\n\nPriority market:\n{local}\n\nHigh-fit keywords:\n{terms}\n\nBest-fit work:\n- RFQs under $10k where AstroBuildCo can make at least $3k gross profit.\n- Low-voltage / Cat6 / AV / projector / sound-system installs.\n- Wireless, WISP, tower-adjacent, Tarana, troubleshooting, site repair, and closeout work.\n- Local government, churches, schools, small businesses, property managers, and telecom subs.\n\nJarvis action:\n1. Search lead sources.\n2. Rank by fit, deadline, distance, risk, and expected profit.\n3. Draft outreach or quote questions.\n4. Put everything in the approval queue before any contact is made.",
        }

    def run_lead_finder(self) -> None:
        self._add(self._lead_radar())
        self._send_discord_brief("Lead Finder Triggered", "I queued the current lead-search targets and next money moves.")

    def _queue_preview(self, limit: int = 5) -> List[str]:
        recent = list(self.approval_queue.values())[-limit:]
        return [f"- {item.get('description', 'Output card')} ({item.get('risk', 'low')} risk)" for item in recent]

    def _send_discord_brief(self, title: str, focus: str) -> Dict[str, str]:
        pending = len(self.approval_queue)
        preview = "\n".join(self._queue_preview()) or "- No cards queued yet"
        link = dashboard_url()
        link_line = f"\nDashboard: {link}" if link else "\nDashboard link: set DASHBOARD_BASE_URL in Settings or Render env."
        message = (
            f"**AstroBuildCo Jarvis — {title}**\n\n"
            f"{focus}\n\n"
            f"Pending approval cards: **{pending}**\n\n"
            f"Top cards:\n{preview}\n\n"
            f"Operating rule: I can search, summarize, draft, rank, and remind. I do **not** send, post, submit, delete, or spend without Ashton approving it."
            f"{link_line}"
        )
        return send_discord_message(message)

    def send_discord_test(self) -> Dict[str, str]:
        result = self._send_discord_brief("Discord Test", "Jarvis voice check. Discord notifications are connected if you are reading this there.")
        if not discord_configured():
            self._add({
                "type": "optional_setup",
                "description": "Connect Discord Jarvis voice",
                "destination": "API Settings",
                "risk": "low",
                "reason": "Discord needs a webhook URL before Jarvis can message you.",
                "draft": "Add DISCORD_WEBHOOK_URL in Settings or Render Environment Variables. Then press Send Discord Test again.\n\nFor best dashboard links, also set DASHBOARD_BASE_URL to your Render app URL.",
            })
        return result

    def run_morning_routine(self) -> None:
        self.last_run = "morning"
        if self._configured("IMAP_HOST", "IMAP_PORT", "IMAP_USER", "IMAP_PASSWORD"):
            self.check_email()
        self._add(self._briefing("Morning Jarvis brief", "Good morning Ashton. First move: clear the approval cards that can create money today. I checked the available setup, queued quote/post/lead actions, and kept all external actions locked behind approval."))
        self._add(self._lead_radar())
        self._add(self._draft_quote())
        self._add(self._draft_facebook("morning"))
        self._send_discord_brief("Morning Brief", "Morning routine completed. Review email/RFQ cards first, then leads, then quote math, then the Facebook post draft.")

    def run_midday_routine(self) -> None:
        self.last_run = "midday"
        if self._configured("IMAP_HOST", "IMAP_PORT", "IMAP_USER", "IMAP_PASSWORD"):
            self.check_email()
        self._add(self._briefing("Midday Jarvis check-in", "Midday check: keep momentum. Review any new email replies, push the best lead, and clear one quote or outreach card."))
        self._add(self._lead_radar())
        self._add(self._draft_facebook("midday"))
        self._send_discord_brief("Midday Check-In", "Midday routine completed. I queued current priorities and any email cards available.")

    def run_evening_routine(self) -> None:
        self.last_run = "evening"
        self._add(self._briefing("Evening closeout", "Evening recap: capture what happened, what needs follow-up, and what should be first tomorrow."))
        self._add({"type": "follow_up_plan", "description": "Tomorrow follow-up list", "destination": "dashboard", "risk": "low", "reason": "Planning only.", "draft": "Tomorrow follow-up template:\n\n- RFQs awaiting response\n- Customers needing scope clarification\n- Quotes to price\n- Emails that need a professional reply\n- Facebook post/engagement check\n- Any SAM/PIEE deadlines\n- Best local lead to chase first\n\nUse this list before starting new tasks."})
        self._send_discord_brief("Evening Closeout", "Evening routine completed. The dashboard now has tomorrow follow-up targets.")

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
        return {"status": "approved_for_review_only", "action_id": action_id, "action": action, "note": "No external send/post/submit hook is active."}

    def skip_action(self, action_id: str) -> Dict:
        action = self.approval_queue.pop(action_id, None)
        if not action:
            return {"status": "not_found", "action_id": action_id}
        return {"status": "skipped", "action_id": action_id, "action": action}
