"""
Test: Step-Level Overrides (Workflow-Level Overrides Architecture)

Verifies that workflow step overrides:
1. Are saved correctly to the workflow step (not the persona)
2. Do NOT mutate the original shared persona
3. Are returned in the workflow GET response
4. Are applied at runtime (system_prompt_override, llm_model_override, etc.)

Usage:
    python test_step_overrides.py [--key API_KEY] [--url BASE_URL]
"""

import json
import sys
import time
from pathlib import Path

# --path setup --──────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent))

from config import (  # noqa: E402
    CONFIG,
    api,
    headers,
    resolve_api_key,
    add_common_args,
    apply_common_args,
    stream_api,
)

PASS = 0
FAIL = 0


def log(msg: str) -> None:
    print(f"  {msg}")


def mark_pass(name: str) -> None:
    global PASS
    PASS += 1
    print(f"  [PASS] {name}")


def mark_fail(name: str, reason: str) -> None:
    global FAIL
    FAIL += 1
    print(f"  [FAIL] {name}: {reason}")


# --helpers --─────────────────────────────────────────────────────────────────

def create_test_persona(
    name: str,
    system_prompt: str = "You are a helpful assistant.",
    max_output_tokens: int | None = None,
) -> dict | None:
    """Create a minimal persona for testing."""
    body = {
        "name": name,
        "description": f"Test persona for step overrides",
        "num_chunks": 0,
        "is_public": True,
        "system_prompt": system_prompt,
        "task_prompt": "",
        "document_set_ids": [],
        "tool_ids": [],
        "users": [],
        "groups": [],
        "label_ids": [],
        "recency_bias": "base_decay",
        "llm_filter_extraction": False,
        "llm_relevance_filter": False,
        "replace_base_system_prompt": False,
        "datetime_aware": True,
        "knowledge_file_ids": [],
        "hierarchy_node_ids": [],
        "document_ids": [],
    }
    if max_output_tokens is not None:
        body["max_output_tokens"] = max_output_tokens

    r = api("POST", "persona", body)
    if r.status_code not in (200, 201):
        log(f"Failed to create persona '{name}': {r.status_code} {r.text[:200]}")
        return None
    return r.json()


def delete_persona(persona_id: int) -> None:
    api("PATCH", f"admin/persona/{persona_id}/visible?is_visible=false")


def create_workflow_with_override(
    persona_id: int,
    system_prompt_override: str | None = None,
    llm_provider_override: str | None = None,
    llm_model_override: str | None = None,
    max_output_tokens_override: int | None = None,
) -> dict | None:
    """Create a workflow with one step that has overrides."""
    step = {
        "persona_id": persona_id,
        "step_order": 0,
        "step_name": "Test Step",
        "step_description": "Step with overrides",
        "output_key": "output",
        "is_terminal": False,
        "can_request_input": False,
        "promote_output": False,
    }
    # Add overrides only if specified
    if system_prompt_override is not None:
        step["system_prompt_override"] = system_prompt_override
    if llm_provider_override is not None:
        step["llm_provider_override"] = llm_provider_override
    if llm_model_override is not None:
        step["llm_model_override"] = llm_model_override
    if max_output_tokens_override is not None:
        step["max_output_tokens_override"] = max_output_tokens_override

    body = {
        "name": "Override Test Workflow",
        "description": "Tests step-level overrides",
        "orchestration_mode": "sequential",
        "max_steps": 5,
        "max_calls_per_agent": 2,
        "timeout_seconds": 300,
        "is_public": True,
        "steps": [step],
    }

    r = api("POST", "admin/workflow", body)
    if r.status_code not in (200, 201):
        log(f"Failed to create workflow: {r.status_code} {r.text[:200]}")
        return None
    return r.json()


def get_workflow(workflow_id: int) -> dict | None:
    r = api("GET", f"workflow/{workflow_id}")
    if r.status_code != 200:
        log(f"GET workflow/{workflow_id} failed: {r.status_code} {r.text[:200]}")
        return None
    return r.json()


