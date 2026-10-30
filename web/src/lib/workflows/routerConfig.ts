/**
 * Helpers for `conditional_router` configs.
 *
 * The editors always work with router v2 configs, whose branch targets are
 * stable node keys. Legacy v1 configs (targets by step order) are converted on
 * load, the same way the backend's `upgrade_router_v1_to_v2` does.
 */

import type { ConditionOperator, RouterConfigV2 } from "./interfaces";

/** The router version the editors read and write. */
export const ROUTER_CONFIG_VERSION = 2;

export type RouterBranch = "true" | "false";

/** Operators that compare against nothing (no match value needed). */
export const VALUELESS_OPERATORS: ReadonlySet<string> = new Set([
  "is_empty",
  "is_not_empty",
]);

export function defaultRouterConfig(): RouterConfigV2 {
  return {
    condition_field: "",
    operator: "contains",
    match_value: "",
    case_sensitive: false,
    true_node_keys: [],
    false_node_keys: [],
  };
}

function stringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((v): v is string => typeof v === "string")
    : [];
}

/** Read a (possibly partial) stored config as a complete v2 config. */
export function normalizeRouterConfig(
  raw: Record<string, unknown> | null | undefined
): RouterConfigV2 {
  const base = defaultRouterConfig();
  if (!raw) return base;
  return {
    condition_field:
      typeof raw.condition_field === "string"
        ? raw.condition_field
        : base.condition_field,
    operator:
      typeof raw.operator === "string"
        ? (raw.operator as ConditionOperator)
        : base.operator,
    match_value:
      typeof raw.match_value === "string" ? raw.match_value : base.match_value,
    case_sensitive: raw.case_sensitive === true,
    true_node_keys: stringList(raw.true_node_keys),
    false_node_keys: stringList(raw.false_node_keys),
  };
}

/**
 * Convert a v1 condition (targets by step order) to a v2 config. Orders that
 * match no step are dropped; they never skipped anything.
 */
export function routerConfigFromV1(
  condition: Record<string, unknown> | null | undefined,
  orderToKey: ReadonlyMap<number, string>
): RouterConfigV2 {
  const toKeys = (orders: unknown): string[] =>
    (Array.isArray(orders) ? orders : [])
      .map((order) => orderToKey.get(Number(order)))
      .filter((key): key is string => key !== undefined);

  return {
    ...normalizeRouterConfig(condition),
    true_node_keys: toKeys(condition?.true_steps),
    false_node_keys: toKeys(condition?.false_steps),
  };
}

/** Whether a stored config is already in v2 (node key) form. */
export function isRouterConfigV2(
  config: Record<string, unknown> | null | undefined
): boolean {
  return (
    !!config &&
    (Array.isArray(config.true_node_keys) ||
      Array.isArray(config.false_node_keys))
  );
}

export function branchTargets(
  config: RouterConfigV2,
  branch: RouterBranch
): string[] {
  return branch === "true" ? config.true_node_keys : config.false_node_keys;
}

export function withBranchTargets(
  config: RouterConfigV2,
  branch: RouterBranch,
  keys: string[]
): RouterConfigV2 {
  return branch === "true"
    ? { ...config, true_node_keys: keys }
    : { ...config, false_node_keys: keys };
}

/** Drop branch targets that no longer exist (e.g. deleted steps). */
export function pruneRouterTargets(
  config: RouterConfigV2,
  existingKeys: ReadonlySet<string>
): RouterConfigV2 {
  return {
    ...config,
    true_node_keys: config.true_node_keys.filter((k) => existingKeys.has(k)),
    false_node_keys: config.false_node_keys.filter((k) => existingKeys.has(k)),
  };
}

/** A short human summary such as `$research.output contains "error"`. */
export function describeCondition(config: RouterConfigV2): string {
  if (!config.condition_field) return "No condition set";
  if (VALUELESS_OPERATORS.has(config.operator)) {
    return `${config.condition_field} ${config.operator}`;
  }
  return `${config.condition_field} ${config.operator} "${config.match_value}"`;
}
