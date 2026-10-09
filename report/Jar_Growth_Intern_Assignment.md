# Jar — Growth Intern Assignment

Sales analysis · App exploration · Product exploration

Vaibhav Tiwari · 9 October 2026

Code: https://github.com/VT69/Jar---Assignment

## Executive summary

**Categories.** Electronics leads on sales (₹1,65,267, 38.3%) and profit per order (₹51.44). Clothing earns the most profit (₹11,163) at the best margin (8.03%). Furniture trails on every metric (1.81% margin).

**Profit leaks.** Two sub-categories lose money: Tables (-₹4,011) and Electronic Games (-₹1,236). In 16 of 17 sub-categories, loss-making lines realise lower unit prices than profitable ones (median 0.55×) at the same quantity.

**Furniture targets.** The target ramps smoothly (no MoM move above 1.89%), but demand is back-loaded. Furniture missed target 7 months in a row, then beat it in 4 of the last 5 (95.7% for the year). Seasonal phasing cuts monthly error from 54.4% to 27.3% (19.5% in-sample).

**Regions.** Madhya Pradesh and Maharashtra hold 38.2% of orders. Mumbai's margin is 2.65%, against 13.56% in Pune. 4 states lose money (-₹3,642), while Uttar Pradesh, Delhi, West Bengal and Kerala earn 44.2% of profit on 16.8% of sales.

**App (Q2).** The most serious issue is a silent failure: Nominee Details does nothing when tapped from Profile, though it works from a home-screen pop-up. Reward screens such as a spin wheel also interrupt users mid-task. Onboarding, AutoPay saving and buying and selling gold were smooth.

**Product (Q3).** Digital gold sits outside SEBI's oversight industry-wide (advisory, November 2025). Jar can lead the category by setting the disclosure standard and moving its automation onto regulated rails. The first moves are connecting existing goals to Nek redemption and a SEBI-regulated gold ETF/FoF, followed by insured deposits, sachet insurance and partner-led gold credit.

## 1. Data and method {: .cont }

### 1.1 Join validation

Order Details (one row per line item) is **left-joined** to List of Orders on Order ID with pandas `validate="many_to_one"` and an indicator column. Order Details carries the grain of every financial metric. The many-to-one check proves Order ID is unique on the header side, so the join cannot duplicate lines. A hard assertion fails the run on any orphan, instead of letting an inner join drop it silently.

| Check | Result |
|---|---|
| List of Orders rows / unique Order IDs | 500 / 500 |
| Order Details rows / unique Order IDs | 1,500 / 500 |
| Duplicate Order IDs in List of Orders | 0 |
| IDs only in List of Orders / only in Order Details | 0 / 0 |
| Rows after merge | 1,500 (equals line items) |

Orders have 1 to 12 lines, and 207 span more than one category. That is why "per order" and "per line" averages differ.

### 1.2 Date repairs

Spreadsheet auto-conversion corrupted both date fields. Both were repaired in code, with assertions; the raw files are untouched.

- **Order Date.** 307 cells are `dd-mm-yyyy` text. The other 193 were read month-first, so day and month were swapped back. Repaired dates rise monotonically with the sequential Order ID and span 01 Apr 2018 to 31 Mar 2019.
- **Sales Target month.** "Apr-18" had been stored as *18 April of the current year*, so year = 2000 + stored day. The months run April 2018 to March 2019, matching the order period exactly.

### 1.3 Definitions

- **Sales** = sum of `Amount`. **Margin** = sum(Profit) ÷ sum(Amount). **Order count** = distinct Order IDs.
- **Average profit per order (primary)** = group profit ÷ distinct orders containing the group. **Per line item** (secondary) = mean line profit. Both rank the categories identically; per-order values are 1.3×–2.4× higher.
- **Price realisation.** The data has no discount field, so discounting can only be tested indirectly: realised unit price (Amount ÷ Quantity) on loss-making lines is compared with profitable lines in the same sub-category.

### 1.4 Sample size

The dataset is small: 500 orders and 1,500 lines over one year. Several cuts rest on few observations: Tables has 17 lines, Tamil Nadu 8 orders, and Furniture sells 10–32 orders a month. A handful of large lines can move a sub-category, city or month. Category-level findings are robust. Single-city and single-month results are directional and should be confirmed with more data before acting.

## 2. Q1 Part 1 — Sales and profitability {: .cont }

### 2.1 Category scorecard

![Figure 1](../outputs/figures/fig1_category_overview.png)

Figure 1. Category totals: sales, average profit (per order and per line) and margin.
{: .caption}

| Category | Sales | Share of sales | Profit | Share of profit | Profit / order | Profit / line | Margin |
|---|---:|---:|---:|---:|---:|---:|---:|
| Electronics | ₹1,65,267 | 38.3% | ₹10,494 | 43.8% | ₹51.44 | ₹34.07 | 6.35% |
| Clothing | ₹1,39,054 | 32.2% | ₹11,163 | 46.6% | ₹28.40 | ₹11.76 | 8.03% |
| Furniture | ₹1,27,181 | 29.5% | ₹2,298 | 9.6% | ₹12.35 | ₹9.46 | 1.81% |
| **Total** | **₹4,31,502** | 100% | **₹23,955** | 100% | | | **5.55%** |

