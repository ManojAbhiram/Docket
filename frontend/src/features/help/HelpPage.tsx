import type { ReactNode } from "react";

import { CaseFileArt } from "@/components/art/CaseFileArt";
import { MarksheetScanArt } from "@/components/art/MarksheetScanArt";
import { VerifiedStampArt } from "@/components/art/VerifiedStampArt";
import { Kbd } from "@/components/Kbd";
import { PageHeader } from "@/components/PageHeader";

const PARTS = [
  { id: "getting-started", title: "Getting started" },
  { id: "staff", title: "Guide for staff" },
  { id: "verifiers", title: "Guide for verifiers" },
  { id: "statuses", title: "What the statuses mean" },
  { id: "questions", title: "Questions people ask" },
] as const;

function Part({
  id,
  children,
  art,
}: {
  id: (typeof PARTS)[number]["id"];
  children: ReactNode;
  art?: ReactNode;
}) {
  const title = PARTS.find((part) => part.id === id)?.title;
  return (
    <section aria-labelledby={id} className="grid gap-6 md:grid-cols-[1fr_12rem] md:items-start">
      <div className="space-y-4">
        <h2 id={id} className="scroll-mt-6 text-xl font-semibold">
          {title}
        </h2>
        {children}
      </div>
      {art && <div className="hidden md:block">{art}</div>}
    </section>
  );
}

function Steps({ children }: { children: ReactNode }) {
  return <ol className="list-decimal space-y-3 pl-5 marker:font-semibold">{children}</ol>;
}

function Step({ title, children }: { title: string; children: ReactNode }) {
  return (
    <li className="pl-1">
      <span className="font-semibold">{title}.</span> {children}
    </li>
  );
}

const QUESTIONS: { q: string; a: string }[] = [
  {
    q: "What files can I upload?",
    a: "JPG, PNG or PDF, up to 8 MiB each. A PDF is read from its first page.",
  },
  {
    q: "Why does a correct document say Needs review?",
    a: "Reading a scan is not perfect. A blurry, rotated or dark page can make Docket read one letter or number differently, and then a person is asked to look. A clearer scan helps, or a verifier can correct the value.",
  },
  {
    q: "Why did the status not change straight after I uploaded?",
    a: "Each page takes a few seconds to read. Keep the page open and in front: the screens refresh by themselves once the reading is done.",
  },
  {
    q: "Where does my data go?",
    a: "Pages are read on the server's own machine by default. Reading with Vision sends the page image to OpenRouter, only when it is chosen for an upload, and the screen says so before you send.",
  },
  {
    q: "Can I use real student documents?",
    a: "No. Docket is for synthetic data only, and every page says so.",
  },
];

/** The Help Center: how to use Docket, by role, with the statuses explained. Open to every signed-in role. */
export function HelpPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Help Center"
        description="How to use Docket, step by step, for staff and verifiers."
      />
      <div className="grid gap-10 lg:grid-cols-[1fr_14rem]">
        <div className="space-y-12">
          <Part id="getting-started" art={<CaseFileArt />}>
            <p className="max-w-[65ch]">
              Docket checks admission applications against the documents that support them. Staff
              add the applications and upload each applicant&apos;s marksheets and ID proof. Docket
              reads every page, compares what it found with the application, and gives the
              application one of three statuses. Verifiers look at anything the machine could not
              settle.
            </p>
          </Part>

          <Part id="staff" art={<MarksheetScanArt />}>
            <Steps>
              <Step title="Import the applications">
                Open Import applications and choose a CSV file with the columns application_id,
                name, father_name, date_of_birth, board, roll_number, marks_by_subject and category.
                Rows that were imported before are skipped, and a row with a problem is listed with
                the reason.
              </Step>
              <Step title="Add the documents">
                In Applications, press Add documents on the row. Choose the files; each one shows
                that it is being read, then what it was recognised as.
              </Step>
              <Step title="See what is still needed">
                An application page lists &quot;Still needed&quot; until a 10th marksheet, a 12th
                marksheet and an ID proof are all read. A transfer certificate is kept but does not
                count towards that.
              </Step>
              <Step title="Export the verified list">
                Open Export verified list to download a CSV of the applications that are Verified.
              </Step>
            </Steps>
          </Part>

          <Part id="verifiers" art={<VerifiedStampArt />}>
            <Steps>
              <Step title="Open the Review queue">
                It lists the applications that need a person, the most recently changed first.
              </Step>
              <Step title="Compare each value">
                Every field shows the application&apos;s value, the value read from the document,
                and a crop of the page beside them. Fields that need a look are outlined with
                dashes. Press <Kbd>j</Kbd> and <Kbd>k</Kbd> to move between fields, <Kbd>d</Kbd> to
                decide and <Kbd>?</Kbd> for the shortcuts.
              </Step>
              <Step title="Judge a page Docket could not read">
                A document that was not recognised, or could not be read, shows its page so you can
                see it for yourself.
              </Step>
              <Step title="Decide">
                Approve when the document is right, Correct to change a value that was read wrongly,
                or Reject and give the reason. The decision is recorded with your name.
              </Step>
            </Steps>
          </Part>

          <Part id="statuses">
            <dl className="space-y-4">
              <div>
                <dt className="font-semibold">Verified</dt>
                <dd className="max-w-[65ch] text-muted-foreground">
                  Every required document is read and every value matches the application, or a
                  verifier approved it.
                </dd>
              </div>
              <div>
                <dt className="font-semibold">Needs review</dt>
                <dd className="max-w-[65ch] text-muted-foreground">
                  A value does not match or was read with low confidence, or a document could not be
                  read or was not recognised. A verifier must look. This takes priority over Missing
                  documents.
                </dd>
              </div>
              <div>
                <dt className="font-semibold">Missing documents</dt>
                <dd className="max-w-[65ch] text-muted-foreground">
                  The application does not yet have a read 10th marksheet, a 12th marksheet and an
                  ID proof. The page names the ones still needed.
                </dd>
              </div>
            </dl>
          </Part>

          <Part id="questions">
            <div className="divide-y divide-border rounded-lg border border-border bg-card">
              {QUESTIONS.map((item) => (
                <details key={item.q} className="group px-4 py-3">
                  <summary className="min-h-11 cursor-pointer font-semibold marker:text-primary">
                    {item.q}
                  </summary>
                  <p className="max-w-[65ch] pt-1 pb-2 text-muted-foreground">{item.a}</p>
                </details>
              ))}
            </div>
          </Part>
        </div>
        <nav aria-label="On this page" className="hidden lg:block">
          <ul className="sticky top-6 space-y-1 border-l border-border pl-4 text-sm">
            {PARTS.map((part) => (
              <li key={part.id}>
                <a
                  href={`#${part.id}`}
                  className="inline-flex min-h-8 items-center text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
                >
                  {part.title}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </div>
  );
}
