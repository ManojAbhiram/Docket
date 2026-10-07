import { useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";

import { SignUpView } from "@/features/auth/components/SignUpView";
import { homeFor, useRegister } from "@/features/auth/hooks";
import { registerOutcome } from "@/features/auth/notices";
import type { RegisterInput } from "@/features/auth/schemas";

/** The sign-up screen with its behaviour: send the form, go to the role's start, say what failed. */
export function SignUpPage() {
  const register = useRegister();
  const navigate = useNavigate();
  const [outcome, setOutcome] = useState<ReturnType<typeof registerOutcome> | null>(null);
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

  function submit(input: RegisterInput) {
    setOutcome(null);
    register.mutate(input, {
      onSuccess: (user) => {
        void navigate({ to: homeFor(user.role) });
      },
      onError: (error) => {
        const failed = registerOutcome(error);
        setOutcome(failed);
        setWait(failed.blockedFor ?? 0);
      },
    });
  }

  const notice = outcome?.notice;
  return (
    <SignUpView
      busy={register.isPending}
      blocked={wait > 0}
      onSubmit={submit}
      {...(notice && { notice })}
    />
  );
}
