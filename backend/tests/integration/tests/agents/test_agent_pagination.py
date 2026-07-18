import requests

from om.server.features.agent.constants import ADMIN_AGENTS_RESOURCE
from om.server.features.agent.constants import AGENTS_RESOURCE
from tests.integration.common_utils.constants import API_SERVER_URL
from tests.integration.common_utils.managers.agent import AgentManager
from tests.integration.common_utils.test_models import DATestUser


def _get_agents_paginated(
    user: DATestUser,
    page_num: int,
    page_size: int,
    include_deleted: bool = False,
    get_editable: bool = False,
    include_default: bool = True,
) -> tuple[dict, int]:
    """Fetches a paginated page of agents, with status code."""
    response = requests.get(
        f"{API_SERVER_URL}{AGENTS_RESOURCE}",
        params={
            "page_num": page_num,
            "page_size": page_size,
            "include_deleted": include_deleted,
            "get_editable": get_editable,
            "include_default": include_default,
        },
        headers=user.headers,
        cookies=user.cookies,
    )
    return response.json(), response.status_code


def _get_agents_admin_paginated(
    user: DATestUser,
    page_num: int,
    page_size: int,
    include_deleted: bool = False,
    get_editable: bool = False,
    include_default: bool = True,
) -> tuple[dict, int]:
    """Fetches a paginated page of agents (admin endpoint) with status code."""
    response = requests.get(
        f"{API_SERVER_URL}{ADMIN_AGENTS_RESOURCE}",
        params={
            "page_num": page_num,
            "page_size": page_size,
            "include_deleted": include_deleted,
            "get_editable": get_editable,
            "include_default": include_default,
        },
        headers=user.headers,
        cookies=user.cookies,
    )
    response.raise_for_status()
    return response.json(), response.status_code


def test_agent_pagination_basic(
    reset: None, admin_user: DATestUser  # noqa: ARG001
) -> None:
    """Test basic pagination - verify correct items and total count."""
    # Preconditions
    agents_to_create = 25
    agents = []
    for i in range(agents_to_create):
        agent = AgentManager.create(
            name=f"Test Agent {i}",
            user_performing_action=admin_user,
        )
        agents.append(agent)

    # Under test and postconditions
    # Test page 0 with size 10.
    page_0, _ = _get_agents_paginated(admin_user, page_num=0, page_size=10)
    assert "items" in page_0
    assert "total_items" in page_0
    assert len(page_0["items"]) == 10
    assert (
        page_0["total_items"] >= agents_to_create
    )  # At least agents_to_create (may have default agents)

    # Test page 2 with size 10 (should have 5+ items if only our test agents
    # exist).
    page_2, _ = _get_agents_paginated(admin_user, page_num=2, page_size=10)
    assert len(page_2["items"]) >= 5
    assert page_2["total_items"] >= agents_to_create

    # Test page beyond end (page 10 with size 10, offset 100).
    page_beyond, _ = _get_agents_paginated(admin_user, page_num=10, page_size=10)
    assert len(page_beyond["items"]) == 0
    assert page_beyond["total_items"] >= agents_to_create  # Total doesn't change.


def test_agent_pagination_ordering(
    reset: None, admin_user: DATestUser  # noqa: ARG001
) -> None:
    """Test ordering - display_priority ASC nulls last, then ID ASC."""
    # Preconditions
    # Create agents with specific display_priority values.
    agent_a = AgentManager.create(
        name="Agent A",
        description="This should be second",
        user_performing_action=admin_user,
        display_priority=2,
    )
    agent_b = AgentManager.create(
        name="Agent B",
        description="This should be first",
        user_performing_action=admin_user,
        display_priority=1,
    )
    agent_c = AgentManager.create(
        name="Agent C",
        description="This should be third",
        user_performing_action=admin_user,
        display_priority=3,
    )
    agent_d = AgentManager.create(
        name="Agent D",
        description="This should be fourth",
        user_performing_action=admin_user,
        display_priority=3,  # Note the same prio as above, should sort by id
    )

    # Under test
    page_0, _ = _get_agents_paginated(admin_user, page_num=0, page_size=100)

    # Postconditions
    # Find our agents in the results.
    our_expected_ordered_agent_ids = [
        agent_b.id,
        agent_a.id,
        agent_c.id,
        agent_d.id,
    ]
    our_agents_in_results = [
        p for p in page_0["items"] if p["id"] in our_expected_ordered_agent_ids
    ]
    assert len(our_agents_in_results) == 4
    # Verify ordering.
    for i in range(len(our_expected_ordered_agent_ids)):
        assert our_expected_ordered_agent_ids[i] == our_agents_in_results[i]["id"]


def test_agent_pagination_admin_endpoint(
    reset: None, admin_user: DATestUser  # noqa: ARG001
) -> None:
    """Test admin paginated endpoint returns AgentSnapshot format."""
    # Preconditions
    agents_to_create = 5
    for i in range(agents_to_create):
        AgentManager.create(
            name=f"Admin Test Agent {i}",
            user_performing_action=admin_user,
        )

    # Under test
    page_0, _ = _get_agents_admin_paginated(admin_user, page_num=0, page_size=10)

    # Postconditions
    assert "items" in page_0
    assert "total_items" in page_0
    assert len(page_0["items"]) >= agents_to_create
    assert page_0["total_items"] >= agents_to_create
    # Verify admin-specific fields are present (AgentSnapshot has more
    # fields).
    first_agent = page_0["items"][0]
    # AgentSnapshot should have these fields that MinimalAgentSnapshot
    # doesn't.
    assert "users" in first_agent
    assert "groups" in first_agent
    assert "knowledge_file_ids" in first_agent