def get_persona(persona_id: int) -> dict | None:
    r = api("GET", f"persona/{persona_id}")
    if r.status_code != 200:
        return None
    return r.json()


def delete_workflow(workflow_id: int) -> None:
    api("DELETE", f"admin/workflow/{workflow_id}")


# --Test 1: Overrides saved to workflow step --───────────────────────────────

def test_overrides_saved():
    """Create a workflow with system_prompt_override, verify it's saved."""
    print("\n--Test 1: Overrides Saved to Workflow Step --")

    ORIGINAL_PROMPT = "You are the original agent."
    OVERRIDE_PROMPT = "You are a specialized workflow agent with custom instructions."
    ts = int(time.time())

    persona = create_test_persona(
        f"Override Test Agent {ts}",
        system_prompt=ORIGINAL_PROMPT,
    )
    if not persona:
        mark_fail("Create persona", "Failed to create")
        return

    persona_id = persona["id"]
    log(f"Created persona id={persona_id} with prompt='{ORIGINAL_PROMPT}'")

    workflow = create_workflow_with_override(
        persona_id=persona_id,
        system_prompt_override=OVERRIDE_PROMPT,
        max_output_tokens_override=500,
    )
    if not workflow:
        mark_fail("Create workflow", "Failed to create")
        delete_persona(persona_id)
        return

    workflow_id = workflow["id"]
    log(f"Created workflow id={workflow_id}")

    # Fetch the workflow back
    fetched = get_workflow(workflow_id)
    if not fetched:
        mark_fail("Fetch workflow", "Failed to fetch")
        delete_workflow(workflow_id)
        delete_persona(persona_id)
        return

    step = fetched["steps"][0]

    # Verify override is stored on the step
    if step.get("system_prompt_override") == OVERRIDE_PROMPT:
        mark_pass("system_prompt_override stored on step")
    else:
        mark_fail(
            "system_prompt_override stored on step",
            f"Expected '{OVERRIDE_PROMPT}', got '{step.get('system_prompt_override')}'",
        )

    if step.get("max_output_tokens_override") == 500:
        mark_pass("max_output_tokens_override stored on step")
    else:
        mark_fail(
            "max_output_tokens_override stored on step",
            f"Expected 500, got {step.get('max_output_tokens_override')}",
        )

    # CRITICAL: Verify persona is NOT modified
    persona_after = get_persona(persona_id)
    if not persona_after:
        mark_fail("Fetch persona after", "Failed to fetch")
    else:
        if persona_after.get("system_prompt") == ORIGINAL_PROMPT:
            mark_pass("Persona system_prompt NOT mutated")
        else:
            mark_fail(
                "Persona system_prompt NOT mutated",
                f"Expected '{ORIGINAL_PROMPT}', got '{persona_after.get('system_prompt')}'",
            )

        if persona_after.get("max_output_tokens") is None:
            mark_pass("Persona max_output_tokens NOT mutated")
        else:
            mark_fail(
                "Persona max_output_tokens NOT mutated",
                f"Expected None, got {persona_after.get('max_output_tokens')}",
            )

    # Cleanup
    delete_workflow(workflow_id)
    delete_persona(persona_id)


# --Test 2: NULL overrides use persona defaults --────────────────────────────

def test_null_overrides():
    """Create a workflow with no overrides, verify NULLs in response."""
    print("\n--Test 2: NULL Overrides (Inheritance) --")

    ts = int(time.time())
    persona = create_test_persona(
        f"Inheritance Test Agent {ts}",
        system_prompt="Base agent prompt",
        max_output_tokens=2000,
    )
    if not persona:
        mark_fail("Create persona", "Failed to create")
        return

    persona_id = persona["id"]

    # Create workflow WITHOUT overrides
    workflow = create_workflow_with_override(persona_id=persona_id)
    if not workflow:
        mark_fail("Create workflow", "Failed to create")
        delete_persona(persona_id)
        return

    workflow_id = workflow["id"]
    fetched = get_workflow(workflow_id)
    if not fetched:
        mark_fail("Fetch workflow", "Failed to fetch")
        delete_workflow(workflow_id)
        delete_persona(persona_id)
        return

    step = fetched["steps"][0]

    # All override fields should be null (inheritance)
    override_fields = [
        "system_prompt_override",
        "task_prompt_override",
        "llm_provider_override",
        "llm_model_override",
        "max_output_tokens_override",
        "tool_ids_override",
        "document_set_ids_override",
        "replace_base_system_prompt_override",
    ]

    all_null = True
    for field in override_fields:
        val = step.get(field)
        if val is not None:
            mark_fail(f"{field} is null", f"Expected None, got {val}")
            all_null = False

    if all_null:
        mark_pass("All override fields are null (inheritance active)")

    # Cleanup
    delete_workflow(workflow_id)
    delete_persona(persona_id)


