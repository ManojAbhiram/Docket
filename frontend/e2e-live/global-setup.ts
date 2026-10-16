import { registerAccount } from "./support/accounts";
import { ensureSeedPngs } from "./support/fixtures";
import { PASSWORD, setAccounts, type LiveAccounts } from "./support/stack";

// Runs once, after both servers are healthy: build the synthetic page images and create the
// two accounts every journey signs in with. The database is fresh for each `make
// test-e2e-live`, so no clean-up is needed; the volume is dropped afterwards.
export default async function globalSetup(): Promise<void> {
  await ensureSeedPngs();

  const run = Date.now().toString(36);
  const accounts: LiveAccounts = {
    staff: { username: `e2e.staff.${run}`, displayName: "E2E Staff", password: PASSWORD },
    verifier: { username: `e2e.verifier.${run}`, displayName: "E2E Verifier", password: PASSWORD },
  };
  await registerAccount("staff", accounts.staff);
  await registerAccount("verifier", accounts.verifier);
  setAccounts(accounts);
}
