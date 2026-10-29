"""Agent mapping utility for demo user identities and org structure.

Maps frontend agent selections (work_area + level) to demo user profiles
with name and email for sandbox provisioning.

Also provides organizational structure data and content generators for org_info files.
Single source of truth for both local and Kubernetes sandbox provisioning.
"""

from typing import TypedDict


class AgentInfo(TypedDict):
    """Type for agent information."""

    name: str
    email: str


# Agent mapping: work_area -> level -> AgentInfo
AGENT_MAPPING: dict[str, dict[str, AgentInfo]] = {
    "engineering": {
        "ic": {
            "name": "Jiwon Kang",
            "email": "jiwon_kang@netherite-extraction.virtualai.com",
        },
        "manager": {
            "name": "Javier Morales",
            "email": "javier_morales@netherite-extraction.virtualai.com",
        },
    },
    "sales": {
        "ic": {
            "name": "Megan Foster",
            "email": "megan_foster@netherite-extraction.virtualai.com",
        },
        "manager": {
            "name": "Valeria Cruz",
            "email": "valeria_cruz@netherite-extraction.virtualai.com",
        },
    },
    "product": {
        "ic": {
            "name": "Michael Anderson",
            "email": "michael_anderson@netherite-extraction.virtualai.com",
        },
        "manager": {
            "name": "David Liu",
            "email": "david_liu@netherite-extraction.virtualai.com",
        },
    },
    "marketing": {
        "ic": {
            "name": "Rahul Patel",
            "email": "rahul_patel@netherite-extraction.virtualai.com",
        },
        "manager": {
            "name": "Olivia Reed",
            "email": "olivia_reed@netherite-extraction.virtualai.com",
        },
    },
    "executives": {
        "ic": {
            "name": "Sarah Mitchell",
            "email": "sarah_mitchell@netherite-extraction.virtualai.com",
        },
        "manager": {
            "name": "Sarah Mitchell",
            "email": "sarah_mitchell@netherite-extraction.virtualai.com",
        },
    },
    "other": {
        "manager": {
            "name": "Ralf Schroeder",
            "email": "ralf_schroeder@netherite-extraction.virtualai.com",
        },
        "ic": {
            "name": "John Carpenter",
            "email": "john_carpenter@netherite-extraction.virtualai.com",
        },
    },
}

# Organization structure - maps managers to their direct reports
ORGANIZATION_STRUCTURE: dict[str, dict[str, list[str]]] = {
    "engineering": {
        "javier_morales@netherite-extraction.virtualai.com": [
            "tyler_jenkins@netherite-extraction.virtualai.com",
            "jiwon_kang@netherite-extraction.virtualai.com",
            "brooke_spencer@netherite-extraction.virtualai.com",
            "andre_robinson@netherite-extraction.virtualai.com",
        ],
        "isabella_torres@netherite-extraction.virtualai.com": [
            "ryan_murphy@netherite-extraction.virtualai.com",
            "jason_morris@netherite-extraction.virtualai.com",
            "kevin_sullivan@netherite-extraction.virtualai.com",
        ],
    },
    "sales": {
        "valeria_cruz@netherite-extraction.virtualai.com": [
            "megan_foster@netherite-extraction.virtualai.com",
            "mina_park@netherite-extraction.virtualai.com",
            "james_choi@netherite-extraction.virtualai.com",
            "camila_vega@netherite-extraction.virtualai.com",
        ],
        "layla_farah@netherite-extraction.virtualai.com": [
            "arjun_mehta@netherite-extraction.virtualai.com",
            "sneha_reddy@netherite-extraction.virtualai.com",
            "irene_shen@netherite-extraction.virtualai.com",
        ],
    },
    "product": {
        "david_liu@netherite-extraction.virtualai.com": [
            "michael_anderson@netherite-extraction.virtualai.com",
            "kenji_watanabe@netherite-extraction.virtualai.com",
            "sofia_ramirez@netherite-extraction.virtualai.com",
        ],
    },
    "marketing": {
        "olivia_reed@netherite-extraction.virtualai.com": [
            "rahul_patel@netherite-extraction.virtualai.com",
            "yuna_lee@netherite-extraction.virtualai.com",
            "peter_yamamoto@netherite-extraction.virtualai.com",
        ],
    },
    "executives": {
        "sarah_mitchell@netherite-extraction.virtualai.com": [
            "daniel_hughes@netherite-extraction.virtualai.com",
            "amanda_brooks@netherite-extraction.virtualai.com",
            "ananya_gupta@netherite-extraction.virtualai.com",
        ],
    },
    "other": {
        "ralf_schroeder@netherite-extraction.virtualai.com": [
            "john_carpenter@netherite-extraction.virtualai.com",
        ],
    },
}

# AGENTS.md content for org_info directory
ORG_INFO_AGENTS_MD = """# AGENTS.md

This file provides information about which organizational information sources are available:

There are two files available that provide important information about the user's company and the user themselves.


## User Identity

The file `user_identity_profile.txt` contains the user's profile.

## Organizational Structure

The file `organization_structure.json` contains a json with the organization's groups, managers, and their reports.
"""


def get_agent_info(work_area: str | None, level: str | None) -> AgentInfo | None:
    """Get agent info from work area and level.

    Args:
        work_area: User's work area (e.g., "engineering", "product", "sales")
        level: User's level (e.g., "ic", "manager")

    Returns:
        AgentInfo with name and email, or None if no matching agent
    """
    if not work_area:
        return None

    work_area_lower = work_area.lower().strip()
    level_lower = (level or "manager").lower().strip()

    work_area_mapping = AGENT_MAPPING.get(work_area_lower)
    if not work_area_mapping:
        return None

    return work_area_mapping.get(level_lower)


def generate_user_identity_content(agent: AgentInfo) -> str:
    """Generate user identity profile content.

    Args:
        agent: AgentInfo with name and email

    Returns:
        Content for user_identity_profile.txt
    """
    return f"Your name is {agent['name']}. Your email is {agent['email']}. You are working at Netherite Extraction Corp.\n"
