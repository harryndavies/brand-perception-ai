interface FormErrorProps {
  error: { message?: string } | undefined;
}

export function FormError({ error }: FormErrorProps) {
  if (!error?.message) return null;
  return <p className="text-sm text-destructive">{error.message}</p>;
}
