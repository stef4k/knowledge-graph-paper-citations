from kgqa.compare import results_match


def test_ignores_column_order_and_variable_names():
    assert results_match([("ArXiv", 2018)], [(2018, "ArXiv")])


def test_ignores_row_order_and_duplicate_rows():
    gold = [("a", 3), ("b", 2), ("c", 1)]
    assert results_match(gold, [("c", 1), ("a", 3), ("b", 2), ("b", 2)])


def test_floats_match_within_tolerance():
    assert results_match([(1.2921348314606742,)], [(1.29213483,)])
    assert not results_match([(1.2921348314606742,)], [(1.3,)])


def test_integer_and_float_with_same_value_match():
    assert results_match([("Workshop", 2000, 0)], [("Workshop", 2000, 0.0)])


def test_booleans_do_not_equal_numbers():
    assert results_match([(True,)], [(True,)])
    assert not results_match([(True,)], [(1,)])


def test_extra_columns_in_the_generated_result_are_allowed():
    gold = [("Ashish Vaswani",), ("Niki Parmar",)]
    pred = [("http://sdm_upc.org/resource/1", "Ashish Vaswani"), ("http://sdm_upc.org/resource/2", "Niki Parmar")]
    assert results_match(gold, pred)


def test_missing_columns_do_not_match():
    assert not results_match([("D. Huson", 283)], [("D. Huson",)])


def test_missing_or_extra_rows_do_not_match():
    gold = [("a",), ("b",)]
    assert not results_match(gold, [("a",)])
    assert not results_match(gold, [("a",), ("b",), ("c",)])  # e.g. LIMIT 100 instead of top-2


def test_empty_results():
    assert results_match([], [])
    assert not results_match([("a",)], [])
    assert not results_match([], [("a",)])
