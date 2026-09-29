# GPW Quant Research — automated baseline

Sample: 2008-01-01 to 2024-01-24
Final OOS: 2019-01-01 to 2024-01-24

| Strategy | Status | OOS CAGR | OOS Sharpe | OOS MaxDD | 2x cost CAGR | OOS DSR approx |
|---|---|---:|---:|---:|---:|---:|
| momentum_12_1 | WATCH | 17.81% | 0.66 | -44.58% | 13.30% | 0.352 |
| trend_sma200 | WATCH | 18.91% | 0.79 | -33.31% | 14.59% | 0.466 |
| reversal_5d | REJECTED | -37.10% | -1.30 | -91.49% | -59.02% | 0.000 |
| lowvol_120d | REJECTED | -3.41% | -0.09 | -43.38% | -6.09% | 0.020 |
| momentum_market_filter | REJECTED | 2.08% | 0.21 | -32.90% | -0.65% | 0.083 |
| momentum_lowvol | WATCH | 10.76% | 0.54 | -44.16% | 5.51% | 0.260 |

## Key limitations
- Historical WIG membership is point-in-time by available GPW Benchmark snapshots, but snapshots are not daily.
- Stock OHLCV has no explicit adjusted-close/dividend field, so strategy legs are price-return based; the primary WIG benchmark is total-return, making relative comparisons conservative with respect to dividends.
- Delisting terminal returns are unavailable; a conservative -30% penalty is applied after 5 consecutive missing sessions while held.
- Execution is next-close, not same-close. Spread/slippage uses ADV buckets and is stress-tested at 1x/1.5x/2x/3x.
- Results end on 2024-01-24 because that is the terminal date of the mirrored Bossa archive used here.