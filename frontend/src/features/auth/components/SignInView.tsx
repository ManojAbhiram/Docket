import { NoticeBox, type NoticeSpec } from "@/components/Notice";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface SignInViewProps {
  busy?: boolean;
  /** The server asked for a wait, or the network is down: the button stays off. */
  blocked?: boolean;
  notice?: NoticeSpec;
}

/** S-01: sign in with a username and password. A wrong password never says which half was wrong. */
export function SignInView({ busy = false, blocked = false, notice }: SignInViewProps) {
  return (
    <div className="mx-auto w-full max-w-sm space-y-6 py-8">
      <h1 className="text-[25px]">Sign in to Docket</h1>
      {notice && <NoticeBox spec={notice} />}
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
        }}
      >
        <div className="space-y-2">
          <Label htmlFor="username">Username</Label>
          <Input id="username" name="username" autoComplete="username" disabled={busy} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            disabled={busy}
          />
        </div>
        <Button type="submit" size="lg" className="min-h-12 w-full" disabled={busy || blocked}>
          {busy ? "Signing in" : "Sign in"}
        </Button>
      </form>
    </div>
  );
}
