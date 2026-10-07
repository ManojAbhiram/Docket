import { Link } from "@tanstack/react-router";

import { NoticeBox, type NoticeSpec } from "@/components/Notice";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { roleSchema, type RegisterInput } from "@/features/auth/schemas";

interface SignUpViewProps {
  busy?: boolean;
  /** The server asked for a wait, or the network is down: the button stays off. */
  blocked?: boolean;
  notice?: NoticeSpec;
  /** Called with what was typed. The design gallery passes nothing and the form stays inert. */
  onSubmit?: (input: RegisterInput) => void;
}

const ROLES = [
  {
    value: "staff",
    label: "Staff: import applications, upload documents, export the verified list",
  },
  { value: "verifier", label: "Verifier: review flagged applications and decide" },
] as const;

/** S-01b: create an account with a name, username, password and a role. */
export function SignUpView({ busy = false, blocked = false, notice, onSubmit }: SignUpViewProps) {
  return (
    <div className="mx-auto w-full max-w-sm space-y-6 py-8">
      <h1 className="text-[25px]">Create your Docket account</h1>
      {notice && <NoticeBox spec={notice} />}
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          const displayName = form.get("display_name");
          const username = form.get("username");
          const password = form.get("password");
          const role = roleSchema.safeParse(form.get("role"));
          if (
            typeof displayName === "string" &&
            typeof username === "string" &&
            typeof password === "string" &&
            role.success
          ) {
            onSubmit?.({
              display_name: displayName.trim(),
              username: username.trim(),
              password,
              role: role.data,
            });
          }
        }}
      >
        <div className="space-y-2">
          <Label htmlFor="display_name">Your name</Label>
          <Input
            id="display_name"
            name="display_name"
            autoComplete="name"
            required
            disabled={busy}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="username">Username</Label>
          <Input id="username" name="username" autoComplete="username" required disabled={busy} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            name="password"
            type="password"
            autoComplete="new-password"
            aria-describedby="password-hint"
            required
            disabled={busy}
          />
          <p id="password-hint" className="text-sm text-muted-foreground">
            At least 10 characters
          </p>
        </div>
        <div className="space-y-2">
          <Label id="role-label">Role</Label>
          <RadioGroup name="role" required disabled={busy} aria-labelledby="role-label">
            {ROLES.map((role) => (
              <div key={role.value} className="flex items-start gap-3">
                <RadioGroupItem value={role.value} id={`role-${role.value}`} className="mt-1" />
                <Label htmlFor={`role-${role.value}`} className="leading-snug font-normal">
                  {role.label}
                </Label>
              </div>
            ))}
          </RadioGroup>
        </div>
        <Button type="submit" size="lg" className="min-h-12 w-full" disabled={busy || blocked}>
          {busy ? "Creating" : "Create account"}
        </Button>
      </form>
      <p className="text-sm">
        Already have an account?{" "}
        <Link to="/sign-in" className="underline underline-offset-4">
          Sign in
        </Link>
      </p>
    </div>
  );
}
