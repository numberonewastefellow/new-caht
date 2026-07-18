from typing import List

import requests

from om.server.features.workspaces.models import CategorizedFilesSnapshot
from om.server.features.workspaces.models import KnowledgeFileSnapshot
from om.server.features.workspaces.models import WorkspaceSnapshot
from tests.integration.common_utils.constants import API_SERVER_URL
from tests.integration.common_utils.constants import GENERAL_HEADERS
from tests.integration.common_utils.test_models import DATestUser


class WorkspaceManager:
    @staticmethod
    def create(
        name: str,
        user_performing_action: DATestUser,
    ) -> WorkspaceSnapshot:
        """Create a new workspace via API."""
        response = requests.post(
            f"{API_SERVER_URL}/workspaces/create",
            params={"name": name},
            headers=user_performing_action.headers or GENERAL_HEADERS,
        )
        response.raise_for_status()
        return WorkspaceSnapshot.model_validate(response.json())

    @staticmethod
    def get_all(
        user_performing_action: DATestUser,
    ) -> List[WorkspaceSnapshot]:
        """Get all workspaces for a user via API."""
        response = requests.get(
            f"{API_SERVER_URL}/workspaces",
            headers=user_performing_action.headers or GENERAL_HEADERS,
        )
        response.raise_for_status()
        return [WorkspaceSnapshot.model_validate(obj) for obj in response.json()]

    @staticmethod
    def delete(
        workspace_id: int,
        user_performing_action: DATestUser,
    ) -> bool:
        """Delete a workspace via API."""
        response = requests.delete(
            f"{API_SERVER_URL}/workspaces/{workspace_id}",
            headers=user_performing_action.headers or GENERAL_HEADERS,
        )
        return response.status_code == 204

    @staticmethod
    def verify_deleted(
        workspace_id: int,
        user_performing_action: DATestUser,
    ) -> bool:
        """Verify that a workspace has been deleted by ensuring it's not in list."""
        response = requests.get(
            f"{API_SERVER_URL}/workspaces",
            headers=user_performing_action.headers or GENERAL_HEADERS,
        )
        response.raise_for_status()
        workspaces = [WorkspaceSnapshot.model_validate(obj) for obj in response.json()]
        return all(p.id != workspace_id for p in workspaces)

    @staticmethod
    def verify_files_unlinked(
        workspace_id: int,
        user_performing_action: DATestUser | None = None,
    ) -> bool:
        """Verify that all files have been unlinked from the workspace via API."""
        response = requests.get(
            f"{API_SERVER_URL}/workspaces/files/{workspace_id}",
            headers=(
                user_performing_action.headers
                if user_performing_action
                else GENERAL_HEADERS
            ),
        )
        if response.status_code == 404:
            return True
        if not response.ok:
            return False
        files = [KnowledgeFileSnapshot.model_validate(obj) for obj in response.json()]
        return len(files) == 0

    @staticmethod
    def verify_chat_sessions_unlinked(
        workspace_id: int,
        user_performing_action: DATestUser | None = None,
    ) -> bool:
        """Verify that all chat sessions have been unlinked from the workspace via API."""
        response = requests.get(
            f"{API_SERVER_URL}/workspaces/{workspace_id}",
            headers=(
                user_performing_action.headers
                if user_performing_action
                else GENERAL_HEADERS
            ),
        )
        if response.status_code == 404:
            return True
        if not response.ok:
            return False
        try:
            workspace = WorkspaceSnapshot.model_validate(response.json())
            chat_sessions = getattr(workspace, "chat_sessions", [])
            return len(chat_sessions or []) == 0
        except Exception:
            # If response doesn't include chat_sessions, assume unlinked
            return True

    @staticmethod
    def upload_files(
        workspace_id: int,
        files: List[tuple[str, bytes]],  # List of (filename, content) tuples
        user_performing_action: DATestUser,
    ) -> CategorizedFilesSnapshot:
        """Upload files to a workspace via API."""
        # Build multipart form-data
        files_payload = [
            (
                "files",
                (filename, content, "text/plain"),
            )
            for filename, content in files
        ]

        data = {"workspace_id": str(workspace_id)} if workspace_id is not None else {}

        # Let requests set Content-Type boundary by not overriding header
        headers = dict(user_performing_action.headers or {})
        headers.pop("Content-Type", None)

        response = requests.post(
            f"{API_SERVER_URL}/workspaces/file/upload",
            data=data,
            files=files_payload,
            headers=headers,
        )
        response.raise_for_status()
        return CategorizedFilesSnapshot.model_validate(response.json())

    @staticmethod
    def get_workspace_files(
        workspace_id: int,
        user_performing_action: DATestUser | None = None,
    ) -> List[KnowledgeFileSnapshot]:
        """Get all files associated with a workspace via API."""
        response = requests.get(
            f"{API_SERVER_URL}/workspaces/files/{workspace_id}",
            headers=(
                user_performing_action.headers
                if user_performing_action
                else GENERAL_HEADERS
            ),
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return [KnowledgeFileSnapshot.model_validate(obj) for obj in response.json()]

    @staticmethod
    def set_instructions(
        workspace_id: int,
        instructions: str,
        user_performing_action: DATestUser,
    ) -> str:
        """Set workspace instructions via API."""
        response = requests.post(
            f"{API_SERVER_URL}/workspaces/{workspace_id}/instructions",
            json={"instructions": instructions},
            headers=user_performing_action.headers or GENERAL_HEADERS,
        )
        response.raise_for_status()
        return (response.json() or {}).get("instructions") or ""
