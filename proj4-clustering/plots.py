def percentplot(data, var, title=None, xlabel='', ax=None):
    ax = sns.barplot(x=var, y=var, data=data, estimator=lambda x: len(x) * 100 / len(data))
    ax.set(ylabel="Percent")
    ax.set(xlabel=xlabel if xlabel else '')
    ax.set(title=var if not title else title)
    return ax

    
def categoryplot(data, feature, category='interest_level', xlabel='', ax=None):
    values = pd.DataFrame()
    grouped = data.groupby([category, feature]).count()
    categories = data[category].cat.categories
    for c in categories:
        values[c] = grouped.xs(c).iloc[:,1]
    values = values.apply(lambda x: x * 100 / np.sum(x), axis=1)
    
    space = 0.1
    n = len(categories)
    width = (1.0 - space) / n
    
    xlabels = None
    for i, cat in enumerate(categories):
        percents = values.loc[:,cat]
        indices = range(len(percents))
        pos = [j - (1.0 - space) / n + i * width for j in indices]
        ax.bar(pos, percents, width=width, label=cat, color=sns.color_palette()[i])
        if i == 0:
            ax.set_xticks(indices)
            ax.set_xticklabels(percents.axes[0])

    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], labels[::-1])
    ax.set_ylabel('percent')
    ax.set_xlabel(xlabel if xlabel else '')
    return ax


def feature_hist(df, column, title=None, xlabel='', rotation=None):
    fig = plt.figure(figsize=(10, 8))
    ax1 = percentplot(df, column, title, xlabel=xlabel, ax=plt.subplot(211))
    ax2 = categoryplot(df, column, xlabel=xlabel, ax=plt.subplot(212))
    if rotation:
        for item in ax1.get_xticklabels():
            item.set_rotation(rotation)
        for item in ax2.get_xticklabels():
            item.set_rotation(rotation)
    fig.tight_layout()
