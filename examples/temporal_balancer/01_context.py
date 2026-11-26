"""
Example 01: building a SeasonalContext from CSV logs.

Generates synthetic sample data if logs.csv does not exist yet, then builds the
SeasonalContext in a single streaming pass via build_seasonal_context.
Prints the seasonality profile (weights from AdditionalContext), the
user_activity_ratio statistics and a sample of hourly tag probabilities.
"""

from pathlib import Path

from rtb_sdk.balancer.seasonal import (
    HistoricalLogsConfig,
    build_seasonal_context,
)

from examples.temporal_balancer.fixtures import ADS, LOGS_CSV, PERIOD, TAG_COL_MAP

HERE = Path(__file__).parent


def ensure_logs() -> None:
    from examples.sample_data import ensure_samples
    ensure_samples()


def main() -> None:
    ensure_logs()

    config = HistoricalLogsConfig(
        path=str(LOGS_CSV),
        timestamp_col='ts',
        user_id_col='user_id',
        aggregation_mode='hour_of_day',
        timezone='UTC',
    )

    print('Build SeasonalContext of', LOGS_CSV.name, '...')
    context = build_seasonal_context(config, ADS, PERIOD, tag_col_map=TAG_COL_MAP)
    print('Ready.')
    print()

    # --- Seasonality profile (weights from AdditionalContext) ---
    print(f'Seasonal profile  (mode={context["mode"]}):')
    print(f'  {"hour":>3}  {"weight":>7}  {"bar"}')
    for h, ac in sorted(context['context'].items()):
        w = ac['weight']
        bar = '█' * int(w * 240)
        print(f'  {h:>3}  {w:.4f}  {bar}')
    print()

    # --- user_activity_ratio (sample — one ad) ---
    sample_ad = next(iter(context['context'][0]['user_activity_ratio']), None)
    if sample_ad is not None:
        print(f'user_activity_ratio for «{sample_ad}» clockwise:')
        for h, ac in sorted(context['context'].items()):
            ratio = ac['user_activity_ratio'].get(sample_ad, 1.0)
            print(f'  hour {h:>3}: {ratio:.4f}')
        print()

    # --- Hourly tag probabilities (sample) ---
    sample_hour = 20
    sample_ac = context['context'].get(sample_hour)
    if sample_ac and sample_ac['tags_probability']:
        print(f'Tag probabilities (sample — hour {sample_hour}, top-3 each vocab):')
        for vocab, raw_probs in sorted(sample_ac['tags_probability'].items()):
            top3 = sorted(raw_probs.items(), key=lambda x: -x[1])[:3]
            vals = '  '.join(f'{tag}={p:.3f}' for tag, p in top3)
            print(f'  {vocab}: {vals}')


if __name__ == '__main__':
    main()
