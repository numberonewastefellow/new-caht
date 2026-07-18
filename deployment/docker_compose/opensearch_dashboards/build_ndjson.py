"""Generate `files_and_chunks.ndjson` (OpenSearch Dashboards saved objects).

Run:  python build_ndjson.py
Then import the generated NDJSON with import_dashboards.sh.

Building the saved objects as Python dicts (and json.dumps-ing them) avoids the
error-prone manual escaping of the nested visState / searchSource / panels JSON
strings that the Dashboards saved-object format requires.
"""

import json
import os

INDEX_PATTERN_ID = "danswer-chunks"
INDEX_PATTERN_TITLE = "chunk_*"
DASHBOARD_ID = "danswer-files-and-chunks"
VERSION = "3.6.0"

# Drill-down: render each `user_projects` value (in the "Files by Project" table
# and the Chunk Text saved search) as a link that reloads THIS dashboard scoped
# to that project via a KQL query. This is the reliable, scales-to-many-projects
# alternative to the legacy data-table cell click, which is broken by an OSD
# 3.5/3.6 filter-button regression.
FIELD_FORMAT_MAP = {
    "user_projects": {
        "id": "url",
        "params": {
            "type": "a",
            "urlTemplate": (
                "/app/dashboards#/view/" + DASHBOARD_ID
                + "?_g=()&_a=(query:(language:kuery,query:'user_projects:{{value}}'))"
            ),
            "labelTemplate": "{{value}}",
            "openLinkInCurrentTab": True,
        },
    }
}

INDEX_REF = {
    "name": "kibanaSavedObjectMeta.searchSourceJSON.index",
    "type": "index-pattern",
    "id": INDEX_PATTERN_ID,
}
SEARCH_SOURCE_VIZ = json.dumps(
    {
        "query": {"query": "", "language": "kuery"},
        "filter": [],
        "indexRefName": "kibanaSavedObjectMeta.searchSourceJSON.index",
    }
)


def metric_viz(obj_id, title, agg):
    vis_state = {
        "title": title,
        "type": "metric",
        "aggs": [agg],
        "params": {
            "addTooltip": True,
            "addLegend": False,
            "type": "metric",
            "metric": {
                "percentageMode": False,
                "useRanges": False,
                "colorSchema": "Green to Red",
                "metricColorMode": "None",
                "colorsRange": [{"from": 0, "to": 1000000}],
                "labels": {"show": True},
                "invertColors": False,
                "style": {
                    "bgFill": "#000",
                    "bgColor": False,
                    "labelColor": False,
                    "subText": "",
                    "fontSize": 48,
                },
            },
        },
    }
    return {
        "id": obj_id,
        "type": "visualization",
        "attributes": {
            "title": title,
            "visState": json.dumps(vis_state),
            "uiStateJSON": "{}",
            "description": "",
            "version": 1,
            "kibanaSavedObjectMeta": {"searchSourceJSON": SEARCH_SOURCE_VIZ},
        },
        "references": [INDEX_REF],
    }


def table_viz(obj_id, title, aggs):
    vis_state = {
        "title": title,
        "type": "table",
        "aggs": aggs,
        "params": {
            "perPage": 20,
            "showPartialRows": False,
            "showMetricsAtAllLevels": False,
            "showTotal": False,
            "totalFunc": "sum",
            "percentageCol": "",
        },
    }
    return {
        "id": obj_id,
        "type": "visualization",
        "attributes": {
            "title": title,
            "visState": json.dumps(vis_state),
            "uiStateJSON": "{}",
            "description": "",
            "version": 1,
            "kibanaSavedObjectMeta": {"searchSourceJSON": SEARCH_SOURCE_VIZ},
        },
        "references": [INDEX_REF],
    }


def terms_bucket(agg_id, field, order_by, size=100):
    return {
        "id": agg_id,
        "enabled": True,
        "type": "terms",
        "schema": "bucket",
        "params": {
            "field": field,
            "orderBy": order_by,
            "order": "desc",
            "size": size,
            "otherBucket": False,
            "otherBucketLabel": "Other",
            "missingBucket": False,
            "missingBucketLabel": "Missing",
        },
    }


objects = []

# 1) index pattern (fields omitted -> Dashboards computes them via field caps)
objects.append(
    {
        "id": INDEX_PATTERN_ID,
        "type": "index-pattern",
        "attributes": {
            "title": INDEX_PATTERN_TITLE,
            "fieldFormatMap": json.dumps(FIELD_FORMAT_MAP),
        },
        "references": [],
    }
)

# 2) Total Files = unique document_id
objects.append(
    metric_viz(
        "danswer-total-files",
        "Total Files",
        {
            "id": "1",
            "enabled": True,
            "type": "cardinality",
            "schema": "metric",
            "params": {"field": "document_id"},
        },
    )
)

