import { zodResolver } from "@hookform/resolvers/zod";
import * as React from "react";
import { useForm } from "react-hook-form";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { z } from "zod";

import { ErrorState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { signup } from "@/features/auth/api";
import { AuthLayout } from "@/features/auth/AuthLayout";
import { useAuth } from "@/features/auth/auth-context";
import { errorMessage } from "@/lib/api";

// Mirrors backend/app/schemas/auth.py: password is 8-128 chars, name is required.
const schema = z.object({
  full_name: z.string().min(1, "Your name is required").max(100, "Keep it under 100 characters"),
  email: z.string().min(1, "Email is required").email("Enter a valid email address"),
  password: z
    .string()
    .min(8, "Use at least 8 characters")
    .max(128, "Keep it under 128 characters"),
});

type SignupValues = z.infer<typeof schema>;

export function SignupPage() {
  const { user, signIn } = useAuth();
  const navigate = useNavigate();
  const [formError, setFormError] = React.useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignupValues>({
    resolver: zodResolver(schema),
    defaultValues: { full_name: "", email: "", password: "" },
  });

  if (user) return <Navigate to="/" replace />;

  const onSubmit = async (values: SignupValues) => {
    setFormError(null);
    try {
      // Signup returns a token as well as the user, so this logs straight in.
      signIn(await signup(values));
      navigate("/", { replace: true });
    } catch (error) {
      setFormError(errorMessage(error, "Could not create the account."));
    }
  };

  return (
    <AuthLayout>
      <div className="space-y-6">
        <div className="space-y-1">
          <h2 className="text-xl font-semibold tracking-tight">Create your account</h2>
          <p className="text-sm text-muted-foreground">
            Start with an empty ledger, or import a statement once you are in.
          </p>
        </div>

        {formError ? <ErrorState message={formError} /> : null}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div className="space-y-1.5">
            <Label htmlFor="full_name">Full name</Label>
            <Input
              id="full_name"
              autoComplete="name"
              placeholder="Alex Morgan"
              aria-invalid={Boolean(errors.full_name)}
              {...register("full_name")}
            />
            {errors.full_name ? (
              <p className="text-xs text-critical">{errors.full_name.message}</p>
            ) : null}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              aria-invalid={Boolean(errors.email)}
              {...register("email")}
            />
            {errors.email ? <p className="text-xs text-critical">{errors.email.message}</p> : null}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              aria-invalid={Boolean(errors.password)}
              {...register("password")}
            />
            {errors.password ? (
              <p className="text-xs text-critical">{errors.password.message}</p>
            ) : (
              <p className="text-xs text-muted-foreground">At least 8 characters.</p>
            )}
          </div>

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Creating account…" : "Create account"}
          </Button>
        </form>

        <p className="border-t border-border pt-4 text-sm text-muted-foreground">
          Already registered?{" "}
          <Link to="/login" className="font-medium text-foreground underline-offset-4 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </AuthLayout>
  );
}