**Verdict.**

- **Electronics leads on scale and order economics:** #1 on sales and on profit per order.
- **Clothing leads on efficiency:** #1 on total profit and on margin. Its per-line profit (₹11.76) understates it, because its lines are small (unit price ₹39.55). It also appears in 393 of 500 orders, the most of any category.
- **Furniture underperforms:** last on all four metrics.

### 2.2 Why the categories differ

**1. One or two sub-categories hold each category back.**

![Figure 2](../outputs/figures/fig2_subcategory_profit.png)

Figure 2. Profit and margin by sub-category.
{: .caption}

- **Furniture.** Tables lose -₹4,011 on ₹22,614 (-17.7% margin; 64.7% of lines in loss). Chairs barely break even (1.7%). Bookcases earn ₹4,888, which is 213% of Furniture's net profit. Without Tables, the margin would be 6.03%, close to Electronics (6.35%).
- **Electronics.** Electronic Games lose -₹1,236 (-3.2%), and Phones earn 4.8% with 49.4% of lines in loss. Printers (56.8% of category profit) and Accessories (16.4% margin) carry the category. Without Games, the margin would be 9.30%.
- **Clothing.** Sarees are 38.5% of sales at a 0.66% margin. The rest of Clothing earns 12.6%.

**2. Losses are concentrated, most severely in Furniture.**

![Figure 3](../outputs/figures/fig3_loss_concentration.png)

Figure 3. Gross gains from profitable lines vs gross losses from loss-making lines.
{: .caption}

| Category | Lines in loss | Loss ÷ gain | Worst 10 lines' share of losses | Lines losing more than their revenue |
|---|---:|---:|---:|---:|
| Electronics | 39.6% | 61.4% | 41.5% | 3 |
| Clothing | 29.4% | 51.8% | 28.7% | 1 |
| Furniture | 42.0% | 87.1% | 57.6% | 10 |

Furniture's loss-making lines give back ₹15,521 of the ₹17,819 its profitable lines earn. Its worst 10 lines account for 57.6% of those losses.

**3. Loss-making lines realise lower prices, not smaller quantities.**

![Figure 4](../outputs/figures/fig4_price_realisation.png)

Figure 4. Median unit price on loss-making vs profitable lines within each sub-category.
{: .caption}

In 16 of 17 sub-categories, loss-making lines sell at a lower median unit price than profitable ones (median ratio 0.55×; Chairs 0.40×). The exception is Trousers (2.77×), where losses sit on high-ticket lines, which suggests a cost problem. Median quantity is the same on both (3 units), so the losses track **low realised prices**, not volume.

The data cannot say *why* prices are low. Discounting (the same item sold for less) is one hypothesis. **Product mix** is the alternative: cheaper variants within a sub-category may carry thin or negative margins. Separating the two needs SKU-level list prices.

**4. Furniture keeps little profit per unit.** Furniture and Electronics sell at similar unit prices (₹134.58 vs ₹143.21). Furniture keeps ₹2.43 per unit against ₹9.09 for Electronics, so a small price concession tips a Furniture line into loss.

**Actions.**

1. Pull SKU-level list prices to test whether losses are discount-driven or mix-driven.
2. If discount-driven, set price floors on Tables and Chairs and a floor on Saree realised prices. If mix-driven, re-cost or prune the loss-making variants instead.
3. Re-price or delist Electronic Games.

## 3. Q1 Part 2 — Target achievement (Furniture) {: .cont }

### 3.1 Month-over-month change in target

![Figure 5](../outputs/figures/fig5_furniture_target_mom.png)

Figure 5. Furniture monthly target and its month-over-month % change.
{: .caption}

**Fluctuation rule.** A month is flagged when its MoM % lies more than 1.5 standard deviations from the series mean (z-score; threshold 1.78%). As a materiality cross-check, it is also flagged if |MoM| ≥ 5%.

| Month | Target | Change (₹) | MoM % | z-score | Flag (z-rule) |
|---|---:|---:|---:|---:|---|
| Apr 2018 | ₹10,400 | – | – | – |  |
| May 2018 | ₹10,500 | +₹100 | +0.96% | -0.46 |  |
| Jun 2018 | ₹10,600 | +₹100 | +0.95% | -0.48 |  |
| Jul 2018 | ₹10,800 | +₹200 | +1.89% | +1.74 | **Flagged** |
| Aug 2018 | ₹10,900 | +₹100 | +0.93% | -0.55 |  |
| Sep 2018 | ₹11,000 | +₹100 | +0.92% | -0.57 |  |
| Oct 2018 | ₹11,100 | +₹100 | +0.91% | -0.59 |  |
| Nov 2018 | ₹11,300 | +₹200 | +1.80% | +1.54 | **Flagged** |
| Dec 2018 | ₹11,400 | +₹100 | +0.88% | -0.65 |  |
| Jan 2019 | ₹11,500 | +₹100 | +0.88% | -0.66 |  |
| Feb 2019 | ₹11,600 | +₹100 | +0.87% | -0.68 |  |
| Mar 2019 | ₹11,800 | +₹200 | +1.72% | +1.36 |  |

