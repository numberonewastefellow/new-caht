from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from functools import lru_cache
from itertools import groupby
from typing import Dict
from typing import List
from typing import Tuple
from uuid import UUID

from dateutil import tz
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session

from om.auth.users import current_chat_accessible_user
from om.db.api_key import is_api_key_email_address
from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.models import ChatMessage
from om.db.models import ChatSession
from om.db.models import TokenRateLimit
from om.db.models import TokenRateLimit__Team
from om.db.models import User
from om.db.models import User__Team
from om.db.models import Team
from om.db.token_limit import fetch_all_global_token_rate_limits
from om.db.token_limit import fetch_all_user_token_rate_limits
from om.utils.logger import setup_logger
from om.utils.threadpool_concurrency import run_functions_tuples_in_parallel


logger = setup_logger()


TOKEN_BUDGET_UNIT = 1_000


def check_token_rate_limits(
    user: User = Depends(current_chat_accessible_user),
) -> None:
    # short circuit if no rate limits are set up
    # NOTE: result of `any_rate_limit_exists` is cached, so this call is fast 99% of the time
    if not any_rate_limit_exists():
        return

    return _check_token_rate_limits(user)


def _check_token_rate_limits(user: User) -> None:
    # Anonymous users are only rate limited by global settings
    if user.is_anonymous:
        _user_is_rate_limited_by_global()

    elif is_api_key_email_address(user.email):
        # API keys are only rate limited by global settings
        _user_is_rate_limited_by_global()

    else:
        run_functions_tuples_in_parallel(
            [
                (_user_is_rate_limited, (user.id,)),
                (_user_is_rate_limited_by_group, (user.id,)),
                (_user_is_rate_limited_by_global, ()),
            ]
        )


"""
User rate limits
"""


def _user_is_rate_limited(user_id: UUID) -> None:
    with get_session_with_current_tenant() as db_session:
        user_rate_limits = fetch_all_user_token_rate_limits(
            db_session=db_session, enabled_only=True, ordered=False
        )

        if user_rate_limits:
            user_cutoff_time = _get_cutoff_time(user_rate_limits)
            user_usage = _fetch_user_usage(user_id, user_cutoff_time, db_session)

            if _is_rate_limited(user_rate_limits, user_usage):
                raise HTTPException(
                    status_code=429,
                    detail="Token budget exceeded for user. Try again later.",
                )


def _fetch_user_usage(
    user_id: UUID, cutoff_time: datetime, db_session: Session
) -> Sequence[tuple[datetime, int]]:
    """
    Fetch user usage within the cutoff time, grouped by minute
    """
    result = db_session.execute(
        select(
            func.date_trunc("minute", ChatMessage.time_sent),
            func.sum(ChatMessage.token_count),
        )
        .join(ChatSession, ChatMessage.chat_session_id == ChatSession.id)
        .where(ChatSession.user_id == user_id, ChatMessage.time_sent >= cutoff_time)
        .group_by(func.date_trunc("minute", ChatMessage.time_sent))
    ).all()

    return [(row[0], row[1]) for row in result]


"""
User Group rate limits
"""


def _user_is_rate_limited_by_group(user_id: UUID) -> None:
    with get_session_with_current_tenant() as db_session:
        group_rate_limits = _fetch_all_team_rate_limits(user_id, db_session)

        if group_rate_limits:
            # Group cutoff time is the same for all groups.
            # This could be optimized to only fetch the maximum cutoff time for
            # a specific group, but seems unnecessary for now.
            group_cutoff_time = _get_cutoff_time(
                [e for sublist in group_rate_limits.values() for e in sublist]
            )

            team_ids = list(group_rate_limits.keys())
            group_usage = _fetch_team_usage(
                team_ids, group_cutoff_time, db_session
            )

            has_at_least_one_untriggered_limit = False
            for team_id, rate_limits in group_rate_limits.items():
                usage = group_usage.get(team_id, [])

                if not _is_rate_limited(rate_limits, usage):
                    has_at_least_one_untriggered_limit = True
                    break

            if not has_at_least_one_untriggered_limit:
                raise HTTPException(
                    status_code=429,
                    detail="Token budget exceeded for user's groups. Try again later.",
                )


