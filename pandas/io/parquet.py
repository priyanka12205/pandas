""" parquet compat """

from warnings import catch_warnings
from distutils.version import LooseVersion
from pandas import DataFrame, RangeIndex, Int64Index, get_option
from pandas.compat import range, string_types
from pandas.core.common import AbstractMethodError
from pandas.io.common import get_filepath_or_buffer


def get_engine(engine):
    """ return our implementation """

    if engine == 'auto':
        engine = get_option('io.parquet.engine')

    if engine == 'auto':
        # try engines in this order
        try:
            return PyArrowImpl()
        except ImportError:
            pass

        try:
            return FastParquetImpl()
        except ImportError:
            pass

    if engine not in ['pyarrow', 'fastparquet']:
        raise ValueError("engine must be one of 'pyarrow', 'fastparquet'")

    if engine == 'pyarrow':
        return PyArrowImpl()
    elif engine == 'fastparquet':
        return FastParquetImpl()


class BaseImpl(object):

    api = None  # module

    @staticmethod
    def validate_dataframe(df):
        if not isinstance(df, DataFrame):
            raise ValueError("to_parquet only supports IO with DataFrames")
        # must have value column names (strings only)
        if df.columns.inferred_type not in {'string', 'unicode'}:
            raise ValueError("parquet must have string column names")
        # index level names must be strings
        valid_names = all(
            isinstance(name, string_types)
            for name in df.index.names
            if name is not None
        )
        if not valid_names:
            raise ValueError("Index level names must be strings")

    def write(self, df, path, compression, **kwargs):
        raise AbstractMethodError(self)

    def read(self, path, columns=None, **kwargs):
        raise AbstractMethodError(self)


class PyArrowImpl(BaseImpl):

    def __init__(self):
        # since pandas is a dependency of pyarrow
        # we need to import on first use
        try:
            import pyarrow
            import pyarrow.parquet
        except ImportError:
            raise ImportError(
                "pyarrow is required for parquet support\n\n"
                "you can install via conda\n"
                "conda install pyarrow -c conda-forge\n"
                "\nor via pip\n"
                "pip install -U pyarrow\n"
            )
        if LooseVersion(pyarrow.__version__) < '0.4.1':
            raise ImportError(
                "pyarrow >= 0.4.1 is required for parquet support\n\n"
                "you can install via conda\n"
                "conda install pyarrow -c conda-forge\n"
                "\nor via pip\n"
                "pip install -U pyarrow\n"
            )
        self._pyarrow_lt_070 = (
           LooseVersion(pyarrow.__version__) < LooseVersion('0.7.0')
        )
        self.api = pyarrow

    def write(self, df, path, compression='snappy',
              coerce_timestamps='ms', **kwargs):
        self.validate_dataframe(df)
        if self._pyarrow_lt_070:
            self._validate_write_lt_070(
                df, path, compression, coerce_timestamps, **kwargs
            )
        path, _, _ = get_filepath_or_buffer(path)
        table = self.api.Table.from_pandas(df)
        self.api.parquet.write_table(
            table, path, compression=compression,
            coerce_timestamps=coerce_timestamps, **kwargs)

    def read(self, path, columns=None, **kwargs):
        path, _, _ = get_filepath_or_buffer(path)
        parquet_file = self.api.parquet.ParquetFile(path)
        if self._pyarrow_lt_070:
            parquet_file.path = path
            return self._read_lt_070(parquet_file, columns, **kwargs)
        kwargs['use_pandas_metadata'] = True
        return parquet_file.read(columns=columns, **kwargs).to_pandas()


    def _validate_write_lt_070(self, df, path, compression='snappy',
                      coerce_timestamps='ms', **kwargs):
        # Compatibility shim for pyarrow < 0.7.0
        # TODO: Remove in pandas 0.22.0
        from pandas.core.indexes.multi import MultiIndex
        if isinstance(df.index, MultiIndex):
            msg = "Mulit-index DataFrames are only supported with pyarrow >= 0.7.0"
            raise ValueError(msg)
        # Validate index
        if not isinstance(df.index, Int64Index):
            msg = (
                "parquet does not support serializing {} for the index;"
                "you can .reset_index() to make the index into column(s)"
            )
            raise ValueError(msg.format(type(df.index)))
        if not df.index.equals(RangeIndex(len(df))):
            raise ValueError(
                "parquet does not support serializing a non-default index "
                "for the index; you can .reset_index() to make the index "
                "into column(s)"
            )
        if df.index.name is not None:
            raise ValueError(
                "parquet does not serialize index meta-data "
                "on a default index"
            )

    def _read_lt_070(self, parquet_file, columns, **kwargs):
        # Compatibility shim for pyarrow < 0.7.0
        # TODO: Remove in pandas 0.22.0
        from itertools import chain
        import json
        if columns is not None:
            metadata = json.loads(parquet_file.metadata.metadata[b'pandas'])
            columns = set(chain(columns, metadata['index_columns']))
        kwargs['columns'] = columns
        return self.api.parquet.read_table(parquet_file.path, **kwargs).to_pandas()


