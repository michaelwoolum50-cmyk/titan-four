from titan_four.proof_scan import select_best_candidate


def test_select_best_candidate_finds_the_best_trending_result():
    prices = [
        100.0, 101.0, 103.0, 106.0, 110.0, 116.0, 122.0, 129.0,
        137.0, 145.0, 155.0, 166.0, 178.0, 192.0, 208.0, 226.0,
        245.0, 267.0, 290.0, 315.0,
    ]
    volumes = [150.0] * len(prices)

    best = select_best_candidate(
        prices=prices,
        volumes=volumes,
        buy_grid=[0.01, 0.02, 0.04],
        sell_grid=[-0.01, -0.02, -0.04],
        min_return_grid=[0.005, 0.01, 0.02],
    )

    assert best is not None
    assert best["trades"] >= 0
    assert best["net_return"] > 0.0
    assert best["best_score"] >= best["candidate_score"]
