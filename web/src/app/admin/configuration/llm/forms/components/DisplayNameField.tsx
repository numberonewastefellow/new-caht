import { TextFormField } from "@/components/Field";

interface DisplayNameFieldProps {
  disabled?: boolean;
}

export function DisplayNameField({ disabled = false }: DisplayNameFieldProps) {
  return (
    <TextFormField
      name="name"
      label="Display Name"
      subtext="How this provider appears to your team across the app."
      placeholder="e.g. Production OpenAI"
      disabled={disabled}
    />
  );
}
