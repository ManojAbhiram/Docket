/** Why Vision was asked for and not used, in words. The code itself never reaches the screen. */
export const FALLBACK_WORDS: Record<string, string> = {
  vision_cap_reached: "Vision's daily limit was reached, so this page was read on this machine.",
  vision_timeout: "Vision took too long, so this page was read on this machine.",
  vision_rate_limited:
    "Vision is busy right now (free-tier limit), so this page was read on this machine.",
  vision_upstream_error: "Vision's provider had a problem, so this page was read on this machine.",
  vision_bad_answer:
    "Vision gave an answer that could not be used, so this page was read on this machine.",
  vision_error: "Vision could not read the page, so it was read on this machine.",
  vision_unavailable: "Vision is not set up, so this page was read on this machine.",
};
