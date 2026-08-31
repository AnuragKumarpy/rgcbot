from src.services.games_service import GamesService


def test_evaluate_dice_slots_jackpot():
    text, reward = GamesService.evaluate_dice_score("🎰", 64)
    assert reward == 100
    assert "JACKPOT" in text


def test_evaluate_dice_darts_bullseye():
    text, reward = GamesService.evaluate_dice_score("🎯", 6)
    assert reward == 25
    assert "BULLSEYE" in text


def test_evaluate_dice_bowling_strike():
    text, reward = GamesService.evaluate_dice_score("🎳", 6)
    assert reward == 30
    assert "STRIKE" in text


def test_evaluate_standard_dice():
    text, reward = GamesService.evaluate_dice_score("🎲", 6)
    assert reward == 10
    assert "Maximum" in text