def test_agent_pagination_with_deleted(
    reset: None, admin_user: DATestUser  # noqa: ARG001
) -> None:
    """Test pagination with include_deleted parameter."""
    # Preconditions
    # Create and delete a agent.
    agent = AgentManager.create(
        name="To Be Deleted",
        user_performing_action=admin_user,
    )
    AgentManager.delete(agent, user_performing_action=admin_user)

    # Under test and postconditions
    # Without include_deleted, should not appear.
    page_without_deleted, _ = _get_agents_paginated(
        admin_user, page_num=0, page_size=100, include_deleted=False
    )
    agent_ids_without_deleted = [p["id"] for p in page_without_deleted["items"]]
    assert agent.id not in agent_ids_without_deleted

    # With include_deleted, should appear.
    page_with_deleted, _ = _get_agents_paginated(
        admin_user, page_num=0, page_size=100, include_deleted=True
    )
    agent_ids_with_deleted = [p["id"] for p in page_with_deleted["items"]]
    assert agent.id in agent_ids_with_deleted

    # Total counts should differ.
    assert page_with_deleted["total_items"] > page_without_deleted["total_items"]


def test_agent_pagination_page_size_limits(
    reset: None, admin_user: DATestUser  # noqa: ARG001
) -> None:
    """Test page_size parameter validation (max 1000)."""
    # Preconditions
    # Create a few agents.
    for i in range(5):
        AgentManager.create(
            name=f"Size Limit Test {i}",
            user_performing_action=admin_user,
        )

    # Under test and postconditions
    # Valid page_size of 1
    data, _ = _get_agents_paginated(admin_user, page_num=0, page_size=1)
    assert len(data["items"]) <= 1

    # Valid page_size of 1000
    data, _ = _get_agents_paginated(admin_user, page_num=0, page_size=1000)
    # We assume not that many default agents are made.
    assert len(data["items"]) == data["total_items"]

    # Invalid page_size of 1001 (exceeds max)
    _, status_code = _get_agents_paginated(admin_user, page_num=0, page_size=1001)
    assert status_code == 422  # Validation error

    # Invalid page_size of 0
    _, status_code = _get_agents_paginated(admin_user, page_num=0, page_size=0)
    assert status_code == 422  # Validation error


def test_agent_pagination_count_accuracy(
    reset: None, admin_user: DATestUser  # noqa: ARG001
) -> None:
    """Test that total_items count is consistent across pages."""
    # Preconditions
    # Create 15 agents.
    created_agents = []
    for i in range(15):
        agent = AgentManager.create(
            name=f"Count Test {i}",
            user_performing_action=admin_user,
        )
        created_agents.append(agent)

    # Under test and postconditions
    # Fetch first page to get total count.
    page_0, _ = _get_agents_paginated(admin_user, page_num=0, page_size=5)
    total_items = page_0["total_items"]
    assert total_items >= 15

    # Fetch all pages to cover all agents.
    all_ids_from_pages: set[int] = set()
    num_pages_needed = (total_items + 4) // 5  # Ceiling division
    for page_num in range(num_pages_needed):
        page, _ = _get_agents_paginated(admin_user, page_num=page_num, page_size=5)
        # All pages should report the same total.
        assert (
            page["total_items"] == total_items
        ), f"Page {page_num} has inconsistent total_items"
        all_ids_from_pages.update(p["id"] for p in page["items"])

    # Our created agents should all appear.
    our_ids = {p.id for p in created_agents}
    assert our_ids.issubset(
        all_ids_from_pages
    ), "All created agents should appear in paginated results"


def test_agent_pagination_user_permissions(
    reset: None, admin_user: DATestUser, basic_user: DATestUser  # noqa: ARG001
) -> None:
    """Test that pagination respects user permissions."""
    # Preconditions
    # Admin creates a private agent (not shared).
    private_agent = AgentManager.create(
        name="Private Agent",
        description="Not shared",
        is_public=False,
        user_performing_action=admin_user,
    )
    # Admin creates a public agent.
    public_agent = AgentManager.create(
        name="Public Agent",
        description="Shared with all",
        is_public=True,
        user_performing_action=admin_user,
    )

    # Under test and postconditions
    # Admin should see both in paginated results.
    admin_page, _ = _get_agents_paginated(admin_user, page_num=0, page_size=100)
    admin_ids = {p["id"] for p in admin_page["items"]}
    assert private_agent.id in admin_ids
    assert public_agent.id in admin_ids

    # Basic user should only see public agent.
    user_page, _ = _get_agents_paginated(basic_user, page_num=0, page_size=100)
    user_ids = {p["id"] for p in user_page["items"]}
    assert private_agent.id not in user_ids
    assert public_agent.id in user_ids

    # Totals should differ.
    assert admin_page["total_items"] > user_page["total_items"]
