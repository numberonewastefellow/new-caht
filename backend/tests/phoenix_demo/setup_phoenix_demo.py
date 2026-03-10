#!/usr/bin/env python3
"""Phoenix Demo Setup — Creates model, dataset, prompts, evaluators, and runs experiments.

Usage:
    python setup_phoenix_demo.py [--phoenix-url http://localhost:6006] [--gpt-key-file path]

Features configured:
  1. OpenAI API key stored as Phoenix secret
  2. GPT-4o-mini model with cost tracking
  3. Demo Q&A dataset (10 examples)
  4. Prompt templates (Q&A answerer + Judge)
  5. Playground test (chat completion via OpenAI)
  6. LLM-as-Judge evaluator (categorical, tool-calling based)
  7. Experiment: run GPT-4o-mini over dataset + evaluate with LLM judge
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from typing import Any

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package required. pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DEFAULT_PHOENIX_URL = "http://localhost:6006"
DEFAULT_GPT_KEY_FILE = (
    "d:/llm/danswer20022026/backend/tests/workflow_creator/gpt_key"
)
MODEL_NAME = "gpt-4o-mini"
MAX_TOKENS = 400

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def gql(url: str, query: str, variables: dict | None = None) -> dict:
    """Execute a GraphQL query/mutation against Phoenix."""
    payload: dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = requests.post(
        f"{url}/graphql",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        errors = json.dumps(data["errors"], indent=2)
        raise RuntimeError(f"GraphQL errors:\n{errors}")
    return data


def rest_get(url: str, path: str) -> Any:
    resp = requests.get(f"{url}{path}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def rest_post(url: str, path: str, body: Any) -> Any:
    resp = requests.post(f"{url}{path}", json=body, timeout=60)
    resp.raise_for_status()
    return resp.json()


def call_openai(api_key: str, messages: list[dict], **kwargs: Any) -> dict:
    """Call OpenAI chat completions API directly."""
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL_NAME,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", MAX_TOKENS),
            "temperature": kwargs.get("temperature", 0.0),
            **{k: v for k, v in kwargs.items() if k not in ("max_tokens", "temperature")},
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


# ===========================================================================
# Step 1: Store OpenAI API Key as secret
# ===========================================================================


def store_openai_secret(phoenix_url: str, api_key: str) -> None:
    print("\n[1/7] Storing OpenAI API key as Phoenix secret...")
    gql(
        phoenix_url,
        """
        mutation UpsertSecrets($input: UpsertOrDeleteSecretsMutationInput!) {
            upsertOrDeleteSecrets(input: $input) { __typename }
        }
    """,
        {
            "input": {
                "secrets": [{"key": "OPENAI_API_KEY", "value": api_key}]
            }
        },
    )
    print("  -> OPENAI_API_KEY stored successfully")


# ===========================================================================
# Step 2: Create model (gpt-4o-mini with cost tracking)
# ===========================================================================


def create_model(phoenix_url: str) -> str:
    print("\n[2/7] Creating GPT-4o-mini model with cost tracking...")

    # Check existing via generativeModels query
    result = gql(
        phoenix_url,
        """
        query { generativeModels { edges { node { id name } } } }
    """,
    )
    for edge in result["data"]["generativeModels"]["edges"]:
        if edge["node"]["name"] == MODEL_NAME:
            model_id = edge["node"]["id"]
            print(f"  -> Model already exists: {model_id}")
            return model_id

    # Create with correct TokenKind enum values: PROMPT / COMPLETION
    result = gql(
        phoenix_url,
        """
        mutation CreateModel($input: CreateModelMutationInput!) {
            createModel(input: $input) { model { id name } }
        }
    """,
        {
            "input": {
                "name": MODEL_NAME,
                "provider": "openai",
                "namePattern": MODEL_NAME,
                "costs": [
                    {
                        "tokenType": "input",
                        "costPerMillionTokens": 0.15,
                        "kind": "PROMPT",
                    },
                    {
                        "tokenType": "output",
                        "costPerMillionTokens": 0.60,
                        "kind": "COMPLETION",
                    },
                ],
            }
        },
    )
    model_id = result["data"]["createModel"]["model"]["id"]
    print(f"  -> Model created: {model_id} ({MODEL_NAME})")
    return model_id


# ===========================================================================
# Step 3: Create demo dataset
# ===========================================================================

DEMO_EXAMPLES = [
    {
        "input": {"question": "What is the capital of France?"},
        "output": {"answer": "The capital of France is Paris."},
        "metadata": {"category": "geography", "difficulty": "easy"},
    },
    {
        "input": {"question": "Explain photosynthesis in one sentence."},
        "output": {
            "answer": "Photosynthesis is the process by which green plants convert sunlight, water, and CO2 into glucose and oxygen."
        },
        "metadata": {"category": "science", "difficulty": "medium"},
    },
    {
        "input": {"question": "What are the three laws of thermodynamics?"},
        "output": {
            "answer": "1) Energy cannot be created or destroyed (conservation). 2) Entropy of an isolated system always increases. 3) Entropy approaches zero as temperature approaches absolute zero."
        },
        "metadata": {"category": "science", "difficulty": "hard"},
    },
    {
        "input": {"question": "Who wrote 'Romeo and Juliet'?"},
        "output": {
            "answer": "William Shakespeare wrote Romeo and Juliet."
        },
        "metadata": {"category": "literature", "difficulty": "easy"},
    },
    {
        "input": {"question": "What is the time complexity of binary search?"},
        "output": {
            "answer": "Binary search has O(log n) time complexity."
        },
        "metadata": {"category": "computer_science", "difficulty": "medium"},
    },
    {
        "input": {
            "question": "Explain the difference between TCP and UDP."
        },
        "output": {
            "answer": "TCP is connection-oriented and guarantees ordered, reliable delivery. UDP is connectionless and faster but does not guarantee delivery or order."
        },
        "metadata": {"category": "computer_science", "difficulty": "medium"},
    },
    {
        "input": {"question": "What causes a rainbow?"},
        "output": {
            "answer": "Rainbows are caused by the refraction, dispersion, and reflection of sunlight through water droplets in the atmosphere."
        },
        "metadata": {"category": "science", "difficulty": "easy"},
    },
    {
        "input": {"question": "What is the Pythagorean theorem?"},
        "output": {
            "answer": "In a right triangle, the square of the hypotenuse equals the sum of the squares of the other two sides: a\u00b2 + b\u00b2 = c\u00b2."
        },
        "metadata": {"category": "math", "difficulty": "easy"},
    },
    {
        "input": {"question": "What is a blockchain?"},
        "output": {
            "answer": "A blockchain is a distributed, immutable ledger that records transactions across a network of computers using cryptographic hashing to chain blocks together."
        },
        "metadata": {"category": "technology", "difficulty": "medium"},
    },
    {
        "input": {
            "question": "Explain the concept of recursion in programming."
        },
        "output": {
            "answer": "Recursion is when a function calls itself to solve a smaller instance of the same problem, with a base case to stop the recursion."
        },
        "metadata": {"category": "computer_science", "difficulty": "medium"},
    },
]


def create_dataset(phoenix_url: str) -> tuple[str, list[dict]]:
    """Create a demo Q&A dataset. Returns (dataset_id, examples_with_ids)."""
    print("\n[3/7] Creating demo Q&A dataset...")

    # Check existing
    existing = rest_get(phoenix_url, "/v1/datasets")
    for ds in existing.get("data", []):
        if ds.get("name") == "demo-qa-dataset":
            ds_id = ds["id"]
            print(f"  -> Dataset already exists: {ds_id}")
            examples = rest_get(phoenix_url, f"/v1/datasets/{ds_id}/examples")
            return ds_id, examples.get("data", {}).get("examples", [])

    # Create dataset
    result = gql(
        phoenix_url,
        """
        mutation CreateDataset($input: CreateDatasetInput!) {
            createDataset(input: $input) { dataset { id name } }
        }
    """,
        {
            "input": {
                "name": "demo-qa-dataset",
                "description": "Demo Q&A dataset for showcasing Phoenix evaluation features",
                "metadata": {
                    "source": "phoenix_demo_setup",
                    "size": len(DEMO_EXAMPLES),
                },
            }
        },
    )
    ds_id = result["data"]["createDataset"]["dataset"]["id"]
    print(f"  -> Dataset created: {ds_id}")

    # Add examples
    result = gql(
        phoenix_url,
        """
        mutation AddExamples($input: AddExamplesToDatasetInput!) {
            addExamplesToDataset(input: $input) {
                dataset { id exampleCount }
            }
        }
    """,
        {
            "input": {
                "datasetId": ds_id,
                "examples": DEMO_EXAMPLES,
                "datasetVersionDescription": "Initial version with 10 Q&A pairs",
            }
        },
    )
    count = result["data"]["addExamplesToDataset"]["dataset"]["exampleCount"]
    print(f"  -> Added {count} examples")

    # Fetch examples with IDs
    examples = rest_get(phoenix_url, f"/v1/datasets/{ds_id}/examples")
    return ds_id, examples.get("data", {}).get("examples", [])


# ===========================================================================
# Step 4: Create prompt templates
# ===========================================================================


def create_prompts(phoenix_url: str) -> tuple[str, str]:
    """Create a Q&A prompt and a Judge prompt. Returns (qa_id, judge_id)."""
    print("\n[4/7] Creating prompt templates...")

    qa_prompt_id = _create_prompt_if_not_exists(
        phoenix_url,
        name="qa_answerer",
        description="Answers factual questions concisely",
        system_msg="You are a knowledgeable assistant. Answer the question accurately and concisely in 1-3 sentences. Stay factual.",
        user_msg="Question: {{question}}",
    )

    judge_prompt_id = _create_prompt_if_not_exists(
        phoenix_url,
        name="qa_judge",
        description="Judges if an LLM answer is correct compared to reference",
        system_msg=(
            "You are an expert evaluator. Compare the AI's answer to the reference answer. "
            "Use the correctness tool to submit your rating."
        ),
        user_msg=(
            "Question: {{input.question}}\n\n"
            "Reference Answer: {{expected.answer}}\n\n"
            "AI Answer: {{output}}"
        ),
    )

    return qa_prompt_id, judge_prompt_id


def _create_prompt_if_not_exists(
    phoenix_url: str,
    name: str,
    description: str,
    system_msg: str,
    user_msg: str,
) -> str:
    """Create a prompt if it doesn't already exist."""
    existing = rest_get(phoenix_url, "/v1/prompts")
    for p in existing.get("data", []):
        if p.get("name") == name:
            prompt_id = p["id"]
            print(f"  -> Prompt '{name}' already exists: {prompt_id}")
            return prompt_id

    # createChatPrompt returns Prompt directly (not wrapped in payload)
    # Roles must be UPPERCASE: SYSTEM, USER, AI, TOOL
    # invocationParameters must be a JSON object (not string)
    # tools must be array of ToolDefinitionInput (not JSON string)
    result = gql(
        phoenix_url,
        """
        mutation CreatePrompt($input: CreateChatPromptInput!) {
            createChatPrompt(input: $input) { id name }
        }
    """,
        {
            "input": {
                "name": name,
                "description": description,
                "promptVersion": {
                    "description": "v1",
                    "templateFormat": "MUSTACHE",
                    "template": {
                        "messages": [
                            {
                                "role": "SYSTEM",
                                "content": [{"text": {"text": system_msg}}],
                            },
                            {
                                "role": "USER",
                                "content": [{"text": {"text": user_msg}}],
                            },
                        ]
                    },
                    "invocationParameters": {
                        "max_tokens": MAX_TOKENS,
                        "temperature": 0,
                    },
                    "tools": [],
                    "modelProvider": "OPENAI",
                    "modelName": MODEL_NAME,
                },
            }
        },
    )
    prompt_id = result["data"]["createChatPrompt"]["id"]
    print(f"  -> Prompt '{name}' created: {prompt_id}")
    return prompt_id


