import logging
from typing import Tuple, List, Dict
from datetime import datetime, date

logger = logging.getLogger(__name__)


class RiskManager:
    """Advanced risk management for trading"""
    
    def __init__(self, config: dict):
        risk_config = config.get("risk_management", {})
        
        self.max_position_size = risk_config.get("max_position_size_usd", 10000)
        self.max_daily_loss = risk_config.get("max_daily_loss_usd", 2000)
        self.risk_per_trade_percent = risk_config.get("risk_per_trade_percent", 2.0)
        self.stop_loss_atr_multiple = risk_config.get("stop_loss_atr_multiple", 2.0)
        self.take_profit_ratio = risk_config.get("take_profit_ratio", 2.5)
        self.max_concurrent_trades = risk_config.get("max_concurrent_trades", 3)
        self.daily_loss_limit_enabled = risk_config.get("daily_loss_limit_enabled", True)
        
        self.daily_pnl = 0.0
        self.daily_trades = []
        self.today = date.today()
        self.peak_balance = 0.0
    
    def reset_daily_if_needed(self) -> bool:
        """Reset daily stats if new day"""
        today = date.today()
        if today != self.today:
            self.daily_pnl = 0.0
            self.daily_trades = []
            self.today = today
            logger.info(f"Daily stats reset for {today}")
            return True
        return False
    
    def check_daily_loss_limit(self) -> bool:
        """Check if daily loss limit exceeded"""
        if not self.daily_loss_limit_enabled:
            return False
        
        if self.daily_pnl <= -self.max_daily_loss:
            logger.warning(f"Daily loss limit exceeded: {self.daily_pnl:.2f}")
            return True
        return False
    
    def calculate_position_size(self, entry_price: float, stop_loss_price: float,
                               account_balance: float) -> float:
        """
        Calculate position size based on risk management rules
        
        Risk per trade = Account balance * Risk percentage
        Position size = Risk amount / (Entry price - Stop loss price)
        """
        if entry_price <= 0 or stop_loss_price <= 0:
            return 0.0
        
        risk_amount = account_balance * (self.risk_per_trade_percent / 100)
        risk_per_ounce = abs(entry_price - stop_loss_price)
        
        if risk_per_ounce <= 0:
            return 0.0
        
        position_ounces = risk_amount / risk_per_ounce
        position_value_usd = position_ounces * entry_price
        
        # Cap at maximum position size
        if position_value_usd > self.max_position_size:
            position_ounces = self.max_position_size / entry_price
        
        logger.info(f"Position size calculated: {position_ounces:.3f} oz (${position_value_usd:.2f})")
        return position_ounces
    
    def calculate_stop_loss_take_profit(self, entry_price: float, direction: str,
                                       atr_value: float) -> Tuple[float, float]:
        """
        Calculate stop loss and take profit based on ATR
        
        Args:
            entry_price: Entry price
            direction: BUY or SELL
            atr_value: Average True Range value
        
        Returns:
            Tuple of (stop_loss_price, take_profit_price)
        """
        stop_distance = atr_value * self.stop_loss_atr_multiple
        
        if direction.upper() == "BUY":
            stop_loss = entry_price - stop_distance
            take_profit = entry_price + (stop_distance * self.take_profit_ratio)
        else:  # SELL
            stop_loss = entry_price + stop_distance
            take_profit = entry_price - (stop_distance * self.take_profit_ratio)
        
        logger.info(f"{direction} SL: ${stop_loss:.2f}, TP: ${take_profit:.2f}")
        return stop_loss, take_profit
    
    def can_open_trade(self, current_open_trades: int) -> Tuple[bool, str]:
        """
        Check if a new trade can be opened
        
        Returns:
            Tuple of (can_trade: bool, reason: str)
        """
        if self.check_daily_loss_limit():
            return False, "Daily loss limit reached"
        
        if current_open_trades >= self.max_concurrent_trades:
            return False, f"Max concurrent trades reached ({self.max_concurrent_trades})"
        
        return True, "OK"
    
    def update_daily_pnl(self, pnl_usd: float, was_winning: bool):
        """Update daily P&L tracking"""
        self.daily_pnl += pnl_usd
        self.daily_trades.append({
            'pnl': pnl_usd,
            'winning': was_winning,
            'time': datetime.now()
        })
        logger.info(f"Daily P&L updated: {self.daily_pnl:+.2f}")
    
    def get_daily_stats(self) -> Dict:
        """Get daily trading statistics"""
        if len(self.daily_trades) == 0:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_pnl': 0.0
            }
        
        winning_trades = sum(1 for t in self.daily_trades if t['winning'])
        losing_trades = len(self.daily_trades) - winning_trades
        win_rate = (winning_trades / len(self.daily_trades) * 100) if len(self.daily_trades) > 0 else 0
        avg_pnl = self.daily_pnl / len(self.daily_trades) if len(self.daily_trades) > 0 else 0
        
        return {
            'total_trades': len(self.daily_trades),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': self.daily_pnl,
            'avg_pnl': avg_pnl
        }
    
    def update_peak_balance(self, current_balance: float):
        """Update peak balance for drawdown calculation"""
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
    
    def calculate_drawdown(self, current_balance: float) -> float:
        """Calculate current drawdown percentage"""
        if self.peak_balance <= 0:
            return 0.0
        
        drawdown = ((self.peak_balance - current_balance) / self.peak_balance) * 100
        return max(0, drawdown)
    
    def get_risk_metrics(self) -> Dict:
        """Get overall risk metrics"""
        return {
            'max_position_size': self.max_position_size,
            'max_daily_loss': self.max_daily_loss,
            'risk_per_trade_percent': self.risk_per_trade_percent,
            'max_concurrent_trades': self.max_concurrent_trades,
            'stop_loss_atr_multiple': self.stop_loss_atr_multiple,
            'take_profit_ratio': self.take_profit_ratio
        }
