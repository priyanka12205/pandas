def scatter_matrix(data):
    pass

def _gca():
    import matplotlib.pyplot as plt
    return plt.gca()

def _gcf():
    import matplotlib.pyplot as plt
    return plt.gcf()

def hist(data, column, by=None, ax=None, fontsize=None):
    keys, values = zip(*data.groupby(by)[column])
    if ax is None:
        ax = _gca()
    ax.boxplot(values)
    ax.set_xticklabels(keys, rotation=0, fontsize=fontsize)
    return ax

def grouped_hist(data, column, by=None, ax=None, bins=50, log=False,
                 figsize=None):
    """

    Returns
    -------
    fig : matplotlib.Figure
    """
    def plot_group(group, ax):
        ax.hist(group[column].dropna(), bins=bins)
    fig = _grouped_plot(plot_group, data, by=by, sharex=False,
                        sharey=False, figsize=figsize)
    fig.subplots_adjust(bottom=0.15, top=0.9, left=0.1, right=0.9,
                        hspace=0.3, wspace=0.2)
    return fig


def boxplot(data, column=None, by=None, ax=None, fontsize=None,
            rot=0, grid=True, figsize=None):
    """
    Make a box plot from DataFrame column optionally grouped by some columns or
    other inputs

    Parameters
    ----------
    data : DataFrame
    column : column name or list of names, or vector
        Can be any valid input to groupby
    by : string or sequence
        Column in the DataFrame to group by
    fontsize : int or string

    Returns
    -------
    ax : matplotlib.axes.AxesSubplot
    """
    def plot_group(grouped, ax):
        keys, values = zip(*grouped)
        keys = [_stringify(x) for x in keys]
        ax.boxplot(values)
        ax.set_xticklabels(keys, rotation=rot, fontsize=fontsize)

    if column == None:
        columns = None
    else:
        if isinstance(column, (list, tuple)):
            columns = column
        else:
            columns = [column]

    if by is not None:
        if not isinstance(by, (list, tuple)):
            by = [by]

        fig, axes = _grouped_plot_by_column(plot_group, data, columns=columns,
                                            by=by, grid=grid, figsize=figsize)
        ax = axes
    else:
        if ax is None:
            ax = _gca()
        fig = ax.get_figure()
        data = data._get_numeric_data()
        if columns:
            cols = columns
        else:
            cols = data.columns
        keys = [_stringify(x) for x in cols]
        ax.boxplot(list(data[cols].values.T))
        ax.set_xticklabels(keys, rotation=rot, fontsize=fontsize)
        ax.grid(grid)

    fig.subplots_adjust(bottom=0.15, top=0.9, left=0.1, right=0.9, wspace=0.2)
    return ax

def _stringify(x):
    if isinstance(x, tuple):
        return '|'.join(str(y) for y in x)
    else:
        return str(x)

def scatter_plot(data, x, y, by=None, ax=None, figsize=None):
    """

    Returns
    -------
    fig : matplotlib.Figure
    """
    import matplotlib.pyplot as plt

    def plot_group(group, ax):
        xvals = group[x].values
        yvals = group[y].values
        ax.scatter(xvals, yvals)

    if by is not None:
        fig = _grouped_plot(plot_group, data, by=by, figsize=figsize)
    else:
        fig = plt.figure()
        ax = fig.add_subplot(111)
        plot_group(data, ax)
        ax.set_ylabel(str(y))
        ax.set_xlabel(str(x))

    return fig

def _grouped_plot(plotf, data, by=None, numeric_only=True, figsize=None,
                  sharex=True, sharey=True):
    import matplotlib.pyplot as plt

    # allow to specify mpl default with 'default'
    if not (isinstance(figsize, str) and figsize == 'default'):
        figsize = (10, 5)               # our default

    grouped = data.groupby(by)
    ngroups = len(grouped)

    nrows, ncols = _get_layout(ngroups)
    if figsize is None:
        # our favorite default beating matplotlib's idea of the
        # default size
        figsize = (10, 5)
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=figsize,
                             sharex=sharex, sharey=sharey)

    ravel_axes = []
    for row in axes:
        ravel_axes.extend(row)

    for i, (key, group) in enumerate(grouped):
        ax = ravel_axes[i]
        if numeric_only:
            group = group._get_numeric_data()
        plotf(group, ax)
        ax.set_title(str(key))

    return fig, axes

def _grouped_plot_by_column(plotf, data, columns=None, by=None,
                            numeric_only=True, grid=False,
                            figsize=None):
    import matplotlib.pyplot as plt

    grouped = data.groupby(by)
    if columns is None:
        columns = data._get_numeric_data().columns - by
    ngroups = len(columns)

    nrows, ncols = _get_layout(ngroups)
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols,
                             sharex=True, sharey=True,
                             figsize=figsize)

    if isinstance(axes, plt.Axes):
        ravel_axes = [axes]
    else:
        ravel_axes = []
        for row in axes:
            if isinstance(row, plt.Axes):
                ravel_axes.append(row)
            else:
                ravel_axes.extend(row)

    for i, col in enumerate(columns):
        ax = ravel_axes[i]
        gp_col = grouped[col]
        plotf(gp_col, ax)
        ax.set_title(col)
        ax.set_xlabel(str(by))
        ax.grid(grid)

    byline = by[0] if len(by) == 1 else by
    fig.suptitle('Boxplot grouped by %s' % byline)

    return fig, axes

def _get_layout(nplots):
    if nplots == 1:
        return (1, 1)
    elif nplots == 2:
        return (1, 2)
    elif nplots < 4:
        return (2, 2)

    k = 1
    while k ** 2 < nplots:
        k += 1

    if (k - 1) * k >= nplots:
        return k, (k - 1)
    else:
        return k, k

if __name__ == '__main__':
    import pandas.rpy.common as com
    sales = com.load_data('sanfrancisco.home.sales', package='nutshell')
    top10 = sales['zip'].value_counts()[:10].index
    sales2 = sales[sales.zip.isin(top10)]

    fig = scatter_plot(sales2, 'squarefeet', 'price', by='zip')

    # plt.show()
