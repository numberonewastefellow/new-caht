"""
Parallel and Loop steps, nested, end to end
===========================================

Runs throwaway workflows through the real API and reads what steps actually produced.
Code steps only, so there are no LLM calls: it needs the code interpreter, not an LLM.

  - a loop inside a parallel branch
  - a loop inside a loop (the inner $loop shadows the outer)
  - a condition inside a branch (skips only within that branch)
  - reading a nested field: $par.output.<branch>[0].v
  - references that can't work are refused on save

Usage:
    python test_container_nesting.py --url http://host:3000 --key YOUR_KEY
"""

import argparse
import json
import sys

from config import add_common_args
from config import api
from config import apply_common_args
from config import stream_api

PREFIX = "flow-nesting-test"


def code(key, order, source, outputs, inputs=None, **extra):
    return {
        "node_key": key,
        "step_type": "code",
        "step_order": order,
        "step_name": key,
        "output_key": key,
        "config": {
            "code": source,
            "inputs": inputs or {},
            "outputs": [{"name": n, "type": t} for n, t in outputs],
        },
        **extra,
    }


def container(key, order, step_type, config, **extra):
    return {
        "node_key": key,
        "step_type": step_type,
        "step_order": order,
        "step_name": key,
        "output_key": key,
        "config": config,
        **extra,
    }


def echo(key, order, value, **extra):
    """A code step returning a constant."""
    return code(
        key,
        order,
        f"def main(inputs):\n    return {{'v': {value!r}}}\n",
        [("v", "string")],
        **extra,
    )


REPORT = (
    "def main(inputs):\n"
    "    return {'seen': inputs['v'] if isinstance(inputs['v'], str) else repr(inputs['v'])}\n"
)


class Suite:
    def __init__(self):
        self.created = []
        self.failures = []

    def check(self, name, ok, detail=""):
        print(f"  {'PASS' if ok else 'FAIL'} {name}" + (f"  [{detail}]" if not ok else ""))
        if not ok:
            self.failures.append(name)

    def save(self, name, steps):
        return api(
            "POST",
            "admin/workflow",
            {
                "name": f"{PREFIX} {name}",
                "orchestration_mode": "sequential",
                "is_public": False,
                "steps": steps,
            },
        )

    def run(self, name, steps):
        print(f"\n{name}")
        response = self.save(name, steps)
        if response.status_code != 200:
            self.check("saved", False, f"{response.status_code} {response.text[:300]}")
            return [], ""
        workflow = response.json()
        self.created.append(workflow["id"])
        stream = stream_api("POST", f"workflow/{workflow['id']}/run", {"message": "go"})
        started, answer = [], ""
        for line in stream.iter_lines():
            if not line:
                continue
            obj = json.loads(line).get("obj", {})
            if obj.get("type") == "workflow_step_start":
                started.append(obj.get("step_name"))
            elif obj.get("type") == "message_delta":
                answer += obj.get("content") or ""
        self.check("ran to the end", bool(answer), str(started))
        return started, answer

    def cleanup(self):
        for workflow_id in self.created:
            api("DELETE", f"admin/workflow/{workflow_id}")


def loop_in_parallel(suite):
    started, answer = suite.run(
        "loop in a parallel branch",
        [
            code("seed", 0, "def main(inputs):\n    return {'items': ['a', 'b']}\n", [("items", "array")]),
            container("par", 1, "parallel", {"branches": [{"label": "Looped"}, {"label": "Plain"}]}),
            container(
                "each", 2, "loop",
                {"mode": "for_each", "items": "$seed.output.items", "max_iterations": 5},
                parent_key="par", branch_index=0,
            ),
            code(
                "upper", 3, "def main(inputs):\n    return {'v': inputs['x'].upper()}\n", [("v", "string")],
                {"x": "$loop.item"}, parent_key="each", branch_index=0,
            ),
            echo("plain", 4, "plain", parent_key="par", branch_index=1),
            code("report", 5, REPORT, [("seen", "string")], {"v": "$par.output.Looped[1].v"}),
        ],
    )
    suite.check("the loop ran once per item", started.count("upper") == 2, str(started))
    suite.check("the other branch ran", "plain" in started, str(started))
    suite.check("a nested field is readable after the join", answer.strip() == "B", repr(answer))


