"""Reproducible local verification. No official replay or score is available."""
import copy
import importlib.util
import json
import statistics
import subprocess
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from server import Handler, ThreadingHTTPServer
from strategy import LiquidityBot


def main():
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover('.', pattern='test_strategy.py'))
    if not result.wasSuccessful():
        raise SystemExit(1)
    srv = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{srv.server_port}/decide'
    obs = json.loads(Path('yeno-sample-observation.json').read_text())
    timings = []
    try:
        smoke = subprocess.run([sys.executable, 'yeno-smoke-test.py', '--url', url], capture_output=True, text=True, check=True)
        for _ in range(100):
            request = urllib.request.Request(url, data=json.dumps(obs).encode(), headers={'Content-Type': 'application/json'})
            start = time.perf_counter()
            with urllib.request.urlopen(request, timeout=1) as response:
                decision = json.load(response)
            timings.append((time.perf_counter()-start)*1000)
            assert decision['action'] in {'HOLD', 'SELL', 'BUY'}
        for payload, expected in [(b'[]', 400), (b'{', 400)]:
            try:
                urllib.request.urlopen(urllib.request.Request(url, data=payload), timeout=1)
                raise AssertionError('malformed request accepted')
            except urllib.error.HTTPError as error:
                assert error.code == expected
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(2)
    spec = importlib.util.spec_from_file_location('house', 'yeno-house-bot-v1.py')
    house = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(house)
    comparisons = []
    for name in ('sample', 'future_reference', 'partial_exit'):
        sample = copy.deepcopy(obs)
        if name == 'future_reference':
            sample['reference']['observedAt'] += 10
        if name == 'partial_exit':
            sample['market']['secondsToClose'] = 20
            sample['account']['position'] = dict(market_id=sample['market']['id'], outcome='YES', shares=5, buy_gross_usd=2.5, buy_fees_usd=.1125)
            sample['books']['YES'].update(bids=[[.45, 1]], asks=[])
        comparisons.append(dict(fixture=name, estuary=LiquidityBot().decide(sample), house=house.HouseBot().decide(sample)))
    assert max(timings) < 200, 'local HTTP response exceeded contract budget'
    report = dict(evidenceClass='LOCAL_CONTRACT_AND_SYNTHETIC_BOUNDARIES_ONLY', tests=result.testsRun, passed=True,
                  officialSmoke=json.loads(smoke.stdout), httpRequests=len(timings), httpP50Ms=statistics.median(timings),
                  httpMaxMs=max(timings), fixtureComparison=comparisons,
                  officialReplayAvailable=False, officialScore=None, qualification=None,
                  note='Handcrafted fixtures are not recorded market data, backtests, or competition performance.')
    Path('verification-results.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
