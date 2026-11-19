import copy
import json
import unittest
from pathlib import Path

class StrategyTests(unittest.TestCase):
    def setUp(self):
        self.obs = json.loads(Path('yeno-sample-observation.json').read_text())

    def test_fee_depth_and_cash_constrained_independent_entry(self):
        try:
            from strategy import LiquidityBot
        except ImportError:
            self.fail('Independent LiquidityBot has not been implemented')
        decision = LiquidityBot().decide(copy.deepcopy(self.obs))
        self.assertEqual(decision['action'], 'BUY')
        self.assertEqual(decision['outcome'], 'YES')
        self.assertGreater(decision['maxCashUsd'], 2.6125)
        self.assertLessEqual(decision['maxCashUsd'], 5)

    def test_multilevel_sell_uses_best_bids_first(self):
        from strategy import sweep
        self.assertAlmostEqual(sweep([[.1, 100], [.8, 5]], 5, False), 3.904)

    def test_partial_exit_is_requested_before_expiry_with_bids_only(self):
        from strategy import LiquidityBot
        self.obs['market']['secondsToClose'] = 29
        self.obs['account']['position'] = dict(market_id=self.obs['market']['id'], outcome='YES', shares=9, buy_gross_usd=4.5, buy_fees_usd=.2025, sell_gross_usd=0, sell_fees_usd=0)
        self.obs['books']['YES'].update(asks=[], bids=[[.4, 2]])
        self.assertEqual(LiquidityBot().decide(self.obs), {'action': 'SELL'})

    def test_timestamp_rejections_and_entry_boundaries(self):
        from strategy import LiquidityBot
        for field, value in [('observedAt', self.obs['timestamp']+1), ('observedAt', self.obs['timestamp']-1.501), ('targetObservedAt', self.obs['timestamp']+1), ('targetProvisional', True)]:
            obs = copy.deepcopy(self.obs)
            obs['reference'][field] = value
            self.assertEqual(LiquidityBot().decide(obs), {'action': 'HOLD'})
        for seconds in (0, 15, 45, 241):
            obs = copy.deepcopy(self.obs)
            obs['market']['secondsToClose'] = seconds
            self.assertEqual(LiquidityBot().decide(obs), {'action': 'HOLD'})

    def test_sufficient_minimum_depth_can_trade_when_larger_grid_cannot(self):
        from strategy import LiquidityBot
        self.obs['account']['cashUsd'] = 5.1
        self.obs['reference']['btcMidUsd'] += 500
        self.obs['books']['YES'].update(asks=[[.9, 100]], bids=[[.89, 100]])
        self.assertEqual(LiquidityBot().decide(self.obs)['action'], 'BUY')

    def test_reference_reversal_requests_exit(self):
        from strategy import LiquidityBot
        self.obs['reference']['btcMidUsd'] -= 200
        self.obs['account']['position'] = dict(market_id=self.obs['market']['id'], outcome='YES', shares=5, buy_gross_usd=2.5, buy_fees_usd=.1125)
        self.assertEqual(LiquidityBot().decide(self.obs), {'action': 'SELL'})

    def test_completed_volume_stops_entries(self):
        from strategy import LiquidityBot
        self.obs['account']['eligibleVolumeUsd'] = 1000
        self.assertEqual(LiquidityBot().decide(self.obs), {'action': 'HOLD'})

    def test_online_volatility_reduces_conviction(self):
        from strategy import LiquidityBot
        bot = LiquidityBot()
        for i in range(15):
            obs = copy.deepcopy(self.obs)
            obs['timestamp'] += i
            obs['reference']['observedAt'] = obs['timestamp']
            obs['reference']['btcMidUsd'] += 1000 if i%2 else -1000
            bot.decide(obs)
        obs['reference']['btcMidUsd'] = self.obs['reference']['btcMidUsd']
        self.assertEqual(bot.decide(obs), {'action': 'HOLD'})

    def test_depth_reserve_rejects_thin_bids(self):
        from strategy import LiquidityBot
        self.obs['books']['YES']['bids'] = [[.49, 6]]
        self.assertEqual(LiquidityBot().decide(self.obs), {'action': 'HOLD'})

    def test_cash_cannot_be_lost_at_wide_spread(self):
        from strategy import LiquidityBot
        self.obs['books']['YES']['bids'] = [[.1, 100]]
        self.assertEqual(LiquidityBot().decide(self.obs), {'action': 'HOLD'})

    def test_partial_received_cash_contributes_to_full_cycle_exit(self):
        from strategy import LiquidityBot
        self.obs['account']['position'] = dict(market_id=self.obs['market']['id'], outcome='YES', shares=1, buy_gross_usd=2.5, buy_fees_usd=.1125, sell_gross_usd=2.3, sell_fees_usd=.03)
        self.assertEqual(LiquidityBot().decide(self.obs), {'action': 'SELL'})

    def test_nonfinite_and_malformed_fail_closed(self):
        from strategy import LiquidityBot
        for value in (None, {}, {'timestamp': float('nan')}, {'timestamp': 3}):
            self.assertEqual(LiquidityBot().decide(value), {'action': 'HOLD'})
        self.obs['reference']['btcMidUsd'] = float('inf')
        self.assertEqual(LiquidityBot().decide(self.obs), {'action': 'HOLD'})

    def test_two_cent_stress_applies_on_both_entry_and_exit(self):
        from strategy import LiquidityBot, sweep
        decision = LiquidityBot().decide(self.obs)
        quantity = decision['maxCashUsd']/.5225
        self.assertLessEqual(sweep([[.5, 100]], quantity, True)-sweep([[.49, 100]], quantity, False)+.04*quantity, .80001)

if __name__ == '__main__':
    unittest.main()