The target rises 13.5% across the year, in steps of ₹100, with ₹200 steps in Jul 2018, Nov 2018 and Mar 2019. The z-rule flags **Jul 2018 and Nov 2018**, with Mar 2019 just under the bar. The materiality rule flags **0 months**. The target's fluctuations are statistically visible but commercially trivial. The problem is a target *too smooth* for a volatile business.

### 3.2 Target vs actual

![Figure 6](../outputs/figures/fig6_furniture_target_vs_actual.png)

Figure 6. Actual Furniture sales vs current and illustrative re-phased target, and monthly attainment.
{: .caption}

- **Annually about right:** ₹1,27,181 achieved against ₹1,32,900 (95.7%).
- **Monthly, phased wrong.** Target was met in only 4 of 12 months. Furniture missed for 7 straight months to Oct 2018 (64.2% attainment, -₹26,936). It then beat target in 4 of the last 5 (136.8%, +₹21,217).
- **H1 over-weighted.** April–September carries 48.3% of the target but only 32.7% of actual sales.
- **Actuals are 12.5× more volatile than the target.** The coefficient of variation is 51.3% for actuals vs 4.1% for the target.
- **Revenue-only targets hide losses.** Furniture lost money in 6 months (-₹9,316 in total).

### 3.3 Aligning targets with performance

1. **Phase by seasonality.** Spread the same ₹1,32,900 across months by each month's share of company-wide sales. The monthly target then ranges from ₹3,993 (Jul 2018) to ₹18,923 (Jan 2019). MAPE falls from 54.4% to 19.5%, and months within ±15% of target rise from 1 to 6.
    - 19.5% is optimistic: company sales include Furniture itself (29.5% of the total), and seasonality comes from the same year. With Clothing and Electronics alone, which excludes Furniture entirely, MAPE is 27.3%, the better estimate. In practice, phase on prior-year or rolling three-year shares.
2. **Add a margin guardrail** (e.g. margin ≥ 0% each month), and tie price approvals on Tables and Chairs to it.
3. **Use a ±15% band and re-forecast quarterly.** With an actual CV of 51%, a point target will be missed almost every month.
4. **Re-balance across categories.** Electronics hit 128.1% of target and Clothing 79.9%. Shift ambition toward demonstrated run-rates.

## 4. Q1 Part 3 — Regional performance {: .cont }

### 4.1 Top 5 states by order count

![Figure 7](../outputs/figures/fig7_top5_states.png)

Figure 7. Top 5 states by distinct orders: order count, total sales and average profit per order.
{: .caption}

| Rank | State | Distinct orders | Total sales | Total profit | Avg profit / order | Avg profit / line | Margin |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | Madhya Pradesh | 101 | ₹1,05,140 | ₹5,551 | ₹54.96 | ₹16.33 | 5.28% |
| 2 | Maharashtra | 90 | ₹95,348 | ₹6,176 | ₹68.62 | ₹21.30 | 6.48% |
| 3 | Rajasthan | 32 | ₹21,149 | ₹1,257 | ₹39.28 | ₹16.99 | 5.94% |
| 4 | Gujarat | 27 | ₹21,058 | ₹465 | ₹17.22 | ₹5.34 | 2.21% |
| 5 | Punjab | 25 | ₹16,786 | -₹609 | -₹24.36 | -₹10.15 | -3.63% |

*Average profit is **per order** (state profit ÷ distinct orders); per-line is shown for reference.* There is no tie at the cut-off: the next states (Delhi, Uttar Pradesh and West Bengal) have 22 orders each. The top 5 hold 55.0% of orders and 60.1% of sales, but only 53.6% of profit.

### 4.2 Regional disparities

![Figure 8](../outputs/figures/fig8_state_share_gap.png)

Figure 8. Each state's share of company profit minus its share of company sales.
{: .caption}

- **Sales-to-profit mismatch.** Madhya Pradesh has 24.4% of sales but 23.2% of profit. Uttar Pradesh, Delhi, West Bengal and Kerala earn 44.2% of profit on 16.8% of sales, a 14.6% margin against 5.55% for the company.
- **Loss-making states, each driven by one category.**
    - Tamil Nadu: -₹2,216, from Furniture.
    - Punjab: -₹609, from Electronics (-₹2,132).
    - Andhra Pradesh: -₹496, from Furniture.
    - Bihar: -₹321, from Electronics.
- **City-level splits.** In Gujarat, Punjab and Rajasthan, one city makes money and the other loses it:

| State | Loss-making city | Sales | Profit | Margin | Profitable city | Margin |
|---|---|---:|---:|---:|---|---:|
| Gujarat | Ahmedabad | ₹14,230 | -₹880 | -6.2% | Surat | 19.7% |
| Punjab | Chandigarh | ₹12,279 | -₹1,153 | -9.4% | Amritsar | 12.1% |
| Rajasthan | Jaipur | ₹10,076 | -₹753 | -7.5% | Udaipur | 18.2% |