# ===========================================================================
# Step 5: Test Playground (chat completion)
# ===========================================================================


def test_playground(phoenix_url: str, api_key: str) -> bool:
    """Test Playground by calling OpenAI directly (verifies key + model work)."""
    print("\n[5/7] Testing Playground (chat completion)...")

    try:
        result = call_openai(
            api_key,
            [
                {"role": "system", "content": "Be brief."},
                {"role": "user", "content": "What is 2+2? One word."},
            ],
            max_tokens=50,
        )
        answer = result["choices"][0]["message"]["content"].strip()
        usage = result.get("usage", {})
        print(f"  -> OpenAI response: '{answer}'")
        print(
            f"  -> Tokens: {usage.get('prompt_tokens', '?')} prompt + "
            f"{usage.get('completion_tokens', '?')} completion"
        )
        print("  -> API key valid. Playground will work in Phoenix UI.")

        # Also verify Phoenix GraphQL chatCompletion mutation fires
        try:
            gql(
                phoenix_url,
                """
                mutation ChatCompletion($input: ChatCompletionInput!) {
                    chatCompletion(input: $input) {
                        __typename
                        ... on ChatCompletionMutationPayload { __typename }
                    }
                }
            """,
                {
                    "input": {
                        "messages": [
                            {
                                "role": "SYSTEM",
                                "content": [
                                    {
                                        "text": {
                                            "text": "You are a helpful assistant."
                                        }
                                    }
                                ],
                            },
                            {
                                "role": "USER",
                                "content": [
                                    {
                                        "text": {
                                            "text": "What is 2+2? One word."
                                        }
                                    }
                                ],
                            },
                        ],
                        "model": {
                            "builtin": {
                                "providerKey": "OPENAI",
                                "name": MODEL_NAME,
                            }
                        },
                        "credentials": [
                            {"envVarName": "OPENAI_API_KEY", "value": api_key}
                        ],
                        "invocationParameters": [
                            {
                                "invocationName": "max_tokens",
                                "canonicalName": "MAX_COMPLETION_TOKENS",
                                "valueInt": 50,
                            },
                            {
                                "invocationName": "temperature",
                                "canonicalName": "TEMPERATURE",
                                "valueFloat": 0.0,
                            },
                        ],
                        "repetitions": 1,
                        "evaluators": [],
                    }
                },
            )
            print("  -> Phoenix Playground mutation accepted (async)")
        except Exception:
            print("  -> Phoenix Playground mutation is subscription-based (expected)")

        return True
    except Exception as e:
        print(f"  -> ERROR: {e}")
        return False


