from typing import List

import pytest

from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.models import KnowledgeFile
from om.server.features.workspaces.models import WorkspaceSnapshot
from tests.integration.common_utils.managers.workspace import WorkspaceManager
from tests.integration.common_utils.reset import reset_all
from tests.integration.common_utils.test_models import DATestLLMProvider
from tests.integration.common_utils.test_models import DATestUser


@pytest.fixture(scope="module", autouse=True)
def reset_for_module() -> None:
    """Reset all data once before running any tests in this module."""
    reset_all()


def test_workspaces_flow(
    reset_for_module: None,  # noqa: ARG001
    basic_user: DATestUser,
    llm_provider: DATestLLMProvider,  # noqa: ARG001
) -> None:
    """End-to-end workspace flow covering creation, listing, files, instructions, deletion, and edge cases."""
    # Case 1: Workspace creation and listing
    WorkspaceManager.create(
        name="Test Workspace 1",
        user_performing_action=basic_user,
    )
    WorkspaceManager.create(
        name="Test Workspace 2",
        user_performing_action=basic_user,
    )

    workspaces = WorkspaceManager.get_all(user_performing_action=basic_user)
    assert len(workspaces) >= 2
    workspace_names = {p.name for p in workspaces}
    assert "Test Workspace 1" in workspace_names
    assert "Test Workspace 2" in workspace_names
    assert all(str(p.user_id) == basic_user.id for p in workspaces)

    # Case 2: File upload and management
    file_workspace = WorkspaceManager.create(
        name="File Test Workspace",
        user_performing_action=basic_user,
    )
    test_files = [
        ("test1.txt", b"This is test file 1 content"),
        ("test2.txt", b"This is test file 2 content"),
    ]
    upload_result = WorkspaceManager.upload_files(
        workspace_id=file_workspace.id,
        files=test_files,
        user_performing_action=basic_user,
    )
    assert len(upload_result.knowledge_files) == 2
    assert len(upload_result.rejected_files) == 0
    workspace_files = WorkspaceManager.get_workspace_files(
        workspace_id=file_workspace.id,
        user_performing_action=basic_user,
    )
    assert len(workspace_files) == 2
    file_names = {f.name for f in workspace_files}
    assert "test1.txt" in file_names
    assert "test2.txt" in file_names

    # Case 3: Instructions set and update
    instructions_workspace = WorkspaceManager.create(
        name="Instructions Test Workspace",
        user_performing_action=basic_user,
    )
    instructions = "These are test workspace instructions"
    result = WorkspaceManager.set_instructions(
        workspace_id=instructions_workspace.id,
        instructions=instructions,
        user_performing_action=basic_user,
    )
    assert result == instructions
    new_instructions = "These are updated test workspace instructions"
    result = WorkspaceManager.set_instructions(
        workspace_id=instructions_workspace.id,
        instructions=new_instructions,
        user_performing_action=basic_user,
    )
    assert result == new_instructions

    # Case 4: Deletion with files (unlink but do not delete files)
    delete_file_workspace = WorkspaceManager.create(
        name="Deletion Test Workspace",
        user_performing_action=basic_user,
    )
    del_test_files = [
        ("delete_test1.txt", b"This is test file 1 content"),
        ("delete_test2.txt", b"This is test file 2 content"),
    ]
    WorkspaceManager.upload_files(
        workspace_id=delete_file_workspace.id,
        files=del_test_files,
        user_performing_action=basic_user,
    )
    del_workspace_files = WorkspaceManager.get_workspace_files(
        workspace_id=delete_file_workspace.id,
        user_performing_action=basic_user,
    )
    assert len(del_workspace_files) == 2
    deletion_success = WorkspaceManager.delete(
        workspace_id=delete_file_workspace.id,
        user_performing_action=basic_user,
    )
    assert deletion_success
    assert WorkspaceManager.verify_deleted(
        workspace_id=delete_file_workspace.id,
        user_performing_action=basic_user,
    )
    assert WorkspaceManager.verify_files_unlinked(
        workspace_id=delete_file_workspace.id,
        user_performing_action=basic_user,
    )
    with get_session_with_current_tenant() as db_session:
        file_ids = [f.id for f in del_workspace_files]
        remaining_files = (
            db_session.query(KnowledgeFile).filter(KnowledgeFile.id.in_(file_ids)).all()
        )
        assert len(remaining_files) == 2

    # Case 5: Deletion with chat sessions unlinked
    chat_workspace = WorkspaceManager.create(
        name="Chat Session Test Workspace",
        user_performing_action=basic_user,
    )
    deletion_success = WorkspaceManager.delete(
        workspace_id=chat_workspace.id,
        user_performing_action=basic_user,
    )
    assert deletion_success
    assert WorkspaceManager.verify_chat_sessions_unlinked(
        workspace_id=chat_workspace.id,
        user_performing_action=basic_user,
    )

    # Case 6: Multiple workspace operations
    workspaces_group: List[WorkspaceSnapshot] = []
    for i in range(3):
        proj = WorkspaceManager.create(
            name=f"Multi-op Workspace {i}",
            user_performing_action=basic_user,
        )
        workspaces_group.append(proj)

    for i, proj in enumerate(workspaces_group):
        tfiles = [
            (f"multi_test{i}_1.txt", b"This is test file 1 content"),
            (f"multi_test{i}_2.txt", b"This is test file 2 content"),
        ]
        WorkspaceManager.upload_files(
            workspace_id=proj.id,
            files=tfiles,
            user_performing_action=basic_user,
        )

    for i, proj in enumerate(workspaces_group):
        instr = f"Instructions for workspace {i}"
        res = WorkspaceManager.set_instructions(
            workspace_id=proj.id,
            instructions=instr,
            user_performing_action=basic_user,
        )
        assert res == instr

    for proj in workspaces_group:
        proj_files = WorkspaceManager.get_workspace_files(
            workspace_id=proj.id,
            user_performing_action=basic_user,
        )
        assert len(proj_files) == 2
        deletion_success = WorkspaceManager.delete(
            workspace_id=proj.id,
            user_performing_action=basic_user,
        )
        assert deletion_success
        assert WorkspaceManager.verify_deleted(
            workspace_id=proj.id,
            user_performing_action=basic_user,
        )
        assert WorkspaceManager.verify_files_unlinked(
            workspace_id=proj.id,
            user_performing_action=basic_user,
        )
        with get_session_with_current_tenant() as db_session:
            file_ids = [f.id for f in proj_files]
            remaining_files = (
                db_session.query(KnowledgeFile).filter(KnowledgeFile.id.in_(file_ids)).all()
            )
            assert len(remaining_files) == 2

    # Case 7: Edge cases
    with pytest.raises(Exception):
        WorkspaceManager.create(
            name="",
            user_performing_action=basic_user,
        )

    non_existent_id = 99999
    deletion_success = WorkspaceManager.delete(
        workspace_id=non_existent_id,
        user_performing_action=basic_user,
    )
    assert not deletion_success

    with pytest.raises(Exception):
        WorkspaceManager.set_instructions(
            workspace_id=non_existent_id,
            instructions="Test instructions",
            user_performing_action=basic_user,
        )

    with pytest.raises(Exception):
        WorkspaceManager.upload_files(
            workspace_id=non_existent_id,
            files=[("test.txt", b"content")],
            user_performing_action=basic_user,
        )

    long_name = "a" * 1000
    with pytest.raises(Exception):
        WorkspaceManager.create(
            name=long_name,
            user_performing_action=basic_user,
        )

    long_instr_workspace = WorkspaceManager.create(
        name="Long Instructions Test",
        user_performing_action=basic_user,
    )
    long_instructions = "a" * 10000
    result = WorkspaceManager.set_instructions(
        workspace_id=long_instr_workspace.id,
        instructions=long_instructions,
        user_performing_action=basic_user,
    )
    assert result == long_instructions
