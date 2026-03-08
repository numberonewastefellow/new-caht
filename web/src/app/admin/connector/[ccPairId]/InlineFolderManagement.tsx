"use client";

import { useState } from "react";
import Button from "@/refresh-components/buttons/Button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "@/hooks/useToast";
import Modal from "@/refresh-components/Modal";
import Text from "@/refresh-components/texts/Text";
import {
  SvgCheck,
  SvgEdit,
  SvgFolder,
  SvgPlusCircle,
  SvgX,
} from "@opal/icons";
import { Button as OpalButton } from "@opal/components";

interface ValidationResult {
  valid: boolean;
  error?: string;
  file_count?: number;
}

interface InlineFolderManagementProps {
  connectorId: number;
  ccPairId: number;
  currentPaths: string[];
  connectorSpecificConfig: Record<string, any>;
  onRefresh: () => void;
}

export default function InlineFolderManagement({
  connectorId,
  ccPairId,
  currentPaths,
  connectorSpecificConfig,
  onRefresh,
}: InlineFolderManagementProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [pathsToRemove, setPathsToRemove] = useState<Set<string>>(new Set());
  const [newPaths, setNewPaths] = useState<string[]>([]);
  const [newPathInput, setNewPathInput] = useState("");
  const [validationResults, setValidationResults] = useState<
    Record<string, ValidationResult>
  >({});
  const [isValidating, setIsValidating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showSaveConfirm, setShowSaveConfirm] = useState(false);

  const togglePathForRemoval = (path: string) => {
    setPathsToRemove((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(path)) {
        newSet.delete(path);
      } else {
        newSet.add(path);
      }
      return newSet;
    });
  };

  const handleValidateAndAdd = async () => {
    const trimmed = newPathInput.trim();
    if (!trimmed) return;

    // Check duplicates
    if (currentPaths.includes(trimmed) || newPaths.includes(trimmed)) {
      toast.error("This path is already in the list.");
      return;
    }

    setIsValidating(true);
    try {
      const res = await fetch(
        "/api/manage/admin/connector/folder/validate-paths",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ paths: [trimmed] }),
        }
      );

      if (!res.ok) {
        toast.error("Failed to validate path");
        return;
      }

      const data = await res.json();
      const result: ValidationResult = data.results[trimmed];

      setValidationResults((prev) => ({ ...prev, [trimmed]: result }));

      if (result.valid) {
        setNewPaths((prev) => [...prev, trimmed]);
        setNewPathInput("");
      } else {
        toast.error(result.error || "Invalid path");
      }
    } catch {
      toast.error("Failed to validate path");
    } finally {
      setIsValidating(false);
    }
  };

  const handleRemoveNewPath = (index: number) => {
    const removedPath = newPaths[index];
    setNewPaths((prev) => prev.filter((_, i) => i !== index));
    if (removedPath) {
      setValidationResults((prev) => {
        const next = { ...prev };
        delete next[removedPath];
        return next;
      });
    }
  };

  const handleSaveClick = () => {
    const remainingPaths = currentPaths.filter((p) => !pathsToRemove.has(p));
    const totalPaths = remainingPaths.length + newPaths.length;

    if (totalPaths === 0) {
      toast.error(
        "Cannot remove all folder paths. Delete the connector if this is desired."
      );
      return;
    }

    setShowSaveConfirm(true);
  };

  const handleConfirmSave = async () => {
    setShowSaveConfirm(false);
    setIsSaving(true);

    try {
      const remainingPaths = currentPaths.filter(
        (p) => !pathsToRemove.has(p)
      );
      const updatedPaths = [...remainingPaths, ...newPaths];
      const hasRemovals = pathsToRemove.size > 0;

      // PATCH connector with updated folder_paths
      const updatedConfig = {
        ...connectorSpecificConfig,
        folder_paths: updatedPaths,
      };

      const patchRes = await fetch(
        `/api/manage/admin/connector/${connectorId}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            connector_specific_config: updatedConfig,
          }),
        }
      );

      if (!patchRes.ok) {
        const errData = await patchRes.json().catch(() => null);
        throw new Error(
          errData?.detail || "Failed to update connector configuration"
        );
      }

      // If paths were removed, trigger a prune to clean up orphan docs
      if (hasRemovals) {
        const pruneRes = await fetch(
          `/api/manage/admin/cc-pair/${ccPairId}/prune`,
          { method: "POST" }
        );
        if (pruneRes.ok) {
          toast.success(
            "Folder paths updated. Pruning triggered to remove documents from deleted folders."
          );
        } else {
          toast.success(
            "Folder paths updated. Pruning will run on the next scheduled cycle."
          );
        }
      } else {
        toast.success(
          "Folder paths updated. New folders will be indexed on the next sync cycle."
        );
      }

      // Reset editing state
      setIsEditing(false);
      setPathsToRemove(new Set());
      setNewPaths([]);
      setNewPathInput("");
      setValidationResults({});
      onRefresh();
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to update folder paths"
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
    setPathsToRemove(new Set());
    setNewPaths([]);
    setNewPathInput("");
    setValidationResults({});
  };

  const remainingCount =
    currentPaths.filter((p) => !pathsToRemove.has(p)).length + newPaths.length;

  return (
    <>
      {/* Header with Edit/Save buttons */}
      <div className="flex justify-between items-center mb-4">
        <Text as="p" mainUiBody>
          Managed Folders ({remainingCount} path
          {remainingCount !== 1 ? "s" : ""})
        </Text>
        <div className="flex gap-2">
          {!isEditing ? (
            <Button
              onClick={() => setIsEditing(true)}
              secondary
              leftIcon={SvgEdit}
            >
              Edit
            </Button>
          ) : (
            <>
              <Button
                onClick={handleCancel}
                secondary
                leftIcon={SvgX}
                disabled={isSaving}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSaveClick}
                primary
                leftIcon={SvgCheck}
                disabled={
                  isSaving ||
                  (pathsToRemove.size === 0 && newPaths.length === 0)
                }
              >
                {isSaving ? "Saving..." : "Save Changes"}
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Path List */}
      {currentPaths.length === 0 && newPaths.length === 0 ? (
        <Text as="p" mainUiMuted className="text-center py-8">
          No folder paths configured
        </Text>
      ) : (
        <div className="border rounded-lg overflow-hidden mb-4">
          <div className="max-h-[400px] overflow-y-auto">
            <Table>
              <TableHeader className="sticky top-0 bg-background z-10">
                <TableRow>
                  <TableHead>Folder Path</TableHead>
                  <TableHead className="w-[100px]">Status</TableHead>
                  {isEditing && <TableHead className="w-12"></TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {/* Existing paths */}
                {currentPaths.map((path) => {
                  const isMarkedForRemoval = pathsToRemove.has(path);
                  return (
                    <TableRow
                      key={path}
                      className={
                        isMarkedForRemoval
                          ? "bg-red-100 dark:bg-red-900/20"
                          : ""
                      }
                    >
                      <TableCell className="font-mono text-sm">
                        <span
                          className={
                            isMarkedForRemoval
                              ? "line-through opacity-60"
                              : ""
                          }
                        >
                          {path}
                        </span>
                        {isMarkedForRemoval && (
                          <span className="ml-2 text-xs font-semibold text-red-600 dark:text-red-400">
                            Removing
                          </span>
                        )}
                      </TableCell>
                      <TableCell>
                        <span className="text-xs text-green-600 dark:text-green-400">
                          Active
                        </span>
                      </TableCell>
                      {isEditing && (
                        <TableCell>
                          <OpalButton
                            icon={SvgX}
                            variant={isMarkedForRemoval ? "default" : "danger"}
                            prominence="tertiary"
                            size="sm"
                            onClick={() => togglePathForRemoval(path)}
                            tooltip={
                              isMarkedForRemoval ? "Undo removal" : "Remove"
                            }
                            title={
                              isMarkedForRemoval ? "Undo removal" : "Remove"
                            }
                          />
                        </TableCell>
                      )}
                    </TableRow>
                  );
                })}

                {/* New paths to be added */}
                {newPaths.map((path, index) => (
                  <TableRow
                    key={`new-${index}`}
                    className="bg-green-50 dark:bg-green-900/10"
                  >
                    <TableCell className="font-mono text-sm">
                      {path}
                      {validationResults[path]?.file_count !== undefined && (
                        <span className="ml-2 text-xs text-text-subtle">
                          ({validationResults[path].file_count} files)
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      <span className="text-xs text-blue-600 dark:text-blue-400">
                        New
                      </span>
                    </TableCell>
                    {isEditing && (
                      <TableCell>
                        <OpalButton
                          icon={SvgX}
                          variant="danger"
                          prominence="tertiary"
                          size="sm"
                          onClick={() => handleRemoveNewPath(index)}
                          tooltip="Remove"
                          title="Remove"
                        />
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      )}

      {/* Add Path Input (only in edit mode) */}
      {isEditing && (
        <div className="mt-4 flex items-center gap-2">
          <input
            type="text"
            value={newPathInput}
            onChange={(e) => setNewPathInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleValidateAndAdd();
              }
            }}
            placeholder="Enter absolute folder path (e.g., /data/docs)"
            className="flex-1 px-3 py-2 border rounded-md text-sm font-mono
              bg-background text-text-default
              border-border focus:outline-none focus:ring-2 focus:ring-primary"
            disabled={isSaving || isValidating}
          />
          <Button
            onClick={handleValidateAndAdd}
            secondary
            leftIcon={SvgPlusCircle}
            disabled={isSaving || isValidating || !newPathInput.trim()}
          >
            {isValidating ? "Validating..." : "Add Path"}
          </Button>
        </div>
      )}

      {/* Warning about removal */}
      {isEditing && pathsToRemove.size > 0 && (
        <div className="mt-3 p-3 bg-yellow-50 dark:bg-yellow-900/10 rounded-md border border-yellow-200 dark:border-yellow-800">
          <Text
            as="p"
            secondaryBody
            className="text-yellow-800 dark:text-yellow-200"
          >
            Removing a folder will trigger a prune to delete its indexed
            documents from the search index.
          </Text>
        </div>
      )}

      {/* Confirmation Modal */}
      <Modal open={showSaveConfirm} onOpenChange={setShowSaveConfirm}>
        <Modal.Content width="sm">
          <Modal.Header
            icon={SvgFolder}
            title="Confirm Folder Changes"
            description="When you save these changes, the following will happen:"
          />

          <Modal.Body>
            {pathsToRemove.size > 0 && (
              <div className="p-3 bg-red-50 dark:bg-red-900/10 rounded-md">
                <Text
                  as="p"
                  mainUiBody
                  className="font-semibold text-red-800 dark:text-red-200"
                >
                  {pathsToRemove.size} folder path(s) will be removed
                </Text>
                <Text
                  as="p"
                  secondaryBody
                  className="text-red-700 dark:text-red-300 mt-1"
                >
                  Documents from these folders will be pruned from the search
                  index. This may take a few minutes.
                </Text>
              </div>
            )}

            {newPaths.length > 0 && (
              <div className="p-3 bg-green-50 dark:bg-green-900/10 rounded-md mt-2">
                <Text
                  as="p"
                  mainUiBody
                  className="font-semibold text-green-800 dark:text-green-200"
                >
                  {newPaths.length} folder path(s) will be added
                </Text>
                <Text
                  as="p"
                  secondaryBody
                  className="text-green-700 dark:text-green-300 mt-1"
                >
                  Files from new folders will be indexed on the next sync cycle.
                </Text>
              </div>
            )}
          </Modal.Body>

          <Modal.Footer>
            <Button
              onClick={() => setShowSaveConfirm(false)}
              secondary
              disabled={isSaving}
            >
              Cancel
            </Button>
            <Button onClick={handleConfirmSave} disabled={isSaving}>
              {isSaving ? "Saving..." : "Confirm & Save"}
            </Button>
          </Modal.Footer>
        </Modal.Content>
      </Modal>
    </>
  );
}
