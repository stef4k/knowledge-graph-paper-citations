"""Step 8: does a generated query return the same result as the gold query?"""

from itertools import permutations

FLOAT_DECIMALS = 4  # numbers are compared after rounding, so 1.29213483 == 1.2921348314606742


def canonical(value):
    """Make a value comparable: numbers rounded (so 2 == 2.0), booleans kept apart from 1/0."""
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, (int, float)):
        return round(float(value), FLOAT_DECIMALS)
    return value


def results_match(gold_rows: list[tuple], pred_rows: list[tuple]) -> bool:
    """True if the generated rows equal the gold rows, ignoring column order and variable names.

    Rows are compared as sets: row order and duplicate rows do not matter, so for a top-k
    question the top-k sets are compared (our top-k gold items have no tie at the cut-off).
    The generated result may have extra columns (e.g. an IRI next to a name): it matches if
    some choice of its columns, in some order, gives exactly the gold rows.
    """
    gold = {tuple(canonical(v) for v in row) for row in gold_rows}
    pred = [tuple(canonical(v) for v in row) for row in pred_rows]
    if not gold or not pred:
        return not gold and not pred
    n_gold_columns, n_pred_columns = len(next(iter(gold))), len(pred[0])
    for columns in permutations(range(n_pred_columns), n_gold_columns):
        if {tuple(row[i] for i in columns) for row in pred} == gold:
            return True
    return False
