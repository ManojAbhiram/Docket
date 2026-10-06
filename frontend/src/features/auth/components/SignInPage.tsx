import { useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";

import type { NoticeSpec } from "@/components/Notice";
import { SignInView } from "@/features/auth/components/SignInView";
import { homeFor, useLogin } from "@/features/auth/hooks";
import { signInOutcome } from "@/features/auth/notices";
import type { Credentials } from "@/features/auth/schemas";

const ENDED: NoticeSpec = {
  tone: "info",
  title: "You were signed out.",
  body: "Sign in to continue.",
};

/** The sign-in screen with its behaviour: send the form, go to the role's start, say what failed. */
export function SignInPage({ ended = false }: { ended?: boolean }) {
  const login = useLogin();
  const navigate = useNavigate();
  const [outcome, setOutcome] = useState<ReturnType<typeof signInOutcome> | null>(null);
  const [wait, setWait] = useState(0);

  useEffect(() => {
    if (wait <= 0) {
      return;
    }
    const timer = setTimeout(() => {
      setWait((seconds) => seconds - 1);
    }, 1000);
    return () => {
      clearTimeout(timer);
    };
  }, [wait]);

  function submit(credentials: Credentials) {
    setOutcome(null);
    login.mutate(credentials, {
      onSuccess: (user) => {
        void navigate({ to: homeFor(user.role) });
      },
      onError: (error) => {
        const failed = signInOutcome(error);
        setOutcome(failed);
        setWait(failed.blockedFor ?? 0);
      },
    });
  }

  const notice = outcome?.notice ?? (ended ? ENDED : undefined);
  return (
    <SignInView
      busy={login.isPending}
      blocked={wait > 0}
      onSubmit={submit}
      {...(notice && { notice })}
    />
  );
}