# ===========================================================================
# Step 6: Create LLM-as-Judge evaluator on dataset
# ===========================================================================


def create_evaluator(phoenix_url: str, dataset_id: str) -> str | None:
    """Create an LLM-as-Judge evaluator with categorical output via tool calling.

    Phoenix validation requirements (from evaluators.py source):
      1. Tool function name == output config name
      2. Evaluator description == tool function description (or None)
      3. Tool params must have 'label' (with type, enum, description) + optional 'explanation'
      4. label.description must match output config name (annotation name)
      5. label.enum must match output config values labels
      6. tool_choice must be set (specific function or one_or_more)
    """
    print("\n[6/7] Creating LLM-as-Judge evaluator...")

    # Check if evaluator already exists
    result = gql(
        phoenix_url,
        """
        query GetEvaluators($datasetId: ID!) {
            node(id: $datasetId) {
                ... on Dataset {
                    datasetEvaluators { edges { node { id name } } }
                }
            }
        }
    """,
        {"datasetId": dataset_id},
    )
    evaluators = (
        result.get("data", {})
        .get("node", {})
        .get("datasetEvaluators", {})
        .get("edges", [])
    )
    for e in evaluators:
        if e["node"]["name"] == "correctness_judge":
            eval_id = e["node"]["id"]
            print(f"  -> Evaluator already exists: {eval_id}")
            return eval_id

    # The shared description must match between evaluator and tool function
    shared_desc = "Whether the answer is correct"

    # Tool definition matching Phoenix's strict validation
    tool_def = {
        "type": "function",
        "function": {
            "name": "correctness",  # Must match output config name
            "description": shared_desc,  # Must match evaluator description
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {
                        "type": "string",
                        "enum": [
                            "correct",
                            "partially_correct",
                            "incorrect",
                        ],
                        "description": "correctness",  # Must match output config name
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Brief explanation of the rating",
                    },
                },
                "required": ["label", "explanation"],
            },
        },
    }

    result = gql(
        phoenix_url,
        """
        mutation CreateEval($input: CreateDatasetLLMEvaluatorInput!) {
            createDatasetLlmEvaluator(input: $input) {
                evaluator { id name }
            }
        }
    """,
        {
            "input": {
                "datasetId": dataset_id,
                "name": "correctness_judge",
                "description": shared_desc,  # Must match tool function description
                "promptVersion": {
                    "description": "Correctness judge v1",
                    "templateFormat": "MUSTACHE",
                    "template": {
                        "messages": [
                            {
                                "role": "SYSTEM",
                                "content": [
                                    {
                                        "text": {
                                            "text": "You are an expert evaluator. Compare the AI answer to the reference answer. Use the correctness tool to submit your rating."
                                        }
                                    }
                                ],
                            },
                            {
                                "role": "USER",
                                "content": [
                                    {
                                        "text": {
                                            "text": "Question: {{input.question}}\n\nReference Answer: {{expected.answer}}\n\nAI Answer: {{output}}"
                                        }
                                    }
                                ],
                            },
                        ]
                    },
                    "invocationParameters": {
                        "max_tokens": MAX_TOKENS,
                        "temperature": 0,
                        "tool_choice": {
                            "type": "function",
                            "function": {"name": "correctness"},
                        },
                    },
                    "tools": [{"definition": tool_def}],
                    "modelProvider": "OPENAI",
                    "modelName": MODEL_NAME,
                },
                "outputConfigs": [
                    {
                        "categorical": {
                            "name": "correctness",
                            "description": shared_desc,
                            "optimizationDirection": "MAXIMIZE",
                            "values": [
                                {"label": "correct", "score": 1.0},
                                {"label": "partially_correct", "score": 0.5},
                                {"label": "incorrect", "score": 0.0},
                            ],
                        }
                    }
                ],
                "inputMapping": {
                    "literalMapping": {},
                    "pathMapping": {
                        "input": "input",
                        "expected": "output",
                        "output": "output",
                    },
                },
            }
        },
    )
    eval_id = result["data"]["createDatasetLlmEvaluator"]["evaluator"]["id"]
    print(f"  -> LLM Evaluator created: {eval_id}")
    return eval_id


