import numpy as np


def column_breakdown(
    row_array,
    col_array,
    entry_array,
    col_amount,
    col_headers,
    col_to_row,
):
    """Return table with distributed values.

    Args:
        row_array: Labels for table rows.
        col_array: Labels for table columns.
        entry_array: Records containing values.
        col_amount: Index of value in ``entry_array`` record.
        col_headers: Index of column label in ``entry_array`` record.
        col_to_row: Index of row label in ``entry_array`` record.

    Returns:
        ``numpy.ndarray`` with filled values or ``None`` when any array is empty.
    """

    entry_array = np.array(entry_array)
    col_array = np.array(col_array)
    row_array = np.array(row_array)

    if (
        entry_array.size == 0
        or col_array.size == 0
        or row_array.size == 0
    ):
        return None

    result = row_array.astype(object).reshape(-1, 1)
    zeros = np.zeros((row_array.size, col_array.size), dtype=object)
    result = np.hstack([result, zeros])

    for record in entry_array:
        col_index = np.where(record[col_headers] == col_array)[0][0]
        row_index = np.where(record[col_to_row] == result[:, 0])[0][0]
        result[row_index, col_index + 1] = record[col_amount]

    return result