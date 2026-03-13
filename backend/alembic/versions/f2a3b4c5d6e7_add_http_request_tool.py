"""add_http_request_tool

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-03-13 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add HttpRequestTool to built-in tools."""
    conn = op.get_bind()

    # Check if it already exists (idempotent)
    result = conn.execute(
        sa.text("SELECT id FROM tool WHERE in_code_tool_id = :tid"),
        {"tid": "HttpRequestTool"},
    )
    if result.fetchone() is not None:
        return

    conn.execute(
        sa.text(
            """
            INSERT INTO tool (name, display_name, description, in_code_tool_id, enabled)
            VALUES (:name, :display_name, :description, :in_code_tool_id, :enabled)
            """
        ),
        {
            "name": "HttpRequestTool",
            "display_name": "HTTP Request",
            "description": (
                "Make HTTP requests to any URL. Supports GET, POST, PUT, DELETE, "
                "PATCH methods with custom headers and request body."
            ),
            "in_code_tool_id": "HttpRequestTool",
            "enabled": True,
        },
    )


def downgrade() -> None:
    """Remove HttpRequestTool from built-in tools."""
    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            DELETE FROM tool
            WHERE in_code_tool_id = :in_code_tool_id
            """
        ),
        {
            "in_code_tool_id": "HttpRequestTool",
        },
    )
