#!/usr/bin/env python3
"""
0102 Autonomous Action Scheduler
WSP 48: Self-improving task scheduling based on natural language

When 012 says "post about the stream in 2 hours" or "schedule a LinkedIn post
for tomorrow at 3pm", 0102 understands and schedules autonomously.
"""

# === UTF-8 ENFORCEMENT (WSP 90) ===
import sys
import io
if __name__ == '__main__' and sys.platform.startswith('win'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (OSError, ValueError):
        # Ignore if stdout/stderr already wrapped or closed
        pass
# === END UTF-8 ENFORCEMENT ===


import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import re

from .simple_posting_orchestrator import SimplePostingOrchestrator, Platform, PostResponse, PostResult

logger = logging.getLogger(__name__)


def _posting_platforms(values: Any) -> Tuple[Platform, ...]:
    """Capture supported, unique targets before a posting dependency can act."""
    error = ('Invalid posting platforms: expected a nonempty unique '
             'list of supported values')
    if (not isinstance(values, list) or not values
            or any(type(value) is not str for value in values)):
        raise ValueError(error)
    try:
        platforms = tuple(Platform(value) for value in values)
    except (TypeError, ValueError):
        raise ValueError(error) from None
    if len(set(platforms)) != len(platforms):
        raise ValueError(error)
    return platforms


def _posting_result_error(response: Any, platforms: Tuple[Platform, ...]) -> Optional[str]:
    """Require coherent complete dependency evidence; this does not verify delivery."""
    if (type(response) is not PostResponse
            or not isinstance(response.results, list) or not response.results):
        return 'Invalid posting response: expected nonempty typed results'
    if any(not isinstance(item, PostResult) or type(item.success) is not bool
           or not isinstance(item.platform, Platform) for item in response.results):
        return 'Invalid posting response: malformed platform result'
    reported = [item.platform for item in response.results]
    if len(set(reported)) != len(reported) or set(reported) != set(platforms):
        return 'Invalid posting response: platform coverage mismatch'
    successes = sum(item.success for item in response.results)
    failures = len(response.results) - successes
    if (type(response.success_count) is not int or type(response.failure_count) is not int
            or response.success_count != successes or response.failure_count != failures):
        return 'Invalid posting response: inconsistent counts'
    if failures:
        return 'Posting did not succeed on all requested platforms'
    return None


class ActionType(Enum):
    """Types of actions 0102 can schedule"""
    POST_SOCIAL = "post_social"
    CHECK_STREAM = "check_stream"
    SEND_MESSAGE = "send_message"
    REMIND = "remind"
    EXECUTE_CODE = "execute_code"
    CUSTOM = "custom"

@dataclass
class ScheduledAction:
    """An action scheduled by 0102 based on 012 request"""
    id: str
    action_type: ActionType
    description: str  # Natural language description
    parameters: Dict[str, Any]
    scheduled_time: datetime
    requested_by: str  # "012" or command source
    requested_at: datetime
    status: str = "pending"  # pending, executed, failed, cancelled
    result: Optional[Any] = None
    error: Optional[str] = None

class AutonomousActionScheduler:
    """
    0102's action scheduling system that understands natural language.

    Examples 012 can say:
    - "Post about the stream in 30 minutes"
    - "Schedule a LinkedIn post for 3pm"
    - "Remind me to check the stream in an hour"
    - "Post to X when the stream goes live"
    - "Every day at 9am, post a good morning message"
    """

    def __init__(self):
        self.orchestrator = SimplePostingOrchestrator()
        self.schedule_file = "memory/0102_scheduled_actions.json"
        self.scheduled_actions: Dict[str, ScheduledAction] = {}
        self.load_schedule()

        # Natural language patterns for time parsing
        self.time_patterns = {
            r"in (\d+) (minute|min)s?": self._parse_minutes,
            r"in (\d+) (hour|hr)s?": self._parse_hours,
            r"in (\d+) (day)s?": self._parse_days,
            r"at (\d{1,2}):?(\d{2})?\s*(am|pm)?": self._parse_time,
            r"tomorrow at (\d{1,2}):?(\d{2})?\s*(am|pm)?": self._parse_tomorrow,
            r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)": self._parse_weekday,
            r"when.*stream.*live": self._parse_stream_trigger,
            r"now": self._parse_now,
            r"immediately": self._parse_now,
        }

        # Platform detection patterns
        self.platform_patterns = {
            "linkedin": Platform.LINKEDIN,
            "ln": Platform.LINKEDIN,
            "twitter": Platform.X_TWITTER,
            "x": Platform.X_TWITTER,
            "both": [Platform.LINKEDIN, Platform.X_TWITTER],
            "all": [Platform.LINKEDIN, Platform.X_TWITTER],
        }

        logger.info("[0102 SCHEDULER] Autonomous action scheduler initialized")
        logger.info("[0102 SCHEDULER] Ready to understand natural language commands")

    def understand_command(self, command: str, context: Dict = None) -> ScheduledAction:
        """
        Parse natural language command from 012 and create scheduled action.

        Examples:
        - "Post 'Going live soon!' to LinkedIn in 30 minutes"
        - "Schedule a post about quantum computing for 3pm on both platforms"
        - "Remind me to check the stream status in an hour"
        """
        command_lower = command.lower()

        # Determine action type
        action_type = self._determine_action_type(command_lower)

        # Extract timing
        scheduled_time = self._extract_time(command_lower)

        # Extract parameters based on action type
        # Note: Pass original command for content extraction to preserve case
        parameters = self._extract_parameters(command, action_type, context)

        # Generate unique ID
        import uuid
        action_id = f"action_{uuid.uuid4().hex[:8]}"

        # Create scheduled action
        action = ScheduledAction(
            id=action_id,
            action_type=action_type,
            description=command,
            parameters=parameters,
            scheduled_time=scheduled_time,
            requested_by="012",
            requested_at=datetime.now()
        )

        # Save to schedule
        self.scheduled_actions[action_id] = action
        self.save_schedule()

        # Log what 0102 understood
        self._log_understanding(command, action)

        return action

    def _determine_action_type(self, command: str) -> ActionType:
        """Determine what type of action is being requested"""
        if any(word in command for word in ["post", "tweet", "share", "publish"]):
            return ActionType.POST_SOCIAL
        elif "remind" in command:
            return ActionType.REMIND
        elif "check" in command and "stream" in command:
            return ActionType.CHECK_STREAM
        elif "message" in command or "tell" in command:
            return ActionType.SEND_MESSAGE
        elif "run" in command or "execute" in command:
            return ActionType.EXECUTE_CODE
        else:
            return ActionType.CUSTOM

    def _extract_time(self, command: str) -> datetime:
        """Extract scheduled time from natural language"""
        for pattern, parser in self.time_patterns.items():
            match = re.search(pattern, command)
            if match:
                return parser(match)

        # Default to 5 minutes from now if no time specified
        return datetime.now() + timedelta(minutes=5)

    def _parse_minutes(self, match) -> datetime:
        """Parse 'in X minutes' format"""
        minutes = int(match.group(1))
        return datetime.now() + timedelta(minutes=minutes)

    def _parse_hours(self, match) -> datetime:
        """Parse 'in X hours' format"""
        hours = int(match.group(1))
        return datetime.now() + timedelta(hours=hours)

    def _parse_days(self, match) -> datetime:
        """Parse 'in X days' format"""
        days = int(match.group(1))
        return datetime.now() + timedelta(days=days)

    def _parse_time(self, match) -> datetime:
        """Parse 'at HH:MM am/pm' format"""
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        am_pm = match.group(3)

        if am_pm and am_pm.lower() == 'pm' and hour < 12:
            hour += 12
        elif am_pm and am_pm.lower() == 'am' and hour == 12:
            hour = 0

        # Set for today or tomorrow based on if time has passed
        target = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target < datetime.now():
            target += timedelta(days=1)

        return target

    def _parse_tomorrow(self, match) -> datetime:
        """Parse 'tomorrow at X' format"""
        base = self._parse_time(match)
        return base + timedelta(days=1)

    def _parse_weekday(self, match) -> datetime:
        """Parse weekday names"""
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        target_day = weekdays.index(match.group(1).lower())
        today = datetime.now().weekday()
        days_ahead = (target_day - today) % 7
        if days_ahead == 0:  # Same day next week
            days_ahead = 7
        return datetime.now() + timedelta(days=days_ahead)

    def _parse_stream_trigger(self, match) -> datetime:
        """Parse stream-based triggers"""
        # This would integrate with stream detection
        # For now, check every 5 minutes
        return datetime.now() + timedelta(minutes=5)

    def _parse_now(self, match) -> datetime:
        """Parse immediate execution"""
        return datetime.now()

    def _extract_parameters(self, command: str, action_type: ActionType, context: Dict) -> Dict:
        """Extract action-specific parameters from command"""
        params = {}

        if action_type == ActionType.POST_SOCIAL:
            # Extract content (text in quotes) - use original command to preserve case
            content_match = re.search(r"['\"]([^'\"]+)['\"]", command)
            if content_match:
                params['content'] = content_match.group(1)
            else:
                # Use context or generate content
                if context and 'stream_title' in context:
                    params['content'] = f"[U+1F534] Going live: {context['stream_title']}"
                else:
                    params['content'] = "Scheduled post from 0102"

            # Extract platforms - use lowercase for matching
            command_lower = command.lower()
            platforms = []
            for platform_key, platform_value in self.platform_patterns.items():
                if platform_key in command_lower:
                    if isinstance(platform_value, list):
                        platforms.extend(platform_value)
                    else:
                        platforms.append(platform_value)

            # Default to both if not specified
            if not platforms:
                platforms = [Platform.LINKEDIN, Platform.X_TWITTER]

            params['platforms'] = [p.value for p in platforms]

            # Add stream context if available
            if context:
                params['metadata'] = context

        elif action_type == ActionType.REMIND:
            # Extract reminder message
            params['message'] = command.replace("remind me to", "").replace("remind", "").strip()

        elif action_type == ActionType.CHECK_STREAM:
            params['check_type'] = 'live_status'
            if context and 'channel_id' in context:
                params['channel_id'] = context['channel_id']

        return params

    def _log_understanding(self, original_command: str, action: ScheduledAction):
        """Log what 0102 understood from the command"""
        logger.info("[0102 UNDERSTANDING] =" * 30)
        logger.info(f"[0102] 012 said: '{original_command}'")
        logger.info(f"[0102] I understood:")
        logger.info(f"  - Action: {action.action_type.value}")
        logger.info(f"  - When: {action.scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"  - Time from now: {(action.scheduled_time - datetime.now()).total_seconds()/60:.1f} minutes")

        if action.action_type == ActionType.POST_SOCIAL:
            logger.info(f"  - Platforms: {action.parameters.get('platforms', [])}")
            logger.info(f"  - Content: {action.parameters.get('content', '')[:50]}...")

        logger.info(f"[0102] Scheduled as: {action.id}")
        logger.info("[0102] =" * 30)

    async def execute_pending_actions(self) -> List[Tuple[str, Any]]:
        """
        Execute any actions that are due.
        Called periodically by 0102 main loop.
        """
        results = []
        now = datetime.now()

        for action_id, action in list(self.scheduled_actions.items()):
            if action.status == "pending" and action.scheduled_time <= now:
                logger.info(f"[0102 EXECUTOR] Executing action: {action_id}")
                logger.info(f"[0102 EXECUTOR] Type: {action.action_type.value}")

                try:
                    platforms = (_posting_platforms(action.parameters.get('platforms'))
                                 if action.action_type == ActionType.POST_SOCIAL else ())
                    result = await self._execute_action(action, platforms)
                    action.result = result
                    action.error = (_posting_result_error(result, platforms)
                                    if platforms else None)
                    action.status = "failed" if action.error else "executed"
                    results.append((action_id, result))
                    if action.error:
                        logger.error(f"[0102 EXECUTOR] [FAIL] Failed to execute {action_id}: {action.error}")
                    else:
                        logger.info(f"[0102 EXECUTOR] [OK] Completed scheduled operation {action_id}")

                except Exception as e:
                    action.status = "failed"
                    action.error = str(e)
                    logger.error(f"[0102 EXECUTOR] [FAIL] Failed to execute {action_id}: {e}")
                    results.append((action_id, {"error": str(e)}))

        if results:
            self.save_schedule()

        return results

    async def _execute_action(
        self, action: ScheduledAction, platforms: Tuple[Platform, ...] = ()
    ) -> Any:
        """Execute a specific action based on its type"""
        if action.action_type == ActionType.POST_SOCIAL:
            # Retain the existing required content field and stream-only boundary.
            _ = action.parameters['content']
            metadata = action.parameters.get('metadata', {})
            if 'stream_url' in metadata:
                targets = platforms or _posting_platforms(action.parameters.get('platforms'))
                return await self.orchestrator.post_stream_notification(
                    stream_title=metadata.get('stream_title', 'Live Stream'),
                    stream_url=metadata['stream_url'],
                    platforms=list(targets)
                )

        elif action.action_type == ActionType.REMIND:
            # Log the reminder
            message = action.parameters.get('message', 'Reminder')
            logger.info(f"[0102 REMINDER] ⏰ REMINDER: {message}")
            logger.info(f"[0102 REMINDER] Requested by 012 at {action.requested_at}")
            return {"reminded": True, "message": message}

        raise NotImplementedError(f"Unsupported scheduled action: {action.action_type.value}")

    def load_schedule(self):
        """Load scheduled actions from file"""
        if os.path.exists(self.schedule_file):
            try:
                with open(self.schedule_file, 'r', encoding="utf-8") as f:
                    data = json.load(f)
                    for action_id, action_data in data.items():
                        # Convert strings to proper types
                        action_data['scheduled_time'] = datetime.fromisoformat(action_data['scheduled_time'])
                        action_data['requested_at'] = datetime.fromisoformat(action_data['requested_at'])
                        action_data['action_type'] = ActionType(action_data['action_type'])
                        self.scheduled_actions[action_id] = ScheduledAction(**action_data)

                logger.info(f"[0102 SCHEDULER] Loaded {len(self.scheduled_actions)} scheduled actions")
            except Exception as e:
                logger.error(f"[0102 SCHEDULER] Error loading schedule: {e}")

    def save_schedule(self):
        """Save scheduled actions to file"""
        try:
            os.makedirs("memory", exist_ok=True)

            data = {}
            for action_id, action in self.scheduled_actions.items():
                action_dict = {
                    'id': action.id,
                    'action_type': action.action_type.value,
                    'description': action.description,
                    'parameters': action.parameters,
                    'scheduled_time': action.scheduled_time.isoformat(),
                    'requested_by': action.requested_by,
                    'requested_at': action.requested_at.isoformat(),
                    'status': action.status,
                    'result': action.result,
                    'error': action.error
                }
                data[action_id] = action_dict

            with open(self.schedule_file, 'w', encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"[0102 SCHEDULER] Error saving schedule: {e}")

    def get_pending_actions(self) -> List[ScheduledAction]:
        """Get all pending actions sorted by time"""
        pending = [a for a in self.scheduled_actions.values() if a.status == "pending"]
        return sorted(pending, key=lambda a: a.scheduled_time)

    def cancel_action(self, action_id: str) -> bool:
        """Cancel a scheduled action"""
        if action_id in self.scheduled_actions:
            self.scheduled_actions[action_id].status = "cancelled"
            self.save_schedule()
            logger.info(f"[0102 SCHEDULER] Cancelled action {action_id}")
            return True
        return False


# Example usage for testing
async def test_natural_language():
    """Test natural language understanding"""
    scheduler = AutonomousActionScheduler()

    # Test commands 012 might say
    test_commands = [
        "Post 'Going live with AI development!' to LinkedIn in 30 minutes",
        "Schedule a post about quantum computing for 3pm on both platforms",
        "Post to X in 2 hours",
        "Remind me to check the stream in an hour",
        "Post 'Stream starting soon!' immediately",
        "Schedule LinkedIn post for tomorrow at 9am",
    ]

    print("\n[0102] Testing natural language understanding:")
    print("=" * 60)

    for command in test_commands:
        action = scheduler.understand_command(command)
        print(f"\n012: '{command}'")
        print(f"0102 will: {action.action_type.value} at {action.scheduled_time.strftime('%H:%M on %Y-%m-%d')}")
        if action.parameters:
            print(f"     with: {action.parameters}")

    print("\n[0102] Pending actions:")
    for action in scheduler.get_pending_actions():
        time_until = (action.scheduled_time - datetime.now()).total_seconds() / 60
        print(f"  - {action.id}: {action.description[:50]}... in {time_until:.1f} minutes")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_natural_language())
