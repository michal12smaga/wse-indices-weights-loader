# GPW Quant Research — Final Findings

## Scope
- Price sample: 2008-01-01 to 2024-01-24
- Train: 2008-2014
- Validation: 2015-2018
- Final OOS: 2019-01-01 to 2024-01-24
- Point-in-time universe: latest available historical WIG snapshot at each signal date
- Baseline liquidity: 60-session median PLN turnover >= PLN 1m
- Execution: signal at close t, rebalance no earlier than close t+1
- One-way costs: 25-75 bps depending on ADV; stress at 1.5x/2x/3x
- Primary benchmark: WIG total-return index

## Final classification

| Strategy | Final classification | Main evidence |
|---|---|---|
| Trend SMA150-250 + positive 12M return | PROMISING BUT NEEDS MORE DATA / REGIME-DEPENDENT | OOS CAGR 18.9%, Sharpe 0.79, MaxDD -33.3%; survives 2x costs and 2-3 session delay; parameter plateau. However 2020 contributes heavily, DSR only ~0.47, and ADV >=10m stress collapses edge. |
| Momentum 12-1 | REGIME-DEPENDENT | OOS CAGR 17.8%, but excluding 2020 CAGR is -2.3% and 2021-2023 CAGR is -5.9%. |
| Momentum + low-vol | PROMISING BUT CAPACITY-LIMITED / NEEDS MORE DATA | OOS CAGR 10.8%; excluding 2020 CAGR 10.4%; delay robust. But ADV >=3m stress turns CAGR negative and 2x-cost alpha vs WIG is weak. |
| Short-term reversal 3/5/10d | REJECTED | Negative across all lookbacks, huge turnover and severe cost sensitivity. |
| Standalone low-vol | REJECTED | No stable positive OOS premium across 60/120/180d windows. |
| Momentum + WIG20 market filter | REJECTED | Weak OOS edge and negative CAGR at 2x costs. |

## Key OOS results

### Trend SMA200
- CAGR: 18.91%
- Sharpe: 0.79
- Sortino: 1.14
- Max drawdown: -33.31%
- Beta vs WIG total return: 0.92
- Annualized alpha vs WIG total return: 13.8%
- Information ratio vs WIG: 0.75
- 2x-cost CAGR: 14.59%
- 3x-cost CAGR: ~10.4%
- DSR approximation (14 trials): 0.466
- Monte Carlo probability of terminal loss over an OOS-length sample: 9.45%

Parameter stability:
- SMA150: CAGR 20.6%, Sharpe 0.80
- SMA200: CAGR 18.9%, Sharpe 0.79
- SMA250: CAGR 18.8%, Sharpe 0.80

Execution delay:
- t+1: CAGR 18.9%, Sharpe 0.79
- t+2: CAGR 17.5%, Sharpe 0.75
- t+3: CAGR 15.9%, Sharpe 0.70

Liquidity stress:
- ADV >=1m: CAGR 18.9%, Sharpe 0.79
- ADV >=3m: CAGR 23.5%, Sharpe 0.85
- ADV >=10m: CAGR 2.0%, Sharpe 0.22, alpha vs WIG slightly negative

Concentration:
- 2020 return: +110.1%
- Excluding 2020: CAGR 3.3%, Sharpe 0.26
- 2021-2023: CAGR 5.4%, Sharpe 0.34

### Momentum + low-vol
- CAGR: 10.76%
- Sharpe: 0.54
- Max drawdown: -44.16%
- Alpha vs WIG total return: 6.5%
- 2x-cost CAGR: 5.51%
- 2x-cost alpha vs WIG: ~1.7%
- DSR approximation: 0.260
- Excluding 2020: CAGR 10.4%, Sharpe 0.55
- 2021-2023: CAGR 22.5%, Sharpe 0.94

Liquidity stress:
- ADV >=1m: CAGR 10.8%
- ADV >=3m: CAGR -2.3%
- ADV >=10m: CAGR 2.8%

Execution delay:
- t+1: CAGR 10.8%
- t+2: CAGR 11.3%
- t+3: CAGR 10.6%

## Data-quality falsification
Six tickers with >100% one-day moves were excluded entirely in a stress test:
BIOMAXIMA, CFI, FMG, MOLECURE, SUWARY, WINVEST.

The core trend, momentum and momentum+low-vol OOS results were effectively unchanged. The detected extreme moves therefore do not explain the reported strategy edge.

## Portfolio test
Adding momentum+low-vol to trend did not improve the OOS portfolio:
- Trend only: Sharpe ~0.78, MaxDD -33.3%
- 70/30 trend / momentum-low-vol: Sharpe ~0.73, MaxDD -35.0%
- 50/50: Sharpe ~0.69, MaxDD -36.4%

The second strategy does not provide enough diversification to justify the extra complexity in this sample.

## What would change the conclusion?
Trend should be downgraded/rejected if:
- a 2024-2026 forward test is materially negative,
- performance disappears when reliable dividend/corporate-action-adjusted stock returns are used,
- the edge fails under a realistic capital/participation-rate capacity model,
- a broader multiple-testing adjustment materially lowers statistical confidence,
- or future rolling 3Y net Sharpe remains <=0.

No strategy currently qualifies as a ROBUST CANDIDATE under the original strict research standard.
