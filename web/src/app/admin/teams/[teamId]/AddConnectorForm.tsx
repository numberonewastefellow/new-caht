import Button from "@/refresh-components/buttons/Button";
import Modal from "@/refresh-components/Modal";
import { useState } from "react";
import { updateTeam } from "./lib";
import { toast } from "@/hooks/useToast";
import { ConnectorStatus, Team } from "@/lib/types";
import { ConnectorMultiSelect } from "@/components/ConnectorMultiSelect";
import { SvgPlus } from "@opal/icons";
export interface AddConnectorFormProps {
  ccPairs: ConnectorStatus<any, any>[];
  team: Team;
  onClose: () => void;
}

export default function AddConnectorForm({
  ccPairs,
  team,
  onClose,
}: AddConnectorFormProps) {
  const [selectedCCPairIds, setSelectedCCPairIds] = useState<number[]>([]);

  // Filter out ccPairs that are already in the user group and are not private
  const availableCCPairs = ccPairs
    .filter(
      (ccPair) =>
        !team.cc_pairs
          .map((teamCCPair) => teamCCPair.id)
          .includes(ccPair.cc_pair_id)
    )
    .filter((ccPair) => ccPair.access_type === "private");

  return (
    <Modal open onOpenChange={onClose}>
      <Modal.Content width="sm" height="sm">
        <Modal.Header
          icon={SvgPlus}
          title="Add New Connector"
          onClose={onClose}
        />
        <Modal.Body>
          <ConnectorMultiSelect
            name="connectors"
            label="Select Connectors"
            connectors={availableCCPairs}
            selectedIds={selectedCCPairIds}
            onChange={setSelectedCCPairIds}
            placeholder="Search for connectors to add..."
            showError={false}
          />

          <Button
            onClick={async () => {
              const newCCPairIds = [
                ...Array.from(
                  new Set(
                    team.cc_pairs
                      .map((ccPair) => ccPair.id)
                      .concat(selectedCCPairIds)
                  )
                ),
              ];
              const response = await updateTeam(team.id, {
                user_ids: team.users.map((user) => user.id),
                cc_pair_ids: newCCPairIds,
              });
              if (response.ok) {
                toast.success("Successfully added connectors to team");
                onClose();
              } else {
                const responseJson = await response.json();
                const errorMsg = responseJson.detail || responseJson.message;
                toast.error(`Failed to add connectors to team - ${errorMsg}`);
                onClose();
              }
            }}
          >
            Add Connectors
          </Button>
        </Modal.Body>
      </Modal.Content>
    </Modal>
  );
}