![Figure 9](../outputs/figures/fig9_city_margin.png)

Figure 9. City sales vs margin; bubble size is distinct orders.
{: .caption}

### 4.3 Where to focus

| Priority | Where | Why (number) | Lever |
|---|---|---|---|
| 1. Margin repair at scale | **Mumbai** | ₹61,867 at 2.65%; 41.1% of lines in loss vs 28.9% in Pune | Pune's margin would add about ₹6,750; the company average, ₹1,798 |
| 2. Investigate | **Chennai (Tamil Nadu)** | -₹2,216 on ₹6,087 (-36.4%) from only 8 orders | Find what drives the Furniture loss (-₹2,487): pricing, freight or one-off returns. Act once the cause is confirmed |
| 3. Fix loss cities in the top 5 | **Ahmedabad, Chandigarh and Jaipur** | -₹2,786 combined; sister cities earn double-digit margins | Copy the sister city's mix and pricing; for Punjab, start with Electronics |
| 4. Defend the volume base | **Indore, Bhopal** | Indore is 75.2% of Madhya Pradesh sales; Bhopal earns 3.7% | Hold Indore near the company margin; lift Bhopal |
| 5. Grow where profit is easy | **Allahabad, Delhi, Kolkata, Thiruvananthapuram** | 14.6% combined margin on only 82 orders | Spend acquisition budget here first |

*Data note:* 3 orders list city "Delhi" under Madhya Pradesh; they are kept as recorded and change no ranking. Chandigarh appears under both Punjab (16 orders) and Haryana (14).

## 5. Q2 — App exploration

**Test setup.** Hands-on session on a Vivo T2x 5G (6 GB RAM) over Jio 5G. Jar blocks screenshots, a standard security measure in fintech apps, so observations are described rather than shown.

### 5.1 Five things that work well

| # | What I observed | Why it works (UX principle) |
|---|---|---|
| 1 | **Onboarding was simple.** | *Low onboarding friction.* For first-time savers, every step removed before the first saving raises the share who get there. |
| 2 | **Daily savings on AutoPay worked smoothly, and a goals feature exists.** | *Habit loop and default effect.* A one-time mandate replaces a daily decision, so saving runs without willpower. Goals give the habit a purpose. |
| 3 | **Buying and selling gold was smooth.** | *Reversibility lowers perceived risk.* Users commit money more readily when getting it back is easy. |
| 4 | **The payment screen carries a trust line: "100% safe and secure payments".** | *Trust signals in fintech.* Reassurance at the moment of payment is well placed. But it addresses payment security, not where the gold is held. Showing the vault partner (Brink's), trustee (Vistra) and insurer (ICICI Lombard) here would answer the question users actually have. The website names all three, but the insurer appears only in its body text; its "100% Insured" badge does not name it. |
| 5 | **Engagement is strong, with multiple reward mechanics.** | *Variable rewards.* Rewards give users a reason to open the app between savings and reinforce the daily habit. Their cost is covered in 5.2 #2. |

### 5.2 Five areas to improve

| # | What I observed | Why it matters (UX principle) and what to change |
|---|---|---|
| 1 | **Nominee Details is unresponsive from the Profile section.** Tapping it does nothing, with no error or feedback. The same flow works from the home-screen pop-up, so one entry point is broken. This is the most serious finding. | *Visibility of system status; error recovery* (Nielsen). A silent failure leaves users unsure whether anything happened. Here it blocks a basic safeguard for a financial asset, naming who inherits the gold, at the place users expect to find it. Fix the Profile entry point, and give every action that can fail an explicit error state. |
| 2 | **Reward screens interrupt intent.** While I was trying to do something else, a spin wheel appeared first. The multiple reward surfaces also make the app feel cluttered. | *Task completion vs interruption.* Engagement mechanics are competing with what the user came to do. Show rewards after a task is done, not before it, and consolidate them into fewer surfaces. |
| 3 | **Several screens load slowly**, despite a capable device on 5G. | *Perceived performance.* In a money app, slow screens read as unreliability. A capable device on 5G rules out the obvious causes on the user's side, which points to the app. Prioritise the saving and payment flows. |
| 4 | **Visual polish.** Several graphics are blurry, and the loader looks unrefined. | *Aesthetic-usability effect.* Users read polish as care. In a product that holds their money, rough visuals quietly erode trust. |
| 5 | **No global search across features.** | *Information scent and findability.* As the feature set grows (savings, goals, rewards, Nek), features get harder to find. Search would also reduce reliance on home-screen pop-ups to surface them. |

## 6. Q3 — Product exploration

### 6.1 Starting point: Jar's strengths and the category's open gap

Jar's moat is behavioural. It has (i) **automation**: UPI AutoPay mandates across more than 35 million registered users; (ii) **micro-ticket access** at ₹10; (iii) **UX simplicity**, in nine languages, for a base that is about 60% tier-2/3; and (iv) **established credibility with first-time savers**, backed by a vault partner (Brink's) and trustee (Vistra) shown in its website's "Secured by" badge, and an insurer (ICICI Lombard) named in the website's body text.

