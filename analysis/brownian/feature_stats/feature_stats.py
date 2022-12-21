"""Plot statistics associated with features."""

import os

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from numpy import linspace
from sklearn.decomposition import PCA

pdidx = pd.IndexSlice

# Load features
features = pd.read_table('../get_features/out/features.tsv')
features.loc[features['kappa'] == -1, 'kappa'] = 1
features.loc[features['omega'] == -1, 'omega'] = 1

# Load segments
rows = []
with open('../regions_filter/out/regions_30.tsv') as file:
    field_names = file.readline().rstrip('\n').split('\t')
    for line in file:
        fields = {key: value for key, value in zip(field_names, line.rstrip('\n').split('\t'))}
        for ppid in fields['ppids'].split(','):
            rows.append({'OGid': fields['OGid'], 'start': int(fields['start']), 'stop': int(fields['stop']),
                         'disorder': fields['disorder'] == 'True', 'ppid': ppid})
segments = pd.DataFrame(rows).merge(features, how='left', on=['OGid', 'start', 'stop', 'ppid'])
regions = segments.groupby(['OGid', 'start', 'stop', 'disorder'])

means = regions.mean()
disorder = means.loc[pdidx[:, :, :, True], :]
order = means.loc[pdidx[:, :, :, False], :]

if not os.path.exists('out/'):
    os.mkdir('out/')

# Feature histograms
for feature_label in means.columns:
    fig, axs = plt.subplots(2, 1, sharex=True)
    xmin, xmax = means[feature_label].min(), means[feature_label].max()
    axs[0].hist(disorder[feature_label], bins=linspace(xmin, xmax, 75), color='C0', label='disorder')
    axs[1].hist(order[feature_label], bins=linspace(xmin, xmax, 75), color='C1', label='order')
    axs[1].set_xlabel(f'Mean {feature_label}')
    for i in range(2):
        axs[i].set_ylabel('Number of regions')
        axs[i].legend()
    plt.savefig(f'out/hist_numregions-{feature_label}.png')
    plt.close()


# Individual PCAs
pca = PCA(n_components=10)
colors = ['#e15759', '#499894', '#59a14f', '#f1ce63', '#b07aa1', '#d37295', '#9d7660', '#bab0ac',
          '#ff9d9a', '#86bcb6', '#8cd17d', '#b6992d', '#d4a6c8', '#fabfd2', '#d7b5a6', '#79706e']

plots = [(disorder, 'disorder', 'no norm', 'nonorm'),
         (order, 'order', 'no norm', 'nonorm'),
         ((disorder - disorder.mean()) / disorder.std(), 'disorder', 'z-score', 'z-score'),
         ((order - order.mean()) / order.std(), 'order', 'z-score', 'z-score'),
         ((disorder - disorder.min()) / (disorder.max() - disorder.min()), 'disorder', 'min-max', 'min-max'),
         ((order - order.min()) / (order.max() - order.min()), 'order', 'min-max', 'min-max')]
for data, data_label, norm_label, file_label in plots:
    color = 'C0' if data_label == 'disorder' else 'C1'
    transform = pca.fit_transform(data.to_numpy())

    # PCA without arrows
    plt.scatter(transform[:, 0], transform[:, 1], label=data_label, color=color, s=5, alpha=0.1, edgecolors='none')
    plt.xlabel('PC1')
    plt.ylabel('PC2')
    plt.title(norm_label)
    legend = plt.legend(markerscale=2)
    for lh in legend.legendHandles:
        lh.set_alpha(1)
    plt.savefig(f'out/scatter_pca_{data_label}_{file_label}.png')
    plt.close()

    # PCA with arrows
    plt.scatter(transform[:, 0], transform[:, 1], label=data_label, color=color, s=5, alpha=0.1, edgecolors='none')
    plt.xlabel('PC1')
    plt.ylabel('PC2')
    plt.title(norm_label)

    xmin, xmax = plt.xlim()
    ymin, ymax = plt.ylim()
    scale = (xmax + ymax - xmin - ymin) / 3
    projections = sorted(zip(data.columns, pca.components_[:2].transpose()), key=lambda x: x[1][0]**2 + x[1][1]**2, reverse=True)

    handles = []
    for i in range(len(colors)):
        feature_label, (x, y) = projections[i]
        handles.append(Line2D([], [], color=colors[i % len(colors)], linewidth=2, label=feature_label))
        plt.annotate('', xy=(scale*x, scale*y), xytext=(0, 0),
                     arrowprops={'headwidth': 6, 'headlength': 6, 'width': 1.75, 'color': colors[i % len(colors)]})
    plt.legend(handles=handles, fontsize=8, loc='right', bbox_to_anchor=(1.05, 0.5))
    plt.savefig(f'out/scatter_pca-arrow_{data_label}_{norm_label}.png')
    plt.close()

    # Scree plot
    plt.bar(range(1, len(pca.explained_variance_ratio_)+1), pca.explained_variance_ratio_, label=data_label, color=color)
    plt.xlabel('Principal component')
    plt.ylabel('Explained variance ratio')
    plt.title(norm_label)
    plt.legend()
    plt.savefig(f'out/bar_scree_{data_label}_{file_label}.png')
    plt.close()
