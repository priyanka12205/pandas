import codecs
from datetime import datetime
from textwrap import dedent

import pytest

import pandas as pd
from pandas import (
    DataFrame,
    Series,
)
import pandas._testing as tm

from pandas.io.formats.format import DataFrameFormatter
from pandas.io.formats.latex import (
    RegularTableBuilder,
    RowBodyIterator,
    RowHeaderIterator,
    RowStringConverter,
)


def _dedent(string):
    """Dedent without new line in the beginning.

    Built-in textwrap.dedent would keep new line character in the beginning
    of multi-line string starting from the new line.
    This version drops the leading new line character.
    """
    return dedent(string).lstrip()


@pytest.fixture
def df_short():
    """Short dataframe for testing table/tabular/longtable LaTeX env."""
    return DataFrame({"a": [1, 2], "b": ["b1", "b2"]})


class TestToLatex:
    def test_to_latex_to_file(self, float_frame):
        with tm.ensure_clean("test.tex") as path:
            float_frame.to_latex(path)
            with open(path) as f:
                assert float_frame.to_latex() == f.read()

    def test_to_latex_to_file_utf8_with_encoding(self):
        # test with utf-8 and encoding option (GH 7061)
        df = DataFrame([["au\xdfgangen"]])
        with tm.ensure_clean("test.tex") as path:
            df.to_latex(path, encoding="utf-8")
            with codecs.open(path, "r", encoding="utf-8") as f:
                assert df.to_latex() == f.read()

    def test_to_latex_to_file_utf8_without_encoding(self):
        # test with utf-8 without encoding option
        df = DataFrame([["au\xdfgangen"]])
        with tm.ensure_clean("test.tex") as path:
            df.to_latex(path)
            with codecs.open(path, "r", encoding="utf-8") as f:
                assert df.to_latex() == f.read()

    def test_to_latex_tabular_with_index(self):
        df = DataFrame({"a": [1, 2], "b": ["b1", "b2"]})
        result = df.to_latex(hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{lrl}
            \toprule
            {} & {a} & {b} \\
            \midrule
            0 & 1 & b1 \\
            1 & 2 & b2 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_tabular_without_index(self):
        df = DataFrame({"a": [1, 2], "b": ["b1", "b2"]})
        result = df.to_latex(index=False, hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{rl}
            \toprule
            {a} & {b} \\
            \midrule
            1 & b1 \\
            2 & b2 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    @pytest.mark.parametrize(
        "bad_column_format",
        [5, 1.2, ["l", "r"], ("r", "c"), {"r", "c", "l"}, {"a": "r", "b": "l"}],
    )
    def test_to_latex_bad_column_format(self, bad_column_format):
        df = DataFrame({"a": [1, 2], "b": ["b1", "b2"]})
        msg = r"`column_format` must be a string"
        with pytest.raises(ValueError, match=msg):
            df.to_latex(column_format=bad_column_format)

    def test_to_latex_column_format_just_works(self, float_frame):
        # GH Bug #9402
        float_frame.to_latex(column_format="lcr")

    def test_to_latex_column_format(self):
        df = DataFrame({"a": [1, 2], "b": ["b1", "b2"]})
        result = df.to_latex(column_format="lcr", hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{lcr}
            \toprule
            {} & {a} & {b} \\
            \midrule
            0 & 1 & b1 \\
            1 & 2 & b2 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_float_format_object_col(self):
        # GH#40024
        ser = Series([1000.0, "test"])
        result = ser.to_latex(precision=0, thousands=",", hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{ll}
            \toprule
            {} & {0} \\
            \midrule
            0 & 1,000 \\
            1 & test \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_empty_tabular(self):
        df = DataFrame()
        result = df.to_latex(hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{l}
            \toprule
            \midrule
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_series(self):
        s = Series(["a", "b", "c"])
        result = s.to_latex(hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{ll}
            \toprule
            {} & {0} \\
            \midrule
            0 & a \\
            1 & b \\
            2 & c \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_midrule_location(self):
        # GH 18326
        df = DataFrame({"a": [1, 2]})
        df.index.name = "foo"
        result = df.to_latex(index_names=False, hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{lr}
            \toprule
            {} & {a} \\
            \midrule
            0 & 1 \\
            1 & 2 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected


class TestToLatexLongtable:
    def test_to_latex_empty_longtable(self):
        df = DataFrame()
        result = df.to_latex(environment="longtable")
        expected = _dedent(
            r"""
            \begin{longtable}{l}
            \endfirsthead
            \endhead
            \multicolumn{1}{r}{Continued on next page} \\
            \endfoot
            \endlastfoot
            \end{longtable}
            """
        )
        assert result == expected

    def test_to_latex_longtable_with_index(self):
        df = DataFrame({"a": [1, 2], "b": ["b1", "b2"]})
        result = df.to_latex(environment="longtable", hrules=True)
        expected = _dedent(
            r"""
            \begin{longtable}{lrl}
            \toprule
            {} & {a} & {b} \\
            \midrule
            \endfirsthead
            \toprule
            {} & {a} & {b} \\
            \midrule
            \endhead
            \midrule
            \multicolumn{3}{r}{Continued on next page} \\
            \midrule
            \endfoot
            \bottomrule
            \endlastfoot
            0 & 1 & b1 \\
            1 & 2 & b2 \\
            \end{longtable}
            """
        )
        assert result == expected

    def test_to_latex_longtable_without_index(self):
        df = DataFrame({"a": [1, 2], "b": ["b1", "b2"]})
        result = df.to_latex(index=False, environment="longtable", hrules=True)
        expected = _dedent(
            r"""
            \begin{longtable}{rl}
            \toprule
            {a} & {b} \\
            \midrule
            \endfirsthead
            \toprule
            {a} & {b} \\
            \midrule
            \endhead
            \midrule
            \multicolumn{2}{r}{Continued on next page} \\
            \midrule
            \endfoot
            \bottomrule
            \endlastfoot
            1 & b1 \\
            2 & b2 \\
            \end{longtable}
            """
        )
        assert result == expected

    @pytest.mark.parametrize(
        "df, expected_number",
        [
            (DataFrame({"a": [1, 2]}), 1),
            (DataFrame({"a": [1, 2], "b": [3, 4]}), 2),
            (DataFrame({"a": [1, 2], "b": [3, 4], "c": [5, 6]}), 3),
        ],
    )
    def test_to_latex_longtable_continued_on_next_page(self, df, expected_number):
        result = df.to_latex(index=False, environment="longtable")
        assert fr"\multicolumn{{{expected_number}}}" in result


class TestToLatexHeader:
    def test_to_latex_no_header_with_index(self):
        # GH 7124
        df = DataFrame({"a": [1, 2], "b": ["b1", "b2"]})
        result = df.to_latex(header=False, hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{lrl}
            \toprule
            \midrule
            0 & 1 & b1 \\
            1 & 2 & b2 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_no_header_without_index(self):
        # GH 7124
        df = DataFrame({"a": [1, 2], "b": ["b1", "b2"]})
        result = df.to_latex(index=False, header=False, hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{rl}
            \toprule
            \midrule
            1 & b1 \\
            2 & b2 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_specified_header_with_index(self):
        # GH 7124
        df = DataFrame({"a": [1, 2], "b": ["b1", "b2"]})
        result = df.to_latex(header=["AA", "BB"], hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{lrl}
            \toprule
            {} & {AA} & {BB} \\
            \midrule
            0 & 1 & b1 \\
            1 & 2 & b2 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_specified_header_without_index(self):
        # GH 7124
        df = DataFrame({"a": [1, 2], "b": ["b1", "b2"]})
        result = df.to_latex(header=["AA", "BB"], index=False, hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{rl}
            \toprule
            {AA} & {BB} \\
            \midrule
            1 & b1 \\
            2 & b2 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    @pytest.mark.parametrize(
        "header, num_aliases",
        [
            (["A"], 1),
            (("B",), 1),
            (("Col1", "Col2", "Col3"), 3),
            (("Col1", "Col2", "Col3", "Col4"), 4),
        ],
    )
    def test_to_latex_number_of_items_in_header_missmatch_raises(
        self,
        header,
        num_aliases,
    ):
        # GH 7124
        df = DataFrame({"a": [1, 2], "b": ["b1", "b2"]})
        msg = f"`header` gave {num_aliases} aliases for 2 columns."
        with pytest.raises(ValueError, match=msg):
            df.to_latex(header=header)

    def test_to_latex_decimal(self):
        # GH 12031
        df = DataFrame({"a": [1.0, 2.1], "b": ["b1", "b2"]})
        result = df.to_latex(decimal=",", precision=1, hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{lrl}
            \toprule
            {} & {a} & {b} \\
            \midrule
            0 & 1,0 & b1 \\
            1 & 2,1 & b2 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected


class TestToLatexBold:
    @pytest.mark.parametrize("bold_header", ["both", "none", "index", "columns"])
    def test_to_latex_bold_rows(self, bold_header):
        # GH 16707
        cols = (
            "{\\textbf{a}} & {\\textbf{b}}"
            if bold_header in ["both", "columns"]
            else "{a} & {b}"
        )
        idx1 = "\\textbf{0}" if bold_header in ["both", "index"] else "0"
        idx2 = "\\textbf{1}" if bold_header in ["both", "index"] else "1"
        df = DataFrame({"a": [1, 2], "b": ["b1", "b2"]})
        result = df.to_latex(bold_header=bold_header, hrules=True)
        expected = _dedent(
            f"""
            \\begin{{tabular}}{{lrl}}
            \\toprule
            {{}} & {cols} \\\\
            \\midrule
            {idx1} & 1 & b1 \\\\
            {idx2} & 2 & b2 \\\\
            \\bottomrule
            \\end{{tabular}}
            """
        )
        assert result == expected


class TestToLatexCaptionLabel:
    @pytest.fixture
    def caption_table(self):
        """Caption for table/tabular LaTeX environment."""
        return "a table in a \\texttt{table/tabular} environment"

    @pytest.fixture
    def short_caption(self):
        """Short caption for testing \\caption[short_caption]{full_caption}."""
        return "a table"

    @pytest.fixture
    def label_table(self):
        """Label for table/tabular LaTeX environment."""
        return "tab:table_tabular"

    @pytest.fixture
    def caption_longtable(self):
        """Caption for longtable LaTeX environment."""
        return "a table in a \\texttt{longtable} environment"

    @pytest.fixture
    def label_longtable(self):
        """Label for longtable LaTeX environment."""
        return "tab:longtable"

    def test_to_latex_caption_only(self, df_short, caption_table):
        # GH 25436
        result = df_short.to_latex(
            caption=caption_table, hrules=True, position_float="centering"
        )
        expected = _dedent(
            r"""
            \begin{table}
            \centering
            \caption{a table in a \texttt{table/tabular} environment}
            \begin{tabular}{lrl}
            \toprule
            {} & {a} & {b} \\
            \midrule
            0 & 1 & b1 \\
            1 & 2 & b2 \\
            \bottomrule
            \end{tabular}
            \end{table}
            """
        )
        assert result == expected

    def test_to_latex_label_only(self, df_short, label_table):
        # GH 25436
        result = df_short.to_latex(
            label=label_table, position_float="centering", hrules=True
        )
        expected = _dedent(
            r"""
            \begin{table}
            \centering
            \label{tab:table_tabular}
            \begin{tabular}{lrl}
            \toprule
            {} & {a} & {b} \\
            \midrule
            0 & 1 & b1 \\
            1 & 2 & b2 \\
            \bottomrule
            \end{tabular}
            \end{table}
            """
        )
        assert result == expected

    def test_to_latex_caption_and_label(self, df_short, caption_table, label_table):
        # GH 25436
        result = df_short.to_latex(
            caption=caption_table,
            label=label_table,
            hrules=True,
            position_float="centering",
        )
        expected = _dedent(
            r"""
            \begin{table}
            \centering
            \caption{a table in a \texttt{table/tabular} environment}
            \label{tab:table_tabular}
            \begin{tabular}{lrl}
            \toprule
            {} & {a} & {b} \\
            \midrule
            0 & 1 & b1 \\
            1 & 2 & b2 \\
            \bottomrule
            \end{tabular}
            \end{table}
            """
        )
        assert result == expected

    def test_to_latex_caption_and_shortcaption(
        self,
        df_short,
        caption_table,
        short_caption,
    ):
        result = df_short.to_latex(
            caption=(caption_table, short_caption),
            hrules=True,
            position_float="centering",
        )
        expected = _dedent(
            r"""
            \begin{table}
            \centering
            \caption[a table]{a table in a \texttt{table/tabular} environment}
            \begin{tabular}{lrl}
            \toprule
            {} & {a} & {b} \\
            \midrule
            0 & 1 & b1 \\
            1 & 2 & b2 \\
            \bottomrule
            \end{tabular}
            \end{table}
            """
        )
        assert result == expected

    def test_to_latex_caption_and_shortcaption_list_is_ok(self, df_short):
        caption = ("Long-long-caption", "Short")
        result_tuple = df_short.to_latex(caption=caption)
        result_list = df_short.to_latex(caption=list(caption))
        assert result_tuple == result_list

    def test_to_latex_caption_shortcaption_and_label(
        self,
        df_short,
        caption_table,
        short_caption,
        label_table,
    ):
        # test when the short_caption is provided alongside caption and label
        result = df_short.to_latex(
            caption=(caption_table, short_caption),
            label=label_table,
            hrules=True,
            position_float="centering",
        )
        expected = _dedent(
            r"""
            \begin{table}
            \centering
            \caption[a table]{a table in a \texttt{table/tabular} environment}
            \label{tab:table_tabular}
            \begin{tabular}{lrl}
            \toprule
            {} & {a} & {b} \\
            \midrule
            0 & 1 & b1 \\
            1 & 2 & b2 \\
            \bottomrule
            \end{tabular}
            \end{table}
            """
        )
        assert result == expected

    @pytest.mark.parametrize(
        "bad_caption",
        [
            ("full_caption", "short_caption", "extra_string"),
            ("full_caption", "short_caption", 1),
            ("full_caption", "short_caption", None),
            ("full_caption",),
            (None,),
        ],
    )
    def test_to_latex_bad_caption_raises(self, bad_caption):
        # test that wrong number of params is raised
        df = DataFrame({"a": [1]})
        msg = "`caption` must be either a string or 2-tuple of strings."
        with pytest.raises(ValueError, match=msg):
            df.to_latex(caption=bad_caption)

    def test_to_latex_two_chars_caption(self, df_short):
        # test that two chars caption is handled correctly
        # it must not be unpacked into long_caption, short_caption.
        result = df_short.to_latex(
            caption="xy", hrules=True, position_float="centering"
        )
        expected = _dedent(
            r"""
            \begin{table}
            \centering
            \caption{xy}
            \begin{tabular}{lrl}
            \toprule
            {} & {a} & {b} \\
            \midrule
            0 & 1 & b1 \\
            1 & 2 & b2 \\
            \bottomrule
            \end{tabular}
            \end{table}
            """
        )
        assert result == expected

    def test_to_latex_longtable_caption_only(self, df_short, caption_longtable):
        # GH 25436
        # test when no caption and no label is provided
        # is performed by test_to_latex_longtable()
        result = df_short.to_latex(
            environment="longtable", caption=caption_longtable, hrules=True
        )
        expected = _dedent(
            r"""
            \begin{longtable}{lrl}
            \caption{a table in a \texttt{longtable} environment} \\
            \toprule
            {} & {a} & {b} \\
            \midrule
            \endfirsthead
            \caption[]{a table in a \texttt{longtable} environment} \\
            \toprule
            {} & {a} & {b} \\
            \midrule
            \endhead
            \midrule
            \multicolumn{3}{r}{Continued on next page} \\
            \midrule
            \endfoot
            \bottomrule
            \endlastfoot
            0 & 1 & b1 \\
            1 & 2 & b2 \\
            \end{longtable}
            """
        )
        assert result == expected

    def test_to_latex_longtable_label_only(self, df_short, label_longtable):
        # GH 25436
        result = df_short.to_latex(
            environment="longtable", label=label_longtable, hrules=True
        )
        expected = _dedent(
            r"""
            \begin{longtable}{lrl}
            \label{tab:longtable}\\
            \toprule
            {} & {a} & {b} \\
            \midrule
            \endfirsthead
            \toprule
            {} & {a} & {b} \\
            \midrule
            \endhead
            \midrule
            \multicolumn{3}{r}{Continued on next page} \\
            \midrule
            \endfoot
            \bottomrule
            \endlastfoot
            0 & 1 & b1 \\
            1 & 2 & b2 \\
            \end{longtable}
            """
        )
        assert result == expected

    def test_to_latex_longtable_caption_and_label(
        self,
        df_short,
        caption_longtable,
        label_longtable,
    ):
        # GH 25436
        result = df_short.to_latex(
            longtable=True,
            caption=caption_longtable,
            label=label_longtable,
        )
        expected = _dedent(
            r"""
            \begin{longtable}{lrl}
            \caption{a table in a \texttt{longtable} environment}
            \label{tab:longtable}\\
            \toprule
            {} & {a} & {b} \\
            \midrule
            \endfirsthead
            \caption[]{a table in a \texttt{longtable} environment} \\
            \toprule
            {} & {a} & {b} \\
            \midrule
            \endhead
            \midrule
            \multicolumn{3}{r}{Continued on next page} \\
            \midrule
            \endfoot

            \bottomrule
            \endlastfoot
            0 & 1 & b1 \\
            1 & 2 & b2 \\
            \end{longtable}
            """
        )
        assert result == expected

    def test_to_latex_longtable_caption_shortcaption_and_label(
        self,
        df_short,
        caption_longtable,
        short_caption,
        label_longtable,
    ):
        # test when the caption, the short_caption and the label are provided
        result = df_short.to_latex(
            environment="longtable",
            caption=(caption_longtable, short_caption),
            label=label_longtable,
            hrules=True,
        )
        expected = _dedent(
            r"""
            \begin{longtable}{lrl}
            \caption[a table]{a table in a \texttt{longtable} environment}
            \label{tab:longtable}\\
            \toprule
            {} & {a} & {b} \\
            \midrule
            \endfirsthead
            \caption[]{a table in a \texttt{longtable} environment}\\
            \toprule
            {} & {a} & {b} \\
            \midrule
            \endhead
            \midrule
            \multicolumn{3}{r}{Continued on next page} \\
            \midrule
            \endfoot

            \bottomrule
            \endlastfoot
            0 & 1 & b1 \\
            1 & 2 & b2 \\
            \end{longtable}
            """
        )
        assert result == expected


class TestToLatexEscape:
    @pytest.fixture
    def df_with_symbols(self):
        """Dataframe with special characters for testing chars escaping."""
        a = "a"
        b = "b"
        yield DataFrame({"co$e^x$": {a: "a", b: "b"}, "co^l1": {a: "a", b: "b"}})

    def test_to_latex_escape_false(self, df_with_symbols):
        result = df_with_symbols.to_latex(escape=False)
        expected = _dedent(
            r"""
            \begin{tabular}{lll}
            \toprule
            {} & co$e^x$ & co^l1 \\
            \midrule
            a &       a &     a \\
            b &       b &     b \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_escape_default(self, df_with_symbols):
        result = df_with_symbols.to_latex(hrules=True)  # default: escape=True
        expected = _dedent(
            r"""
            \begin{tabular}{lll}
            \toprule
            {} & co\$e\textasciicircum x\$ & co\textasciicircum l1 \\
            \midrule
            a &       a &     a \\
            b &       b &     b \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_special_escape(self):
        df = DataFrame([r"a\b\c", r"^a^b^c", r"~a~b~c"])
        result = df.to_latex(hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{ll}
            \toprule
            {} &       0 \\
            \midrule
            0 &   a\textbackslash b\textbackslash c \\
            1 &  \textasciicircum a\textasciicircum b\textasciicircum c \\
            2 &  \textasciitilde a\textasciitilde b\textasciitilde c \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_escape_special_chars(self):
        special_characters = ["&", "%", "$", "#", "_", "{", "}", "~", "^", "\\"]
        df = DataFrame(data=special_characters)
        result = df.to_latex(hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{ll}
            \toprule
            {} &  0 \\
            \midrule
            0 &  \& \\
            1 &  \% \\
            2 &  \$ \\
            3 &  \# \\
            4 &  \_ \\
            5 &  \{ \\
            6 &  \} \\
            7 &  \textasciitilde  \\
            8 &  \textasciicircum  \\
            9 &  \textbackslash  \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_specified_header_special_chars_without_escape(self):
        # GH 7124
        df = DataFrame({"a": [1, 2], "b": ["b1", "b2"]})
        result = df.to_latex(header=["$A$", "$B$"], escape=False)
        expected = _dedent(
            r"""
            \begin{tabular}{lrl}
            \toprule
            {} & $A$ & $B$ \\
            \midrule
            0 &   1 &  b1 \\
            1 &   2 &  b2 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected


class TestToLatexPosition:
    def test_to_latex_position(self):
        the_position = "h"
        df = DataFrame({"a": [1, 2], "b": ["b1", "b2"]})
        result = df.to_latex(position=the_position)
        expected = _dedent(
            r"""
            \begin{table}[h]
            \centering
            \begin{tabular}{lrl}
            \toprule
            {} & {a} & {b} \\
            \midrule
            0 & 1 & b1 \\
            1 & 2 & b2 \\
            \bottomrule
            \end{tabular}
            \end{table}
            """
        )
        assert result == expected

    def test_to_latex_longtable_position(self):
        the_position = "t"
        df = DataFrame({"a": [1, 2], "b": ["b1", "b2"]})
        result = df.to_latex(longtable=True, position=the_position)
        expected = _dedent(
            r"""
            \begin{longtable}[t]{lrl}
            \toprule
            {} & {a} & {b} \\
            \midrule
            \endfirsthead

            \toprule
            {} & {a} & {b} \\
            \midrule
            \endhead
            \midrule
            \multicolumn{3}{r}{Continued on next page} \\
            \midrule
            \endfoot

            \bottomrule
            \endlastfoot
            0 & 1 & b1 \\
            1 & 2 & b2 \\
            \end{longtable}
            """
        )
        assert result == expected


class TestToLatexFormatters:
    def test_to_latex_with_formatters(self):
        df = DataFrame(
            {
                "datetime64": [
                    datetime(2016, 1, 1),
                    datetime(2016, 2, 5),
                    datetime(2016, 3, 3),
                ],
                "float": [1.0, 2.0, 3.0],
                "int": [1, 2, 3],
                "object": [(1, 2), True, False],
            }
        )

        formatters = {
            "datetime64": lambda x: x.strftime("%Y-%m"),
            "float": lambda x: f"[{x: 4.1f}]",
            "int": lambda x: f"0x{x:x}",
            "object": lambda x: f"-{x!s}-",
            "__index__": lambda x: f"index: {x}",
        }
        result = df.to_latex(formatters=dict(formatters))

        expected = _dedent(
            r"""
            \begin{tabular}{llrrl}
            \toprule
            {} & datetime64 &  float & int &    object \\
            \midrule
            index: 0 &    2016-01 & [ 1.0] & 0x1 &  -(1, 2)- \\
            index: 1 &    2016-02 & [ 2.0] & 0x2 &    -True- \\
            index: 2 &    2016-03 & [ 3.0] & 0x3 &   -False- \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_float_format_no_fixed_width_3decimals(self):
        # GH 21625
        df = DataFrame({"x": [0.19999]})
        result = df.to_latex(float_format="%.3f")
        expected = _dedent(
            r"""
            \begin{tabular}{lr}
            \toprule
            {} &     x \\
            \midrule
            0 & 0.200 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_float_format_no_fixed_width_integer(self):
        # GH 22270
        df = DataFrame({"x": [100.0]})
        result = df.to_latex(float_format="%.0f")
        expected = _dedent(
            r"""
            \begin{tabular}{lr}
            \toprule
            {} &   x \\
            \midrule
            0 & 100 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    @pytest.mark.parametrize("na_rep", ["NaN", "Ted"])
    def test_to_latex_na_rep_and_float_format(self, na_rep):
        df = DataFrame(
            [
                ["A", 1.2225],
                ["A", None],
            ],
            columns=["Group", "Data"],
        )
        result = df.to_latex(na_rep=na_rep, float_format="{:.2f}".format)
        expected = _dedent(
            fr"""
            \begin{{tabular}}{{llr}}
            \toprule
            {{}} & Group &  Data \\
            \midrule
            0 &     A &  1.22 \\
            1 &     A &   {na_rep} \\
            \bottomrule
            \end{{tabular}}
            """
        )
        assert result == expected


class TestToLatexMultiindex:
    @pytest.fixture
    def multiindex_frame(self):
        """Multiindex dataframe for testing multirow LaTeX macros."""
        yield DataFrame.from_dict(
            {
                ("c1", 0): Series({x: x for x in range(4)}),
                ("c1", 1): Series({x: x + 4 for x in range(4)}),
                ("c2", 0): Series({x: x for x in range(4)}),
                ("c2", 1): Series({x: x + 4 for x in range(4)}),
                ("c3", 0): Series({x: x for x in range(4)}),
            }
        ).T

    @pytest.fixture
    def multicolumn_frame(self):
        """Multicolumn dataframe for testing multicolumn LaTeX macros."""
        yield DataFrame(
            {
                ("c1", 0): {x: x for x in range(5)},
                ("c1", 1): {x: x + 5 for x in range(5)},
                ("c2", 0): {x: x for x in range(5)},
                ("c2", 1): {x: x + 5 for x in range(5)},
                ("c3", 0): {x: x for x in range(5)},
            }
        )

    def test_to_latex_multindex_header(self):
        # GH 16718
        df = DataFrame({"a": [0], "b": [1], "c": [2], "d": [3]})
        df = df.set_index(["a", "b"])
        observed = df.to_latex(header=["r1", "r2"])
        expected = _dedent(
            r"""
            \begin{tabular}{llrr}
            \toprule
              &   & r1 & r2 \\
            a & b &    &    \\
            \midrule
            0 & 1 &  2 &  3 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert observed == expected

    def test_to_latex_multiindex_empty_name(self):
        # GH 18669
        mi = pd.MultiIndex.from_product([[1, 2]], names=[""])
        df = DataFrame(-1, index=mi, columns=range(4))
        observed = df.to_latex(hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{lrrrr}
            \toprule
              &  0 &  1 &  2 &  3 \\
            {} &    &    &    &    \\
            \midrule
            1 & -1 & -1 & -1 & -1 \\
            2 & -1 & -1 & -1 & -1 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert observed == expected

    def test_to_latex_multiindex_column_tabular(self):
        df = DataFrame({("x", "y"): ["a"]})
        result = df.to_latex(hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{ll}
            \toprule
            {} &  x \\
            {} &  y \\
            \midrule
            0 &  a \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_multiindex_small_tabular(self):
        df = DataFrame({("x", "y"): ["a"]}).T
        result = df.to_latex(hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{lll}
            \toprule
              &   &  0 \\
            \midrule
            x & y &  a \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_multiindex_tabular(self, multiindex_frame):
        result = multiindex_frame.to_latex(hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{llrrrr}
            \toprule
               &   &  0 &  1 &  2 &  3 \\
            \midrule
            c1 & 0 &  0 &  1 &  2 &  3 \\
               & 1 &  4 &  5 &  6 &  7 \\
            c2 & 0 &  0 &  1 &  2 &  3 \\
               & 1 &  4 &  5 &  6 &  7 \\
            c3 & 0 &  0 &  1 &  2 &  3 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_multicolumn_tabular(self, multiindex_frame):
        # GH 14184
        df = multiindex_frame.T
        df.columns.names = ["a", "b"]
        result = df.to_latex(hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{lrrrrr}
            \toprule
            a & \multicolumn{2}{l}{c1} & \multicolumn{2}{l}{c2} & c3 \\
            b &  0 &  1 &  0 &  1 &  0 \\
            \midrule
            0 &  0 &  4 &  0 &  4 &  0 \\
            1 &  1 &  5 &  1 &  5 &  1 \\
            2 &  2 &  6 &  2 &  6 &  2 \\
            3 &  3 &  7 &  3 &  7 &  3 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_index_has_name_tabular(self):
        # GH 10660
        df = DataFrame({"a": [0, 0, 1, 1], "b": list("abab"), "c": [1, 2, 3, 4]})
        result = df.set_index(["a", "b"]).to_latex(hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{llr}
            \toprule
              &   &  c \\
            a & b &    \\
            \midrule
            0 & a &  1 \\
              & b &  2 \\
            1 & a &  3 \\
              & b &  4 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_groupby_tabular(self):
        # GH 10660
        df = DataFrame({"a": [0, 0, 1, 1], "b": list("abab"), "c": [1, 2, 3, 4]})
        result = df.groupby("a").describe().to_latex(hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{lrrrrrrrr}
            \toprule
            {} & \multicolumn{8}{l}{c} \\
            {} & count & mean &       std &  min &   25\% &  50\% &   75\% &  max \\
            a &       &      &           &      &       &      &       &      \\
            \midrule
            0 &   2.0 &  1.5 &  0.707107 &  1.0 &  1.25 &  1.5 &  1.75 &  2.0 \\
            1 &   2.0 &  3.5 &  0.707107 &  3.0 &  3.25 &  3.5 &  3.75 &  4.0 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_multiindex_dupe_level(self):
        # see gh-14484
        #
        # If an index is repeated in subsequent rows, it should be
        # replaced with a blank in the created table. This should
        # ONLY happen if all higher order indices (to the left) are
        # equal too. In this test, 'c' has to be printed both times
        # because the higher order index 'A' != 'B'.
        df = DataFrame(
            index=pd.MultiIndex.from_tuples([("A", "c"), ("B", "c")]), columns=["col"]
        )
        result = df.to_latex(hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{lll}
            \toprule
              &   &  col \\
            \midrule
            A & c &  NaN \\
            B & c &  NaN \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_multicolumn_default(self, multicolumn_frame):
        result = multicolumn_frame.to_latex(hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{lrrrrr}
            \toprule
            {} & \multicolumn{2}{l}{c1} & \multicolumn{2}{l}{c2} & c3 \\
            {} &  0 &  1 &  0 &  1 &  0 \\
            \midrule
            0 &  0 &  5 &  0 &  5 &  0 \\
            1 &  1 &  6 &  1 &  6 &  1 \\
            2 &  2 &  7 &  2 &  7 &  2 \\
            3 &  3 &  8 &  3 &  8 &  3 \\
            4 &  4 &  9 &  4 &  9 &  4 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_multicolumn_false(self, multicolumn_frame):
        result = multicolumn_frame.to_latex(multicolumn=False)
        expected = _dedent(
            r"""
            \begin{tabular}{lrrrrr}
            \toprule
            {} & c1 &    & c2 &    & c3 \\
            {} &  0 &  1 &  0 &  1 &  0 \\
            \midrule
            0 &  0 &  5 &  0 &  5 &  0 \\
            1 &  1 &  6 &  1 &  6 &  1 \\
            2 &  2 &  7 &  2 &  7 &  2 \\
            3 &  3 &  8 &  3 &  8 &  3 \\
            4 &  4 &  9 &  4 &  9 &  4 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_multirow_true(self, multicolumn_frame):
        result = multicolumn_frame.T.to_latex(multirow=True)
        expected = _dedent(
            r"""
            \begin{tabular}{llrrrrr}
            \toprule
               &   &  0 &  1 &  2 &  3 &  4 \\
            \midrule
            \multirow{2}{*}{c1} & 0 &  0 &  1 &  2 &  3 &  4 \\
               & 1 &  5 &  6 &  7 &  8 &  9 \\
            \cline{1-7}
            \multirow{2}{*}{c2} & 0 &  0 &  1 &  2 &  3 &  4 \\
               & 1 &  5 &  6 &  7 &  8 &  9 \\
            \cline{1-7}
            c3 & 0 &  0 &  1 &  2 &  3 &  4 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_multicolumnrow_with_multicol_format(self, multicolumn_frame):
        multicolumn_frame.index = multicolumn_frame.T.index
        result = multicolumn_frame.T.to_latex(
            multirow=True,
            multicolumn=True,
            multicolumn_format="c",
        )
        expected = _dedent(
            r"""
            \begin{tabular}{llrrrrr}
            \toprule
               &   & \multicolumn{2}{c}{c1} & \multicolumn{2}{c}{c2} & c3 \\
               &   &  0 &  1 &  0 &  1 &  0 \\
            \midrule
            \multirow{2}{*}{c1} & 0 &  0 &  1 &  2 &  3 &  4 \\
               & 1 &  5 &  6 &  7 &  8 &  9 \\
            \cline{1-7}
            \multirow{2}{*}{c2} & 0 &  0 &  1 &  2 &  3 &  4 \\
               & 1 &  5 &  6 &  7 &  8 &  9 \\
            \cline{1-7}
            c3 & 0 &  0 &  1 &  2 &  3 &  4 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    @pytest.mark.parametrize("name0", [None, "named0"])
    @pytest.mark.parametrize("name1", [None, "named1"])
    @pytest.mark.parametrize("axes", [[0], [1], [0, 1]])
    def test_to_latex_multiindex_names(self, name0, name1, axes):
        # GH 18667
        names = [name0, name1]
        mi = pd.MultiIndex.from_product([[1, 2], [3, 4]])
        df = DataFrame(-1, index=mi.copy(), columns=mi.copy())
        for idx in axes:
            df.axes[idx].names = names

        index_names_row = (
            f"{{{name0 if name0 else ''}}} & {{{name1 if name1 else ''}}} & {{}} & "
            f"{{}} & {{}} & {{}} \\\\\n"
            if (0 in axes and (name0 is not None or name1 is not None))
            else ""
        )
        column_name0 = f"{{{name0 if (name0 and 1 in axes) else ''}}}"
        column_name1 = f"{{{name1 if (name1 and 1 in axes) else ''}}}"

        observed = df.to_latex(
            hrules=True, multicol_align="l", sparse_columns=False, sparse_index=False
        )
        expected = dedent(
            f"""\
\\begin{{tabular}}{{llrrrr}}
\\toprule
{{}} & {column_name0} & {{1}} & {{1}} & {{2}} & {{2}} \\\\
{{}} & {column_name1} & {{3}} & {{4}} & {{3}} & {{4}} \\\\
{index_names_row}\\midrule
1 & 3 & -1 & -1 & -1 & -1 \\\\
1 & 4 & -1 & -1 & -1 & -1 \\\\
2 & 3 & -1 & -1 & -1 & -1 \\\\
2 & 4 & -1 & -1 & -1 & -1 \\\\
\\bottomrule
\\end{{tabular}}
"""
        )
        assert observed == expected

    @pytest.mark.parametrize("one_row", [True, False])
    def test_to_latex_multiindex_nans(self, one_row):
        # GH 14249
        df = DataFrame({"a": [None, 1], "b": [2, 3], "c": [4, 5]})
        if one_row:
            df = df.iloc[[0]]
        observed = df.set_index(["a", "b"]).to_latex(hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{llr}
            \toprule
                &   &  c \\
            a & b &    \\
            \midrule
            NaN & 2 &  4 \\
            """
        )
        if not one_row:
            expected += r"""1.0 & 3 &  5 \\
"""
        expected += r"""\bottomrule
\end{tabular}
"""
        assert observed == expected

    def test_to_latex_non_string_index(self):
        # GH 19981
        df = DataFrame([[1, 2, 3]] * 2).set_index([0, 1])
        result = df.to_latex(hrules=True)
        expected = _dedent(
            r"""
            \begin{tabular}{llr}
            \toprule
            {} & {} & {2} \\
            {0} & {1} & {} \\
            \midrule
            1 & 2 &  3 \\
              & 2 &  3 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected

    def test_to_latex_multiindex_multirow(self):
        # GH 16719
        mi = pd.MultiIndex.from_product(
            [[0.0, 1.0], [3.0, 2.0, 1.0], ["0", "1"]], names=["i", "val0", "val1"]
        )
        df = DataFrame(index=mi)
        result = df.to_latex(multirow=True, escape=False)
        expected = _dedent(
            r"""
            \begin{tabular}{lll}
            \toprule
                &     &   \\
            i & val0 & val1 \\
            \midrule
            \multirow{6}{*}{0.0} & \multirow{2}{*}{3.0} & 0 \\
                &     & 1 \\
            \cline{2-3}
                & \multirow{2}{*}{2.0} & 0 \\
                &     & 1 \\
            \cline{2-3}
                & \multirow{2}{*}{1.0} & 0 \\
                &     & 1 \\
            \cline{1-3}
            \cline{2-3}
            \multirow{6}{*}{1.0} & \multirow{2}{*}{3.0} & 0 \\
                &     & 1 \\
            \cline{2-3}
                & \multirow{2}{*}{2.0} & 0 \\
                &     & 1 \\
            \cline{2-3}
                & \multirow{2}{*}{1.0} & 0 \\
                &     & 1 \\
            \bottomrule
            \end{tabular}
            """
        )
        assert result == expected


class TestTableBuilder:
    @pytest.fixture
    def dataframe(self):
        return DataFrame({"a": [1, 2], "b": ["b1", "b2"]})

    @pytest.fixture
    def table_builder(self, dataframe):
        return RegularTableBuilder(formatter=DataFrameFormatter(dataframe))

    def test_create_row_iterator(self, table_builder):
        iterator = table_builder._create_row_iterator(over="header")
        assert isinstance(iterator, RowHeaderIterator)

    def test_create_body_iterator(self, table_builder):
        iterator = table_builder._create_row_iterator(over="body")
        assert isinstance(iterator, RowBodyIterator)

    def test_create_body_wrong_kwarg_raises(self, table_builder):
        with pytest.raises(ValueError, match="must be either 'header' or 'body'"):
            table_builder._create_row_iterator(over="SOMETHING BAD")


class TestRowStringConverter:
    @pytest.mark.parametrize(
        "row_num, expected",
        [
            (0, r"{} &  Design &  ratio &  xy \\"),
            (1, r"0 &       1 &      4 &  10 \\"),
            (2, r"1 &       2 &      5 &  11 \\"),
        ],
    )
    def test_get_strrow_normal_without_escape(self, row_num, expected):
        df = DataFrame({r"Design": [1, 2, 3], r"ratio": [4, 5, 6], r"xy": [10, 11, 12]})
        row_string_converter = RowStringConverter(
            formatter=DataFrameFormatter(df, escape=True),
        )
        assert row_string_converter.get_strrow(row_num=row_num) == expected

    @pytest.mark.parametrize(
        "row_num, expected",
        [
            (0, r"{} &  Design \# &  ratio, \% &  x\&y \\"),
            (1, r"0 &         1 &         4 &   10 \\"),
            (2, r"1 &         2 &         5 &   11 \\"),
        ],
    )
    def test_get_strrow_normal_with_escape(self, row_num, expected):
        df = DataFrame(
            {r"Design #": [1, 2, 3], r"ratio, %": [4, 5, 6], r"x&y": [10, 11, 12]}
        )
        row_string_converter = RowStringConverter(
            formatter=DataFrameFormatter(df, escape=True),
        )
        assert row_string_converter.get_strrow(row_num=row_num) == expected

    @pytest.mark.parametrize(
        "row_num, expected",
        [
            (0, r"{} & \multicolumn{2}{r}{c1} & \multicolumn{2}{r}{c2} & c3 \\"),
            (1, r"{} &  0 &  1 &  0 &  1 &  0 \\"),
            (2, r"0 &  0 &  5 &  0 &  5 &  0 \\"),
        ],
    )
    def test_get_strrow_multindex_multicolumn(self, row_num, expected):
        df = DataFrame(
            {
                ("c1", 0): {x: x for x in range(5)},
                ("c1", 1): {x: x + 5 for x in range(5)},
                ("c2", 0): {x: x for x in range(5)},
                ("c2", 1): {x: x + 5 for x in range(5)},
                ("c3", 0): {x: x for x in range(5)},
            }
        )

        row_string_converter = RowStringConverter(
            formatter=DataFrameFormatter(df),
            multicolumn=True,
            multicolumn_format="r",
            multirow=True,
        )

        assert row_string_converter.get_strrow(row_num=row_num) == expected
