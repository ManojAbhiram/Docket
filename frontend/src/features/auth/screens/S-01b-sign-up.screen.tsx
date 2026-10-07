import type { ScreenModule } from "@/design/screen";
import { SignUpView } from "@/features/auth/components/SignUpView";

export const screen: ScreenModule["screen"] = {
  id: "S-01b",
  name: "Sign up",
  feature: "auth",
  job: "Lets a new staff member or verifier create their own account and start working.",
  states: {
    loading: () => <SignUpView busy />,
    empty: () => <SignUpView />,
    "error: conflict": () => (
      <SignUpView
        notice={{
          title: "That username is taken.",
          body: "Choose another, or sign in if this was you.",
        }}
      />
    ),
    "error: rate_limited": () => (
      <SignUpView
        blocked
        notice={{ title: "Too many attempts.", body: "Try again in 42 seconds." }}
      />
    ),
    "error: unavailable": () => (
      <SignUpView
        notice={{ title: "Docket cannot reach its server.", body: "Try again in a minute." }}
      />
    ),
  },
};