def _fetch_all_team_rate_limits(
    user_id: UUID, db_session: Session
) -> Dict[int, List[TokenRateLimit]]:
    group_limits = (
        select(TokenRateLimit, User__Team.team_id)
        .join(
            TokenRateLimit__Team,
            TokenRateLimit.id == TokenRateLimit__Team.rate_limit_id,
        )
        .join(
            Team,
            Team.id == TokenRateLimit__Team.team_id,
        )
        .join(
            User__Team,
            User__Team.team_id == Team.id,
        )
        .where(
            User__Team.user_id == user_id,
            TokenRateLimit.enabled.is_(True),
        )
    )

    raw_rate_limits = db_session.execute(group_limits).all()

    group_rate_limits = defaultdict(list)
    for rate_limit, team_id in raw_rate_limits:
        group_rate_limits[team_id].append(rate_limit)

    return group_rate_limits


def _fetch_team_usage(
    team_ids: list[int], cutoff_time: datetime, db_session: Session
) -> dict[int, list[Tuple[datetime, int]]]:
    """
    Fetch user group usage within the cutoff time, grouped by minute
    """
    team_usage = db_session.execute(
        select(
            func.sum(ChatMessage.token_count),
            func.date_trunc("minute", ChatMessage.time_sent),
            Team.id,
        )
        .join(ChatSession, ChatMessage.chat_session_id == ChatSession.id)
        .join(User__Team, User__Team.user_id == ChatSession.user_id)
        .join(Team, Team.id == User__Team.team_id)
        .filter(Team.id.in_(team_ids), ChatMessage.time_sent >= cutoff_time)
        .group_by(func.date_trunc("minute", ChatMessage.time_sent), Team.id)
    ).all()

    return {
        team_id: [(usage, time_sent) for time_sent, usage, _ in group_usage]
        for team_id, group_usage in groupby(
            team_usage, key=lambda row: row[2]
        )
    }


"""
Global rate limits
"""


def _user_is_rate_limited_by_global() -> None:
    with get_session_with_current_tenant() as db_session:
        global_rate_limits = fetch_all_global_token_rate_limits(
            db_session=db_session, enabled_only=True, ordered=False
        )

        if global_rate_limits:
            global_cutoff_time = _get_cutoff_time(global_rate_limits)
            global_usage = _fetch_global_usage(global_cutoff_time, db_session)

            if _is_rate_limited(global_rate_limits, global_usage):
                raise HTTPException(
                    status_code=429,
                    detail="Token budget exceeded for organization. Try again later.",
                )


def _fetch_global_usage(
    cutoff_time: datetime, db_session: Session
) -> Sequence[tuple[datetime, int]]:
    """
    Fetch global token usage within the cutoff time, grouped by minute
    """
    result = db_session.execute(
        select(
            func.date_trunc("minute", ChatMessage.time_sent),
            func.sum(ChatMessage.token_count),
        )
        .join(ChatSession, ChatMessage.chat_session_id == ChatSession.id)
        .filter(
            ChatMessage.time_sent >= cutoff_time,
        )
        .group_by(func.date_trunc("minute", ChatMessage.time_sent))
    ).all()

    return [(row[0], row[1]) for row in result]


"""
Common functions
"""


def _get_cutoff_time(rate_limits: Sequence[TokenRateLimit]) -> datetime:
    max_period_hours = max(rate_limit.period_hours for rate_limit in rate_limits)
    return datetime.now(tz=timezone.utc) - timedelta(hours=max_period_hours)


def _is_rate_limited(
    rate_limits: Sequence[TokenRateLimit], usage: Sequence[tuple[datetime, int]]
) -> bool:
    """
    If at least one rate limit is exceeded, return True
    """
    for rate_limit in rate_limits:
        tokens_used = sum(
            u_token_count
            for u_date, u_token_count in usage
            if u_date
            >= datetime.now(tz=tz.UTC) - timedelta(hours=rate_limit.period_hours)
        )

        if tokens_used >= rate_limit.token_budget * TOKEN_BUDGET_UNIT:
            return True

    return False


@lru_cache()
def any_rate_limit_exists() -> bool:
    """Checks if any rate limit exists in the database. Is cached, so that if no rate limits
    are setup, we don't have any effect on average query latency."""
    logger.debug("Checking for any rate limits...")
    with get_session_with_current_tenant() as db_session:
        return (
            db_session.scalar(
                select(TokenRateLimit.id).where(
                    TokenRateLimit.enabled == True  # noqa: E712
                )
            )
            is not None
        )
