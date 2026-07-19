import { Form, Formik } from "formik";
import * as Yup from "yup";
import { toast } from "@/hooks/useToast";
import { ConnectorStatus, User, Team } from "@/lib/types";
import { TextFormField } from "@/components/Field";
import { createUserGroup } from "./lib";
import { UserEditor } from "./UserEditor";
import { ConnectorEditor } from "./ConnectorEditor";
import Modal from "@/refresh-components/Modal";
import Button from "@/refresh-components/buttons/Button";
import Separator from "@/refresh-components/Separator";
import Text from "@/refresh-components/texts/Text";
import { SvgUsers } from "@opal/icons";
export interface TeamCreationFormProps {
  onClose: () => void;
  users: User[];
  ccPairs: ConnectorStatus<any, any>[];
  existingUserGroup?: Team;
}

export default function TeamCreationForm({
  onClose,
  users,
  ccPairs,
  existingUserGroup,
}: TeamCreationFormProps) {
  const isUpdate = existingUserGroup !== undefined;

  // Filter out ccPairs that aren't access_type "private"
  const privateCcPairs = ccPairs.filter(
    (ccPair) => ccPair.access_type === "private"
  );

  return (
    <Modal open onOpenChange={onClose}>
      <Modal.Content>
        <Modal.Header
          icon={SvgUsers}
          title={isUpdate ? "Update a Team" : "Create a new Team"}
          onClose={onClose}
        />
        <Modal.Body>
          <Separator />

          <Formik
            initialValues={{
              name: existingUserGroup ? existingUserGroup.name : "",
              user_ids: [] as string[],
              cc_pair_ids: [] as number[],
            }}
            validationSchema={Yup.object().shape({
              name: Yup.string().required("Please enter a name for the team"),
              user_ids: Yup.array().of(Yup.string().required()),
              cc_pair_ids: Yup.array().of(Yup.number().required()),
            })}
            onSubmit={async (values, formikHelpers) => {
              formikHelpers.setSubmitting(true);
              let response;
              response = await createUserGroup(values);
              formikHelpers.setSubmitting(false);
              if (response.ok) {
                toast.success(
                  isUpdate
                    ? "Successfully updated team!"
                    : "Successfully created team!"
                );
                onClose();
              } else {
                const responseJson = await response.json();
                const errorMsg = responseJson.detail || responseJson.message;
                toast.error(
                  isUpdate
                    ? `Error updating team - ${errorMsg}`
                    : `Error creating team - ${errorMsg}`
                );
              }
            }}
          >
            {({ isSubmitting, values, setFieldValue }) => (
              <Form>
                <TextFormField
                  name="name"
                  label="Name:"
                  placeholder="A name for the Team"
                  disabled={isUpdate}
                />

                <Separator />

                <Text as="p" className="font-medium">
                  Select which private connectors this team has access to:
                </Text>
                <Text as="p" text02>
                  All documents indexed by the selected connectors will be
                  visible to users in this team.
                </Text>

                <ConnectorEditor
                  allCCPairs={privateCcPairs}
                  selectedCCPairIds={values.cc_pair_ids}
                  setSetCCPairIds={(ccPairsIds) =>
                    setFieldValue("cc_pair_ids", ccPairsIds)
                  }
                />

                <Separator />

                <Text as="p" className="font-medium">
                  Select which Users should be a part of this Team.
                </Text>
                <Text as="p" text02>
                  All selected users will be able to search through all
                  documents indexed by the selected connectors.
                </Text>
                <div className="mb-3 gap-2">
                  <UserEditor
                    selectedUserIds={values.user_ids}
                    setSelectedUserIds={(userIds) =>
                      setFieldValue("user_ids", userIds)
                    }
                    allUsers={users}
                    existingUsers={[]}
                  />
                </div>
                <div className="flex">
                  <Button
                    type="submit"
                    disabled={isSubmitting}
                    className="mx-auto w-64"
                  >
                    {isUpdate ? "Update!" : "Create!"}
                  </Button>
                </div>
              </Form>
            )}
          </Formik>
        </Modal.Body>
      </Modal.Content>
    </Modal>
  );
}