def loop_in_loop(suite):
    started, answer = suite.run(
        "loop in a loop",
        [
            code("seed", 0, "def main(inputs):\n    return {'rows': [[1, 2], [3]]}\n", [("rows", "array")]),
            container("outer", 1, "loop", {"mode": "for_each", "items": "$seed.output.rows", "max_iterations": 5}),
            container(
                "inner", 2, "loop",
                {"mode": "for_each", "items": "$loop.item", "max_iterations": 5},
                parent_key="outer", branch_index=0,
            ),
            code(
                "double", 3, "def main(inputs):\n    return {'v': inputs['n'] * 2}\n", [("v", "integer")],
                {"n": "$loop.item"}, parent_key="inner", branch_index=0,
            ),
            code("report", 4, REPORT, [("seen", "string")], {"v": "$outer.output"}),
        ],
    )
    suite.check("the inner loop ran for every value", started.count("double") == 3, str(started))
    for value in ("2", "4", "6"):
        suite.check(f"the result holds {value}", value in answer, repr(answer))


def router_in_branch(suite):
    started, answer = suite.run(
        "condition in a branch",
        [
            container("par", 0, "parallel", {"branches": [{"label": "Routed"}, {"label": "Other"}]}),
            echo("flag", 1, "yes", parent_key="par", branch_index=0),
            {
                "node_key": "route",
                "step_type": "conditional_router",
                "step_order": 2,
                "step_name": "route",
                "output_key": "route",
                "parent_key": "par",
                "branch_index": 0,
                "config": {
                    "condition_field": "$flag.output",
                    "operator": "contains",
                    "match_value": "yes",
                    "case_sensitive": False,
                    "true_node_keys": ["taken"],
                    "false_node_keys": ["not_taken"],
                },
            },
            echo("taken", 3, "TAKEN", parent_key="par", branch_index=0),
            echo("not_taken", 4, "NOT_TAKEN", parent_key="par", branch_index=0),
            echo("other", 5, "OTHER", parent_key="par", branch_index=1),
            code("report", 6, REPORT, [("seen", "string")], {"v": "$par.output"}),
        ],
    )
    suite.check("the true path ran", "taken" in started, str(started))
    suite.check("the false path was skipped", "not_taken" not in started, str(started))
    suite.check("the other branch still ran", "other" in started, str(started))
    suite.check("the skipped step left no output", "NOT_TAKEN" not in answer, repr(answer))


def refused_on_save(suite):
    print("\nrefused on save")
    sibling = suite.save(
        "bad sibling",
        [
            container("par", 0, "parallel", {"branches": [{"label": "A"}, {"label": "B"}]}),
            echo("x", 1, "x", parent_key="par", branch_index=0),
            code(
                "y", 2, "def main(inputs):\n    return {'v': inputs['n']}\n", [("v", "string")],
                {"n": "$x.output"}, parent_key="par", branch_index=1,
            ),
        ],
    )
    suite.check("reading a sibling branch", sibling.status_code == 400, sibling.text[:200])
    names = suite.save(
        "bad names",
        [
            container("par", 0, "parallel", {"branches": [{"label": "Same"}, {"label": "Same"}]}),
            echo("x", 1, "x", parent_key="par", branch_index=0),
            echo("y", 2, "y", parent_key="par", branch_index=1),
        ],
    )
    suite.check("duplicate branch names", names.status_code == 400, names.text[:200])
    deep = suite.save(
        "bad parallel in parallel",
        [
            container("outer", 0, "parallel", {"branches": [{"label": "A"}, {"label": "B"}]}),
            container("inner", 1, "parallel", {"branches": [{"label": "C"}, {"label": "D"}]}, parent_key="outer", branch_index=0),
            echo("x", 2, "x", parent_key="inner", branch_index=0),
            echo("y", 3, "y", parent_key="inner", branch_index=1),
            echo("z", 4, "z", parent_key="outer", branch_index=1),
        ],
    )
    suite.check("a parallel inside a parallel", deep.status_code == 400, deep.text[:200])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    apply_common_args(parser.parse_args())

    suite = Suite()
    try:
        loop_in_parallel(suite)
        loop_in_loop(suite)
        router_in_branch(suite)
        refused_on_save(suite)
    finally:
        suite.cleanup()

    print(f"\n{'FAILED: ' + ', '.join(suite.failures) if suite.failures else 'All checks passed'}")
    sys.exit(1 if suite.failures else 0)


if __name__ == "__main__":
    main()
