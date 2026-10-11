# Custom-parts spend review: Laurentide Fabrication

*Sample memo drafted by Claude from `prompts/exec_memo.md` and `output/metrics.json`, then passed through `spend/grounding.py`. Synthetic data.*

**The three plants pay different prices for the same parts. Harmonizing to the best price already achieved inside the company is worth $3.8M (8.3% of the $45.7M analyzed). Closing half of that gap, a conservative target, recovers $1.9M.**

## Findings

- **Montreal carries most of the gap.** It pays $2.3M above the internal benchmark, 11.9% of its spend, against 9.5% in Ontario and 1.9% in Ohio. Ohio's prices are effectively the benchmark the other plants should be measured against.
- **The gap sits with a few supplier relationships.** Montreal's purchases from Saint-Laurent Usinage account for $744K of gap on $3.7M of spend. Boreal Metal Works adds $663K in Ontario and $653K in Montreal.
- **Price spread is widespread, not a few outliers.** 24 of 40 parts show a spread above 10% between the cheapest and most expensive plant and supplier combination. The largest single item, machined bracket LF-0007, carries $406K of gap at a 26% spread.
- **Supply risk is concentrated.** Northshore Plastics holds 30.4% of spend and only delivers on time 82.9% of the time. 16 parts have a single supplier across the company, and the top three suppliers hold 65.5% of spend.
- **One supplier is a delivery problem.** Lakeshore Castings delivers on time 72.5% of the time, and late orders arrive 10.8 days late on average.

## Recommendations

- **Rebid Montreal's machined brackets and Boreal Metal Works contracts at Ohio pricing.** Start with the Saint-Laurent Usinage spend, the largest single pocket of gap.
- **Qualify a second source for Northshore Plastics parts.** It reduces the 30.4% concentration and gives leverage on an 82.9% on-time record.
- **Open a delivery review with Lakeshore Castings** before its next renewal, using the 72.5% on-time rate as the baseline.

**Data basis:** 1,640 purchase-order lines from 3 ERP exports (SAP, Epicor, spreadsheet), 17 supplier spellings resolved to 7 suppliers, 6 lines quarantined for failed quality rules and excluded.