# 3) Total Chunks = count
objects.append(
    metric_viz(
        "danswer-total-chunks",
        "Total Chunks",
        {"id": "1", "enabled": True, "type": "count", "schema": "metric", "params": {}},
    )
)

# 4) Files table: document_id -> filename (top_hits, since semantic_identifier
#    has doc_values disabled and can't be a terms bucket) -> chunk count
objects.append(
    table_viz(
        "danswer-files-table",
        "Files (click to see chunks)",
        [
            {"id": "1", "enabled": True, "type": "count", "schema": "metric", "params": {}},
            {
                "id": "2",
                "enabled": True,
                "type": "top_hits",
                "schema": "metric",
                "params": {
                    "field": "semantic_identifier",
                    "aggregate": "concat",
                    "size": 1,
                    "sortField": "chunk_index",
                    "sortOrder": "asc",
                },
            },
            terms_bucket("3", "document_id", "1"),
        ],
    )
)

# 5) Files by Project: user_projects -> #files (cardinality) + #chunks (count)
objects.append(
    table_viz(
        "danswer-files-by-project",
        "Files by Project (click a project)",
        [
            {"id": "1", "enabled": True, "type": "count", "schema": "metric", "params": {}},
            {
                "id": "2",
                "enabled": True,
                "type": "cardinality",
                "schema": "metric",
                "params": {"field": "document_id"},
            },
            terms_bucket("3", "user_projects", "2"),
        ],
    )
)

# 6) Chunk Text saved search
objects.append(
    {
        "id": "danswer-chunk-text",
        "type": "search",
        "attributes": {
            "title": "Chunk Text",
            "description": "",
            "hits": 0,
            "columns": [
                "semantic_identifier",
                "document_id",
                "chunk_index",
                "user_projects",
                "source_type",
                "content",
            ],
            "sort": [["document_id", "asc"], ["chunk_index", "asc"]],
            "version": 1,
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps(
                    {
                        "highlightAll": True,
                        "version": True,
                        "query": {"query": "", "language": "kuery"},
                        "filter": [],
                        "indexRefName": "kibanaSavedObjectMeta.searchSourceJSON.index",
                    }
                )
            },
        },
        "references": [INDEX_REF],
    }
)

# 7) Dashboard
panels = [
    {"x": 0, "y": 0, "w": 12, "h": 8, "i": "1", "ref": "panel_1"},
    {"x": 12, "y": 0, "w": 12, "h": 8, "i": "2", "ref": "panel_2"},
    {"x": 0, "y": 8, "w": 24, "h": 15, "i": "3", "ref": "panel_3"},
    {"x": 24, "y": 8, "w": 24, "h": 15, "i": "4", "ref": "panel_4"},
    {"x": 0, "y": 23, "w": 48, "h": 20, "i": "5", "ref": "panel_5"},
]
panels_json = [
    {
        "version": VERSION,
        "gridData": {"x": p["x"], "y": p["y"], "w": p["w"], "h": p["h"], "i": p["i"]},
        "panelIndex": p["i"],
        "embeddableConfig": {},
        "panelRefName": p["ref"],
    }
    for p in panels
]
dashboard_refs = [
    {"name": "panel_1", "type": "visualization", "id": "danswer-total-files"},
    {"name": "panel_2", "type": "visualization", "id": "danswer-total-chunks"},
    {"name": "panel_3", "type": "visualization", "id": "danswer-files-table"},
    {"name": "panel_4", "type": "visualization", "id": "danswer-files-by-project"},
    {"name": "panel_5", "type": "search", "id": "danswer-chunk-text"},
]
objects.append(
    {
        "id": DASHBOARD_ID,
        "type": "dashboard",
        "attributes": {
            "title": "VirtualAI — Files & Chunks",
            "hits": 0,
            "description": (
                "Files indexed in OpenSearch: totals, chunks per file, and per-project "
                "breakdown. Click a file or project row to drill into chunk text."
            ),
            "panelsJSON": json.dumps(panels_json),
            "optionsJSON": json.dumps({"useMargins": True, "hidePanelTitles": False}),
            "version": 1,
            "timeRestore": False,
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps(
                    {"query": {"query": "", "language": "kuery"}, "filter": []}
                )
            },
        },
        "references": dashboard_refs,
    }
)

out_path = os.path.join(os.path.dirname(__file__), "files_and_chunks.ndjson")
with open(out_path, "w", encoding="utf-8") as f:
    for obj in objects:
        f.write(json.dumps(obj) + "\n")
print(f"Wrote {len(objects)} saved objects to {out_path}")
