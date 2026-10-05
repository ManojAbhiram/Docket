import { FileDrop } from "@/components/FileDrop";
import { NoticeBox, type NoticeSpec } from "@/components/Notice";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export interface RefusedRow {
  row: number;
  column: string | null;
  reason: keyof typeof REASONS;
}

export interface ImportResult {
  read: number;
  created: number;
  refused: RefusedRow[];
}

/** The server's reason codes in words. A value is never shown: the applicants are minors. */
const REASONS = {
  missing_value: "Missing value",
  bad_date: "Unreadable date",
  out_of_range: "Date out of range",
  bad_marks: "Marks not readable",
  duplicate_application_ref: "Application id already imported",
  too_long: "Value too long",
  malformed_row: "Wrong number of columns",
} as const;

interface ImportViewProps {
  fileName?: string;
  busy?: boolean;
  offline?: boolean;
  notice?: NoticeSpec;
  result?: ImportResult;
}

/** S-03: load applications from a CSV and say which rows were refused and why. */
export function ImportView({
  fileName,
  busy = false,
  offline = false,
  notice,
  result,
}: ImportViewProps) {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Import applications"
        description="A CSV with application_id, name, father_name, date_of_birth, board, roll_number, marks_by_subject and category."
      />
      {notice && <NoticeBox spec={notice} />}
      {busy && fileName && (
        <p role="status" aria-live="polite">
          Importing {fileName}
        </p>
      )}
      <FileDrop
        id="import-file"
        label="Choose a CSV file"
        hint="One .csv file in UTF-8. Rows already imported are skipped."
        accept=".csv,text/csv"
        disabled={busy || offline}
      />
      <Button size="lg" className="min-h-12" disabled={busy || offline || !fileName}>
        {busy ? "Importing" : "Import applications"}
      </Button>
      {offline && (
        <p role="status" className="text-muted-foreground">
          You are offline. Connect to import.
        </p>
      )}
      {result && <ImportOutcome result={result} />}
    </div>
  );
}

function ImportOutcome({ result }: { result: ImportResult }) {
  const refused = result.refused.length;
  return (
    <section aria-labelledby="import-result" className="space-y-4">
      <h2 id="import-result" className="text-xl" tabIndex={-1}>
        Imported {result.created} of {result.read} rows.
      </h2>
      {refused > 0 && (
        <>
          <p>
            {refused} {refused === 1 ? "row was" : "rows were"} refused. Fix{" "}
            {refused === 1 ? "it" : "them"} in the file and import it again. Rows already created
            are skipped.
          </p>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead scope="col">Row</TableHead>
                <TableHead scope="col">Column</TableHead>
                <TableHead scope="col">Reason</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {result.refused.map((item) => (
                <TableRow key={`${String(item.row)}-${item.reason}`}>
                  <TableCell data-numeric>{item.row}</TableCell>
                  <TableCell className="font-mono">{item.column ?? "whole row"}</TableCell>
                  <TableCell>{REASONS[item.reason]}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </>
      )}
      <Button variant="outline" className="min-h-11 sm:min-h-9">
        View applications
      </Button>
    </section>
  );
}
