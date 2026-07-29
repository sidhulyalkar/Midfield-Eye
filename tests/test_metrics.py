import numpy as np

from midfielders_eye.metrics import ndcg_at_k, pairwise_ranking_accuracy, recall_at_k


def test_perfect_ranking_metrics():
    truth = np.array([1.0, 0.5, 0.0])
    score = np.array([0.9, 0.5, 0.1])
    assert ndcg_at_k(truth, score, k=3) == 1.0
    assert pairwise_ranking_accuracy(truth, score) == 1.0


def test_recall_at_k():
    available = np.array([True, False, True, False])
    score = np.array([0.8, 0.7, 0.6, 0.1])
    assert recall_at_k(available, score, k=2) == 0.5
