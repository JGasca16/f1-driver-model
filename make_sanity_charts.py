"""Make four inspection charts from the saved 2025 results, without changing them."""

import argparse
import os
from pathlib import Path
import tempfile

# Keep matplotlib's temporary font cache outside the project and user settings.
os.environ.setdefault('MPLCONFIGDIR', tempfile.mkdtemp(prefix='sanity-matplotlib-'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
FILENAMES = (
    'rating_by_group.png', 'qualifying_vs_dry.png',
    'gap_by_race_selected_pairs.png', 'data_coverage.png',
)
SIGN = 'Negative = faster than teammate'
# Bit values record qualifying (1), dry (2), and wet (4) availability.
CATEGORIES = {
    0: ('None', '#eeeeee'),
    1: ('Qualifying only', '#f0e442'),
    2: ('Dry only', '#56b4e9'),
    3: ('Qualifying + dry', '#0072b2'),
    4: ('Wet only', '#cc79a7'),
    5: ('Qualifying + wet', '#009e73'),
    6: ('Dry + wet', '#d55e00'),
}


def grouped_driver_order(ratings):
    """Group names set the order; scores only order drivers inside each group."""
    return ratings.sort_values(
        ['comparison_group', 'combined_rating', 'driver'], kind='stable'
    ).copy()


def save_chart(fig, path):
    # Exclusive creation protects earlier charts, including on a repeated run.
    with path.open('xb') as handle:
        fig.savefig(handle, format='png', dpi=150)
    plt.close(fig)


def chart_groups(ratings, path):
    ordered = grouped_driver_order(ratings)
    fig, ax = plt.subplots(figsize=(11, 12))
    positions, labels, group_ranges = [], [], []
    y = 0
    for group, rows in ordered.groupby('comparison_group', sort=False):
        start = y
        for row in rows.itertuples():
            provisional = row.rating_status == 'provisional'
            ax.barh(y, row.combined_rating, height=.7, color='#0072b2',
                    edgecolor='#222222', hatch='///' if provisional else None)
            if pd.notna(row.combined_ci_low) and pd.notna(row.combined_ci_high):
                # Draw endpoints directly, so even an interval not enclosing the bar is shown.
                ax.hlines(y, row.combined_ci_low, row.combined_ci_high, color='#222222')
                ax.vlines([row.combined_ci_low, row.combined_ci_high], y-.15, y+.15,
                          color='#222222')
            positions.append(y)
            labels.append(row.driver + (' *' if provisional else ''))
            y += 1
        group_ranges.append((group, start, y-1))
        y += 1
    for group, start, end in group_ranges:
        ax.text(-.14, (start+end)/2, group, transform=ax.get_yaxis_transform(),
                ha='right', va='center', fontsize=9, fontweight='bold')
        if start:
            ax.axhline(start-1, color='#bbbbbb', linewidth=.8)
    ax.set_yticks(positions, labels)
    ax.invert_yaxis()
    ax.axvline(0, color='black', linewidth=.8)
    ax.set_xlabel('Combined rating (log-percentage points)\n' + SIGN)
    ax.set_title('2025 ratings within comparison groups\nBars: saved rating; whiskers: saved 95% interval', pad=15)
    ax.grid(axis='x', alpha=.15)
    ax.set_axisbelow(True)
    fig.text(.32, .025, '* Hatched bar: provisional (Doohan). Group order is alphabetical, not a global ranking.', fontsize=9)
    fig.subplots_adjust(left=.32, right=.97, top=.93, bottom=.10)
    save_chart(fig, path)


def scatter_statistics(ratings):
    valid = ratings[['qualifying_rating', 'dry_rating']].dropna()
    opposite = int((valid.qualifying_rating * valid.dry_rating < 0).sum())
    return opposite, float(valid.qualifying_rating.corr(valid.dry_rating)), len(valid)


def chart_scatter(ratings, path):
    opposite, correlation, count = scatter_statistics(ratings)
    fig, ax = plt.subplots(figsize=(10, 9))
    valid = ratings.dropna(subset=['qualifying_rating', 'dry_rating'])
    ax.scatter(valid.qualifying_rating, valid.dry_rating, color='#0072b2', s=38, zorder=3)
    # Offsets keep labels readable around the dense central cluster.
    offsets = {'BEA':(-30,10), 'NOR':(-12,-26), 'OCO':(9,-14), 'PIA':(9,8),
               'BOR':(-29,8), 'ALB':(10,-2), 'HUL':(10,-13), 'SAI':(-25,-20),
               'LAW':(-45,5), 'COL':(-8,20), 'ANT':(12,-7), 'HAM':(-38,7),
               'STR':(12,8), 'ALO':(-40,0), 'RUS':(-5,-30), 'GAS':(7,-18),
               'LEC':(10,-1), 'HAD':(-65,6)}
    for row in valid.itertuples():
        ax.annotate(row.driver, (row.qualifying_rating, row.dry_rating),
                    xytext=offsets.get(row.driver, (7,7)), textcoords='offset points',
                    fontsize=9, arrowprops={'arrowstyle':'-', 'color':'#aaaaaa', 'lw':.5})
    lower = min(valid.qualifying_rating.min(), valid.dry_rating.min())-.18
    upper = max(valid.qualifying_rating.max(), valid.dry_rating.max())+.18
    ax.plot([lower, upper], [lower, upper], '--', color='#888888', label='Equal qualifying and dry rating')
    ax.axvline(0, color='black', linewidth=.7)
    ax.axhline(0, color='black', linewidth=.7)
    ax.set(xlim=(lower, upper), ylim=(lower, upper), aspect='equal',
           xlabel='Qualifying rating (log-percentage points)', ylabel='Dry rating (log-percentage points)')
    ax.set_title(f'Qualifying vs dry pace: {opposite}/{count} opposite signs; Pearson r = {correlation:.3f}\n{SIGN} on both axes')
    ax.legend(loc='upper left', fontsize=9)
    fig.text(.13, .025, 'Descriptive correlation: teammate scores are related, not independent observations.', fontsize=9)
    fig.tight_layout(rect=(0,.05,1,1))
    save_chart(fig, path)


def pair_series(dry, driver, teammate):
    rows = []
    for row in dry.itertuples():
        if {row.driver, row.teammate} != {driver, teammate}:
            continue
        gap, se = row.final_gap, row.final_se_pp
        if row.driver != driver and pd.notna(gap):
            # Ordinary percentages reverse reciprocally, not just by changing sign.
            se = se / (1 + gap/100)**2
            gap = -100 * gap / (100 + gap)
        rows.append({'round_number': row.round_number, 'gap': gap,
                     'se': se, 'method': row.method_used})
    return pd.DataFrame(rows).set_index('round_number').reindex(range(1,25))


def chart_races(dry, path):
    fig, axes = plt.subplots(3, 1, figsize=(13, 10), sharex=True)
    for ax, (driver, teammate), color in zip(axes, [('TSU','VER'),('NOR','PIA'),('HAM','LEC')],
                                            ['#0072b2','#d55e00','#009e73']):
        series = pair_series(dry, driver, teammate)
        # Reindexing the whole season leaves real breaks at missing races and absent pairings.
        ax.plot(series.index, series.gap, color=color, alpha=.6, linewidth=1)
        for method, marker in [('strict','o'), ('linear','s')]:
            part = series[(series.method == method) & series.gap.notna()]
            ax.plot(part.index, part.gap, linestyle='none', marker=marker, color=color)
            errors = part.dropna(subset=['se'])
            ax.errorbar(errors.index, errors.gap, yerr=errors.se, fmt='none',
                        ecolor=color, capsize=3, linewidth=1)
        ax.axhline(0, color='black', linewidth=.7)
        ax.axvline(8, color='#777777', linestyle=':', linewidth=1)
        ax.text(8.15, .96, 'Monaco', transform=ax.get_xaxis_transform(), va='top', fontsize=9)
        ax.set_title(f'{driver} relative to {teammate}', loc='left', fontsize=11)
        ax.set_ylabel('Dry gap (%)')
        ax.grid(axis='y', alpha=.15)
    axes[-1].set_xticks(range(1,25))
    axes[-1].set_xlabel('2025 race round')
    axes[-1].set_xlim(.5,24.5)
    fig.suptitle('Selected teammate pairs: per-race dry pace\n' + SIGN + ' (first-named driver)', fontsize=14)
    fig.legend(handles=[Line2D([], [], color='#555555', marker='o', linestyle='none', label='Strict'),
                        Line2D([], [], color='#555555', marker='s', linestyle='none', label='Linear regression')],
               loc='lower center', bbox_to_anchor=(.5,.015), ncol=2)
    fig.text(.5, .006, 'Error bars: ±1 standard error. Missing observations break the line. Monaco retains its reported gap.', ha='center', fontsize=9)
    fig.tight_layout(rect=(0,.065,1,.94))
    save_chart(fig, path)


def coverage_data(ratings, qualifying, dry, wet):
    drivers = sorted(ratings.driver)
    entered = set(zip(qualifying.driver, qualifying.round_number))
    matrix = np.full((len(drivers),24), -1, dtype=int)
    signals = {}
    for row in qualifying.itertuples():
        signals[(row.driver,row.round_number)] = 1 if pd.notna(row.combined_gap) else 0
    for frame, column, bit in [(dry,'final_gap',2), (wet,'wet_gap_2pct',4)]:
        for row in frame.itertuples():
            for driver in (row.driver,row.teammate):
                key = (driver,row.round_number)
                if key not in entered:
                    raise ValueError(f'Race pace appearance absent from qualifying roster: {key}')
                if pd.notna(getattr(row,column)):
                    signals[key] |= bit
    for i, driver in enumerate(drivers):
        for round_number in range(1,25):
            matrix[i,round_number-1] = signals.get((driver,round_number), -1)
    return drivers, matrix


def chart_coverage(ratings, qualifying, dry, wet, path):
    drivers, matrix = coverage_data(ratings, qualifying, dry, wet)
    # Dry and wet races are separate, so "All three" is not a coverage category.
    codes = [0,1,2,3,5] + [code for code in (4,6) if (matrix == code).any()]
    display = np.zeros_like(matrix)
    for i, code in enumerate(codes, start=1):
        display[matrix == code] = i
    colors = ['#ffffff'] + [CATEGORIES[c][1] for c in codes]
    fig, ax = plt.subplots(figsize=(14,10))
    ax.imshow(display, cmap=ListedColormap(colors), norm=BoundaryNorm(np.arange(len(colors)+1)-.5,len(colors)), aspect='auto')
    absent_y, absent_x = np.where(matrix == -1)
    ax.scatter(absent_x, absent_y, marker='x', s=24, color='#555555', linewidths=1)
    ax.set_xticks(range(24), range(1,25))
    ax.set_yticks(range(len(drivers)), drivers)
    ax.set_xticks(np.arange(-.5,24,1), minor=True)
    ax.set_yticks(np.arange(-.5,len(drivers),1), minor=True)
    ax.grid(which='minor', color='white', linewidth=.8)
    ax.tick_params(which='minor', bottom=False, left=False)
    ax.set_xlabel('2025 race round')
    ax.set_title('Usable signals by driver and race\nBlank gaps are missing evidence, not zero pace gaps', pad=14)
    handles = [Patch(facecolor=CATEGORIES[c][1], edgecolor='#999999', label=f'{CATEGORIES[c][0]} ({int((matrix == c).sum())})') for c in codes]
    handles.append(Line2D([],[], color='#555555', marker='x', linestyle='none', label=f'Not entered ({int((matrix == -1).sum())})'))
    fig.legend(handles=handles, loc='lower center', ncol=4, bbox_to_anchor=(.5,.015), fontsize=10)
    fig.tight_layout(rect=(0,.10,1,1))
    save_chart(fig, path)
    return {CATEGORIES[c][0]: int((matrix == c).sum()) for c in CATEGORIES} | {'Not entered':int((matrix == -1).sum())}


def make_charts(data_dir=ROOT/'data', output_dir=ROOT/'charts'):
    data_dir, output_dir = Path(data_dir), Path(output_dir)
    # The wet file was explicitly approved as a fourth input for round-level coverage.
    ratings = pd.read_csv(data_dir/'driver_rating_2025.csv')
    qualifying = pd.read_csv(data_dir/'2025_qualifying_gaps_combined.csv')
    dry = pd.read_csv(data_dir/'race_pace_dry_final.csv')
    wet = pd.read_csv(data_dir/'race_pace_wet_final.csv')
    for name in FILENAMES:
        if (output_dir/name).exists():
            raise FileExistsError(f'{output_dir/name} exists; choose a new --output-dir.')
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_groups(ratings, output_dir/FILENAMES[0])
    chart_scatter(ratings, output_dir/FILENAMES[1])
    chart_races(dry, output_dir/FILENAMES[2])
    counts = chart_coverage(ratings, qualifying, dry, wet, output_dir/FILENAMES[3])
    opposite, correlation, count = scatter_statistics(ratings)
    print(f'Saved four charts at 150 dpi in {output_dir}')
    print(f'Opposite signs: {opposite}/{count}; Pearson correlation: {correlation:.6f}')
    print('Coverage (driver-rounds):', counts)
    return counts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'charts')
    args = parser.parse_args()
    make_charts(output_dir=args.output_dir)
