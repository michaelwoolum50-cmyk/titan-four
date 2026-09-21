class RiskManager:
    def __init__(self, max_position_fraction=0.2, max_positions=3, leverage_allowed=False):
        self.max_position_fraction = max_position_fraction
        self.max_positions = max_positions
        self.leverage_allowed = leverage_allowed

    def can_trade(self):
        return True

    def calculate_position_value(self, account_value, percent_of_account):
        if percent_of_account <= 0:
            return 0.0
        if percent_of_account > self.max_position_fraction:
            percent_of_account = self.max_position_fraction
        return account_value * percent_of_account
