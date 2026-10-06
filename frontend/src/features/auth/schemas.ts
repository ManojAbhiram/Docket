import { z } from "zod";

export const roleSchema = z.enum(["staff", "verifier"]);
export type Role = z.infer<typeof roleSchema>;

/** Who is signed in. The API sends no username, no hash and no session version. */
export const userSchema = z.object({
  id: z.string(),
  display_name: z.string(),
  role: roleSchema,
});
export type User = z.infer<typeof userSchema>;

export interface Credentials {
  username: string;
  password: string;
}