The category has an open gap that every platform shares. SEBI's advisory of 8 November 2025 noted that digital gold is neither a security nor a regulated commodity derivative, so it sits outside SEBI's oversight. Industry voices have since called for standardised disclosure of storage, fees, redemption and insurance. Jar is best placed to lead here. It already names its custody, insurance and trustee partners on its website, and it has the scale to set a disclosure standard others follow. Leading on transparency in digital gold, while extending its automation onto regulated rails, both deepens Jar's credibility and opens new revenue.

![Figure 10](../outputs/figures/fig10_q3_priority_matrix.png)

Figure 10. Effort vs impact for the five opportunities (analyst-judgement scores, 1–5).
{: .caption}

| Rank | Opportunity | Impact | Effort | Quadrant | Horizon |
|---:|---|---:|---:|---|---|
| 1 | B. Connect savings goals to Nek redemption | 3.5 | 1.0 | Quick win / do now | Now (0-3 months) |
| 2 | A. SEBI-regulated gold ETF / FoF | 4.0 | 2.5 | Quick win / do now | Now (0-6 months) |
| 3 | C. Insured micro-deposits via bank partners | 4.0 | 3.5 | Big bet / sequence | Next (6-12 months) |
| 4 | D. Sachet insurance on the AutoPay rail | 3.5 | 3.5 | Big bet / sequence | Next (9-15 months) |
| 5 | E. Gold-backed micro-credit (partner-led) | 4.5 | 4.5 | Big bet / sequence | Later (gated, 12+ months) |

### 6.2 Opportunity cards

**A. SEBI-regulated gold ETF / fund-of-funds — the defensive priority**

- **What it is.** A SEBI-regulated gold ETF or gold fund-of-funds, held in the user's own name. This is distinct from Jar's existing digital-gold SIP and daily saving, which buy unregulated digital gold.

- **User problem.** Savers who want gold *with* investor protection don't know how to buy an ETF.
- **Why Jar wins.** It already holds the AutoPay mandate and the gold-saving intent. A "Gold+ (SEBI-regulated)" option moves an existing habit rather than acquiring a new customer. Low-ticket mutual-fund SIPs (₹100–500 at many AMCs) fit Jar's micro-ticket DNA.
- **Integration path.** Become a mutual-fund distributor, or partner with a registered platform → add a second "jar" on the home card → route new savings there, with a cost comparison shown.
- **Monetisation.** Distribution trail on regular plans, or a platform fee on direct plans. Lower per-rupee take than the digital-gold spread, but recurring and defensible.
- **Sizing (back-of-envelope).** 35 million is *registered* users, and Jar does not publish its active base, so assume 20% are active savers (70 lakh).
    - *New revenue:* if 10% of active savers (7 lakh) invest ₹500 a month in it, that is about ₹420 crore of regulated inflow in year one. At an indicative 0.3% annual trail, the book earns a year-end run-rate of about ₹1.26 crore a year.
    - *Retention:* FY25 operating revenue of about ₹208 crore works out to roughly ₹297 per active saver a year. If a regulated option cuts annual churn by 2 percentage points, it keeps 1.4 lakh savers and about ₹4.16 crore a year.
    - *Total:* about ₹5.42 crore a year, or 2.6% of FY25 operating revenue.
- **Why impact is 4.0.** The quantified value is material but not the largest on the list. The rest is defensibility: keeping the gold habit, and its AutoPay mandate, inside Jar for savers who want investor protection. That is real but hard to size.
- **Key risk.** Cannibalising the digital-gold spread; distributor conduct rules (suitability, commission disclosure).
- **Success metric.** Share of active savers holding the SEBI-regulated product within 6 months; regulated share of gold AUM.

**B. Connect savings goals to Nek redemption — the quick win**

- **User problem.** Households save for jewellery around weddings, Akshaya Tritiya and Dhanteras, often through jeweller 11-month schemes that lock money to one store.
- **Why Jar wins.** Jar already has a goals feature and its own jewellery brand, Nek. Connecting them turns a completed goal into a purchase the user has been working toward.
- **Integration path.** Goal completion → one-tap Nek purchase, with a making-charge discount for completed goals. Both pieces exist, so the build is the connection, not a new product.
- **Monetisation.** Nek margin and making charges. CAC is lower because the buyer is pre-funded and pre-committed.
- **Sizing (back-of-envelope).** On the same assumed active base (70 lakh), say 5% of active savers (3.5 lakh) save toward a jewellery goal averaging ₹12,000, and 30% complete and redeem at Nek. That gives about 1.1 lakh orders and ₹126 crore of GMV.
    - *Margin:* at an assumed 10% gross margin on jewellery, that is about ₹12.6 crore.
- **Key risk.** Must be framed as accumulation of the user's own gold, not a deposit scheme. Fulfilment quality at Nek.
- **Success metric.** Share of completed goals redeemed at Nek; 12-month retention of goal vs non-goal savers.

**C. Insured micro-deposits via bank partners**

