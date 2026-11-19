"""Estuary: independent fee-aware liquidity/continuation policy; paper API only."""
from __future__ import annotations
import math
from collections import deque


def number(value):
    x = float(value)
    if not math.isfinite(x):
        raise ValueError('nonfinite input')
    return x


def levels(rows, reverse=False):
    result = []
    for row in rows:
        p, q = number(row[0]), number(row[1])
        if not 0 < p < 1 or q <= 0:
            raise ValueError('invalid L2 level')
        result.append((p, q))
    return sorted(result, reverse=reverse)


def sweep(book, quantity, buy):
    """Full depth walk; return None if requested quantity cannot fully execute."""
    remaining, gross, crypto = quantity, 0.0, 0.0
    for p, available in levels(book, reverse=not buy):
        q = min(remaining, available)
        gross += p*q
        crypto += .07*q*p*(1-p)
        remaining -= q
        if remaining <= 1e-9:
            break
    if remaining > 1e-9:
        return None
    fees = round(crypto + 1e-12, 5) + round(.01*gross + 1e-12, 5)
    return gross + fees if buy else gross - fees


class LiquidityBot:
    """No order client. Positions and completed volume remain evaluator-owned."""
    def __init__(self):
        self.samples = deque(maxlen=60)

    def decide(self, obs):
        try:
            return self._decide(obs)
        except (KeyError, TypeError, ValueError, IndexError, OverflowError):
            return {'action': 'HOLD'}

    def _decide(self, obs):
        now = number(obs['timestamp'])
        seconds = number(obs['market']['secondsToClose'])
        account = obs['account']
        pos = account.get('position')
        probability_yes = None
        ref = obs.get('reference', {})
        try:
            age = now-number(ref['observedAt'])
            spot, target = number(ref['btcMidUsd']), number(ref['openingTargetUsd'])
            valid = (ref.get('targetProvisional') is False and 0 <= age <= 1.5
                     and number(ref['targetObservedAt']) <= now and min(spot, target) > 0)
            if valid:
                stamp = number(ref['observedAt'])
                if not self.samples or stamp > self.samples[-1][0]:
                    self.samples.append((stamp, spot))
                rates = [(b[1]-a[1])**2/(b[0]-a[0])
                         for a, b in zip(self.samples, list(self.samples)[1:])
                         if .05 <= b[0]-a[0] <= 10]
                sigma = max(12., math.sqrt(sum(rates)/len(rates))) if rates else 12.
                probability_yes = .5*(1+math.erf((spot-target)/(sigma*math.sqrt(max(seconds, 1))*math.sqrt(2))))
        except (KeyError, TypeError, ValueError, OverflowError):
            pass
        if pos is not None:
            book = obs['books'][pos['outcome']]
            bids = levels(book.get('bids', []), reverse=True)
            shares = number(pos['shares'])
            if not bids or shares <= 0:
                return {'action': 'HOLD'}
            received = sweep(bids, shares, False)
            paid = number(pos['buy_gross_usd'])+number(pos['buy_fees_usd'])
            realized = number(pos.get('sell_gross_usd', 0))-number(pos.get('sell_fees_usd', 0))
            # Urgent reduction can partially execute and must not require asks/full depth.
            if seconds <= 30 or str(pos['market_id']) != str(obs['market']['id']):
                return {'action': 'SELL'}
            if received is None:
                return {'action': 'SELL'}
            owned_probability = probability_yes if pos['outcome'] == 'YES' else (1-probability_yes if probability_yes is not None else None)
            if owned_probability is not None and owned_probability < .5:
                return {'action': 'SELL'}
            pnl = realized+received-paid
            if pnl >= 0 or pnl <= -.06*(number(account['cashUsd'])+paid):
                return {'action': 'SELL'}
            return {'action': 'HOLD'}
        if not 45 < seconds <= 240:
            return {'action': 'HOLD'}
        if probability_yes is None or number(account['eligibleVolumeUsd']) >= number(obs['rules']['targetVolumeUsd']):
            return {'action': 'HOLD'}
        pyes = probability_yes
        cash = number(account['cashUsd'])
        cap = min(5., number(obs['rules']['maximumBuyCashUsd']), cash)
        candidates = []
        for side, probability in [('YES', pyes), ('NO', 1-pyes)]:
            book = obs['books'][side]
            asks = levels(book['asks'])
            bids = levels(book['bids'], reverse=True)
            if not asks or not bids or bids[0][0] >= asks[0][0]:
                continue
            minimum = number(book['minOrderSize'])
            if minimum <= 0:
                continue
            # Reserve twice the shares on the bid ladder; never rely on top price alone.
            depth = sum(q for _, q in bids)/2
            if depth < minimum:
                continue
            for step in range(41):
                q = minimum+(depth-minimum)*step/40
                if q < minimum:
                    continue
                paid = sweep(asks, q, True)
                # sweep() preserves input ordering; bids must be explicitly descending.
                received = sweep(bids, q, False)
                if paid is None or received is None or paid > cap-0.000002:
                    continue
                loss = paid-received+.04*q
                edge = probability-paid/q-.02
                if loss <= .08*cash and edge >= .025:
                    candidates.append((edge*q, side, paid))
        if not candidates:
            return {'action': 'HOLD'}
        _, side, paid = max(candidates)
        return {'action': 'BUY', 'outcome': side, 'maxCashUsd': round(paid+0.000001, 6)}