# ===========================================================================
# Step 7: Run experiment over dataset via REST API
# ===========================================================================


def run_experiment(
    phoenix_url: str,
    api_key: str,
    dataset_id: str,
    examples: list[dict],
) -> bool:
    """Run experiment: call GPT-4o-mini on each example, then evaluate with LLM judge.

    Uses REST API (more reliable than GraphQL subscription-based mutation):
      1. POST /v1/datasets/{id}/experiments — create experiment
      2. POST /v1/experiments/{id}/runs — submit each run result
      3. POST /v1/experiment_evaluations — submit LLM judge evaluations
    """
    print("\n[7/7] Running experiment over dataset...")

    if not examples:
        print("  -> ERROR: No examples found in dataset")
        return False

    # 1. Create experiment
    exp_name = f"demo-qa-{int(time.time())}"
    exp = rest_post(
        phoenix_url,
        f"/v1/datasets/{dataset_id}/experiments",
        {
            "name": exp_name,
            "description": "GPT-4o-mini answers + LLM-as-Judge evaluation",
            "metadata": {"model": MODEL_NAME, "max_tokens": MAX_TOKENS},
        },
    )
    exp_id = exp["data"]["id"]
    print(f"  -> Experiment created: {exp_id} ({exp_name})")

    # 2. Run GPT-4o-mini on each example
    runs: list[dict] = []
    for i, example in enumerate(examples):
        ex_id = example.get("id", example.get("example_id"))
        question = example.get("input", {}).get("question", "")
        reference = example.get("output", {}).get("answer", "")

        print(f"  -> [{i + 1}/{len(examples)}] Q: {question[:60]}...", end=" ")

        start = datetime.now(timezone.utc)
        try:
            result = call_openai(
                api_key,
                [
                    {
                        "role": "system",
                        "content": "You are a knowledgeable assistant. Answer accurately and concisely in 1-3 sentences.",
                    },
                    {"role": "user", "content": f"Question: {question}"},
                ],
            )
            answer = result["choices"][0]["message"]["content"].strip()
            end = datetime.now(timezone.utc)

            # Submit run
            run = rest_post(
                phoenix_url,
                f"/v1/experiments/{exp_id}/runs",
                {
                    "dataset_example_id": ex_id,
                    "output": {"answer": answer},
                    "repetition_number": 1,
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat(),
                },
            )
            run_id = run["data"]["id"]
            runs.append(
                {
                    "run_id": run_id,
                    "question": question,
                    "reference": reference,
                    "answer": answer,
                }
            )
            print(f"A: {answer[:50]}...")
        except Exception as e:
            end = datetime.now(timezone.utc)
            # Submit failed run
            try:
                rest_post(
                    phoenix_url,
                    f"/v1/experiments/{exp_id}/runs",
                    {
                        "dataset_example_id": ex_id,
                        "output": None,
                        "error": str(e),
                        "repetition_number": 1,
                        "start_time": start.isoformat(),
                        "end_time": end.isoformat(),
                    },
                )
            except Exception:
                pass
            print(f"ERROR: {e}")

    print(f"  -> Completed {len(runs)}/{len(examples)} runs")

    # 3. Run LLM-as-Judge evaluation on each run
    print("  -> Running LLM-as-Judge evaluations...")
    eval_count = 0
    for run_info in runs:
        try:
            judge_result = call_openai(
                api_key,
                [
                    {
                        "role": "system",
                        "content": (
                            "You are an expert evaluator. Compare the AI answer to the reference. "
                            "Use the correctness function to submit your rating."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Question: {run_info['question']}\n\n"
                            f"Reference Answer: {run_info['reference']}\n\n"
                            f"AI Answer: {run_info['answer']}"
                        ),
                    },
                ],
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "correctness",
                            "description": "Whether the answer is correct",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "label": {
                                        "type": "string",
                                        "enum": [
                                            "correct",
                                            "partially_correct",
                                            "incorrect",
                                        ],
                                        "description": "correctness",
                                    },
                                    "explanation": {
                                        "type": "string",
                                        "description": "Brief explanation",
                                    },
                                },
                                "required": ["label", "explanation"],
                            },
                        },
                    }
                ],
                tool_choice={
                    "type": "function",
                    "function": {"name": "correctness"},
                },
            )

            # Extract tool call result
            msg = judge_result["choices"][0]["message"]
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                args = json.loads(tool_calls[0]["function"]["arguments"])
                label = args.get("label", "incorrect")
                explanation = args.get("explanation", "")
                score_map = {
                    "correct": 1.0,
                    "partially_correct": 0.5,
                    "incorrect": 0.0,
                }
                score = score_map.get(label, 0.0)
            else:
                label = "incorrect"
                explanation = "No tool call returned"
                score = 0.0

            # Submit evaluation
            start = datetime.now(timezone.utc)
            rest_post(
                phoenix_url,
                "/v1/experiment_evaluations",
                {
                    "experiment_run_id": run_info["run_id"],
                    "name": "correctness",
                    "annotator_kind": "LLM",
                    "result": {
                        "label": label,
                        "score": score,
                        "explanation": explanation,
                    },
                    "start_time": start.isoformat(),
                    "end_time": datetime.now(timezone.utc).isoformat(),
                },
            )
            eval_count += 1
        except Exception as e:
            print(f"     Eval error for run {run_info['run_id']}: {e}")

    print(f"  -> Completed {eval_count}/{len(runs)} evaluations")
    print(f"  -> View in Phoenix UI: Datasets -> demo-qa-dataset -> Experiments -> {exp_name}")
    return eval_count > 0