- **User problem.** First-time savers want a safe, fixed-return home for emergency money, and bank FDs feel out of reach.
- **Why Jar wins.** The same mandate rail can sweep daily ₹10s into an RD or FD at partner small finance banks. Jar already works with Unity Small Finance Bank for UPI. DICGC insurance up to ₹5 lakh per depositor per bank is a regulated trust anchor Jar can explain simply.
- **Integration path.** Bank-partner FD/RD marketplace → a "safe jar" next to the gold jar → auto-split rules (e.g., 70% gold, 30% deposit).
- **Monetisation.** Distribution fee from partner banks; cross-sell lift.
- **Key risk.** Partner concentration; outsourcing and KYC obligations; keeping deposit messaging separate from gold.
- **Success metric.** Deposit balance per active saver; share of savers holding both gold and a deposit.

**D. Sachet insurance on the AutoPay rail**

- **User problem.** Tier-2/3 and gig workers are under-insured. Annual premiums feel large; ₹2–5 a day does not.
- **Why Jar wins.** Daily auto-debit is exactly how sachet premiums need to be collected, and Jar's plain-language style suits explaining cover.
- **Integration path.** IRDAI corporate-agent licence or broker partner → add-on toggles (personal accident, hospital cash) when a saving streak is set up.
- **Monetisation.** Commission within IRDAI expense limits.
- **Key risk.** Mis-selling or claim rejections would erode the core trust asset.
- **Success metric.** Attach rate; claim turnaround; 13-month persistency.

**E. Gold-backed micro-credit (partner-led) — gated**

- **User problem.** Small emergencies are funded by informal lenders, or by selling gold at a bad moment.
- **Why Jar wins.** The collateral is already vaulted and valued daily, so a small loan needs no branch visit or assayer.
- **Integration path.** Jar as lending service provider to an RBI-regulated bank or NBFC → "borrow instead of sell" offered on the sell screen.
- **Monetisation.** Sourcing fee or revenue share on disbursals.
- **Key risk.** The highest regulatory load of the five: digital-lending and gold-loan rules, plus the open question of pledging *digital* gold as collateral. Start only after the regulated rails (A, C) are live.
- **Success metric.** Loans per 1,000 active savers; 90+ day delinquency; share of borrowers who keep saving.

**Deprioritised.** Digital silver (same regulatory exposure, little new value); B2B payroll saving (long sales cycles).

### 6.3 Sequenced roadmap

| Horizon | Moves | Milestone |
|---|---|---|
| 0–6 months | B (goals → Nek) and A (SEBI-regulated gold ETF/FoF); publish a digital-gold disclosure standard | Regulated product live; first goal cohorts redeemed at Nek |
| 6–15 months | C (insured deposits), then D (sachet insurance) | Majority of new savings on regulated or insured rails |
| 12+ months, gated | E (gold-backed credit) via a regulated partner | Clean compliance; delinquency within plan |

### 6.4 Sources (Section 6)

TechCrunch, "Indian fintech Jar turns profitable by helping millions save in gold", 18 Sep 2025: users, tier-2/3 share, languages. · Entrackr, "Jar clocks Rs 208 Cr operating revenue in FY25, turns profitable in H2", 19 Sep 2025: FY25 operating revenue. · Jar website (myjar.app): Brink's (vault) and Vistra (trustee) in the "Secured by" badge; ICICI Lombard named as insurer in body text, not on the "100% Insured" badge. Accessed Oct 2026. · Inc42, "India's Digital Gold Rush Gets Regulatory Reality Check", 12 Nov 2025; Groww explainer: SEBI advisory of 8 Nov 2025 and calls for standardised disclosure. · Entrackr: Jar enters UPI payments through BharatPe and Unity Small Finance Bank, 2025.
{: .small}

## Appendix A — Assumptions log

| # | Assumption | Why | Effect if wrong |
|---|---|---|---|
| A1 | Order Date datetime cells have day and month swapped; text cells are `dd-mm-yyyy` | Only reading that makes dates monotonic in sequential Order ID | Part 2 monthly actuals would shift months |
| A2 | Sales Target "day" component encodes the year (18 → 2018) | Months then run Apr-2018 to Mar-2019, exactly the order period | No overlap for target-vs-actual |
| A3 | Target values are monthly *sales* (Amount) targets in ₹ | Same order of magnitude as monthly category sales | Attainment metrics would not apply |
| A4 | "Average profit per order" = profit ÷ distinct orders containing the group | Matches the brief's wording; per-line reported alongside | Magnitudes change; rankings do not |
| A5 | Lower realised unit price on loss lines may reflect discounting (hypothesis) | No discount column exists | Product mix explains the same pattern; loss concentration still holds |
| A6 | 3 "Delhi, Madhya Pradesh" orders kept as recorded | Brief analyses the State field | Madhya Pradesh loses 3 orders; still #1 |
| A7 | Re-phased target uses same-year, company-wide seasonality, which includes Furniture | Only one year of data | MAPE gain is an upper bound; ex-Furniture sensitivity: 27.3% |
| A8 | Q3 impact/effort scores and sizing inputs are analyst judgement, including a 20% active share of registered users and a 10% jewellery gross margin | Jar does not publish active users or unit economics | Sizes scale linearly with the active share; ranking is a starting point for discussion |

