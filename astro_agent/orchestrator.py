from __future__ import annotations

import uuid
from typing import Dict, List


class Orchestrator:
    def __init__(self) -> None:
        self.approval_queue: Dict[str, Dict] = {}

    def _add(self, task: Dict) -> str:
        action_id = str(uuid.uuid4())
        self.approval_queue[action_id] = task
        return action_id

    def _draft_email(self) -> Dict:
        return {
            "type": "email",
            "description": "Draft professional reply",
            "destination": "customer / RFQ contact",
            "risk": "medium",
            "reason": "Needs Ashton approval before sending.",
            "draft": "Dear [Name],\n\nThank you for reaching out to AstroBuild&Co. I reviewed your message and would be happy to assist. Please send any scope details, site address, required timeline, and supporting documents so I can prepare the most accurate response.\n\nSincerely,\nAshton Hill\nAstroBuild&Co., LLC\n937-765-3581\nashtonhill@astrobuildco.org",
        }

    def _draft_quote(self) -> Dict:
        return {
            "type": "quote",
            "description": "Draft quote notes",
            "destination": "quote packet / customer email",
            "risk": "high",
            "reason": "Pricing must be approved before submission.",
            "draft": "Quote Notes\n- Pricing style: job-based, lowest realistic grind price.\n- Target profit margin: 15%.\n- Include labor, travel, hotel, food, materials, equipment rental, risk, urgency, and difficulty.\n- Payment terms: Net 30.\n- Quote expiration: 60 days.\n\nMissing info to confirm before final quote:\n1. Exact site address\n2. SOW/PWS\n3. Required completion date\n4. Materials provided vs contractor-provided\n5. Access/lift requirements",
        }

    def _draft_facebook(self, time_of_day: str = "daily") -> Dict:
        return {
            "type": "facebook",
            "description": f"Draft {time_of_day} Facebook Business Page post",
            "destination": "AstroBuild&Co. Facebook Business Page",
            "risk": "medium",
            "reason": "Post must be reviewed before publishing.",
            "draft": "AstroBuild&Co. is built around real field work, reliable execution, and keeping critical infrastructure connected. From tower work to AV installs and contract support, we bring a hands-on approach to every job.\n\nWhat matters most on any project? Clear scope, safe execution, and finishing the job right.\n\n#TowerWork #Telecom #AVInstall #SmallBusiness #AstroBuildCo",
        }

    def run_morning_routine(self) -> None:
        self._add({
            "type": "summary",
            "description": "Morning briefing",
            "destination": "dashboard",
            "risk": "low",
            "reason": "Daily planning only.",
            "draft": "Good morning Ashton. Priorities: check urgent emails, identify RFQs/deadlines, prepare quote drafts, and draft the first Facebook post. Nothing sends or posts without your approval.",
        })
        self._add(self._draft_email())
        self._add(self._draft_quote())
        self._add(self._draft_facebook("morning"))

    def run_midday_routine(self) -> None:
        self._add({
            "type": "summary",
            "description": "Midday check-in",
            "destination": "dashboard",
            "risk": "low",
            "reason": "Daily planning only.",
            "draft": "Midday check-in: review new email, update RFQ/quote progress, check pending approvals, draft second Facebook post if needed.",
        })
        self._add(self._draft_email())
        self._add(self._draft_facebook("midday"))

    def run_evening_routine(self) -> None:
        self._add({
            "type": "summary",
            "description": "Evening recap",
            "destination": "dashboard",
            "risk": "low",
            "reason": "Daily planning only.",
            "draft": "Evening recap: review what got done, unresolved opportunities, follow-ups needed, and tomorrow's priority list.",
        })
        self._add(self._draft_email())
        self._add(self._draft_quote())

    def check_email(self) -> None:
        self._add(self._draft_email())

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
        # Real send/post hooks go here after approval.
        return {"status": "approved", "action_id": action_id, "action": action}

    def skip_action(self, action_id: str) -> Dict:
        action = self.approval_queue.pop(action_id, None)
        if not action:
            return {"status": "not_found", "action_id": action_id}
        return {"status": "skipped", "action_id": action_id, "action": action}
