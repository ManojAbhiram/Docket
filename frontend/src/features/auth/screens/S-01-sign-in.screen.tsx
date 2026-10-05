import type { ScreenModule } from "@/design/screen";
import { SignInView } from "@/features/auth/components/SignInView";

export const screen: ScreenModule["screen"] = {
  id: "S-01",
  name: "Sign in",
  feature: "auth",
  job: "Gets a staff member or verifier into the product with their own account.",
  states: {
    loading: () => <SignInView busy />,
    empty: () => <SignInView />,
    "error: unauthorized": () => (
      <SignInView
        notice={{
          title: "That username and password do not match.",
          body: "Check them and try again.",
        }}
      />
    ),
    "error: rate_limited": () => (
      <SignInView
        blocked
        notice={{ title: "Too many attempts.", body: "Try again in 42 seconds." }}
      />
    ),
    "error: unavailable": () => (
      <SignInView
        notice={{
          title: "Docket cannot reach its database.",
          body: "Try again in a minute.",
        }}
      />
    ),
    success: () => (
      <SignInView
        notice={{
          tone: "info",
          title: "Signed in as Demo Verifier",
          body: "Opening the review queue.",
        }}
      />
    ),
    offline: () => (
      <SignInView
        blocked
        notice={{ tone: "info", title: "You are offline.", body: "Connect and try again." }}
      />
    ),
    "session ended": () => (
      <SignInView
        notice={{ tone: "info", title: "You were signed out.", body: "Sign in to continue." }}
      />
    ),
  },
};
