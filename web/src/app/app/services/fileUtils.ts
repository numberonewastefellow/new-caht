import { FileDescriptor } from "../interfaces";
import { WorkspaceFile } from "../workspaces/workspacesService";

export function workspacesFileToFileDescriptor(
  file: WorkspaceFile
): FileDescriptor {
  return {
    id: file.file_id,
    type: file.chat_file_type,
    name: file.name,
    knowledge_file_id: file.id,
  };
}

export function workspaceFilesToFileDescriptors(
  files: WorkspaceFile[]
): FileDescriptor[] {
  return files.map(workspacesFileToFileDescriptor);
}
