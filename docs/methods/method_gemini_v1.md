# PROFESSIONAL MLB HANDICAPPING METHODOLOGY

## 1. DATA PRIORITIZATION (WHAT I WEIGH & DISTRUST)
*   **Distrust:** Raw ERA, L10 team records, and L10 Runs Scored. These metrics are lagging, highly volatile, and over-weighted by the public. 
*   **Weigh:** Pitcher aggregate SIERA, xFIP, and Stuff+; platoon-specific offense wRC+; and bullpen fresh-arm availability. 
*   **Contextual Modifiers:** 3-year park factors and wind velocity. 

## 2. THE THREE-PILLAR PROJECTION MODEL
My model projects an expected run margin (ERM) by calculating team performance across three game phases:

*   **Phase 1: Starting Pitching (50%):** I establish a baseline ERA projection using a 70/30 blend of aggregate SIERA and xFIP. This is adjusted using the opponent’s split-specific wRC+ and hard-hit percentage (HH%). L14 metrics are used strictly as a trend-check; if L14 SIERA is >1.50 runs worse than aggregate SIERA, I apply a 10% penalty to the baseline projection.
*   **Phase 2: Bullpen Bridge (30%):** I calculate a "fatigued bullpen ERA." If $\le 1$ high-leverage arm is fresh, or if key setup/closers are taxed (30+ pitches last 2 days), I inflate the bullpen's season ERA by 1.50 runs. If $\ge 2$ high-leverage arms are fresh, I use the season average.
*   **Phase 3: Park & Environment (20%):** I scale the raw projected runs using the 3-year park factors. If wind exceeds 10 mph blowing out, I scale the home run factor up by 1.2% per mph.

## 3. PROBABILITY CONVERSION & EDGE GATE
To convert the projected runs scored ($RS$) and runs allowed ($RA$) into a win probability, I use the Pythagorean expectation formula:

$$\text{Win Probability} = \frac{RS^{1.83}}{RS^{1.83} + RA^{1.83}}$$

I convert the best available market price to an implied probability (minus the vig). The difference determines our play:
*   **Gap $\ge$ 7.0 pts (Clean Data):** 3 units (Max Play).
*   **Gap 4.0 to 6.9 pts:** 1 unit.
*   **Gap < 4.0 pts:** PASS / LEAN.

## 4. STRICT PASS TRIGGERS
I immediately pass, demote, or hold under these conditions:
*   **TBD Starter:** Absolute PASS.
*   **Starter flagged [small sample]:** Cap the maximum stake at 1 unit (no 3-unit plays allowed).
*   **Price flagged suspect/stale:** Disregard that specific market; pass unless alternative clean books are available.
*   **Coors Field or high-wind environments ($>$15 mph):** Pass on all total/run line markets due to extreme variance; limit exposure to Moneyline only if the edge gate is met.