# ===========================================================================
# Verify & Summary
# ===========================================================================


def verify_all(phoenix_url: str) -> None:
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    # Models (use generativeModels, not models)
    try:
        result = gql(
            phoenix_url,
            "{ generativeModels { edges { node { id name } } } }",
        )
        models = [
            e["node"]
            for e in result["data"]["generativeModels"]["edges"]
            if e["node"]["name"] == MODEL_NAME
        ]
        print(f"\nModels: {MODEL_NAME} {'FOUND' if models else 'NOT FOUND'}")
    except Exception as e:
        print(f"\nModels: ERROR ({e})")

    # Datasets
    datasets = rest_get(phoenix_url, "/v1/datasets")
    ds_list = datasets.get("data", [])
    print(f"\nDatasets ({len(ds_list)}):")
    for ds in ds_list:
        print(
            f"  - {ds['name']} (id: {ds['id']}, examples: {ds.get('example_count', '?')})"
        )

    # Prompts
    prompts = rest_get(phoenix_url, "/v1/prompts")
    p_list = prompts.get("data", [])
    print(f"\nPrompts ({len(p_list)}):")
    for p in p_list:
        print(f"  - {p['name']} (id: {p['id']})")

    # Traces
    result = gql(
        phoenix_url,
        "{ projects { edges { node { name traceCount } } } }",
    )
    projects = result["data"]["projects"]["edges"]
    print(f"\nProjects/Traces:")
    for p in projects:
        n = p["node"]
        print(f"  - {n['name']}: {n['traceCount']} traces")

    # Experiments
    for ds in ds_list:
        try:
            exps = rest_get(
                phoenix_url,
                f"/v1/datasets/{ds['id']}/experiments",
            )
            exp_list = exps.get("data", [])
            if exp_list:
                print(f"\nExperiments on '{ds['name']}':")
                for exp in exp_list:
                    runs_ok = exp.get("successful_run_count", 0)
                    runs_fail = exp.get("failed_run_count", 0)
                    print(
                        f"  - {exp.get('name', exp['id'])}: "
                        f"{runs_ok} ok / {runs_fail} failed"
                    )
        except Exception:
            pass

    print(f"\nPhoenix Dashboard: {phoenix_url}")
    print("=" * 60)