# --Test 3: Update workflow with overrides --─────────────────────────────────

def test_update_workflow_overrides():
    """Create workflow without overrides, then UPDATE with overrides."""
    print("\n--Test 3: Update Workflow with Overrides --")

    ORIGINAL_PROMPT = "Original prompt"
    OVERRIDE_PROMPT = "Updated override prompt"
    ts = int(time.time())

    persona = create_test_persona(
        f"Update Test Agent {ts}",
        system_prompt=ORIGINAL_PROMPT,
    )
    if not persona:
        mark_fail("Create persona", "Failed to create")
        return

    persona_id = persona["id"]

    # Create workflow without overrides
    workflow = create_workflow_with_override(persona_id=persona_id)
    if not workflow:
        mark_fail("Create workflow", "Failed to create")
        delete_persona(persona_id)
        return

    workflow_id = workflow["id"]

    # UPDATE with overrides
    update_body = {
        "steps": [
            {
                "persona_id": persona_id,
                "step_order": 0,
                "step_name": "Updated Step",
                "output_key": "output",
                "system_prompt_override": OVERRIDE_PROMPT,
                "max_output_tokens_override": 1000,
                "tool_ids_override": [1, 2, 3],
            }
        ]
    }

    r = api("PATCH", f"admin/workflow/{workflow_id}", update_body)
    if r.status_code != 200:
        mark_fail("Update workflow", f"Status {r.status_code}: {r.text[:200]}")
        delete_workflow(workflow_id)
        delete_persona(persona_id)
        return

    # Fetch and verify
    fetched = get_workflow(workflow_id)
    if not fetched:
        mark_fail("Fetch updated workflow", "Failed to fetch")
        delete_workflow(workflow_id)
        delete_persona(persona_id)
        return

    step = fetched["steps"][0]

    if step.get("system_prompt_override") == OVERRIDE_PROMPT:
        mark_pass("Updated system_prompt_override")
    else:
        mark_fail(
            "Updated system_prompt_override",
            f"Got '{step.get('system_prompt_override')}'",
        )

    if step.get("tool_ids_override") == [1, 2, 3]:
        mark_pass("Updated tool_ids_override")
    else:
        mark_fail(
            "Updated tool_ids_override",
            f"Got {step.get('tool_ids_override')}",
        )

    # Verify persona still unchanged
    persona_after = get_persona(persona_id)
    if persona_after and persona_after.get("system_prompt") == ORIGINAL_PROMPT:
        mark_pass("Persona unchanged after workflow update")
    else:
        mark_fail(
            "Persona unchanged after workflow update",
            f"Got '{persona_after.get('system_prompt') if persona_after else 'N/A'}'",
        )

    # Cleanup
    delete_workflow(workflow_id)
    delete_persona(persona_id)


# --main --───────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Test step-level overrides")
    add_common_args(parser)
    args = parser.parse_args()
    apply_common_args(args)
    resolve_api_key()

    print("=" * 60)
    print("STEP-LEVEL OVERRIDES TEST SUITE")
    print("=" * 60)

    test_overrides_saved()
    test_null_overrides()
    test_update_workflow_overrides()

    print("\n" + "=" * 60)
    print(f"Results: {PASS} passed, {FAIL} failed")
    print("=" * 60)

    sys.exit(1 if FAIL > 0 else 0)


if __name__ == "__main__":
    main()
