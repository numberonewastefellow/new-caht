"use client";

import { useState, useEffect } from "react";
import Button from "@/refresh-components/buttons/Button";
import { useProjectsContext } from "@/providers/ProjectsContext";
import { useKeyPress } from "@/hooks/useKeyPress";
import { useAppRouter } from "@/hooks/appNavigation";
import { useModal } from "@/refresh-components/contexts/ModalContext";
import { SvgFolderPlus, SvgSparkle } from "@opal/icons";
import Modal from "@/refresh-components/Modal";
import { toast } from "@/hooks/useToast";
import Text from "@/refresh-components/texts/Text";

interface CreateProjectModalProps {
  initialProjectName?: string;
}

export default function CreateProjectModal({
  initialProjectName,
}: CreateProjectModalProps) {
  const { createProject } = useProjectsContext();
  const modal = useModal();
  const route = useAppRouter();
  const [projectName, setProjectName] = useState(initialProjectName ?? "");

  // Reset when prop changes (modal reopens with different value)
  useEffect(() => {
    setProjectName(initialProjectName ?? "");
  }, [initialProjectName]);

  async function handleSubmit() {
    const name = projectName.trim();
    if (!name) return;

    try {
      const newProject = await createProject(name);
      route({ projectId: newProject.id });
      modal.toggle(false);
    } catch (e) {
      toast.error(`Failed to create the workspace ${name}`);
    }
  }

  useKeyPress(handleSubmit, "Enter");

  return (
    <Modal open={modal.isOpen} onOpenChange={modal.toggle}>
      <Modal.Content width="sm">
        {/* Clean header — title + close X inline (no icon, no description) */}
        <Modal.Header
          title="Create workspace"
          onClose={() => modal.toggle(false)}
        />

        <Modal.Body twoTone={false}>
          {/* Input with colorful project icon inline */}
          <div className="flex items-center gap-3 px-3 py-2.5 bg-background-tint-01 border border-border-01 rounded-12 focus-within:border-border-03 transition-colors">
            <span className="inline-flex items-center justify-center rounded-[5px] w-5 h-5 flex-shrink-0 bg-emerald-500">
              <SvgFolderPlus className="w-3 h-3 text-white" />
            </span>
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="Name your workspace"
              className="flex-1 bg-transparent outline-none text-text-05 placeholder:text-text-02 text-sm"
              autoFocus
            />
          </div>

          {/* Info card — subtle description */}
          <div className="flex items-start gap-2.5 px-3 py-2.5 bg-background-neutral-01 rounded-12">
            <SvgSparkle className="w-4 h-4 stroke-text-03 flex-shrink-0 mt-0.5" />
            <Text as="p" secondaryBody text03>
              Workspaces keep chats, files, and custom instructions in one
              place. Use them for ongoing work, or just to keep things tidy.
            </Text>
          </div>
        </Modal.Body>

        <Modal.Footer>
          <Button onClick={handleSubmit} disabled={!projectName.trim()}>
            Create workspace
          </Button>
        </Modal.Footer>
      </Modal.Content>
    </Modal>
  );
}