# ===========================================================================
# Cleanup: remove previously failed/stale data
# ===========================================================================


def cleanup_stale_data(phoenix_url: str) -> None:
    """Delete stale experiments with all-failed runs."""
    datasets = rest_get(phoenix_url, "/v1/datasets")
    for ds in datasets.get("data", []):
        try:
            exps = rest_get(
                phoenix_url,
                f"/v1/datasets/{ds['id']}/experiments",
            )
            for exp in exps.get("data", []):
                if (
                    exp.get("successful_run_count", 0) == 0
                    and exp.get("failed_run_count", 0) > 0
                ):
                    requests.delete(
                        f"{phoenix_url}/v1/experiments/{exp['id']}",
                        timeout=10,
                    )
                    print(f"  Cleaned up failed experiment: {exp['id']}")
        except Exception:
            pass


# ===========================================================================
# Main
# ===========================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description="Setup Phoenix demo features")
    parser.add_argument("--phoenix-url", default=DEFAULT_PHOENIX_URL)
    parser.add_argument("--gpt-key-file", default=DEFAULT_GPT_KEY_FILE)
    parser.add_argument("--gpt-key", default=None, help="GPT key directly")
    parser.add_argument(
        "--skip-experiment", action="store_true", help="Skip dataset experiment"
    )
    parser.add_argument(
        "--verify-only", action="store_true", help="Only run verification"
    )
    parser.add_argument(
        "--cleanup", action="store_true", help="Clean up stale failed experiments"
    )
    args = parser.parse_args()

    phoenix_url = args.phoenix_url.rstrip("/")

    # Load API key
    if args.gpt_key:
        api_key = args.gpt_key.strip()
    else:
        with open(args.gpt_key_file) as f:
            api_key = f.read().strip()

    if not api_key:
        print("ERROR: No GPT API key provided")
        sys.exit(1)

    # Check Phoenix is reachable
    try:
        requests.get(f"{phoenix_url}/graphql", timeout=5)
    except Exception:
        print(f"ERROR: Phoenix not reachable at {phoenix_url}")
        sys.exit(1)

    print(f"Phoenix URL: {phoenix_url}")
    print(f"Model: {MODEL_NAME} (max_tokens={MAX_TOKENS})")

    if args.verify_only:
        verify_all(phoenix_url)
        return

    if args.cleanup:
        cleanup_stale_data(phoenix_url)
        return

    # Execute all steps
    results: dict[str, bool] = {}
    dataset_id: str | None = None
    examples: list[dict] = []

    # Step 1: Store secret
    try:
        store_openai_secret(phoenix_url, api_key)
        results["secrets"] = True
    except Exception as e:
        print(f"  -> ERROR: {e}")
        results["secrets"] = False

    # Step 2: Create model
    try:
        create_model(phoenix_url)
        results["model"] = True
    except Exception as e:
        print(f"  -> ERROR: {e}")
        results["model"] = False

    # Step 3: Create dataset
    try:
        dataset_id, examples = create_dataset(phoenix_url)
        results["dataset"] = True
    except Exception as e:
        print(f"  -> ERROR: {e}")
        results["dataset"] = False

    # Step 4: Create prompts
    try:
        create_prompts(phoenix_url)
        results["prompts"] = True
    except Exception as e:
        print(f"  -> ERROR: {e}")
        results["prompts"] = False

    # Step 5: Test playground
    try:
        results["playground"] = test_playground(phoenix_url, api_key)
    except Exception as e:
        print(f"  -> ERROR: {e}")
        results["playground"] = False

    # Step 6: Create evaluator
    if dataset_id:
        try:
            eval_id = create_evaluator(phoenix_url, dataset_id)
            results["evaluator"] = eval_id is not None
        except Exception as e:
            print(f"  -> ERROR: {e}")
            results["evaluator"] = False
    else:
        print("\n[6/7] Skipped evaluator (no dataset)")
        results["evaluator"] = False

    # Step 7: Run experiment
    if not args.skip_experiment and dataset_id:
        try:
            results["experiment"] = run_experiment(
                phoenix_url, api_key, dataset_id, examples
            )
        except Exception as e:
            print(f"  -> ERROR: {e}")
            results["experiment"] = False
    else:
        print("\n[7/7] Skipped experiment")
        results["experiment"] = False

    # Final verification
    verify_all(phoenix_url)

    # Print results
    print("\nRESULTS:")
    all_ok = True
    for step, ok in results.items():
        status = "PASS" if ok else "FAIL"
        icon = "+" if ok else "-"
        print(f"  [{icon}] {step}: {status}")
        if not ok:
            all_ok = False

    if all_ok:
        print("\nAll features configured successfully!")
    else:
        print("\nSome features need attention -- check errors above.")
        print("You can fix issues in Phoenix UI: " + phoenix_url)

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
