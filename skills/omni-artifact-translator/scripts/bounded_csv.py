"""Original stdlib CSV iterator with allocation budgets; no format inference.

The caller owns byte, profile and typed-cell validation. CSV quoting, escaping,
CR/LF and multiline fields remain the standard library's responsibility. The
logical-record character cap bounds even a single oversized row before its
field list can grow with the entire file. No process-global CSV limits change.
"""
import csv
import io

MAX_ROWS = 100000
MAX_COLUMNS = 512
MAX_CELLS = 1000000
MAX_RECORD_CHARS = 1000000


def need(condition, prefix, code):
    if not condition:
        raise ValueError(prefix + "." + code)


class _RecordLines:
    """Limit physical lines cumulatively until csv.reader completes one row."""
    def __init__(self, stream, prefix):
        self.stream, self.prefix, self.used = stream, prefix, 0

    def __iter__(self):
        return self

    def __next__(self):
        line = self.stream.readline(MAX_RECORD_CHARS - self.used + 1)
        if not line:
            raise StopIteration
        self.used += len(line)
        need(self.used <= MAX_RECORD_CHARS, self.prefix, "csv_record_limit")
        return line


def rows(raw, headers, prefix, *, ragged_code="ragged_rows"):
    """Yield data rows only, rejecting before any later record is consumed.

    Budgets include 100,000 data rows, 512 columns and 1,000,000 data cells.
    A logical record includes delimiters, quoting and line endings in its
    1,000,000-character budget. Headers count toward the column/record budgets.
    """
    need(type(headers) is list and bool(headers), prefix, "csv_headers_mismatch")
    need(len(headers) <= MAX_COLUMNS, prefix, "csv_column_limit")
    try:
        with io.StringIO(raw.decode("utf-8-sig"), newline="") as stream:
            source = _RecordLines(stream, prefix)
            reader = csv.reader(source, strict=True)
            header = next(reader, None)
            need(header is not None, prefix, "csv_headers_mismatch")
            need(len(header) <= MAX_COLUMNS, prefix, "csv_column_limit")
            need(header == headers, prefix, "csv_headers_mismatch")
            count = cells = 0
            while True:
                source.used = 0
                row = next(reader, None)
                if row is None:
                    break
                count += 1
                need(count <= MAX_ROWS, prefix, "result_row_limit")
                need(len(row) <= MAX_COLUMNS, prefix, "csv_column_limit")
                need(len(row) == len(headers), prefix, ragged_code)
                cells += len(row)
                need(cells <= MAX_CELLS, prefix, "csv_cell_limit")
                yield row
    except (UnicodeError, csv.Error):
        raise ValueError(prefix + ".invalid_csv") from None