## Appendix B — Detail tables

**B1. Sub-category performance**

| Category | Sub-category | Sales | Profit | Margin | Lines | Orders | Loss lines | Profit / line |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Clothing | Trousers | ₹30,039 | ₹2,847 | 9.5% | 39 | 37 | 38.5% | ₹73.00 |
| Clothing | Stole | ₹18,546 | ₹2,559 | 13.8% | 192 | 157 | 27.1% | ₹13.33 |
| Clothing | Hankerchief | ₹14,608 | ₹2,098 | 14.4% | 198 | 138 | 21.2% | ₹10.60 |
| Clothing | T-shirt | ₹7,382 | ₹1,500 | 20.3% | 77 | 70 | 15.6% | ₹19.48 |
| Clothing | Shirt | ₹7,555 | ₹1,131 | 15.0% | 69 | 66 | 17.4% | ₹16.39 |
| Clothing | Saree | ₹53,511 | ₹352 | 0.7% | 210 | 156 | 46.7% | ₹1.68 |
| Clothing | Leggings | ₹2,106 | ₹260 | 12.3% | 53 | 49 | 30.2% | ₹4.91 |
| Clothing | Skirt | ₹1,946 | ₹235 | 12.1% | 64 | 56 | 28.1% | ₹3.67 |
| Clothing | Kurti | ₹3,361 | ₹181 | 5.4% | 47 | 41 | 29.8% | ₹3.85 |
| Electronics | Printers | ₹58,252 | ₹5,964 | 10.2% | 74 | 67 | 33.8% | ₹80.59 |
| Electronics | Accessories | ₹21,728 | ₹3,559 | 16.4% | 72 | 65 | 22.2% | ₹49.43 |
| Electronics | Phones | ₹46,119 | ₹2,207 | 4.8% | 83 | 71 | 49.4% | ₹26.59 |
| Electronics | Electronic Games | ₹39,168 | -₹1,236 | -3.2% | 79 | 73 | 50.6% | -₹15.65 |
| Furniture | Bookcases | ₹56,861 | ₹4,888 | 8.6% | 79 | 72 | 27.8% | ₹61.87 |
| Furniture | Furnishings | ₹13,484 | ₹844 | 6.3% | 73 | 66 | 41.1% | ₹11.56 |
| Furniture | Chairs | ₹34,222 | ₹577 | 1.7% | 74 | 64 | 52.7% | ₹7.80 |
| Furniture | Tables | ₹22,614 | -₹4,011 | -17.7% | 17 | 16 | 64.7% | -₹235.94 |

**B2. Furniture: target vs actual by month**

| Month | Target | Actual | Gap | Attainment | Furniture profit | Re-phased target |
|---|---:|---:|---:|---:|---:|---:|
| Apr 2018 | ₹10,400 | ₹8,121 | -₹2,279 | 78.1% | -₹3,425 | ₹10,079 |
| May 2018 | ₹10,500 | ₹6,220 | -₹4,280 | 59.2% | -₹794 | ₹8,792 |
| Jun 2018 | ₹10,600 | ₹5,532 | -₹5,068 | 52.2% | -₹856 | ₹7,287 |
| Jul 2018 | ₹10,800 | ₹3,483 | -₹7,317 | 32.2% | -₹457 | ₹3,993 |
| Aug 2018 | ₹10,900 | ₹9,538 | -₹1,362 | 87.5% | ₹443 | ₹9,517 |
| Sep 2018 | ₹11,000 | ₹8,704 | -₹2,296 | 79.1% | -₹2,468 | ₹8,201 |
| Oct 2018 | ₹11,100 | ₹6,766 | -₹4,334 | 61.0% | -₹1,316 | ₹9,737 |
| Nov 2018 | ₹11,300 | ₹15,165 | ₹3,865 | 134.2% | ₹3,945 | ₹14,810 |
| Dec 2018 | ₹11,400 | ₹9,474 | -₹1,926 | 83.1% | ₹187 | ₹11,574 |
| Jan 2019 | ₹11,500 | ₹21,257 | ₹9,757 | 184.8% | ₹3,284 | ₹18,923 |
| Feb 2019 | ₹11,600 | ₹16,262 | ₹4,662 | 140.2% | ₹2,168 | ₹11,834 |
| Mar 2019 | ₹11,800 | ₹16,659 | ₹4,859 | 141.2% | ₹1,587 | ₹18,152 |

**B3. All states**