class FastParquetImpl(BaseImpl):

    def __init__(self):
        # since pandas is a dependency of fastparquet
        # we need to import on first use
        try:
            import fastparquet
        except ImportError:
            raise ImportError(
                "fastparquet is required for parquet support\n\n"
                "you can install via conda\n"
                "conda install fastparquet -c conda-forge\n"
                "\nor via pip\n"
                "pip install -U fastparquet"
            )
        if LooseVersion(fastparquet.__version__) < '0.1.0':
            raise ImportError(
                "fastparquet >= 0.1.0 is required for parquet "
                "support\n\n"
                "you can install via conda\n"
                "conda install fastparquet -c conda-forge\n"
                "\nor via pip\n"
                "pip install -U fastparquet"
            )
        self.api = fastparquet

    def write(self, df, path, compression='snappy', **kwargs):
        self.validate_dataframe(df)
        # thriftpy/protocol/compact.py:339:
        # DeprecationWarning: tostring() is deprecated.
        # Use tobytes() instead.
        path, _, _ = get_filepath_or_buffer(path)
        with catch_warnings(record=True):
            self.api.write(path, df,
                           compression=compression, **kwargs)

    def read(self, path, columns=None, **kwargs):
        path, _, _ = get_filepath_or_buffer(path)
        parquet_file = self.api.ParquetFile(path)
        return parquet_file.to_pandas(columns=columns, **kwargs)


def to_parquet(df, path, engine='auto', compression='snappy', **kwargs):
    """
    Write a DataFrame to the parquet format.

    Parameters
    ----------
    df : DataFrame
    path : string
        File path
    engine : {'auto', 'pyarrow', 'fastparquet'}, default 'auto'
        Parquet reader library to use. If 'auto', then the option
        'io.parquet.engine' is used. If 'auto', then the first
        library to be installed is used.
    compression : str, optional, default 'snappy'
        compression method, includes {'gzip', 'snappy', 'brotli'}
    kwargs
        Additional keyword arguments passed to the engine
    """
    impl = get_engine(engine)
    return impl.write(df, path, compression=compression, **kwargs)


def read_parquet(path, engine='auto', columns=None, **kwargs):
    """
    Load a parquet object from the file path, returning a DataFrame.

    .. versionadded 0.21.0

    Parameters
    ----------
    path : string
        File path
    columns: list, default=None
        If not None, only these columns will be read from the file.

        .. versionadded 0.21.1
    engine : {'auto', 'pyarrow', 'fastparquet'}, default 'auto'
        Parquet reader library to use. If 'auto', then the option
        'io.parquet.engine' is used. If 'auto', then the first
        library to be installed is used.
    kwargs are passed to the engine

    Returns
    -------
    DataFrame

    """

    impl = get_engine(engine)
    return impl.read(path, columns=columns, **kwargs)