| Rank | State | Orders | Sales | Profit | Margin | Profit / order | Sales share | Profit share |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | Madhya Pradesh | 101 | ₹1,05,140 | ₹5,551 | 5.3% | ₹54.96 | 24.4% | 23.2% |
| 2 | Maharashtra | 90 | ₹95,348 | ₹6,176 | 6.5% | ₹68.62 | 22.1% | 25.8% |
| 3 | Rajasthan | 32 | ₹21,149 | ₹1,257 | 5.9% | ₹39.28 | 4.9% | 5.2% |
| 4 | Gujarat | 27 | ₹21,058 | ₹465 | 2.2% | ₹17.22 | 4.9% | 1.9% |
| 5 | Punjab | 25 | ₹16,786 | -₹609 | -3.6% | -₹24.36 | 3.9% | -2.5% |
| 6 | Delhi | 22 | ₹22,531 | ₹2,987 | 13.3% | ₹135.77 | 5.2% | 12.5% |
| 7 | Uttar Pradesh | 22 | ₹22,359 | ₹3,237 | 14.5% | ₹147.14 | 5.2% | 13.5% |
| 8 | West Bengal | 22 | ₹14,086 | ₹2,500 | 17.7% | ₹113.64 | 3.3% | 10.4% |
| 9 | Karnataka | 21 | ₹15,058 | ₹645 | 4.3% | ₹30.71 | 3.5% | 2.7% |
| 10 | Kerala | 16 | ₹13,459 | ₹1,871 | 13.9% | ₹116.94 | 3.1% | 7.8% |
| 11 | Bihar | 16 | ₹12,943 | -₹321 | -2.5% | -₹20.06 | 3.0% | -1.3% |
| 12 | Andhra Pradesh | 15 | ₹13,256 | -₹496 | -3.7% | -₹33.07 | 3.1% | -2.1% |
| 13 | Nagaland | 15 | ₹11,903 | ₹148 | 1.2% | ₹9.87 | 2.8% | 0.6% |
| 14 | Jammu and Kashmir | 14 | ₹10,829 | ₹8 | 0.1% | ₹0.57 | 2.5% | 0.0% |
| 15 | Haryana | 14 | ₹8,863 | ₹1,325 | 14.9% | ₹94.64 | 2.1% | 5.5% |
| 16 | Himachal Pradesh | 14 | ₹8,666 | ₹656 | 7.6% | ₹46.86 | 2.0% | 2.7% |
| 17 | Goa | 14 | ₹6,705 | ₹370 | 5.5% | ₹26.43 | 1.6% | 1.5% |
| 18 | Sikkim | 12 | ₹5,276 | ₹401 | 7.6% | ₹33.42 | 1.2% | 1.7% |
| 19 | Tamil Nadu | 8 | ₹6,087 | -₹2,216 | -36.4% | -₹277.00 | 1.4% | -9.3% |

**B4. Cities in the top-5 and loss-making states**

| State | City | Orders | Sales | Profit | Margin | Share of state sales | Loss lines |
|---|---|---:|---:|---:|---:|---:|---:|
| Andhra Pradesh | Hyderabad | 15 | ₹13,256 | -₹496 | -3.7% | 100.0% | 26.2% |
| Bihar | Patna | 16 | ₹12,943 | -₹321 | -2.5% | 100.0% | 38.7% |
| Gujarat | Ahmedabad | 17 | ₹14,230 | -₹880 | -6.2% | 67.6% | 40.3% |
| Gujarat | Surat | 10 | ₹6,828 | ₹1,345 | 19.7% | 32.4% | 8.0% |
| Madhya Pradesh | Indore | 76 | ₹79,069 | ₹4,159 | 5.3% | 75.2% | 36.0% |
| Madhya Pradesh | Bhopal | 22 | ₹23,583 | ₹871 | 3.7% | 22.4% | 39.4% |
| Madhya Pradesh | Delhi | 3 | ₹2,488 | ₹521 | 20.9% | 2.4% | 0.0% |
| Maharashtra | Mumbai | 68 | ₹61,867 | ₹1,637 | 2.6% | 64.9% | 41.1% |
| Maharashtra | Pune | 22 | ₹33,481 | ₹4,539 | 13.6% | 35.1% | 28.9% |
| Punjab | Chandigarh | 16 | ₹12,279 | -₹1,153 | -9.4% | 73.2% | 42.2% |
| Punjab | Amritsar | 9 | ₹4,507 | ₹544 | 12.1% | 26.8% | 13.3% |
| Rajasthan | Udaipur | 13 | ₹11,073 | ₹2,010 | 18.2% | 52.4% | 10.0% |
| Rajasthan | Jaipur | 19 | ₹10,076 | -₹753 | -7.5% | 47.6% | 27.3% |
| Tamil Nadu | Chennai | 8 | ₹6,087 | -₹2,216 | -36.4% | 100.0% | 40.0% |

## Appendix C — Reproducibility

- **Run:** `python main.py`. This regenerates every table in `outputs/tables/`, every figure in `outputs/figures/`, `outputs/report_numbers.json`, the report Markdown and HTML in `report/`, and this PDF. Every number in this report is injected from `report_numbers.json`, and the build fails on any unresolved placeholder or broken claim. The Q1 analysis is also walked through step by step in `Q1_Sales_Analysis.ipynb`.
- **Environment:** Python 3.12.1; pandas 3.0.6; matplotlib 3.11.2; PDF rendered by headless Chromium.
- **Data:** raw Excel files in `data/` are read-only; all repairs happen in memory (Section 1.2).
