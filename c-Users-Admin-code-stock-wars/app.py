import random
import threading
import time
import json
import os
import copy
from collections import deque
from functools import wraps
from flask import Flask, render_template, session, redirect, url_for, request, jsonify, flash

print("DEBUG: Loading app.py - VERSION: MARKET_SELECTION_AND_EFFECTS_V2_AUDIO_FIX")

# ============================================================================
# CONFIGURATION
# ============================================================================

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Force Upgrade HTTP to HTTPS only if behind a proxy like ngrok
@app.before_request
def upgrade_protocol():
    if request.headers.get("X-Forwarded-Proto") == "https":
        request.environ["wsgi.url_scheme"] = "https"

@app.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:;"
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    return response

# Game Constants
STARTING_NET_WORTH = 100000
TICK_INTERVAL = 1
MAX_GAME_TICKS = 300
USERS_DB_FILE = 'users.json'

# ============================================================================
# MARKET DEFINITIONS
# ============================================================================

MARKETS = [
    {"id": "blue_chip", "name": "Blue Chip Stable", "description": "Low volatility, steady trends. Good for beginners.", "volatility": "low", "volatility_label": "Low", "bias": "Neutral", "risk_level": "Low"},
    {"id": "tech_sector", "name": "Tech Sector", "description": "Moderate volatility with occasional spikes.", "volatility": "medium", "volatility_label": "Medium", "bias": "Bullish", "risk_level": "Medium"},
    {"id": "crypto_exchange", "name": "Crypto Exchange", "description": "High volatility, rapid crashes and pumps.", "volatility": "high", "volatility_label": "High", "bias": "Volatile", "risk_level": "High"},
    {"id": "penny_stocks", "name": "Penny Stocks", "description": "Extreme manipulation and illiquidity.", "volatility": "extreme", "volatility_label": "Extreme", "bias": "Manipulation", "risk_level": "Extreme"},
    {"id": "forex_market", "name": "Forex Market", "description": "High leverage, fast reversals.", "volatility": "fast", "volatility_label": "Fast", "bias": "Cyclical", "risk_level": "High"},
    {"id": "commodities", "name": "Commodities Futures", "description": "Trend-heavy, susceptible to shocks.", "volatility": "trend", "volatility_label": "Trend", "bias": "Bearish", "risk_level": "Medium"}
]

# ============================================================================
# ROGUE TRADER DATA
# ============================================================================

ROGUE_BOSSES = [
    {"id": "boss_1", "name": "Mr. X", "title": "Sector Bubble", "ability_desc": "Hypetrain (x2 Volatility)", "token_id": "token_tech_wave", "token_name": "Tech-Wave", "volatility": "high_velocity", "ability_id": "hypetrain", "image": "Mr_X.true.png",
     "theme": {"bg": "linear-gradient(135deg, #000428 0%, #004e92 100%)", "accent": "#00d2ff", "panel_bg": "rgba(0, 10, 30, 0.9)", "border": "#00d2ff", "text": "#e2e8f0"}},
    {"id": "boss_2", "name": "Ben Dover", "title": "Forex Black Market", "ability_desc": "Devaluation (-10% Cash)", "token_id": "token_foreign_exchange", "token_name": "Foreign Exchange", "volatility": "crash_risk", "ability_id": "devaluation", "image": "BenDover.true.png",
     "theme": {"bg": "linear-gradient(to bottom, #000000, #434343)", "accent": "#859398", "panel_bg": "rgba(20, 20, 20, 0.95)", "border": "#303030", "text": "#94a3b8"}},
    {"id": "boss_3", "name": "Goldfinger", "title": "Precious Metals", "ability_desc": "Hoarding (Block Buy)", "token_id": "token_golden_reserve", "token_name": "Golden Reserve", "volatility": "low_volatility", "ability_id": "hoarding", "image": "GoldFinger.true.png",
     "theme": {"bg": "linear-gradient(to bottom, #504000, #1a1200)", "accent": "#ffd700", "panel_bg": "rgba(40, 30, 0, 0.9)", "border": "#daa520", "text": "#fef3c7", "btn_bg": "linear-gradient(to bottom, #ffd700, #b8860b)"}},
    {"id": "boss_4", "name": "Sheik Shaker", "title": "Energy Futures", "ability_desc": "Oil Spill (Double Pump/Dump)", "token_id": "token_oil_futures", "token_name": "Oil Futures", "volatility": "spikes", "ability_id": "oil_spill", "image": "SheikShaker.true.png",
     "theme": {"bg": "linear-gradient(to bottom, #1a0b00, #000000)", "accent": "#ff4500", "panel_bg": "rgba(20, 5, 0, 0.9)", "border": "#ff8c00", "text": "#ffedd5"}},
    {"id": "boss_5", "name": "Baron Von BustMargin", "title": "Junk Bonds", "ability_desc": "Margin Call (Force Sell)", "token_id": "token_debt_note", "token_name": "Debt Note", "volatility": "extreme", "ability_id": "margin_call", "image": "BaronVonBust.true.png",
     "theme": {"bg": "repeating-linear-gradient(45deg, #2b1111, #2b1111 10px, #1a0505 10px, #1a0505 20px)", "accent": "#ff0000", "panel_bg": "rgba(40, 10, 10, 0.9)", "border": "#8b0000", "text": "#fca5a5"}},
    {"id": "boss_6", "name": "Mister Real Estate", "title": "Global Real Estate", "ability_desc": "Zoning Freeze (Block Abilities)", "token_id": "token_land_title", "token_name": "Land Title", "volatility": "illiquid", "ability_id": "zoning_freeze", "image": "Mister_Real_Estate.true.png",
     "theme": {"bg": "linear-gradient(135deg, #065f46 0%, #022c22 100%)", "accent": "#34d399", "panel_bg": "rgba(6, 78, 59, 0.9)", "border": "#10b981", "text": "#ecfdf5"}},
    {"id": "final_boss", "name": "The Bear-on of Wall Street", "title": "The Pit", "ability_desc": "All Boss Abilities", "token_id": "token_victory", "token_name": "Victory", "volatility": "chaos", "ability_id": "final_form", "image": "WallStreetBoss.true.png",
     "theme": {"bg": "radial-gradient(circle at center, #7f1d1d 0%, #000 100%)", "accent": "#ef4444", "panel_bg": "rgba(0,0,0,0.8)", "border": "#ef4444", "text": "#fff"}},
    # --- CHAPTER 3: THE GLOBAL BLACKOUT ---
    {"id": "boss_ch3_sovereign", "name": "\"Senator\" Sovereign", "title": "The Sovereign Wealth Fund", "ability_desc": "Debt Default: Halves the opponent's available capital (cash) for the next 3 ticks in both markets.", "token_id": "emblem_sovereign", "token_name": "👑 Sovereign Emblem", "volatility": "systemic", "ability_id": "debt_default", "image": "senator_1_chapter3.png", "theme_name": "Global Debt & Currencies (Forex vs. Government Bonds)",
     "theme": {"bg": "linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)", "accent": "#fbbf24", "panel_bg": "rgba(26, 26, 46, 0.9)", "border": "#fbbf24", "text": "#fef3c7"}},
    {"id": "boss_ch3_regulator", "name": "\"The Regulator\" Rhonda", "title": "The Central Clearing House", "ability_desc": "Margin Contraction: Instantly halves the opponent's Stock Held position in both markets, but forces the sale at 90% of the current price.", "token_id": "emblem_clearing", "token_name": "🔑 Clearing Emblem", "volatility": "systemic", "ability_id": "margin_contraction", "image": "Rhonda_2_chapter3.png", "theme_name": "Systemic Liquidity (High-Volume Tech vs. Mid-Cap Industrials)",
     "theme": {"bg": "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)", "accent": "#60a5fa", "panel_bg": "rgba(15, 23, 42, 0.9)", "border": "#60a5fa", "text": "#e0e7ff"}},
    {"id": "boss_ch3_moody", "name": "\"Moody\" Mitch", "title": "The Credit Rating Agency", "ability_desc": "Panic Sell: Forces the opponent to sell all shares in their highest-PnL asset at a 5% penalty.", "token_id": "emblem_rating", "token_name": "⭐ Rating Emblem", "volatility": "systemic", "ability_id": "panic_sell", "image": "moodyMitch_3_chapter3.png", "theme_name": "Fear & Sentiment (VIX/Volatility Index vs. Precious Metals)",
     "theme": {"bg": "linear-gradient(135deg, #1e1b4b 0%, #312e81 100%)", "accent": "#a78bfa", "panel_bg": "rgba(30, 27, 75, 0.9)", "border": "#a78bfa", "text": "#ede9fe"}},
    {"id": "boss_ch3_phantom", "name": "\"The Phantom\" Pascal", "title": "The Shadow Bank Network", "ability_desc": "Flash Freeze (Systemic): Blocks ALL trades (but not abilities) for both traders for the next 2 ticks in both markets.", "token_id": "emblem_phantom", "token_name": "👻 Phantom Emblem", "volatility": "systemic", "ability_id": "flash_freeze_systemic", "image": "phantomPascal_4_chapter3.png", "theme_name": "Untraceable Assets (Crypto vs. Rare Earths)",
     "theme": {"bg": "linear-gradient(135deg, #000000 0%, #1a1a1a 100%)", "accent": "#94a3b8", "panel_bg": "rgba(0, 0, 0, 0.9)", "border": "#94a3b8", "text": "#f1f5f9"}}
]

# --- CHAPTER 2: SYNDICATE WARS ---

SYNDICATES = [
    {"id": "syn_locusts", "name": "The Liquidity Locusts", "theme": "High-Frequency Trading", "desc": "Best-of-5. Extreme speed & volatility.", "boss_name": "\"Zero-Latency\" Zeta", "token_id": "emblem_hft", "token_name": "High-Frequency Emblem", "match_type": "bo5", "volatility": "hft", "image": "1.png"}, # Placeholder image
    {"id": "syn_bears", "name": "The Bear Market Brotherhood", "theme": "Short-Selling", "desc": "Best-of-3. Downward bias. Short Seller unlocked.", "boss_name": "\"The Negative\" Nate", "token_id": "emblem_bear", "token_name": "Bear Market Emblem", "match_type": "bo3", "volatility": "bearish", "image": "2.png"},
    {"id": "syn_hostile", "name": "The Hostile Takeovers", "theme": "Mergers & Acquisitions", "desc": "Best-of-7. Momentum buffs on wins.", "boss_name": "\"The Merger\" Maxwell", "token_id": "emblem_hostile", "token_name": "Hostile Takeover Emblem", "match_type": "bo7", "volatility": "momentum", "image": "3.png"},
    {"id": "syn_tax", "name": "The Tax Havens", "theme": "Offshore Accounts", "desc": "Best-of-5. Persistent tax on transactions.", "boss_name": "\"Cayman\" Carlos", "token_id": "emblem_tax", "token_name": "Tax Haven Emblem", "match_type": "bo5", "volatility": "taxed", "image": "4.png"}
]

MERCENARIES = [
    {"id": "merc_whale", "name": "Big Whale Billy", "cost": 50000, "token_req": "token_oil_futures", "desc": "Specialist in market manipulation.", "abilities": ["pump", "dump", "market_maker"], "passive": "Whale Watch: +10% to Pump effects."},
    {"id": "merc_shark", "name": "Shark Tank Sarah", "cost": 50000, "token_req": "token_debt_note", "desc": "Aggressive opponent disruption.", "abilities": ["flash_freeze", "audit", "smoke_screen"], "passive": "Blood in Water: Opponent cooldowns +2s."},
    {"id": "merc_insider", "name": "Insider Ivan", "cost": 50000, "token_req": "token_tech_wave", "desc": "Information is power.", "abilities": ["volume_spy", "rumor", "the_oracle"], "passive": "Wiretap: See opponent cash always."},
    {"id": "merc_algo", "name": "Algo-Bot 9000", "cost": 100000, "token_req": "token_victory", "desc": "Cold, calculated trading.", "abilities": ["trend_lines", "stop_loss_shield", "leverage_x10"], "passive": "Zero Latency: Abilities have -2s cooldown."}
]

SYNDICATE_LEGENDARIES = [
    {"id": "emblem_hft", "name": "High-Frequency Emblem", "desc": "Proof of conquering the Locusts."},
    {"id": "emblem_bear", "name": "Bear Market Emblem", "desc": "Proof of conquering the Brotherhood."},
    {"id": "emblem_hostile", "name": "Hostile Takeover Emblem", "desc": "Proof of conquering the Takeovers."},
    {"id": "emblem_tax", "name": "Tax Haven Emblem", "desc": "Proof of conquering the Havens."}
]

ROGUE_LEGENDARIES = [
    {"id": "quantum_leap", "name": "The Quantum Leap", "description": "Teleports stock price to 10s high.", "cost": 350000, "token_req_id": "token_tech_wave", "token_req_name": "Tech-Wave", "behavior_type": "legendary_rogue", "cooldown": 30},
    {"id": "audit_immunity", "name": "Audit Immunity", "description": "Fee waiver & immunity to devaluation.", "cost": 350000, "token_req_id": "token_foreign_exchange", "token_req_name": "Foreign Exchange", "behavior_type": "legendary_rogue", "cooldown": 30},
    {"id": "vulture_fund", "name": "Vulture Fund", "description": "Liquidates opponent stock to your cash.", "cost": 350000, "token_req_id": "token_debt_note", "token_req_name": "Debt Note", "behavior_type": "legendary_rogue", "cooldown": 30}
]

# ============================================================================
# GLOBAL STATE
# ============================================================================

GAMES = {} # Keys: "single_player" or "ROOM_CODE" or "rogue_USEREMAIL"
QUICK_MATCH_QUEUE = [] # List of user emails waiting for quick match
game_state_lock = threading.Lock()
market_thread_running = False
market_thread = None

# ============================================================================
# DATA DEFINITIONS
# ============================================================================

ALL_POSSIBLE_ABILITIES = [
    # --- Common (15s CD) ---
    {"id": "trend_lines", "name": "Trend Lines", "type": "common", "behavior_type": "passive", "hotkey": "Passive", "cost": 5000, "cooldown": 15, "function": "Buy button flashes green if next ticks will be good (price rising), sell button flashes red if bad (price falling) for 7 ticks. Tick = 1 second of match time.", "rarity": "Common", "description": "Visual guidance on buy/sell timing. Green = good time to buy, Red = good time to sell."},
    {"id": "fee_waiver", "name": "Fee Waiver", "type": "common", "behavior_type": "passive", "hotkey": "Passive", "cost": 8000, "cooldown": 15, "function": "Removes all base trading commissions for the match.", "rarity": "Common", "description": "Removes trading fees."},
    {"id": "stop_loss_shield", "name": "Stop-Loss Shield", "type": "common", "behavior_type": "passive", "hotkey": "Passive", "cost": 5000, "cooldown": 15, "function": "Auto-sells position if PnL drops below -5% of investment.", "rarity": "Common", "description": "Auto-sells on loss."},
    # --- Rare (20s CD) ---
    {"id": "volume_spy", "name": "Volume Spy", "type": "rare", "behavior_type": "insider", "hotkey": "Q", "cost": 20000, "cooldown": 20, "function": "Shows a text box revealing one of your opponent's abilities. Can only be used once per round. Ability = special power your opponent can use. Round = one complete match.", "rarity": "Rare", "description": "Reveals opponent ability. Shows ability name, rarity, and description in a text box."},
    {"id": "rumor", "name": "The Rumor", "type": "rare", "behavior_type": "passive", "hotkey": "Passive", "cost": 15000, "cooldown": 20, "function": "Cancels the ability the opponent was going to use and puts it on cooldown. Ability = special power. Cooldown = time before ability can be used again. Use to disrupt opponent's strategy.", "rarity": "Rare", "description": "Cancels opponent's next ability. Prevents them from using their planned ability and forces them to wait."},
    {"id": "smoke_screen", "name": "Smoke Screen", "type": "rare", "behavior_type": "shark", "hotkey": "W", "cost": 10000, "cooldown": 15, "function": "Hides the price chart from the opponent for 7 ticks. Opponent cannot see price movements during this time. Tick = 1 second of match time.", "rarity": "Rare", "description": "Hides chart from opponent. Chart = the visual graph showing stock price over time."},
    {"id": "pump", "name": "The Pump", "type": "rare", "behavior_type": "whale", "hotkey": "Q", "cost": 20000, "cooldown": 20, "function": "Instantly raises the current market price by +2.5%. Price = the current value of one share of stock. Market = the trading environment where stocks are bought and sold.", "rarity": "Rare", "description": "Instantly increase stock price significantly. Use when you own stock to increase its value."},
    {"id": "dump", "name": "The Dump", "type": "rare", "behavior_type": "whale", "hotkey": "W", "cost": 20000, "cooldown": 20, "function": "Instantly lowers the current market price by -2.5%. Price = the current value of one share of stock. Market = the trading environment where stocks are bought and sold.", "rarity": "Rare", "description": "Instantly decrease stock price significantly. Use before buying to get stock cheaper, or if opponent owns stock to hurt them."},
    {"id": "short_seller", "name": "Short Seller", "type": "rare", "behavior_type": "market_manipulation", "hotkey": "Passive", "cost": 35000, "cooldown": 30, "function": "Remains active until player sells, then goes on 30 tick cooldown. Shorting = betting the price will go down. When active, selling stock when price is high and buying back when low makes profit. Tick = 1 second of match time.", "rarity": "Rare", "description": "Toggle shorting mode. Shorting = profit when price falls instead of rises."},
    {"id": "flash_freeze", "name": "Flash Freeze", "type": "rare", "behavior_type": "shark", "hotkey": "R", "cost": 25000, "cooldown": 20, "function": "Blocks the opponent's ability to sell for the next 4 ticks.", "rarity": "Rare", "description": "Blocks opponent's selling."},
    {"id": "fake_out", "name": "Fake Out", "type": "rare", "behavior_type": "shark", "hotkey": "F", "cost": 30000, "cooldown": 25, "function": "Applies a temporary -2% volatility drop to opponent's PnL view. Lasts 7, 10, or 14 ticks (random). PnL = Profit and Loss, your score. Volatility = how much price moves. Tick = 1 second of match time.", "rarity": "Rare", "description": "Psychological attack on opponent PnL. Makes opponent think they're losing more than they are."},
    {"id": "news_flash", "name": "News Flash", "type": "rare", "behavior_type": "manipulation", "hotkey": "N", "cost": 45000, "cooldown": 15, "function": "Forces strong trend bias for 11 ticks. Trend = the direction price is moving (up or down). Bias = makes price more likely to move in your favor. Tick = 1 second of match time.", "rarity": "Rare", "description": "Forces market trend to favor you. Use when you own stock to push price up, or before buying to get better entry."},
    {"id": "leverage_x10", "name": "Leverage x10", "type": "rare", "behavior_type": "manipulation", "hotkey": "L", "cost": 50000, "cooldown": 30, "function": "Multiplies PnL changes by 10x for 8 ticks. PnL = Profit and Loss, your score. Leverage = amplifies gains and losses. Tick = 1 second of match time.", "rarity": "Rare", "description": "High risk, high reward leverage. 10x means if you gain $100, you get $1000, but losses are also 10x bigger."},
    {"id": "audit", "name": "Audit", "type": "rare", "behavior_type": "shark", "hotkey": "A", "cost": 50000, "cooldown": 30, "function": "Forces opponent to pay 6% commission for 10 ticks. Commission = trading fee. 6% means opponent loses 6% of trade value on every buy/sell. Tick = 1 second of match time.", "rarity": "Rare", "description": "Imposes fees on opponent. Makes opponent's trades cost more, reducing their profit."},
    {"id": "frozen_time", "name": "Frozen Time", "type": "rare", "behavior_type": "defensive", "hotkey": "Z", "cost": 40000, "cooldown": 20, "function": "Resets your capital/position to before your last trade. Capital = your cash. Position = your stock holdings. Trade = buying or selling stock.", "rarity": "Rare", "description": "Undo last trade. Use if you made a bad trade and want to revert it."},
    {"id": "bailout", "name": "Bailout", "type": "epic", "behavior_type": "defensive", "hotkey": "B", "cost": 25000, "cooldown": 25, "function": "Injects $10,000 if Net Worth < $90,000.", "rarity": "Epic", "description": "Emergency cash injection."},
    # --- Epic (25s CD) ---
    {"id": "golden_parachute", "name": "Golden Parachute", "type": "epic", "behavior_type": "hedge_fund", "hotkey": "Passive", "cost": 75000, "cooldown": 25, "function": "Restores 25% of losses if net worth drops below 50%.", "rarity": "Epic", "description": "Protects from large losses."},
    # --- Legendary (30s CD) ---
    {"id": "market_maker", "name": "Market Maker", "type": "legendary", "behavior_type": "legendary", "hotkey": "M", "cost": 250000, "cooldown": 30, "function": "Manually sets trend bias to favor your position.", "rarity": "Legendary", "description": "Control the market trend."},
    {"id": "the_oracle", "name": "The Oracle", "type": "legendary", "behavior_type": "legendary", "hotkey": "O", "cost": 150000, "cooldown": 60, "function": "Shows a text box telling you when to buy then sell for 1 trade. Trade = buying then selling stock. Follow the guidance for guaranteed profit on that one trade. Cooldown = 60 ticks (1 minute).", "rarity": "Legendary", "description": "Perfect trade timing guidance. Shows exact tick numbers to buy and sell for maximum profit."},
    {"id": "server_crash", "name": "Server Crash", "type": "legendary", "behavior_type": "legendary", "hotkey": "X", "cost": 200000, "cooldown": 45, "function": "Liquidates opponent's position and freezes them for 15 ticks. Liquidate = forces sale of all stock at current price. Freeze = blocks all actions. Position = opponent's stock holdings. Tick = 1 second of match time.", "rarity": "Legendary", "description": "Total opponent disruption. Removes opponent's stock and prevents them from trading."},
    {"id": "insurance_policy", "name": "Insurance Policy", "type": "legendary", "behavior_type": "passive", "hotkey": "Passive", "cost": 200000, "cooldown": 0, "function": "Can only be used once per match. Retains that round's wager if you lose.", "rarity": "Legendary", "description": "Protects your wager once per match."},
    # --- ROGUE LEGENDARIES ---
    *ROGUE_LEGENDARIES,
    # --- CHAPTER 3: GLOBAL BLACKOUT LEGENDARIES ---
    {"id": "black_swan", "name": "The Black Swan", "type": "legendary", "behavior_type": "legendary_systemic", "hotkey": "S", "cost": 250000, "cooldown": 35, "function": "System Destabilization: Instantly causes a random, extreme spike or collapse (5x Pump/Dump) for 4 ticks. Spike = price goes way up. Collapse = price goes way down. 5x means 5 times stronger than normal Pump/Dump. Tick = 1 second of match time.", "rarity": "Legendary", "description": "System Destabilization: Extreme market shock. Creates massive unpredictable price movement.", "token_req_id": "emblem_sovereign", "token_req_name": "Sovereign Emblem", "token_req_id2": "token_debt_note", "token_req_name2": "Debt Note"},
    {"id": "quantum_arbitrage", "name": "Quantum Arbitrage", "type": "legendary", "behavior_type": "legendary_systemic", "hotkey": "Q", "cost": 250000, "cooldown": 30, "function": "HFT Counter: Execute Buy and Sell in the same tick for 5 ticks.", "rarity": "Legendary", "description": "HFT Counter: Dual actions per tick.", "token_req_id": "emblem_clearing", "token_req_name": "Clearing Emblem", "token_req_id2": "emblem_hft", "token_req_name2": "High-Frequency Emblem"},
    {"id": "global_hedge", "name": "Global Hedge", "type": "legendary", "behavior_type": "legendary_passive", "hotkey": "Passive", "cost": 250000, "cooldown": 0, "function": "Loss Protection: If PnL drops below -$10,000, automatically restores 50% of that loss once per match.", "rarity": "Legendary", "description": "Loss Protection: Auto-recovery from major losses.", "token_req_id": "emblem_rating", "token_req_name": "Rating Emblem", "token_req_id2": "token_golden_reserve", "token_req_name2": "Golden Reserve"},
    {"id": "system_collapse", "name": "The System Collapse", "type": "legendary", "behavior_type": "legendary_systemic", "hotkey": "C", "cost": 250000, "cooldown": 30, "function": "The Ultimate Lockout: Removes opponent's ability to use Whale or Shark abilities for 5 ticks.", "rarity": "Legendary", "description": "The Ultimate Lockout: Total market control.", "token_req_id": "emblem_phantom", "token_req_name": "Phantom Emblem", "token_req_id2": "emblem_hostile", "token_req_name2": "Hostile Takeover Emblem"}
]

ALL_POSSIBLE_ITEMS = [
    {"id": "neon_banner_kit", "name": "Neon Banner Kit", "category": "Cosmetic", "cost": 5000, "function": "Unlocks custom color schemes.", "rarity": "Common"},
    {"id": "market_monitor", "name": "Market Monitor", "category": "Tool", "cost": 30000, "function": "Provides volatility notifications.", "rarity": "Rare"},
    {"id": "golden_bull_statue", "name": "Golden Bull Statue", "category": "Cosmetic", "cost": 40000, "function": "Unlocks the Flex button.", "rarity": "Rare"},
    {"id": "sector_analyst", "name": "Sector Analyst", "category": "Tool", "cost": 75000, "function": "Provides a guaranteed favorable rumor.", "rarity": "Epic"},
    {"id": "bot_blocker", "name": "Bot Blocker", "category": "Tool", "cost": 150000, "function": "Increases opponent cooldowns.", "rarity": "Epic"},
    {"id": "trading_coach", "name": "Trading Coach", "category": "Tool", "cost": 500000, "function": "Increases Net Worth floor.", "rarity": "Legendary"}
]

# ============================================================================
# DATA PERSISTENCE (MULTI-USER)
# ============================================================================

import uuid

def generate_player_id():
    """Generate a unique 8-character player ID"""
    return str(uuid.uuid4())[:8].upper()

def get_default_player_data(username="Player"):
    return {
        "username": username,
        "player_id": generate_player_id(),
        "net_worth": STARTING_NET_WORTH,
        "owned_abilities": [
            {"id": "pump", "name": "The Pump", "type": "whale", "behavior_type": "whale", "hotkey": "Q", "cost": 30000, "cooldown": 15, "function": "Raises price.", "rarity": "Rare", "description": "Raises price."},
            {"id": "dump", "name": "The Dump", "type": "whale", "behavior_type": "whale", "hotkey": "W", "cost": 30000, "cooldown": 15, "function": "Lowers price.", "rarity": "Rare", "description": "Lowers price."},
            {"id": "rumor", "name": "The Rumor", "type": "insider", "behavior_type": "insider", "hotkey": "E", "cost": 20000, "cooldown": 15, "function": "Reveals trend.", "rarity": "Rare", "description": "Reveals trend."}
        ],
        "wins": 0,
        "losses": 0,
        "match_history": [],  # List of multiplayer matches: [{"result": "win"/"loss", "opponent_username": "...", "opponent_id": "...", "timestamp": ...}, ...]
        "owned_items": [],
        "rogue_run": {
            "active": False,
            "hearts": 4,
            "tokens": [],
            "defeated_bosses": []
        },
        "syndicate_data": {
            "active": False,
            "recruited_mercs": [],
            "emblems": [],
            "current_tournament": None # {id, wins, losses, history: []}
        },
        "loan": {
            "active": False,
            "amount": 0,
            "matches_remaining": 0,
            "interest_rate": 0.0
        },
        "friends": [],
        "friend_requests_sent": [],  # Player IDs of requests you sent
        "friend_requests_received": [],  # Player IDs of requests you received
        "first_signin_welcome_played": False,
        "first_loss_welcome_played": False,
        "loans_received": [],  # Loans from friends
        "loans_given": [],  # Loans given to friends
        "founding_trader": {
            "tier": None,  # 1-5 or None
            "badge": None,
            "frame": None,
            "soundtrack": None,
            "trading_buddy_enabled": False,
            "systemic_risk_mode_enabled": False,
            "title": None,  # "Market Menace" for tier 4+
            "narrator_line": None,  # Custom narrator line/joke for tier 4+
            "unique_ending_unlocked": False  # For tier 5
        }
    }

def load_all_users():
    if os.path.exists(USERS_DB_FILE):
        try:
            with open(USERS_DB_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_all_users(users_data):
    with open(USERS_DB_FILE, 'w') as f:
        json.dump(users_data, f, indent=4)

def load_player_data():
    """Loads data for the currently logged-in user."""
    email = session.get('user_email')
    users = load_all_users()
    
    if email and email in users:
        data = users[email]['data']
        # Merge with full abilities definitions
        if 'owned_abilities' in data:
            full_abilities = []
            for owned in data['owned_abilities']:
                defn = next((a for a in ALL_POSSIBLE_ABILITIES if a['id'] == owned['id']), None)
                if defn: full_abilities.append({**defn, **owned})
                else: full_abilities.append(owned)
            data['owned_abilities'] = full_abilities
        
        # Ensure rogue_run exists (migration)
        if 'rogue_run' not in data:
            data['rogue_run'] = {"active": False, "hearts": 4, "tokens": [], "defeated_bosses": []}
        
        # Ensure syndicate_data exists (migration)
        if 'syndicate_data' not in data:
            data['syndicate_data'] = {"active": False, "recruited_mercs": [], "emblems": [], "current_tournament": None}
            
        # Ensure loan exists (migration)
        if 'loan' not in data:
            data['loan'] = {"active": False, "amount": 0, "matches_remaining": 0, "interest_rate": 0.0}
        
        # Ensure loans_received and loans_given exist (migration)
        if 'loans_received' not in data:
            data['loans_received'] = []
        if 'loans_given' not in data:
            data['loans_given'] = []
        
        # Ensure founding_trader exists (migration)
        if 'founding_trader' not in data:
            data['founding_trader'] = {
                "tier": None,
                "badge": None,
                "frame": None,
                "soundtrack": None,
                "trading_buddy_enabled": False,
                "systemic_risk_mode_enabled": False,
                "title": None,
                "narrator_line": None,
                "unique_ending_unlocked": False
            }
        
        return data
        
    return get_default_player_data("Guest")

def save_player_data(data):
    """Saves data for the currently logged-in user."""
    email = session.get('user_email')
    if not email: return # Don't save guest data persistently
    
    users = load_all_users()
    if email in users:
        users[email]['data'] = data
        save_all_users(users)

# ============================================================================
# DECORATORS
# ============================================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def is_admin_user():
    """Check if current user is admin"""
    return session.get('user_email') == 'rennelldenton2495@gmail.com'

# ============================================================================
# GAME CLASSES & LOGIC
# ============================================================================

class Ability:
    def __init__(self, id, name, hotkey, cost, description, rarity, behavior_type=None, cooldown=0, function="", **kwargs):
        self.id = id
        self.name = name
        self.hotkey = hotkey
        self.cost = cost
        self.description = description
        self.rarity = rarity
        self.behavior_type = behavior_type
        self.cooldown = cooldown
        self.function = function

    def to_dict(self): return self.__dict__

class Trader:
    def __init__(self, name, is_ai=False, initial_capital=STARTING_NET_WORTH):
        self.name = name
        self.is_ai = is_ai
        self.capital = initial_capital
        self.stock_held = 0
        self.match_pnl = 0.0
        self.abilities_equipped = []
        self.abilities_cooldown = {}
        self.game_log = deque(maxlen=10)
        self.commission_multiplier = 0.0
        self.leverage = 1.0
        self.history = deque(maxlen=10)
        self.pnl_spoof_factor = 0.0

    def to_dict(self):
        return {
            "name": self.name,
            "is_ai": self.is_ai,
            "capital": self.capital,
            "stock_held": self.stock_held,
            "match_pnl": self.match_pnl,
            "abilities_equipped": [a.to_dict() if hasattr(a, 'to_dict') else a for a in self.abilities_equipped],
            "abilities_cooldown": self.abilities_cooldown,
            "game_log": list(self.game_log)
        }

    @staticmethod
    def from_dict(data):
        t = Trader(data['name'], data['is_ai'], data['capital'])
        t.stock_held = data['stock_held']
        t.match_pnl = data['match_pnl']
        t.abilities_equipped = [Ability(**a) for a in data['abilities_equipped']]
        t.abilities_cooldown = data['abilities_cooldown']
        t.game_log = deque(data['game_log'], maxlen=10)
        return t

    def add_log(self, text, game_state_ref=None):
        tick = game_state_ref['current_tick'] if game_state_ref else 0
        self.game_log.append(f"Tick {tick}: {text}")

    def buy_stock(self, quantity, price, game_state_ref=None):
        if game_state_ref is None:
            return False
        cost = quantity * price * (1 + self.commission_multiplier)
        # Check for AI-specific buy blocks
        cant_buy_key = 'ai_bot_cant_buy' if self.is_ai else 'player_cant_buy'
        if self.capital >= cost and not game_state_ref['market_info'].get(cant_buy_key):
            self.capital -= cost
            self.stock_held += quantity
            self.add_log(f"Bought {quantity} @ ${price:.2f}", game_state_ref)
            return True
        if not self.is_ai:  # Only log failures for player
            self.add_log("Buy failed (Funds/Blocked)", game_state_ref)
        return False

    def sell_stock(self, quantity, price, game_state_ref=None):
        if game_state_ref is None:
            return False
        # Check for AI-specific sell blocks
        cant_sell_key = 'ai_bot_cant_sell' if self.is_ai else 'player_cant_sell'
        if self.stock_held >= quantity and not game_state_ref['market_info'].get(cant_sell_key):
            # Save snapshot for Frozen Time
            player_key = "player" if not self.is_ai else "ai_bot"
            old_snapshot = game_state_ref['market_info'].get('last_trade_snapshot', {})
            game_state_ref['market_info']['last_trade_snapshot'] = {
                'capital': old_snapshot.get('capital', self.capital),
                'stock_held': old_snapshot.get('stock_held', self.stock_held)
            }
            
            revenue = quantity * price * (1 - self.commission_multiplier)
            self.capital += revenue
            self.stock_held -= quantity
            
            # Check if short seller was active - deactivate and trigger cooldown
            if game_state_ref['market_info'].get(f"{player_key}_short_active", False):
                game_state_ref['market_info'][f"{player_key}_short_active"] = False
                # Find short_seller ability and put on cooldown
                for ab in self.abilities_equipped:
                    if ab.id == 'short_seller':
                        self.abilities_cooldown['short_seller'] = 30
                        break
            
            self.add_log(f"Sold {quantity} @ ${price:.2f}", game_state_ref)
            return True
        if not self.is_ai:  # Only log failures for player
            self.add_log("Sell failed (Stock)", game_state_ref)
        return False

    def use_ability(self, ability_id, game_state_ref):
        ability = next((a for a in self.abilities_equipped if a.id == ability_id), None)
        if not ability: return False
        
        if self.abilities_cooldown.get(ability_id, 0) > 0:
            self.add_log(f"{ability.name} on cooldown", game_state_ref)
            return False

        # System Collapse: Block Whale/Shark abilities
        if game_state_ref['market_info'].get('system_collapse_ticks', 0) > 0:
            if ability.behavior_type in ['whale', 'shark']:
                opp_key = "ai_bot" if self.name == game_state_ref['player']['name'] else "player"
                if opp_key == "ai_bot":  # Only block if opponent used System Collapse
                    self.add_log(f"{ability.name} blocked by System Collapse!", game_state_ref)
                    return False

        handler = ABILITY_HANDLERS.get(ability.behavior_type)
        if handler:
            success, msg = handler(self, ability, game_state_ref, game_state_ref['current_stock_price'])
            if success:
                self.abilities_cooldown[ability_id] = ability.cooldown
                self.add_log(f"Used {ability.name}", game_state_ref)
            return success
        return False

    def calculate_pnl(self, current_price):
        current_val = self.capital + (self.stock_held * current_price)
        raw_pnl = current_val - STARTING_NET_WORTH
        self.match_pnl = (raw_pnl * self.leverage) * (1.0 + self.pnl_spoof_factor)
        return self.match_pnl
        
    def snapshot(self): return {"capital": self.capital, "stock_held": self.stock_held}

# --- Simplified Ability Handlers ---
def _handle_whale(t, a, gs, p):
    mult = 2.0 if any(x.id == 'market_maker' for x in t.abilities_equipped) else 1.0
    if a.id == 'pump': 
        gs['current_stock_price'] *= (1 + (0.025 * mult))  # Changed from 0.015 to 0.025 (2.5%)
        gs['market_info']['pump_effect'] = 2 # Visual effect
    if a.id == 'dump': 
        gs['current_stock_price'] *= (1 - (0.025 * mult))  # Changed from 0.015 to 0.025 (2.5%)
        gs['market_info']['dump_effect'] = 2 # Visual effect
    gs['game_log'].append(f"Market: {a.name} used by {t.name}!")
    return True, "Used"

def _handle_insider(t, a, gs, p):
    if a.id == 'volume_spy':
        # Check if already used this round
        player_key = "player" if t.name == gs['player']['name'] else "ai_bot"
        if gs['market_info'].get(f"{player_key}_volume_spy_used", False):
            t.add_log("Volume Spy already used this round", gs)
            return False, "Already used"
        
        # Target the OTHER player
        # If caster is player (p1), target ai_bot (p2). If caster is ai_bot (p2), target player (p1).
        # Note: In multiplayer, 'ai_bot' key holds the Guest data.
        target_key = "ai_bot" if t.name == gs['player']['name'] else "player"
        opp_data = gs[target_key]
        
        opp_abilities = [x for x in opp_data['abilities_equipped']]
        
        reveal = None
        if opp_abilities:
            chosen_ability = random.choice(opp_abilities)
            reveal = chosen_ability.get('name', chosen_ability.get('id', 'Unknown'))
            # Store revealed ability info for frontend display
            gs['market_info'][f"{player_key}_volume_spy_reveal"] = {
                'name': reveal,
                'description': chosen_ability.get('description', ''),
                'rarity': chosen_ability.get('rarity', 'Unknown')
            }
        
        # Mark as used for this round
        gs['market_info'][f"{player_key}_volume_spy_used"] = True
        gs['game_log'].append(f"🔍 {t.name} used Volume Spy - Revealed opponent ability!")
        t.add_log(f"Spy: Opponent has {reveal or 'No abilities'}", gs)
        return True, "Used"
    if a.id == 'rumor':
        # Cancel opponent's next ability and put it on cooldown
        opp_key = "ai_bot" if t.name == gs['player']['name'] else "player"
        opp_data = gs[opp_key]
        
        # Get opponent's next queued ability or random ability
        if gs.get('ai_action_queue') and opp_key == 'ai_bot':
            # Check if there's a queued ability action
            for act, val in list(gs['ai_action_queue']):
                if act == 'ability':
                    # Cancel this ability and put on cooldown
                    opp_data['abilities_cooldown'][val] = 30  # Put on cooldown
                    gs['ai_action_queue'] = deque([x for x in gs['ai_action_queue'] if x != (act, val)], maxlen=100)
                    gs['game_log'].append(f"📢 {t.name} used Rumor - Cancelled opponent's {val}!")
                    return True, "Used"
        elif gs.get('player_action_queue') and opp_key == 'player':
            for act, val in list(gs['player_action_queue']):
                if act == 'ability':
                    opp_data['abilities_cooldown'][val] = 30
                    gs['player_action_queue'] = deque([x for x in gs['player_action_queue'] if x != (act, val)], maxlen=100)
                    gs['game_log'].append(f"📢 {t.name} used Rumor - Cancelled opponent's {val}!")
                    return True, "Used"
        
        # If no queued ability, cancel a random one
        opp_abilities = [x['id'] for x in opp_data['abilities_equipped']]
        if opp_abilities:
            cancelled = random.choice(opp_abilities)
            opp_data['abilities_cooldown'][cancelled] = 30
            gs['game_log'].append(f"📢 {t.name} used Rumor - Cancelled opponent's {cancelled}!")
    return True, "Used"

def _handle_shark(t, a, gs, p):
    # Determine Opponent Key
    opp_key = "ai_bot" if t.name == gs['player']['name'] else "player"
    
    if a.id == "smoke_screen": 
        gs['market_info'][f"{opp_key}_chart_hidden"] = 7  # Hide chart for 7 seconds
        gs['game_log'].append(f"💨 {t.name} used Smoke Screen - Chart hidden!")
    if a.id == "flash_freeze": gs['market_info'][f"{opp_key}_cant_sell"] = 10 # 10 seconds freeze
    if a.id == "audit": 
        gs['market_info'][f"{opp_key}_audit"] = 10  # 10 seconds at 6% (will be handled in market loop)
        gs['market_info'][f"{opp_key}_audit_rate"] = 0.06  # 6% commission
        gs['game_log'].append(f"📋 {t.name} used Audit - 6% commission for 10 seconds!")
    if a.id == "fake_out":
        # Random duration: 7, 10, or 14 seconds
        duration = random.choice([7, 10, 14])
        gs['market_info'][f"{opp_key}_fake_out"] = duration
        gs['game_log'].append(f"🎭 {t.name} used Fake Out - PnL view distorted for {duration}s!")
    gs['game_log'].append(f"{t.name} used {a.name}!")
    return True, "Used"

def _handle_legendary_rogue(t, a, gs, p):
    opp_key = "ai_bot" if t.name == gs['player']['name'] else "player"
    if a.id == "quantum_leap":
        recent = gs['price_history'][-10:]
        highest = max((x['price'] for x in recent), default=p)
        gs['current_stock_price'] = highest
        gs['game_log'].append(f"{t.name} QUANTUM LEAP to ${highest:.2f}!")
    elif a.id == "vulture_fund":
        gs['market_info']['vulture_event'] = t.name # Store NAME of attacker
    return True, "Used"

def _handle_passive(t, a, gs, p): return True, "Passive"
def _handle_defensive(t, a, gs, p):
    if a.id == "bailout":
        if (t.capital + t.stock_held*p) < 90000:
            t.capital += 10000
            return True, "Bailout"
    if a.id == "frozen_time":
        # Reset to before last trade - need to track last trade state
        if 'last_trade_snapshot' in gs['market_info']:
            snapshot = gs['market_info']['last_trade_snapshot']
            t.capital = snapshot.get('capital', t.capital)
            t.stock_held = snapshot.get('stock_held', t.stock_held)
            gs['game_log'].append(f"⏰ {t.name} used Frozen Time - Reverted to before last trade!")
            return True, "Used"
        return False, "No trade to revert"
    return False, "Failed"

def _handle_legendary_systemic(t, a, gs, p):
    opp_key = "ai_bot" if t.name == gs['player']['name'] else "player"
    
    if a.id == "black_swan":
        # 5x Pump/Dump effect (random direction) for 4 seconds
        direction = random.choice([1, -1])
        multiplier = 0.025 * 5  # 5x the new pump/dump (2.5%)
        gs['current_stock_price'] *= (1 + (direction * multiplier))
        gs['market_info']['black_swan_effect'] = 4  # 4 seconds
        gs['market_info']['black_swan_dir'] = direction
        gs['market_info']['pump_effect' if direction > 0 else 'dump_effect'] = 4
        gs['game_log'].append(f"⚡ BLACK SWAN: Extreme {'spike' if direction > 0 else 'collapse'} for 4 seconds!")
        return True, "Used"
    
    elif a.id == "quantum_arbitrage":
        # Allow Buy and Sell in same tick for 5 ticks
        gs['market_info']['quantum_arbitrage_ticks'] = 5
        gs['game_log'].append(f"⚛️ QUANTUM ARBITRAGE: Dual actions enabled for 5 ticks!")
        return True, "Used"
    
    elif a.id == "system_collapse":
        # Block opponent's Whale/Shark abilities for 5 ticks
        gs['market_info']['system_collapse_ticks'] = 5
        gs['game_log'].append(f"💥 SYSTEM COLLAPSE: Opponent Whale/Shark abilities locked!")
        return True, "Used"
    
    return False, "Unknown"

def _handle_legendary_passive(t, a, gs, p):
    if a.id == "global_hedge":
        # Passive: Auto-restore 50% of loss if PnL < -$10k (once per match)
        if t.match_pnl < -10000 and not gs['market_info'].get('global_hedge_used', False):
            loss_amount = abs(t.match_pnl)
            restore = loss_amount * 0.5
            t.capital += restore
            gs['market_info']['global_hedge_used'] = True
            gs['game_log'].append(f"🛡️ GLOBAL HEDGE: Restored ${restore:.2f}!")
            return True, "Used"
    return True, "Passive"

def _handle_manipulation(t, a, gs, p):
    opp_key = "ai_bot" if t.name == gs['player']['name'] else "player"
    
    if a.id == "news_flash":
        gs['market_info']['news_flash_ticks'] = 11  # 11 seconds = 11 ticks (assuming 1 tick per second)
        gs['market_info']['news_flash_dir'] = 1 if t.stock_held > 0 else -1  # Favor current position
        gs['game_log'].append(f"📰 {t.name} used News Flash - Strong trend for 11 seconds!")
        return True, "Used"
    
    if a.id == "leverage_x10":
        gs['market_info'][f"{'player' if t.name == gs['player']['name'] else 'ai_bot'}_leverage"] = 8  # 8 seconds
        gs['game_log'].append(f"⚡ {t.name} used Leverage x10 - 10x PnL for 8 seconds!")
        return True, "Used"
    
    return True, "Used"

def _handle_legendary(t, a, gs, p):
    opp_key = "ai_bot" if t.name == gs['player']['name'] else "player"
    opp_data = gs[opp_key]
    
    if a.id == "the_oracle":
        # Predict next good buy/sell times
        # Calculate future price movements (simplified prediction)
        future_ticks = 30  # Look ahead 30 ticks
        current_tick = gs['current_tick']
        time_remaining = 300 - current_tick
        
        # Predict optimal buy and sell times
        buy_time = current_tick + random.randint(5, min(15, time_remaining // 2))
        sell_time = buy_time + random.randint(5, min(20, time_remaining - (buy_time - current_tick)))
        
        gs['market_info']['oracle_active'] = True
        gs['market_info']['oracle_buy_time'] = buy_time
        gs['market_info']['oracle_sell_time'] = sell_time
        gs['market_info']['oracle_used'] = False  # Track if player used the oracle trade
        gs['game_log'].append(f"🔮 {t.name} used The Oracle - Check the guidance box!")
        return True, "Used"
    
    if a.id == "server_crash":
        # Liquidate opponent position and freeze
        opp_trader = Trader.from_dict(opp_data)
        opp_trader.stock_held = 0
        opp_trader.capital += opp_trader.stock_held * p  # Convert stock to cash
        opp_trader.stock_held = 0
        gs[opp_key] = opp_trader.to_dict()
        gs['market_info'][f"{opp_key}_frozen"] = 15  # Freeze for 15 seconds
        gs['game_log'].append(f"💥 {t.name} used Server Crash - Opponent liquidated and frozen!")
        return True, "Used"
    
    return True, "Used"

def _handle_market_manipulation(t, a, gs, p):
    if a.id == "short_seller":
        # Toggle short seller mode - remains active until player sells
        player_key = "player" if t.name == gs['player']['name'] else "ai_bot"
        if not gs['market_info'].get(f"{player_key}_short_active", False):
            gs['market_info'][f"{player_key}_short_active"] = True
            gs['game_log'].append(f"📉 {t.name} activated Short Seller mode!")
            return True, "Activated"
        return False, "Already active"
    
    return True, "Used"

ABILITY_HANDLERS = {
    "whale": _handle_whale, "insider": _handle_insider, "shark": _handle_shark,
    "passive": _handle_passive, "defensive": _handle_defensive, "common": _handle_passive,
    "rare": _handle_passive, "epic": _handle_passive, "legendary": _handle_legendary,
    "market_manipulation": _handle_market_manipulation, "manipulation": _handle_manipulation,
    "legendary_rogue": _handle_legendary_rogue,
    "legendary_systemic": _handle_legendary_systemic,
    "legendary_passive": _handle_legendary_passive
}

# ============================================================================
# STATE INIT
# ============================================================================

def _initialize_match_state(room_code, player1_name, player2_name, p1_abilities, p2_abilities, wager, market_id=None, systemic_risk_mode=False):
    p1 = Trader(player1_name, is_ai=False)
    p1.abilities_equipped = p1_abilities
    
    # AI is True if player2 is NOT "Guest" (multiplayer indicator)
    # Guest means it's a real player in multiplayer, everything else is AI
    is_ai = player2_name != "Guest"
    p2 = Trader(player2_name, is_ai=is_ai)
    p2.abilities_equipped = p2_abilities

    # Get market definition if exists
    market_def = next((m for m in MARKETS if m['id'] == market_id), None)
    
    game_state = {
        "player": p1.to_dict(),
        "ai_bot": p2.to_dict(), # "ai_bot" key acts as Player 2/Opponent container
        "current_stock_price": 100.00,
        "current_tick": 0,
        "round_over": False,
        "winner": None,
        "wager": wager,
        "game_log": deque(["Market Open!"], maxlen=20),
        "price_history": [{"tick":0, "price":100.0, "open":100, "close":100, "high":100, "low":100}],
        "market_info": {},
        "market_config": market_def, # Store volatility settings
        "player_action_queue": deque(), # For P1
        "ai_action_queue": deque(),      # For P2/AI
        "systemic_risk_mode": systemic_risk_mode,
        "market_id": market_id
    }
    
    if systemic_risk_mode:
        game_state["game_log"].append("🌐 SYSTEMIC RISK MODE: Markets are interconnected!")
    
    return game_state

# ============================================================================
# THREAD LOOP
# ============================================================================

def market_loop():
    global market_thread_running
    print("DEBUG: Market Loop Started")
    while market_thread_running:
        try:
            with game_state_lock:
                rooms = list(GAMES.keys())
                for room_code in rooms:
                    game = GAMES[room_code]
                    
                    # Skip if lobby or over
                    if game.get('status') == 'lobby' or game.get('round_over'):
                        continue

                    # 1. Rehydrate
                    p1 = Trader.from_dict(game['player'])
                    p2 = Trader.from_dict(game['ai_bot'])
                    price = game['current_stock_price']
                    
                    # SYSTEMIC RISK MODE - Check if enabled
                    systemic_risk_enabled = game.get('systemic_risk_mode', False)
                    if systemic_risk_enabled:
                        # Initialize related markets if not exists
                        if 'related_markets' not in game['market_info']:
                            game['market_info']['related_markets'] = {
                                'tech': 100.0,
                                'crypto': 100.0,
                                'energy': 100.0,
                                'transport': 100.0,
                                'consumer': 100.0
                            }
                        
                        related_markets = game['market_info']['related_markets']
                        prev_price = game.get('prev_price', 100.0)
                        price_change_pct = (price - prev_price) / prev_price if prev_price > 0 else 0
                        
                        # Big moves in main market cause ripple effects
                        if abs(price_change_pct) > 0.05:  # 5% move triggers systemic effects
                            # Determine market type from current market config
                            market_id = game.get('market_id', 'blue_chip')
                            
                            # Tech crashes → Crypto dips → Energy spikes
                            if 'tech' in market_id or 'crypto' in market_id:
                                if price_change_pct < -0.05:  # Crash
                                    related_markets['crypto'] *= (1 + price_change_pct * 0.8)  # Crypto dips
                                    related_markets['energy'] *= (1 - price_change_pct * 0.6)  # Energy spikes
                                    game['game_log'].append(f"🌐 SYSTEMIC: Tech crash → Crypto -{abs(price_change_pct)*80:.1f}% → Energy +{abs(price_change_pct)*60:.1f}%")
                            
                            # Oil/Energy moves → Transport → Consumer
                            if 'commodities' in market_id or 'energy' in market_id:
                                if abs(price_change_pct) > 0.05:
                                    related_markets['transport'] *= (1 + price_change_pct * 0.7)
                                    related_markets['consumer'] *= (1 - price_change_pct * 0.5)
                                    game['game_log'].append(f"🌐 SYSTEMIC: Energy move → Transport {price_change_pct*70:+.1f}% → Consumer {-price_change_pct*50:+.1f}%")
                            
                            # Feed back into main market (portfolio effect)
                            avg_related = sum(related_markets.values()) / len(related_markets)
                            feedback_effect = (avg_related - 100.0) * 0.1  # 10% feedback
                            price *= (1 + feedback_effect / 100.0)
                        
                        # Update related markets with small random drift
                        for market_key in related_markets:
                            drift = 1.0 + random.uniform(-0.002, 0.002)
                            related_markets[market_key] = max(50.0, min(200.0, related_markets[market_key] * drift))
                        
                        game['prev_price'] = price

                    # Vulture Event Logic
                    if game['market_info'].get('vulture_event'):
                        attacker_name = game['market_info']['vulture_event']
                        
                        # Identify Attacker and Victim properly based on Name
                        if attacker_name == p1.name:
                            attacker = p1
                            victim = p2
                            victim_key = 'ai_bot' # P2/Guest
                        else:
                            attacker = p2
                            victim = p1
                            victim_key = 'player' # P1/Host

                        loot = victim.stock_held * price
                        victim.stock_held = 0
                        attacker.capital += loot
                        
                        game['market_info']['vulture_event'] = None
                        game['market_info'][f"{victim_key}_cant_buy"] = 15

                    # 2. Process Actions
                    while game['player_action_queue']:
                        act, val = game['player_action_queue'].popleft()
                        if not game['market_info'].get('player_frozen'):
                            if not game['market_info'].get('player_silenced') or act != 'ability':
                                if act == 'buy': p1.buy_stock(val, price, game)
                                elif act == 'sell': 
                                    if not game['market_info'].get('player_cant_sell'): p1.sell_stock(val, price, game)
                                elif act == 'ability': p1.use_ability(val, game)
                    
                    if p2.is_ai:
                        if not game['market_info'].get('ai_bot_frozen'):
                            # Boss/Syndicate Specific AI Logic
                            boss_id = game.get('boss_id')
                            syndicate_id = game.get('syndicate_id')
                            boss_acted = False
                                
                            # Chapter 2 Syndicate AI
                            if syndicate_id:
                                syn = next((s for s in SYNDICATES if s['id'] == syndicate_id), None)
                                if syn:
                                    # 1. "Zero-Latency" Zeta (HFT - High Frequency Trading)
                                    if syndicate_id == 'syn_locusts':
                                        # Very aggressive, trades frequently
                                        if random.random() < 0.4:  # 40% chance per tick
                                            if price < 100 and p2.capital > price and not game['market_info'].get('ai_bot_cant_buy'): 
                                                p2.buy_stock(30, price, game)
                                            elif price > 100 and p2.stock_held > 0 and not game['market_info'].get('ai_bot_cant_sell'): 
                                                p2.sell_stock(30, price, game)
                                        boss_acted = True
                                    
                                    # 2. "The Negative" Nate (Bear Market - Short Selling)
                                    elif syndicate_id == 'syn_bears':
                                        # Prefers selling, holds cash
                                        if p2.stock_held > 5 and price > 95 and not game['market_info'].get('ai_bot_cant_sell'): 
                                            p2.sell_stock(40, price, game)
                                        elif price < 85 and p2.capital > price and not game['market_info'].get('ai_bot_cant_buy'): 
                                            p2.buy_stock(15, price, game)  # Buy very low
                                        boss_acted = True
                                    
                                    # 3. "The Merger" Maxwell (M&A - Momentum)
                                    elif syndicate_id == 'syn_hostile':
                                        # Momentum trading based on recent price movement
                                        if len(game['price_history']) > 5:
                                            recent_prices = [p['price'] for p in game['price_history'][-5:]]
                                            trend = recent_prices[-1] - recent_prices[0]
                                            if trend > 2 and p2.capital > price and not game['market_info'].get('ai_bot_cant_buy'):  # Uptrend
                                                p2.buy_stock(50, price, game)
                                            elif trend < -2 and p2.stock_held > 0 and not game['market_info'].get('ai_bot_cant_sell'):  # Downtrend
                                                p2.sell_stock(50, price, game)
                                        boss_acted = True
                                    
                                    # 4. "Cayman" Carlos (Tax Havens - Conservative)
                                    elif syndicate_id == 'syn_tax':
                                        # Conservative, trades less frequently due to tax
                                        if random.random() < 0.15:  # 15% chance per tick
                                            if price < 98 and p2.capital > price and not game['market_info'].get('ai_bot_cant_buy'): 
                                                p2.buy_stock(40, price, game)
                                            elif price > 102 and p2.stock_held > 0 and not game['market_info'].get('ai_bot_cant_sell'): 
                                                p2.sell_stock(40, price, game)
                                        boss_acted = True
                            
                            if boss_id:
                                # --- BOSS AI STRATEGIES ---
                                
                                # 1. Mr. X (High Volatility/Momentum)
                                if boss_id == 'boss_1':
                                    # Buys on pumps, Sells on dumps (Momentum) - More active
                                    if price > 102 and p2.capital > price and not game['market_info'].get('ai_bot_cant_buy'): 
                                        p2.buy_stock(25, price, game)
                                    elif price < 98 and p2.stock_held > 0 and not game['market_info'].get('ai_bot_cant_sell'): 
                                        p2.sell_stock(25, price, game)
                                    # Also trade on momentum even if price is near 100
                                    elif len(game['price_history']) > 2:
                                        recent = [p['price'] for p in game['price_history'][-2:]]
                                        if recent[-1] > recent[0] and p2.capital > price and not game['market_info'].get('ai_bot_cant_buy'):
                                            p2.buy_stock(20, price, game)  # Buy on uptrend
                                        elif recent[-1] < recent[0] and p2.stock_held > 0 and not game['market_info'].get('ai_bot_cant_sell'):
                                            p2.sell_stock(20, price, game)  # Sell on downtrend
                                    boss_acted = True

                                # 2. Ben Dover (Short/Devaluation)
                                elif boss_id == 'boss_2':
                                    # Prefers to hold cash, sells aggressively if holding stock - More active
                                    if p2.stock_held > 5 and price > 95 and not game['market_info'].get('ai_bot_cant_sell'): 
                                        p2.sell_stock(50, price, game)
                                    elif price < 90 and p2.capital > price and not game['market_info'].get('ai_bot_cant_buy'): 
                                        p2.buy_stock(20, price, game) # Buy dip
                                    boss_acted = True
                                
                                # 3. Goldfinger (Hoarding)
                                elif boss_id == 'boss_3':
                                    # Only Buys. Rarely sells. - More active buying
                                    if p2.capital > price and random.random() < 0.3 and not game['market_info'].get('ai_bot_cant_buy'): 
                                        p2.buy_stock(100, price, game)
                                    if price > 120 and p2.stock_held > 0 and not game['market_info'].get('ai_bot_cant_sell'): 
                                        p2.sell_stock(10, price, game) # Take profit rarely
                                    boss_acted = True
                                    
                                # 4. Sheik Shaker (Pump/Dump)
                                elif boss_id == 'boss_4':
                                    # Swing trader - More frequent trading
                                    if game['current_tick'] % 15 < 8: # Buying phase
                                        if p2.capital > price and not game['market_info'].get('ai_bot_cant_buy'): 
                                            p2.buy_stock(50, price, game)
                                    else: # Selling phase
                                        if p2.stock_held > 0 and not game['market_info'].get('ai_bot_cant_sell'): 
                                            p2.sell_stock(50, price, game)
                                    boss_acted = True
                                    
                                # 5. Baron Von BustMargin (High Risk)
                                elif boss_id == 'boss_5':
                                    # All in - More active
                                    if p2.capital > price * 50 and not game['market_info'].get('ai_bot_cant_buy'): 
                                        p2.buy_stock(500, price, game)
                                    elif p2.match_pnl < -3000 and p2.stock_held > 0 and not game['market_info'].get('ai_bot_cant_sell'): 
                                        p2.sell_stock(500, price, game) # Panic sell
                                    elif p2.match_pnl > 3000 and p2.stock_held > 0 and not game['market_info'].get('ai_bot_cant_sell'): 
                                        p2.sell_stock(500, price, game) # Greed sell
                                    boss_acted = True

                                # 6. Mister Real Estate (Slow/Illiquid)
                                elif boss_id == 'boss_6':
                                    # Trades rarely but big - More frequent
                                    if random.random() < 0.08:
                                        if p2.capital > price * 50 and not game['market_info'].get('ai_bot_cant_buy'): 
                                            p2.buy_stock(300, price, game)
                                        elif p2.stock_held > 0 and not game['market_info'].get('ai_bot_cant_sell'): 
                                            p2.sell_stock(300, price, game)
                                    boss_acted = True

                                # Final Boss
                                elif boss_id == 'final_boss':
                                    # Perfect counter-trading (Cheating AI?)
                                    # Actually just high frequency random - More active
                                    if random.random() < 0.4:
                                        if random.random() > 0.5 and p2.capital > price and not game['market_info'].get('ai_bot_cant_buy'): 
                                            p2.buy_stock(random.randint(20,150), price, game)
                                        elif p2.stock_held > 0 and not game['market_info'].get('ai_bot_cant_sell'): 
                                            p2.sell_stock(random.randint(20,150), price, game)
                                    boss_acted = True
                                
                                # --- CHAPTER 3 BOSSES ---
                                # 1. "Senator" Sovereign (Debt Default)
                                elif boss_id == 'boss_ch3_sovereign':
                                    if random.random() < 0.1:  # 10% chance per tick
                                        game['market_info']['debt_default_ticks'] = 3
                                        game['game_log'].append("💸 DEBT DEFAULT: Capital halved for 3 ticks!")
                                    if price < 98 and p2.capital > price and not game['market_info'].get('ai_bot_cant_buy'): 
                                        p2.buy_stock(50, price, game)
                                    elif price > 102 and p2.stock_held > 0 and not game['market_info'].get('ai_bot_cant_sell'): 
                                        p2.sell_stock(50, price, game)
                                    boss_acted = True
                                
                                # 2. "The Regulator" Rhonda (Margin Contraction)
                                elif boss_id == 'boss_ch3_regulator':
                                    if random.random() < 0.08:  # 8% chance per tick
                                        game['market_info']['margin_contraction'] = True
                                        game['game_log'].append("📉 MARGIN CONTRACTION: Stock positions halved at 90% price!")
                                    if price < 100 and p2.capital > price and not game['market_info'].get('ai_bot_cant_buy'): 
                                        p2.buy_stock(75, price, game)
                                    elif price > 100 and p2.stock_held > 0 and not game['market_info'].get('ai_bot_cant_sell'): 
                                        p2.sell_stock(75, price, game)
                                    boss_acted = True
                                
                                # 3. "Moody" Mitch (Panic Sell)
                                elif boss_id == 'boss_ch3_moody':
                                    if random.random() < 0.12:  # 12% chance per tick
                                        game['market_info']['panic_sell'] = True
                                        game['game_log'].append("😱 PANIC SELL: Forcing sale of highest PnL asset at 5% penalty!")
                                    if price < 99 and p2.capital > price and not game['market_info'].get('ai_bot_cant_buy'): 
                                        p2.buy_stock(60, price, game)
                                    elif price > 101 and p2.stock_held > 0 and not game['market_info'].get('ai_bot_cant_sell'): 
                                        p2.sell_stock(60, price, game)
                                    boss_acted = True
                                
                                # 4. "The Phantom" Pascal (Flash Freeze Systemic)
                                elif boss_id == 'boss_ch3_phantom':
                                    if random.random() < 0.06:  # 6% chance per tick
                                        game['market_info']['flash_freeze_systemic_ticks'] = 2
                                        game['game_log'].append("❄️ FLASH FREEZE SYSTEMIC: All trades blocked for 2 ticks! (Abilities still usable)")
                                    if price < 100 and p2.capital > price and not game['market_info'].get('ai_bot_cant_buy'): 
                                        p2.buy_stock(40, price, game)
                                    elif price > 100 and p2.stock_held > 0 and not game['market_info'].get('ai_bot_cant_sell'): 
                                        p2.sell_stock(40, price, game)
                                    boss_acted = True

                            # Fallback / Default AI (for non-boss matches or if boss logic didn't act)
                            if not boss_acted:
                                # Smarter default AI that reacts to price movements
                                if len(game['price_history']) > 3:
                                    recent_prices = [p['price'] for p in game['price_history'][-3:]]
                                    price_change = recent_prices[-1] - recent_prices[0]
                                    
                                    # Buy on dips, sell on peaks
                                    if price < 97 and p2.capital > price * 20 and not game['market_info'].get('ai_bot_cant_buy'): 
                                        p2.buy_stock(20, price, game)
                                    elif price > 103 and p2.stock_held > 0 and not game['market_info'].get('ai_bot_cant_sell'): 
                                        p2.sell_stock(20, price, game)
                                    # React to trends
                                    elif price_change < -1 and p2.capital > price and not game['market_info'].get('ai_bot_cant_buy'):  # Falling price
                                        p2.buy_stock(15, price, game)  # Buy the dip
                                    elif price_change > 1 and p2.stock_held > 0 and not game['market_info'].get('ai_bot_cant_sell'):  # Rising price
                                        p2.sell_stock(15, price, game)  # Take profit
                                else:
                                    # Early game: simple strategy
                                    if price < 98 and p2.capital > price and not game['market_info'].get('ai_bot_cant_buy'): 
                                        p2.buy_stock(15, price, game)
                                    elif price > 102 and p2.stock_held > 0 and not game['market_info'].get('ai_bot_cant_sell'): 
                                        p2.sell_stock(15, price, game)
                            
                            # Ability Usage Logic - More aggressive for bosses
                            ability_chance = 0.08 if boss_id or syndicate_id else 0.05
                            if random.random() < ability_chance:
                                avail = [a for a in p2.abilities_equipped if p2.abilities_cooldown.get(a.id, 0) == 0]
                                if avail: 
                                    # Prioritize offensive abilities for bosses
                                    offensive = [a for a in avail if a.behavior_type in ['whale', 'shark', 'insider']]
                                    ability_to_use = random.choice(offensive if offensive else avail)
                                    p2.use_ability(ability_to_use.id, game)
                    else:
                        while game['ai_action_queue']:
                            act, val = game['ai_action_queue'].popleft()
                            if not game['market_info'].get('ai_bot_frozen'):
                                if act == 'buy': p2.buy_stock(val, price, game)
                                elif act == 'sell': 
                                    if not game['market_info'].get('ai_bot_cant_sell'): p2.sell_stock(val, price, game)
                                elif act == 'ability': p2.use_ability(val, game)

                    # 3. Market Movement
                    drift = 1.0 + random.uniform(-0.01, 0.01)
                    
                    # Apply Selected Market Volatility
                    market_cfg = game.get('market_config')
                    if market_cfg:
                        vol = market_cfg.get('volatility')
                        if vol == 'low': drift = 1.0 + random.uniform(-0.005, 0.005)
                        elif vol == 'medium': drift = 1.0 + random.uniform(-0.015, 0.015)
                        elif vol == 'high': drift = 1.0 + random.uniform(-0.025, 0.025)
                        elif vol == 'extreme': drift = 1.0 + random.uniform(-0.04, 0.04)
                        elif vol == 'fast': drift = 1.0 + random.uniform(-0.03, 0.03) 
                        elif vol == 'trend': 
                            bias = 0.002 if random.random() > 0.5 else -0.002
                            drift = 1.0 + bias + random.uniform(-0.005, 0.005)

                    # Syndicate Volatility
                    syn_id = game.get('syndicate_id')
                    if syn_id:
                        s = next((x for x in SYNDICATES if x['id'] == syn_id), None)
                        if s:
                            if s['volatility'] == 'hft': drift = 1.0 + random.uniform(-0.05, 0.05) # Extreme volatility
                            if s['volatility'] == 'bearish': drift = 1.0 + random.uniform(-0.02, 0.005) # Downward bias
                            if s['volatility'] == 'taxed': 
                                if game['current_tick'] % 10 == 0:
                                    p1.capital *= 0.99; p2.capital *= 0.99 # 1% Tax every 10 ticks
                            
                    # Rogue Boss Volatility Override
                    boss_id = game.get('boss_id')
                    if boss_id:
                        # (Boss logic similar to before)
                        pass
                    
                    if game['market_info'].get('rumor_ticks', 0) > 0:
                        drift += 0.005 if game['market_info']['rumor_dir'] == 'up' else -0.005
                        game['market_info']['rumor_ticks'] -= 1
                    
                    # Hypetrain effect
                    if game['market_info'].get('volatility_mult'):
                         diff = drift - 1.0
                         drift = 1.0 + (diff * game['market_info']['volatility_mult'])
                    
                    new_price = max(1.0, price * drift)
                    game['current_stock_price'] = new_price
                    game['current_tick'] += 1
                    
                    # History
                    game['price_history'].append({
                        "tick": game['current_tick'], "price": new_price,
                        "open": price, "close": new_price, "high": max(price, new_price), "low": min(price, new_price)
                    })

                    # 4. Updates
                    for t in [p1, p2]:
                        for aid in t.abilities_cooldown:
                            if t.abilities_cooldown[aid] > 0: t.abilities_cooldown[aid] -= 1
                        t.calculate_pnl(new_price)

                    # Chapter 3 Boss Effects
                    # Debt Default: Halves capital for 3 ticks
                    if game['market_info'].get('debt_default_ticks', 0) > 0:
                        if game['market_info']['debt_default_ticks'] == 3:  # Apply on first tick
                            p1.capital *= 0.5
                            p2.capital *= 0.5
                            game['game_log'].append("💸 Debt Default: Capital halved!")
                        game['market_info']['debt_default_ticks'] -= 1
                    
                    # Margin Contraction: Halves stock held at 90% price
                    if game['market_info'].get('margin_contraction', False):
                        if p1.stock_held > 0:
                            sell_qty = p1.stock_held // 2
                            p1.sell_stock(sell_qty, price * 0.9, game)
                        if p2.stock_held > 0:
                            sell_qty = p2.stock_held // 2
                            p2.sell_stock(sell_qty, price * 0.9, game)
                        game['market_info']['margin_contraction'] = False
                        game['game_log'].append("📉 Margin Contraction: Positions halved at 90%!")
                    
                    # Panic Sell: Force sell highest PnL asset at 5% penalty
                    if game['market_info'].get('panic_sell', False):
                        # For single asset, just force sell all at penalty
                        if p1.stock_held > 0:
                            p1.sell_stock(p1.stock_held, price * 0.95, game)
                        if p2.stock_held > 0:
                            p2.sell_stock(p2.stock_held, price * 0.95, game)
                        game['market_info']['panic_sell'] = False
                        game['game_log'].append("😱 Panic Sell: All positions sold at 5% penalty!")
                    
                    # Flash Freeze Systemic: Block all trades (but NOT abilities)
                    if game['market_info'].get('flash_freeze_systemic_ticks', 0) > 0:
                        game['market_info']['player_cant_buy'] = True
                        game['market_info']['player_cant_sell'] = True
                        game['market_info']['ai_bot_cant_buy'] = True
                        game['market_info']['ai_bot_cant_sell'] = True
                        # Note: We do NOT set player_frozen or ai_bot_frozen, so abilities can still be used
                        game['market_info']['flash_freeze_systemic_ticks'] -= 1
                        if game['market_info']['flash_freeze_systemic_ticks'] == 0:
                            game['market_info']['player_cant_buy'] = False
                            game['market_info']['player_cant_sell'] = False
                            game['market_info']['ai_bot_cant_buy'] = False
                            game['market_info']['ai_bot_cant_sell'] = False
                            game['game_log'].append("❄️ Flash Freeze lifted!")
                    
                    # Quantum Arbitrage: Allow Buy and Sell in same tick
                    if game['market_info'].get('quantum_arbitrage_ticks', 0) > 0:
                        game['market_info']['quantum_arbitrage_ticks'] -= 1
                    
                    # System Collapse: Block opponent Whale/Shark abilities
                    if game['market_info'].get('system_collapse_ticks', 0) > 0:
                        game['market_info']['system_collapse_ticks'] -= 1

                    # Apply ability effects with durations
                    # News Flash: Strong trend bias for 11 seconds
                    if game['market_info'].get('news_flash_ticks', 0) > 0:
                        dir = game['market_info'].get('news_flash_dir', 1)
                        drift += 0.01 * dir  # Strong bias
                        game['market_info']['news_flash_ticks'] -= 1
                    
                    # Leverage x10: Multiply PnL by 10x
                    if game['market_info'].get('player_leverage', 0) > 0:
                        p1.leverage = 10.0
                        game['market_info']['player_leverage'] -= 1
                        if game['market_info']['player_leverage'] == 0:
                            p1.leverage = 1.0
                    if game['market_info'].get('ai_bot_leverage', 0) > 0:
                        p2.leverage = 10.0
                        game['market_info']['ai_bot_leverage'] -= 1
                        if game['market_info']['ai_bot_leverage'] == 0:
                            p2.leverage = 1.0
                    
                    # Audit: 6% commission for opponent
                    if game['market_info'].get('player_audit', 0) > 0:
                        p1.commission_multiplier = game['market_info'].get('player_audit_rate', 0.06)
                        game['market_info']['player_audit'] -= 1
                        if game['market_info']['player_audit'] == 0:
                            p1.commission_multiplier = 0.0
                    if game['market_info'].get('ai_bot_audit', 0) > 0:
                        p2.commission_multiplier = game['market_info'].get('ai_bot_audit_rate', 0.06)
                        game['market_info']['ai_bot_audit'] -= 1
                        if game['market_info']['ai_bot_audit'] == 0:
                            p2.commission_multiplier = 0.0
                    
                    # Fake Out: Distort opponent PnL view
                    if game['market_info'].get('player_fake_out', 0) > 0:
                        p1.pnl_spoof_factor = -0.02  # -2% view
                        game['market_info']['player_fake_out'] -= 1
                        if game['market_info']['player_fake_out'] == 0:
                            p1.pnl_spoof_factor = 0.0
                    if game['market_info'].get('ai_bot_fake_out', 0) > 0:
                        p2.pnl_spoof_factor = -0.02
                        game['market_info']['ai_bot_fake_out'] -= 1
                        if game['market_info']['ai_bot_fake_out'] == 0:
                            p2.pnl_spoof_factor = 0.0
                    
                    # Black Swan: Continue extreme effect for 4 seconds
                    if game['market_info'].get('black_swan_effect', 0) > 0:
                        dir = game['market_info'].get('black_swan_dir', 1)
                        multiplier = 0.025 * 5  # 5x the new pump/dump
                        drift += (multiplier * dir) / 4  # Spread over 4 seconds
                        game['market_info']['black_swan_effect'] -= 1
                    
                    # Trend Lines: Predict next ticks (for button flashing - handled in frontend)
                    if any(a.id == 'trend_lines' for a in p1.abilities_equipped):
                        # Predict next few ticks
                        future_drift = drift
                        if len(game['price_history']) > 5:
                            recent = [p['price'] for p in game['price_history'][-5:]]
                            trend = (recent[-1] - recent[0]) / len(recent)
                            future_drift = 1.0 + (trend / recent[-1]) if recent[-1] > 0 else drift
                        game['market_info']['trend_lines_active'] = 7  # 7 ticks
                        game['market_info']['trend_lines_good'] = future_drift > 1.0  # Good if price going up
                    
                    # Reset Volume Spy usage at round start (tick 0)
                    if game['current_tick'] == 0:
                        game['market_info']['player_volume_spy_used'] = False
                        game['market_info']['ai_bot_volume_spy_used'] = False
                        game['market_info'].pop('player_volume_spy_reveal', None)
                        game['market_info'].pop('ai_bot_volume_spy_reveal', None)
                    
                    # 5. Status Tick Down
                    for k in list(game['market_info'].keys()):
                         if isinstance(game['market_info'][k], int) and game['market_info'][k] > 0:
                             game['market_info'][k] -= 1
                         if k == 'volatility_mult' and game['market_info'].get('rumor_ticks', 0) <= 0:
                             game['market_info'].pop(k, None)

                    # 6. End Check
                    if game['current_tick'] >= MAX_GAME_TICKS:
                        game['round_over'] = True
                        # Winner determined by most cash (capital + stock value), not PnL
                        p1_total_cash = p1.capital + (p1.stock_held * price)
                        p2_total_cash = p2.capital + (p2.stock_held * price)
                        game['winner'] = "Player" if p1_total_cash > p2_total_cash else "Opponent"
                        # Store total cash for wager calculations
                        game['p1_total_cash'] = p1_total_cash
                        game['p2_total_cash'] = p2_total_cash
                        
                    # Save Back
                    game['player'] = p1.to_dict()
                    game['ai_bot'] = p2.to_dict()

        except Exception as e:
            print(f"Error in Loop: {e}")
            import traceback; traceback.print_exc()
        time.sleep(TICK_INTERVAL)

def start_thread():
    global market_thread_running, market_thread
    if not market_thread_running:
        market_thread_running = True
        market_thread = threading.Thread(target=market_loop, daemon=True)
        market_thread.start()

# ============================================================================
# ROUTES
# ============================================================================

# ... (Login/Register/Logout/Index/Store/Vault routes same as before) ...
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        users = load_all_users()
        if email in users and users[email]['password'] == password:
            session['user_email'] = email
            return redirect(url_for('index'))
        return "Invalid Credentials"
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    users = load_all_users()
    if email in users: return "Email already exists"
    users[email] = {"username": username, "password": password, "data": get_default_player_data(username)}
    save_all_users(users)
    session['user_email'] = email
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('user_email', None)
    return redirect(url_for('login_page'))

@app.route('/favicon.ico')
def favicon():
    from flask import send_from_directory
    import os
    favicon_path = os.path.join(app.root_path, 'static', 'favicon.ico')
    if os.path.exists(favicon_path):
        return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    else:
        # Return 204 No Content if favicon doesn't exist (prevents 404 errors)
        return '', 204

@app.route('/')
@login_required
def index():
    data = load_player_data()
    
    # Check if first sign-in welcome should play
    first_signin_welcome = not data.get('first_signin_welcome_played', False)
    if first_signin_welcome:
        data['first_signin_welcome_played'] = True
        save_player_data(data)
    
    # Check if first loss welcome should play (only once ever, unless manually reset)
    # We need to track if it's been played this visit to avoid playing multiple times
    first_loss_welcome = data.get('first_loss_welcome_played', False) and not session.get('first_loss_welcome_played_this_visit', False)
    if first_loss_welcome:
        session['first_loss_welcome_played_this_visit'] = True
    
    # Check loan deadline
    loan = data.get('loan', {})
    loan_overdue = loan.get('active', False) and loan.get('matches_remaining', 0) < 0
    
    # Get top 5 players by net worth
    all_users = load_all_users()
    top_players = []
    for email, user_data in all_users.items():
        if 'data' in user_data and 'net_worth' in user_data['data']:
            top_players.append({
                'username': user_data.get('username', 'Unknown'),
                'player_id': user_data['data'].get('player_id', 'N/A'),
                'net_worth': user_data['data']['net_worth']
            })
    
    # Sort by net worth and take top 5
    top_players.sort(key=lambda x: x['net_worth'], reverse=True)
    top_players = top_players[:5]
    
    # Check for friend invites (placeholder - friend system may need invites)
    friend_invites = []  # TODO: Implement friend invite system if needed
    
    # Updates/notifications
    updates = []
    if loan_overdue:
        updates.append({
            'type': 'loan',
            'message': f'⚠️ Loan Shark: Pay ${loan.get("amount", 0):,.0f} now! Interest: {loan.get("interest_rate", 0)*100:.0f}%',
            'sound': 'sharky.mp3'
        })
    
    # Check if admin
    is_admin = session.get('user_email') == 'rennelldenton2495@gmail.com'
    
    return render_template('index.html',
                          first_signin_welcome=first_signin_welcome, 
                          first_loss_welcome=first_loss_welcome, 
                         loan_overdue=loan_overdue,
                         top_players=top_players,
                         friend_invites=friend_invites,
                         updates=updates,
                         is_admin=is_admin)

@app.route('/lobby')
@login_required
def lobby():
    data = load_player_data()
    return render_template('lobby.html', player_data=data, abilities=data['owned_abilities'])

@app.route('/store')
@login_required
def store():
    data = load_player_data()
    owned = [a['id'] for a in data['owned_abilities']]
    return render_template('store.html', player_data=data, abilities=ALL_POSSIBLE_ABILITIES, owned_ids=owned)

@app.route('/buy_ability', methods=['POST'])
@login_required
def buy_ability():
    aid = request.form.get('ability_id')
    data = load_player_data()
    ab = next((a for a in ALL_POSSIBLE_ABILITIES if a['id'] == aid), None)
    if not ab: return redirect(url_for('store'))
    
    # Check cost
    if data['net_worth'] < ab['cost']:
        return redirect(url_for('store'))
    
    # Check token requirements for Chapter 3 legendaries
    if ab.get('token_req_id'):
        tokens = data.get('rogue_run', {}).get('tokens', [])
        emblems = data.get('syndicate_data', {}).get('emblems', [])
        all_tokens = tokens + emblems
        
        if ab['token_req_id'] not in all_tokens:
            return redirect(url_for('store'))  # Missing first token
        
        # Check second token if required
        if ab.get('token_req_id2'):
            if ab['token_req_id2'] not in all_tokens:
                return redirect(url_for('store'))  # Missing second token
    
    # Purchase
    data['net_worth'] -= ab['cost']
    data['owned_abilities'].append(ab)
    save_player_data(data)
    return redirect(url_for('store'))

@app.route('/loan_shark')
@login_required
def loan_shark():
    data = load_player_data()
    return render_template('loan_shark.html', player_data=data)

@app.route('/loan_shark/jobs')
@login_required
def loan_shark_jobs():
    """Show available jobs for the Loan Shark"""
    import json
    import os
    
    data = load_player_data()
    loan = data.get('loan', {})
    
    # Load job definitions
    jobs_file = 'loan_shark_jobs.json'
    if os.path.exists(jobs_file):
        with open(jobs_file, 'r') as f:
            jobs_data = json.load(f)
        jobs = [j for j in jobs_data.get('jobs', []) if j.get('enabled', True)]
    else:
        jobs = []
    
    return render_template('loan_shark_jobs.html', player_data=data, jobs=jobs, loan=loan)

@app.route('/loan_shark/job/<job_id>')
@login_required
def start_job(job_id):
    """Start a specific job mini-game"""
    import json
    import os
    
    data = load_player_data()
    
    # Load job definitions
    jobs_file = 'loan_shark_jobs.json'
    if os.path.exists(jobs_file):
        with open(jobs_file, 'r') as f:
            jobs_data = json.load(f)
        jobs = {j['id']: j for j in jobs_data.get('jobs', [])}
    else:
        flash('Job system not configured', 'error')
        return redirect(url_for('loan_shark'))
    
    job = jobs.get(job_id)
    if not job or not job.get('enabled', True):
        flash('Job not available', 'error')
        return redirect(url_for('loan_shark_jobs'))
    
    # Store job in session for completion tracking
    session['current_job'] = {
        'id': job_id,
        'start_time': time.time(),
        'payout': job.get('base_payout', 0)
    }
    
    # Render appropriate mini-game template
    if job_id == 'market_manipulation':
        return render_template('minigames/market_manipulation.html', job=job, player_data=data)
    elif job_id == 'insider_cleanup':
        return render_template('minigames/insider_cleanup.html', job=job, player_data=data)
    elif job_id == 'liquidity_run':
        return render_template('minigames/liquidity_run.html', job=job, player_data=data)
    elif job_id == 'enforcer_favor':
        return render_template('minigames/enforcer_favor.html', job=job, player_data=data)
    else:
        flash('Unknown job type', 'error')
        return redirect(url_for('loan_shark_jobs'))

@app.route('/loan_shark/job/complete', methods=['POST'])
@login_required
def complete_job():
    """Handle job completion and calculate rewards"""
    import json
    import os
    
    data = request.get_json()
    job_id = session.get('current_job', {}).get('id')
    score = data.get('score', 0)  # 0.0 to 1.0
    time_taken = data.get('time_taken', 0)
    
    if not job_id:
        return jsonify({"success": False, "message": "No active job"})
    
    # Load job definitions
    jobs_file = 'loan_shark_jobs.json'
    if not os.path.exists(jobs_file):
        return jsonify({"success": False, "message": "Job system not configured"})
    
    with open(jobs_file, 'r') as f:
        jobs_data = json.load(f)
    jobs = {j['id']: j for j in jobs_data.get('jobs', [])}
    job = jobs.get(job_id)
    
    if not job:
        return jsonify({"success": False, "message": "Job not found"})
    
    player_data = load_player_data()
    loan = player_data.get('loan', {})
    
    # Calculate payout based on performance
    base_payout = job.get('base_payout', 0)
    max_payout = job.get('max_payout', 0)
    settings = jobs_data.get('settings', {})
    
    if score >= 0.95:  # Perfect
        payout = int(max_payout * settings.get('perfect_bonus_multiplier', 1.5))
        result = "perfect"
        message = f"Perfect execution! Earned ${payout:,} + bonus!"
    elif score >= settings.get('success_threshold', 0.7):  # Success
        payout = int(base_payout + (max_payout - base_payout) * ((score - 0.7) / 0.25))
        result = "success"
        message = f"Job completed! Earned ${payout:,}!"
    elif score >= settings.get('partial_threshold', 0.5):  # Partial
        payout = int(base_payout * score)
        result = "partial"
        message = f"Partial completion. Earned ${payout:,}. Penalty applied."
    else:  # Fail
        payout = 0
        result = "fail"
        message = "Job failed! Full penalty + interest increase."
    
    # Apply results
    if loan.get('active', False):
        if result == "perfect" or result == "success":
            # Clear debt or reduce it
            debt_amount = loan.get('amount', 0)
            if payout >= debt_amount:
                player_data['loan'] = {"active": False, "amount": 0, "matches_remaining": 0, "interest_rate": 0.0}
                remaining = payout - debt_amount
                if remaining > 0:
                    player_data['net_worth'] += remaining
                message += f" Debt cleared!"
            else:
                player_data['loan']['amount'] = max(0, debt_amount - payout)
                message += f" Debt reduced by ${payout:,}!"
        elif result == "partial":
            # Reduce debt but apply penalty
            debt_amount = loan.get('amount', 0)
            player_data['loan']['amount'] = max(0, debt_amount - payout)
            player_data['loan']['interest_rate'] = min(1.0, player_data['loan'].get('interest_rate', 0) + 0.1)
            message += f" Interest increased by 10%!"
        else:  # fail
            # Apply failure penalty
            if job.get('failure_penalty') == 'double_penalty':
                player_data['loan']['amount'] = int(loan.get('amount', 0) * 1.5)
            elif job.get('failure_penalty') == 'interest_increase':
                player_data['loan']['interest_rate'] = min(1.0, player_data['loan'].get('interest_rate', 0) + 0.2)
            elif job.get('failure_penalty') == 'portfolio_damage':
                player_data['net_worth'] = max(0, player_data.get('net_worth', 0) - 5000)
            message += " Penalty applied!"
    else:
        # No active loan - just add payout
        player_data['net_worth'] += payout
    
    save_player_data(player_data)
    session.pop('current_job', None)
    
    return jsonify({
        "success": True,
        "result": result,
        "payout": payout,
        "message": message
    })

@app.route('/bank/take_loan', methods=['POST'])
@login_required
def take_loan():
    amount = int(request.form.get('amount', 0))
    data = load_player_data()
    loan = data.get('loan', {})
    
    # Validation
    if amount < 1000:
        flash('Minimum loan amount is $1,000', 'error')
        return redirect(url_for('loan_shark'))
    
    if amount > 1000000:
        flash('Maximum loan amount is $1,000,000', 'error')
        return redirect(url_for('loan_shark'))
    
    # Simple validation: only one loan at a time
    if not loan.get('active', False):
        # Calculate interest rate based on amount (scaling penalty)
        # Base rate: 10% for $5k, increases with amount
        if amount <= 5000:
            interest_rate = 0.10
        elif amount <= 10000:
            interest_rate = 0.15
        elif amount <= 25000:
            interest_rate = 0.20
        elif amount <= 50000:
            interest_rate = 0.25
        elif amount <= 100000:
            interest_rate = 0.35
        elif amount <= 250000:
            interest_rate = 0.45
        elif amount <= 500000:
            interest_rate = 0.55
        else:  # 500k+
            interest_rate = 0.65
        
        data['net_worth'] += amount
        data['loan'] = {
            "active": True,
            "amount": amount,
            "matches_remaining": 5,
            "interest_rate": interest_rate
        }
        save_player_data(data)
        flash(f'Loan of ${amount:,} approved. Pay back in 5 matches or face the consequences.', 'warning')
    else:
        flash('You already have an active loan. Pay it off first.', 'error')
    
    return redirect(url_for('loan_shark'))

@app.route('/bank/pay_loan', methods=['POST'])
@login_required
def pay_loan():
    data = load_player_data()
    loan = data.get('loan', {})
    
    if loan.get('active', False):
        cost = loan['amount']
        if data['net_worth'] >= cost:
            data['net_worth'] -= cost
            data['loan'] = {"active": False, "amount": 0, "matches_remaining": 0, "interest_rate": 0.0}
            save_player_data(data)
            
    return redirect(url_for('loan_shark'))

@app.route('/vault')
@login_required
def vault(): 
    data = load_player_data()
    # Ensure player has an ID
    if 'player_id' not in data:
        data['player_id'] = generate_player_id()
        save_player_data(data)
    
    # Get all players for the all players list
    all_users = load_all_users()
    all_players = []
    current_player_id = data.get('player_id')
    
    for email, user_data in all_users.items():
        if 'data' in user_data:
            player_id = user_data['data'].get('player_id')
            username = user_data.get('username', 'Unknown')
            net_worth = user_data['data'].get('net_worth', 0)
            # Don't show current player in the list
            if player_id and player_id != current_player_id:
                all_players.append({
                    'username': username,
                    'player_id': player_id,
                    'net_worth': net_worth
                })
    
    # Sort by net worth (descending)
    all_players.sort(key=lambda x: x['net_worth'], reverse=True)
    
    # Create friend map for displaying friend usernames
    friend_map = {}
    for friend_id in data.get('friends', []):
        for email, user_data in all_users.items():
            if user_data.get('data', {}).get('player_id') == friend_id:
                friend_map[friend_id] = {
                    'username': user_data.get('username', 'Unknown'),
                    'player_id': friend_id
                }
                break
    
    # Create map for friend request usernames (both sent and received)
    for req_id in data.get('friend_requests_received', []) + data.get('friend_requests_sent', []):
        if req_id not in friend_map:
            for email, user_data in all_users.items():
                if user_data.get('data', {}).get('player_id') == req_id:
                    friend_map[req_id] = {
                        'username': user_data.get('username', 'Unknown'),
                        'player_id': req_id
                    }
                    break
    
    # Check if admin
    is_admin = session.get('user_email') == 'rennelldenton2495@gmail.com'
    
    return render_template('vault.html', player_data=data, all_players=all_players, friend_map=friend_map, is_admin=is_admin)

@app.route('/founding_traders')
@login_required
def founding_traders():
    try:
        data = load_player_data()
        admin_user = is_admin_user()
        
        # Ensure founding_trader data exists
        if 'founding_trader' not in data:
            data['founding_trader'] = {
                "tier": None,
                "badge": None,
                "frame": None,
                "soundtrack": None,
                "trading_buddy_enabled": False,
                "systemic_risk_mode_enabled": False,
                "title": None,
                "narrator_line": None,
                "unique_ending_unlocked": False
            }
            save_player_data(data)
        
        # Admin gets full tier 5 access automatically
        if admin_user:
            ft_data = data.get('founding_trader', {})
            if not ft_data:
                ft_data = {}
            current_tier = ft_data.get('tier')
            if not current_tier or current_tier < 5:
                ft_data['tier'] = 5
                ft_data['badge'] = 'Legendary Founding Trader'
                ft_data['title'] = 'Market Menace'
                ft_data['narrator_line'] = 'The admin who controls the markets themselves.'
                data['founding_trader'] = ft_data
                save_player_data(data)
        
        # Get all founding traders grouped by tier
        all_users = load_all_users()
        founding_traders_by_tier = {1: [], 2: [], 3: [], 4: [], 5: []}
        
        for email, user_data in all_users.items():
            try:
                if 'data' in user_data and user_data['data']:
                    ft_data = user_data['data'].get('founding_trader', {})
                    if not ft_data:
                        ft_data = {}
                    tier = ft_data.get('tier')
                    if tier and tier in [1, 2, 3, 4, 5]:
                        founding_traders_by_tier[tier].append({
                            'username': user_data.get('username', 'Unknown'),
                            'player_id': user_data['data'].get('player_id', 'N/A'),
                            'badge': ft_data.get('badge'),
                            'frame': ft_data.get('frame'),
                            'title': ft_data.get('title'),
                            'narrator_line': ft_data.get('narrator_line')
                        })
            except Exception as e:
                print(f"Error processing user {email}: {e}")
                continue
        
        # Available soundtracks for tier 3+
        available_soundtracks = [
            {'id': 'default', 'name': 'Default Theme'},
            {'id': 'Neon Shark Algorithms.mp3', 'name': 'Neon Shark Algorithms'},
            {'id': 'Pixel Punch.mp3', 'name': 'Pixel Punch'},
            {'id': 'amapiano-loop-base-banny-fernandes-297939.mp3', 'name': 'Amapiano Loop'}
        ]
        
        # Get effective tier (admin always gets tier 5)
        ft_data = data.get('founding_trader', {})
        if not ft_data:
            ft_data = {}
        effective_tier = 5 if admin_user else ft_data.get('tier', 0) or 0
        
        return render_template('founding_traders.html', 
                             player_data=data, 
                             founding_traders_by_tier=founding_traders_by_tier,
                             available_soundtracks=available_soundtracks,
                             is_admin=admin_user,
                             effective_tier=effective_tier)
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"Error in founding_traders route: {error_msg}")
        return f"Error loading Founding Traders page: {str(e)}<br><pre>{error_msg}</pre>", 500

@app.route('/update_founding_trader', methods=['POST'])
@login_required
def update_founding_trader():
    data = load_player_data()
    
    if 'founding_trader' not in data:
        data['founding_trader'] = {}
    
    # Handle soundtrack selection
    if 'soundtrack' in request.form:
        data['founding_trader']['soundtrack'] = request.form.get('soundtrack')
        save_player_data(data)
        return jsonify({"success": True, "message": "Soundtrack updated"})
    
    # Handle trading buddy toggle
    if 'trading_buddy_enabled' in request.form:
        data['founding_trader']['trading_buddy_enabled'] = request.form.get('trading_buddy_enabled') == 'true'
        save_player_data(data)
        return jsonify({"success": True, "message": "Trading buddy setting updated"})
    
    # Handle systemic risk mode toggle
    if 'systemic_risk_mode_enabled' in request.form:
        data['founding_trader']['systemic_risk_mode_enabled'] = request.form.get('systemic_risk_mode_enabled') == 'true'
        save_player_data(data)
        return jsonify({"success": True, "message": "Systemic Risk Mode setting updated"})
    
    return jsonify({"success": False, "message": "Invalid request"})

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    data = load_player_data()
    new_codename = request.form.get('name', '').strip()
    if new_codename:
        data['username'] = new_codename
        save_player_data(data)
    return redirect(url_for('vault'))

# --- NEW MARKET SELECTION FLOW ---

@app.route('/select_market', methods=['POST'])
@login_required
def select_market():
    # Save equipped abilities to session temporarily
    ids = request.form.getlist('equipped_abilities')
    session['temp_equipped_ids'] = ids
    
    # Pre-generate AI Abilities for this session if not exists or if new match flow
    ai_abs = [Ability(**a) for a in random.sample(ALL_POSSIBLE_ABILITIES, 3)]
    session['temp_ai_abilities'] = [a.to_dict() for a in ai_abs]
    
    # Check if Rumor is equipped for hint
    has_rumor = 'rumor' in ids
    
    rumor_info = None
    if has_rumor:
        if random.random() > 0.5:
            # Show an ability
            rand_ability = random.choice(ai_abs)
            rumor_info = f"Opponent has {rand_ability.name}"
        else:
            # Show market info placeholder (resolved in template per market)
            rumor_info = "MARKET_INFO"

    return render_template('select_market.html', markets=MARKETS, has_rumor=has_rumor, rumor_info=rumor_info, ai_abilities=session['temp_ai_abilities'])

@app.route('/start_match_with_market', methods=['POST'])
@login_required
def start_match_with_market():
    market_id = request.form.get('market_id')
    ids = session.get('temp_equipped_ids', [])
    
    data = load_player_data()
    all_abs = data['owned_abilities']
    equipped = [a for a in all_abs if a['id'] in ids]
    if not equipped: equipped = all_abs[:3]
    
    user_email = session.get('user_email')
    game_key = f"sp_{user_email}"
    
    # Retrieve pre-generated AI abilities
    ai_abs_dicts = session.get('temp_ai_abilities', [])
    if ai_abs_dicts:
        ai_abs = [Ability(**a) for a in ai_abs_dicts]
    else:
        ai_abs = [Ability(**a) for a in random.sample(ALL_POSSIBLE_ABILITIES, 3)]

    # Check for systemic risk mode (admin always has access)
    admin_user = is_admin_user()
    ft_data = data.get('founding_trader', {})
    effective_tier = 5 if admin_user else ft_data.get('tier', 0)
    systemic_risk = (effective_tier >= 5 and ft_data.get('systemic_risk_mode_enabled', False)) or admin_user
    
    with game_state_lock:
        # Pass market_id to init
        GAMES[game_key] = _initialize_match_state(game_key, "Player", "AI Bot", equipped, ai_abs, 1000, market_id, systemic_risk)
        GAMES[game_key]['status'] = 'active'
    
    session['room_code'] = game_key
    session['role'] = 'host'
    start_thread()
    return redirect(url_for('battle'))

# --- ROGUE & MULTIPLAYER ROUTES (Kept as is) ---
# ... (rest of the file remains similar, ensuring _initialize_match_state calls are updated if needed)

@app.route('/rogue/start_run')
@login_required
def rogue_start_run():
    data = load_player_data()
    # Check if we need to show premise
    premises_shown = data.get('premises_shown', {})
    
    # Determine which chapter premise to show
    ch1_complete = len(data.get('rogue_run', {}).get('defeated_bosses', [])) >= 7
    ch2_complete = len(data.get('syndicate_data', {}).get('emblems', [])) >= 4
    
    if not premises_shown.get('chapter_1', False):
        # Show Chapter 1 premise
        return redirect(url_for('premise_slideshow', chapter=1))
    elif ch1_complete and not premises_shown.get('chapter_2', False):
        # Show Chapter 2 premise
        return redirect(url_for('premise_slideshow', chapter=2))
    elif ch2_complete and not premises_shown.get('chapter_3', False):
        # Show Chapter 3 premise
        return redirect(url_for('premise_slideshow', chapter=3))
    
    # No premise to show, start run
    data['rogue_run'] = {"active": True, "hearts": 4, "tokens": [], "defeated_bosses": []}
    save_player_data(data)
    return redirect(url_for('rogue_menu'))

@app.route('/rogue/menu')
@login_required
def rogue_menu():
    data = load_player_data()
    if not data.get('rogue_run', {}).get('active'): return redirect(url_for('rogue_start_run'))
    
    # Separate bosses by chapter
    ch1_bosses = [b for b in ROGUE_BOSSES if not b['id'].startswith('boss_ch3_')]
    ch3_bosses = [b for b in ROGUE_BOSSES if b['id'].startswith('boss_ch3_')]
    
    # Check if Chapter 2 is unlocked (defeated final boss)
    ch2_unlocked = len(data['rogue_run'].get('defeated_bosses', [])) >= 7
    # Check if Chapter 3 is unlocked (all Chapter 2 syndicates defeated)
    ch3_unlocked = len(data.get('syndicate_data', {}).get('emblems', [])) >= 4
    
    return render_template('rogue_menu.html', 
                         bosses=ch1_bosses, 
                         run_state=data['rogue_run'], 
                         syndicates=SYNDICATES, 
                         syndicate_data=data.get('syndicate_data', {}),
                         ch3_bosses=ch3_bosses,
                         ch2_unlocked=ch2_unlocked,
                         ch3_unlocked=ch3_unlocked)

@app.route('/rogue/lobby/<boss_id>')
@login_required
def rogue_lobby(boss_id):
    data = load_player_data()
    boss = next((b for b in ROGUE_BOSSES if b['id'] == boss_id), None)
    if not boss: return redirect(url_for('rogue_menu'))
    return render_template('rogue_lobby.html', boss=boss, abilities=data['owned_abilities'])

@app.route('/rogue/start_match', methods=['POST'])
@login_required
def rogue_start_match():
    boss_id = request.form.get('boss_id')
    boss = next((b for b in ROGUE_BOSSES if b['id'] == boss_id), None)
    ids = request.form.getlist('equipped_abilities')
    data = load_player_data()
    equipped = [a for a in data['owned_abilities'] if a['id'] in ids]
    
    user_email = session.get('user_email')
    game_key = f"rogue_{user_email}"
    
    # Check for systemic risk mode (admin always has access)
    admin_user = is_admin_user()
    ft_data = data.get('founding_trader', {})
    effective_tier = 5 if admin_user else ft_data.get('tier', 0)
    systemic_risk = (effective_tier >= 5 and ft_data.get('systemic_risk_mode_enabled', False)) or admin_user
    
    with game_state_lock:
        GAMES[game_key] = _initialize_match_state(game_key, data['username'], boss['name'], equipped, [], 0, market_id=None, systemic_risk_mode=systemic_risk)
        GAMES[game_key]['status'] = 'active'
        GAMES[game_key]['boss_id'] = boss_id
        GAMES[game_key]['game_type'] = 'rogue'
    
    session['room_code'] = game_key
    session['role'] = 'host'
    start_thread()
    return redirect(url_for('battle'))

# --- SYNDICATE ROUTES ---

@app.route('/syndicate/recruit')
@login_required
def mercenary_store():
    data = load_player_data()
    return render_template('mercenary_store.html', mercs=MERCENARIES, player_data=data)

@app.route('/syndicate/buy_merc', methods=['POST'])
@login_required
def buy_merc():
    merc_id = request.form.get('merc_id')
    data = load_player_data()
    merc = next((m for m in MERCENARIES if m['id'] == merc_id), None)
    
    if merc and data['net_worth'] >= merc['cost'] and merc_id not in data['syndicate_data']['recruited_mercs']:
        # Check token req
        if merc['token_req'] in data['rogue_run'].get('tokens', []):
            data['net_worth'] -= merc['cost']
            data['syndicate_data']['recruited_mercs'].append(merc_id)
            save_player_data(data)
    return redirect(url_for('mercenary_store'))

@app.route('/syndicate/lobby/<syndicate_id>')
@login_required
def syndicate_lobby(syndicate_id):
    data = load_player_data()
    syndicate = next((s for s in SYNDICATES if s['id'] == syndicate_id), None)
    if not syndicate: return redirect(url_for('rogue_menu'))
    
    # Initialize tournament if new or different
    curr_tourney = data['syndicate_data'].get('current_tournament')
    if not curr_tourney or curr_tourney['id'] != syndicate_id:
        data['syndicate_data']['current_tournament'] = {
            "id": syndicate_id,
            "wins": 0,
            "losses": 0,
            "history": []
        }
        save_player_data(data)
        curr_tourney = data['syndicate_data']['current_tournament']

    # Get available fighters (Player + Recruited Mercs)
    fighters = [{"id": "player", "name": data['username'], "type": "Avatar"}]
    for mid in data['syndicate_data']['recruited_mercs']:
        m = next((x for x in MERCENARIES if x['id'] == mid), None)
        if m: fighters.append(m)

    return render_template('syndicate_lobby.html', syndicate=syndicate, tournament=curr_tourney, fighters=fighters)

@app.route('/syndicate/start_match', methods=['POST'])
@login_required
def start_syndicate_match():
    syndicate_id = request.form.get('syndicate_id')
    fighter_id = request.form.get('fighter_id')
    
    data = load_player_data()
    syndicate = next((s for s in SYNDICATES if s['id'] == syndicate_id), None)
    
    # Determine abilities based on fighter
    p_abilities = []
    p_name = data['username']
    
    if fighter_id == 'player':
        # Use player's equipped abilities from main lobby? Or simplify for Chapter 2
        # Let's use the first 3 owned abilities for now or random if none, to simplify "loadout" step
        p_abilities = data['owned_abilities'][:3]
    else:
        # Use Mercenary abilities
        merc = next((m for m in MERCENARIES if m['id'] == fighter_id), None)
        if merc:
            p_name = merc['name']
            # Convert ability IDs to objects
            for aid in merc['abilities']:
                a_def = next((a for a in ALL_POSSIBLE_ABILITIES if a['id'] == aid), None)
                if a_def: p_abilities.append(a_def)
    
    # Init Match
    user_email = session.get('user_email')
    game_key = f"syn_{user_email}"
    
    # Random opponent from syndicate
    opp_name = f"Syndicate Trader {random.randint(1,99)}"
    
    with game_state_lock:
        GAMES[game_key] = _initialize_match_state(game_key, p_name, opp_name, p_abilities, [], 0, market_id=None, systemic_risk_mode=False)
        GAMES[game_key]['status'] = 'active'
        GAMES[game_key]['syndicate_id'] = syndicate_id
        GAMES[game_key]['game_type'] = 'syndicate'
        
        # Apply Passive Merc Bonuses if any
        if fighter_id != 'player':
             GAMES[game_key]['merc_passive'] = merc['passive'] # Handle in loop
    
    session['room_code'] = game_key
    session['role'] = 'host'
    start_thread()
    return redirect(url_for('battle'))

@app.route('/black_market')
@login_required
def black_market():
    data = load_player_data()
    owned = [a['id'] for a in data['owned_abilities']]
    
    # Get all legendaries that require tokens/emblems
    all_legendaries = []
    
    # Chapter 1 Rogue Legendaries
    all_legendaries.extend(ROGUE_LEGENDARIES)
    
    # Chapter 3 Legendaries (from ALL_POSSIBLE_ABILITIES)
    ch3_legendaries = [a for a in ALL_POSSIBLE_ABILITIES if a.get('token_req_id') and a.get('behavior_type') in ['legendary_systemic', 'legendary_passive']]
    all_legendaries.extend(ch3_legendaries)
    
    # Also include any other legendaries with token requirements
    other_token_legendaries = [a for a in ALL_POSSIBLE_ABILITIES if a.get('token_req_id') and a.get('rarity') == 'Legendary' and a not in ch3_legendaries]
    all_legendaries.extend(other_token_legendaries)
    
    return render_template('black_market.html', player_data=data, legendaries=all_legendaries, owned_ids=owned)

@app.route('/buy_black_market', methods=['POST'])
@login_required
def buy_black_market():
    aid = request.form.get('ability_id')
    data = load_player_data()
    
    # Search in all legendaries
    tokens = data.get('rogue_run', {}).get('tokens', [])
    emblems = data.get('syndicate_data', {}).get('emblems', [])
    all_tokens = tokens + emblems
    
    # Find in ROGUE_LEGENDARIES first
    item = next((i for i in ROGUE_LEGENDARIES if i['id'] == aid), None)
    
    # If not found, search in ALL_POSSIBLE_ABILITIES
    if not item:
        item = next((a for a in ALL_POSSIBLE_ABILITIES if a.get('id') == aid and a.get('token_req_id')), None)
    
    if item and data['net_worth'] >= item['cost']:
        # Check token requirements
        has_token1 = item['token_req_id'] in all_tokens
        has_token2 = True
        if item.get('token_req_id2'):
            has_token2 = item['token_req_id2'] in all_tokens
        
        if has_token1 and has_token2:
            data['net_worth'] -= item['cost']
            ab_copy = item.copy()
            # Remove token requirement fields
            ab_copy.pop('token_req_id', None)
            ab_copy.pop('token_req_name', None)
            ab_copy.pop('token_req_id2', None)
            ab_copy.pop('token_req_name2', None)
            
            # Set defaults if missing
            if 'type' not in ab_copy:
                ab_copy['type'] = 'legendary'
            if 'rarity' not in ab_copy:
                ab_copy['rarity'] = 'Legendary'
            if 'hotkey' not in ab_copy:
                ab_copy['hotkey'] = 'X'
            
            data['owned_abilities'].append(ab_copy)
            save_player_data(data)
    return redirect(url_for('black_market'))

# ... Multiplayer Routes (Keep as is, but update initialize call) ...
@app.route('/multiplayer')
@login_required
def multiplayer_menu(): return render_template('multiplayer_menu.html')

@app.route('/create_room', methods=['POST'])
@login_required
def create_room():
    code = str(random.randint(1000, 9999))
    while code in GAMES: code = str(random.randint(1000, 9999))
    data = load_player_data()
    host_username = data.get('username', 'Host')
    host_player_id = data.get('player_id')
    game_mode = request.form.get('game_mode', 'one_v_one')  # Default to 1v1
    
    with game_state_lock:
        GAMES[code] = {
            "status": "lobby", 
            "host_ready": False, 
            "guest_ready": False, 
            "guest_joined": False, 
            "wager": 1000, 
            "host_abilities": [], 
            "guest_abilities": [], 
            "abilities_enabled": True,
            "is_multiplayer": True,
            "host_username": host_username,
            "host_player_id": host_player_id,
            "game_mode": game_mode,  # 'one_v_one', 'free_for_all', or 'coop'
            "max_players": 2 if game_mode == 'one_v_one' else 4,
            "num_rounds": 1,  # Default to 1 round
            "current_round": 0,
            "round_wins": {"host": 0, "guest": 0},  # Track round wins for each player
            "players": [{"username": host_username, "player_id": host_player_id, "role": "host", "ready": False}],
            "teams": None if game_mode == 'free_for_all' else {"team1": [], "team2": []}  # For coop mode
        }
    session['room_code'] = code; session['role'] = 'host'
    start_thread()
    return redirect(url_for('multiplayer_lobby', room_code=code))

@app.route('/join_room', methods=['POST'])
@login_required
def join_room():
    code = request.form.get('room_code')
    data = load_player_data()
    guest_username = data.get('username', 'Guest')
    guest_player_id = data.get('player_id')
    with game_state_lock:
        if code in GAMES and GAMES[code]['status'] == 'lobby':
            g = GAMES[code]
            # Check if player already in room
            players = g.get('players', [])
            existing_player = next((p for p in players if p.get('player_id') == guest_player_id), None)
            
            if not existing_player:
                # Add player to players list
                players.append({"username": guest_username, "player_id": guest_player_id, "role": "guest", "ready": False})
                g['players'] = players
                
                # For backwards compatibility, also set guest_joined if it's the first guest
                if not g.get('guest_joined'):
                    g['guest_joined'] = True
                    g['guest_username'] = guest_username
                    g['guest_player_id'] = guest_player_id
                    g['is_multiplayer'] = True
                    session['role'] = 'guest'
                else:
                    # Additional players joining (for 4-player modes)
                    session['role'] = f'player_{len(players)}'
            
            session['room_code'] = code
            return redirect(url_for('multiplayer_lobby', room_code=code))
    return "Room Not Found", 404

@app.route('/quick_match', methods=['POST'])
@login_required
def quick_match():
    user_email = session.get('user_email')
    if not user_email: return redirect(url_for('multiplayer_menu'))
    
    with game_state_lock:
        # Remove from queue if already there
        if user_email in QUICK_MATCH_QUEUE:
            QUICK_MATCH_QUEUE.remove(user_email)
            return redirect(url_for('multiplayer_menu'))
        
        # Check if there's someone waiting
        if QUICK_MATCH_QUEUE:
            # Match found!
            host_email = QUICK_MATCH_QUEUE.pop(0)
            code = str(random.randint(1000, 9999))
            while code in GAMES: code = str(random.randint(1000, 9999))
            
            GAMES[code] = {
                "status": "lobby", 
                "host_ready": False, 
                "guest_ready": False, 
                "guest_joined": True, 
                "wager": 1000, 
                "host_abilities": [], 
                "guest_abilities": [],
                "host_email": host_email,
                "guest_email": user_email,
                "abilities_enabled": True
            }
            session['room_code'] = code
            session['role'] = 'guest'
            start_thread()
            return redirect(url_for('multiplayer_lobby', room_code=code))
        else:
            # No one waiting, join queue
            QUICK_MATCH_QUEUE.append(user_email)
            code = str(random.randint(1000, 9999))
            while code in GAMES: code = str(random.randint(1000, 9999))
            
            GAMES[code] = {
                "status": "lobby", 
                "host_ready": False, 
                "guest_ready": False, 
                "guest_joined": False, 
                "wager": 1000, 
                "host_abilities": [], 
                "guest_abilities": [],
                "host_email": user_email,
                "abilities_enabled": True
            }
            session['room_code'] = code
            session['role'] = 'host'
            start_thread()
            return redirect(url_for('multiplayer_lobby', room_code=code))

@app.route('/multiplayer/lobby/<room_code>')
@login_required
def multiplayer_lobby(room_code):
    if session.get('room_code') != room_code: return redirect(url_for('multiplayer_menu'))
    data = load_player_data()
    with game_state_lock:
        if not GAMES.get(room_code): return redirect(url_for('multiplayer_menu'))
        game = GAMES[room_code]
    game_mode = game.get('game_mode', 'one_v_one')
    # Check if user is admin
    is_admin = session.get('user_email') == 'rennelldenton2495@gmail.com'
    return render_template('multiplayer_lobby.html', room_code=room_code, is_host=(session.get('role') == 'host'), guest_joined=game['guest_joined'], abilities=data['owned_abilities'], markets=MARKETS, abilities_enabled=game.get('abilities_enabled', True), game_mode=game_mode, max_players=game.get('max_players', 2), is_admin=is_admin)

@app.route('/multiplayer/state/<room_code>')
def multiplayer_state(room_code):
    with game_state_lock:
        g = GAMES.get(room_code)
        if not g: return jsonify({"error": "No Room"}), 404
        
        market_name = "Pending..."
        if g.get('market_id'):
            m = next((m for m in MARKETS if m['id'] == g['market_id']), None)
            if m: market_name = m['name']

        return jsonify({
            "guest_joined": g.get('guest_joined'), 
            "host_ready": g.get('host_ready'), 
            "guest_ready": g.get('guest_ready'), 
            "wager": g.get('wager'), 
            "game_started": (g.get('status') == 'active'),
            "market_name": market_name,
            "abilities_enabled": g.get('abilities_enabled', True),
            "game_mode": g.get('game_mode', 'one_v_one'),
            "num_rounds": g.get('num_rounds', 1),
            "players": g.get('players', [])
        })

@app.route('/multiplayer/set_game_mode', methods=['POST'])
@login_required
def set_game_mode():
    data = request.get_json()
    code = data.get('room_code')
    game_mode = data.get('game_mode', 'free_for_all')
    
    with game_state_lock:
        if code not in GAMES: return jsonify({"success": False, "message": "Room not found"})
        g = GAMES[code]
        if session.get('role') != 'host': return jsonify({"success": False, "message": "Only host can change game mode"})
        
        g['game_mode'] = game_mode
        if game_mode == 'one_v_one':
            g['max_players'] = 2
            g['teams'] = None
        elif game_mode == 'coop':
            g['max_players'] = 4
            if 'teams' not in g or g['teams'] is None:
                g['teams'] = {"team1": [], "team2": []}
        else:  # free_for_all
            g['max_players'] = 4
            g['teams'] = None
        
        return jsonify({"success": True})

@app.route('/multiplayer/toggle_abilities', methods=['POST'])
@login_required
def toggle_abilities():
    data = request.json
    code = data.get('room_code')
    abilities_enabled = data.get('abilities_enabled', True)
    
    with game_state_lock:
        if code not in GAMES: return jsonify({"success": False})
        if session.get('role') != 'host': return jsonify({"success": False})
        GAMES[code]['abilities_enabled'] = abilities_enabled
        return jsonify({"success": True})

@app.route('/multiplayer/ready', methods=['POST'])
def multiplayer_ready():
    data = request.json
    code = data.get('room_code'); abilities = data.get('abilities', []); wager = data.get('wager'); role = session.get('role')
    market_id = data.get('market_id')
    abilities_enabled = data.get('abilities_enabled', True)
    
    with game_state_lock:
        if code not in GAMES: return jsonify({"success": False})
        g = GAMES[code]
        if role == 'host': 
            g['host_ready'] = True; g['host_abilities'] = abilities; g['wager'] = wager
            if market_id: g['market_id'] = market_id
            g['abilities_enabled'] = abilities_enabled
            num_rounds = data.get('num_rounds', 1)
            if num_rounds: g['num_rounds'] = max(1, min(10, int(num_rounds)))  # Clamp between 1-10
        else: g['guest_ready'] = True; g['guest_abilities'] = abilities
        if g['host_ready'] and g['guest_ready']:
            # Only add abilities if enabled
            h_abs = []
            g_abs = []
            if g.get('abilities_enabled', True):
                h_abs = [Ability(**next((a for a in ALL_POSSIBLE_ABILITIES if a['id']==id), {})) for id in g['host_abilities']]
                g_abs = [Ability(**next((a for a in ALL_POSSIBLE_ABILITIES if a['id']==id), {})) for id in g['guest_abilities']]
            # Use selected market_id or default
            mid = g.get('market_id', 'blue_chip')
            new_state = _initialize_match_state(code, "Host", "Guest", h_abs, g_abs, int(g['wager']), market_id=mid)
            new_state['status'] = 'active'
            new_state['abilities_enabled'] = g.get('abilities_enabled', True)
            new_state['is_multiplayer'] = True
            new_state['host_username'] = g.get('host_username', 'Host')
            new_state['guest_username'] = g.get('guest_username', 'Guest')
            new_state['game_mode'] = g.get('game_mode', 'one_v_one')
            new_state['num_rounds'] = g.get('num_rounds', 1)
            new_state['current_round'] = 0
            new_state['round_wins'] = {"host": 0, "guest": 0}
            GAMES[code] = new_state
        return jsonify({"success": True})

@app.route('/multiplayer/admin_solo_test', methods=['POST'])
def admin_solo_test():
    """Admin-only: Start game solo for testing without waiting for other players"""
    if session.get('user_email') != 'rennelldenton2495@gmail.com':
        return jsonify({"success": False, "message": "Admin only"})
    
    data = request.json
    code = data.get('room_code')
    abilities = data.get('abilities', [])
    wager = data.get('wager', 0)
    market_id = data.get('market_id', 'blue_chip')
    abilities_enabled = data.get('abilities_enabled', True)
    num_rounds = data.get('num_rounds', 1)
    
    with game_state_lock:
        if code not in GAMES: return jsonify({"success": False})
        g = GAMES[code]
        
        # Create AI bot to play against
        h_abs = []
        g_abs = []
        if abilities_enabled:
            h_abs = [Ability(**next((a for a in ALL_POSSIBLE_ABILITIES if a['id']==id), {})) for id in abilities]
        
        new_state = _initialize_match_state(code, "Host", "AI Test Bot", h_abs, g_abs, int(wager), market_id=market_id)
        new_state['status'] = 'active'
        new_state['abilities_enabled'] = abilities_enabled
        new_state['is_multiplayer'] = True
        new_state['host_username'] = g.get('host_username', 'Admin')
        new_state['guest_username'] = 'AI Test Bot'
        new_state['game_mode'] = g.get('game_mode', 'one_v_one')
        new_state['num_rounds'] = max(1, min(10, int(num_rounds)))
        new_state['current_round'] = 0
        new_state['round_wins'] = {"host": 0, "guest": 0}
        new_state['ai_bot']['is_ai'] = True  # Mark as AI for bot logic
        GAMES[code] = new_state
        
    return jsonify({"success": True})

# ... Game Routes ...
@app.route('/battle')
@login_required
def battle():
    code = session.get('room_code')
    if code not in GAMES: return redirect(url_for('index'))
    
    # Theme Logic
    game = GAMES[code]
    theme = None
    if game.get('game_type') == 'rogue' and game.get('boss_id'):
        boss = next((b for b in ROGUE_BOSSES if b['id'] == game['boss_id']), None)
        if boss: 
            theme = boss.get('theme').copy()
            # Override bg to use the boss image
            theme['bg'] = f"url('{url_for('static', filename='images/' + boss['image'])}') no-repeat center center fixed"
        
    role = session.get('role', 'host')
    boss_id = game.get('boss_id') if game.get('game_type') == 'rogue' else None
    
    # Get usernames for multiplayer display
    data = load_player_data()
    p1_username = None
    p2_username = None
    if game.get('is_multiplayer'):
        # Get usernames from game state (stored when room was created/joined)
        p1_username = game.get('host_username', game.get('player', {}).get('name', 'Host'))
        p2_username = game.get('guest_username', game.get('ai_bot', {}).get('name', 'Guest'))
    else:
        # Single player - use current user's username
        p1_username = data.get('username', 'Player')
        p2_username = 'AI Opponent'
    
    return render_template('battle.html', theme=theme, player_role=role, boss_id=boss_id, 
                          p1_username=p1_username, p2_username=p2_username, player_data=data)

@app.route('/state')
def get_state():
    code = session.get('room_code')
    role = session.get('role')
    with game_state_lock:
        if code not in GAMES: return jsonify({})
        g = GAMES[code]
        if g.get('status') == 'lobby': return jsonify({})
        s = copy.deepcopy(g)
        s['game_log'] = list(s['game_log']); s['player']['game_log'] = list(s['player']['game_log']); s['ai_bot']['game_log'] = list(s['ai_bot']['game_log'])
        
        # Check if it's multiplayer (not AI) - multiplayer has role 'host' or 'guest'
        is_multiplayer = role in ['host', 'guest']
        
        if role == 'guest': s['player'], s['ai_bot'] = s['ai_bot'], s['player']
        
        # Always hide opponent abilities (both AI and multiplayer for fairness)
        if 'abilities_equipped' in s['ai_bot']:
            del s['ai_bot']['abilities_equipped']
        if 'abilities_cooldown' in s['ai_bot']:
            del s['ai_bot']['abilities_cooldown']
        
        # Add multiplayer flag
        s['is_multiplayer'] = is_multiplayer
            
        del s['player_action_queue']; del s['ai_action_queue']
        return jsonify(s)

@app.route('/action/<action_type>', methods=['POST'])
def action(action_type):
    code = session.get('room_code'); role = session.get('role')
    with game_state_lock:
        if code not in GAMES: return jsonify({})
        g = GAMES[code]
        data = request.json
        val = data.get('quantity') if action_type in ['buy','sell'] else data.get('ability_id')
        q_type = 'ability' if action_type == 'use_ability' else action_type
        if role == 'host': g['player_action_queue'].append((q_type, val))
        else: g['ai_action_queue'].append((q_type, val))
        return jsonify({"success": True})

@app.route('/round_results')
@login_required
def round_results():
    code = session.get('room_code')
    g = GAMES.get(code)
    if not g: return redirect(url_for('index'))
    p1_pnl = g['player']['match_pnl']
    p2_pnl = g['ai_bot']['match_pnl']
    
    if g.get('is_tutorial'):
        # Check for Tutorial/Academy Match
        tips = [
            "Tip: Remember, buying when the candle is red often yields better profits.",
            "Tip: Use your abilities strategically to manipulate the market.",
            "Tip: Keep an eye on the clock! Don't get stuck holding stock at tick 300.",
            "Tip: Watching the AI's moves in the log can give you a hint about market trends."
        ]
        selected_tip = random.choice(tips)
        winner = "Player (Training Complete)" if p1_pnl > p2_pnl else "AI Instructor (Try Again!)"
        
        # Do NOT save player data (no money lost/gained)
        return render_template('round_results.html', winner=winner, player_pnl=p1_pnl, ai_pnl=p2_pnl, is_academy=True, tip=selected_tip, next_url="/trader_academy")

    # Regular Match Processing
    data = load_player_data()
    
    # Track first loss for welcome sound (only set flag, don't mark as played yet - will be marked when played on menu)
    if p1_pnl < p2_pnl and not data.get('first_loss_welcome_played', False):
        data['first_loss_welcome_played'] = True
        save_player_data(data)
    
    # --- LOAN SHARK LOGIC ---
    loan = data.get('loan', {})
    if loan.get('active', False):
        loan['matches_remaining'] -= 1
        if loan['matches_remaining'] < 0:
            # Deadline passed - Garnishment!
            # If player profited, take cut. If player lost, well... they just accrue interest maybe? 
            # Request said "percentage will be taken out of there money from each match"
            # Let's take it from net_worth directly, simulating a "wage garnishment"
            if p1_pnl > 0:
                penalty = p1_pnl * loan['interest_rate']
                p1_pnl -= penalty # Reduce winnings visual
                # Note: The actual cash update happens below when we add pnl to net_worth (in rogue mode)
                # But wait, rogue mode adds profit. We need to handle this carefully.
                
                # Let's just deduct from existing Net Worth to be safe and clear
                garnishment = data['net_worth'] * (loan['interest_rate'] / 2) # Stronger penalty? Or match based?
                # User: "percentage will be taken out of there money from each match"
                garnishment = max(0, p1_pnl * loan['interest_rate']) # Take from winnings
                
                # If they didn't win, maybe take from stash?
                if p1_pnl <= 0:
                    garnishment = 1000 # Minimum penalty fee
                
                data['net_worth'] -= garnishment
                
        data['loan'] = loan # Save state back
    # ------------------------

    if g.get('game_type') == 'rogue':
        run = data.get('rogue_run', {})
        boss_id = g.get('boss_id')
        boss_def = next((b for b in ROGUE_BOSSES if b['id'] == boss_id), None)
        if p1_pnl > p2_pnl:
            # Player won - give choice between heart or token
            if boss_id not in run['defeated_bosses']: 
                run['defeated_bosses'].append(boss_id)
                # Award $20,000 for defeating boss
                data['net_worth'] += 20000
                save_player_data(data)
                # Store reward choice in session for next page
                session['boss_reward_choice'] = None
                session['boss_id'] = boss_id
                session['boss_token_id'] = boss_def['token_id']
                session['boss_token_name'] = boss_def['token_name']
                profit = max(0, p1_pnl)
                data['net_worth'] += profit
                
                # Check for Tier 5 unique ending after Chapter 3 boss defeat (admin always gets it)
                admin_user = is_admin_user()
                ft_data = data.get('founding_trader', {})
                effective_tier = 5 if admin_user else ft_data.get('tier', 0)
                show_unique_ending = False
                unique_ending_text = None
                if effective_tier >= 5 and boss_id.startswith('boss_ch3_'):
                    show_unique_ending = True
                    unique_ending_text = f"🌟 LEGENDARY FOUNDING TRADER ENDING 🌟\n\n" \
                                       f"As a Tier 5 Founding Trader, you've transcended the ordinary market.\n" \
                                       f"Your victory over {boss_def['name']} echoes through interconnected markets worldwide.\n" \
                                       f"The systemic risk you've mastered has become your greatest strength.\n\n" \
                                       f"You are not just a trader—you are a market force of nature.\n" \
                                       f"Welcome to the true elite."
                    if not ft_data.get('unique_ending_unlocked', False):
                        ft_data['unique_ending_unlocked'] = True
                        data['founding_trader'] = ft_data
                
                save_player_data(data)
                return render_template('round_results.html', winner="PLAYER (BOSS DEFEATED)", player_pnl=p1_pnl, ai_pnl=p2_pnl, next_url="/rogue/menu", show_reward_choice=True, boss_token_name=boss_def['token_name'], show_unique_ending=show_unique_ending, unique_ending_text=unique_ending_text)
            else:
                # Already defeated, just give profit
                profit = max(0, p1_pnl)
                data['net_worth'] += profit
                save_player_data(data)
                return render_template('round_results.html', winner="PLAYER (VICTORY)", player_pnl=p1_pnl, ai_pnl=p2_pnl, next_url="/rogue/menu")
        else:
            run['hearts'] -= 1
            if run['hearts'] <= 0:
                # Player lost all 4 hearts - reset hearts, clear boss progress, lose $10,000
                run['hearts'] = 4  # Restore all 4 hearts
                run['defeated_bosses'] = []  # Clear boss progress
                data['net_worth'] = max(0, data['net_worth'] - 10000)  # Lose $10,000 (can't go below 0)
                run['active'] = False
                save_player_data(data)
                return render_template('round_results.html', winner="BOSS (ALL HEARTS LOST - RUN RESET)", player_pnl=p1_pnl, ai_pnl=p2_pnl, next_url="/rogue/start_run", reset_message="Hearts restored, boss progress cleared, -$10,000")
        save_player_data(data)
        if not run.get('active', True): 
            return render_template('round_results.html', winner="BOSS (RUN OVER)", player_pnl=p1_pnl, ai_pnl=p2_pnl, next_url="/rogue/start_run")
        else: 
            return render_template('round_results.html', winner="BOSS (HEART LOST)", player_pnl=p1_pnl, ai_pnl=p2_pnl, next_url="/rogue/menu")

    if g.get('game_type') == 'syndicate':
        tourney = data['syndicate_data']['current_tournament']
        syn_id = g.get('syndicate_id')
        syndicate = next((s for s in SYNDICATES if s['id'] == syn_id), None)
        
        # Determine Series Length
        needed_wins = 3 # Default bo5 (first to 3)
        if syndicate['match_type'] == 'bo3': needed_wins = 2
        elif syndicate['match_type'] == 'bo7': needed_wins = 4
        
        if p1_pnl > p2_pnl:
            tourney['wins'] += 1
            tourney['history'].append('W')
        else:
            tourney['losses'] += 1
            tourney['history'].append('L')
            
        save_player_data(data)
        
        # Check Series End
        if tourney['wins'] >= needed_wins:
            # Win Series - give choice between heart or emblem
            if syndicate['token_id'] not in data['syndicate_data']['emblems']:
                data['syndicate_data']['emblems'].append(syndicate['token_id'])
                # Check if all Chapter 2 syndicates defeated (4 emblems) - unlock Chapter 3 premise
                if len(data['syndicate_data']['emblems']) >= 4:
                    premises_shown = data.get('premises_shown', {})
                    if not premises_shown.get('chapter_3', False):
                        # Will show Chapter 3 premise next time they click ROGUE TRADER
                        pass
                session['syndicate_reward_choice'] = None
                session['syndicate_token_id'] = syndicate['token_id']
                session['syndicate_token_name'] = syndicate['token_name']
                # Award $20,000 for defeating syndicate
                data['net_worth'] += 20000
                data['syndicate_data']['current_tournament'] = None
                save_player_data(data)
                return render_template('round_results.html', winner="SYNDICATE DEFEATED!", player_pnl=p1_pnl, ai_pnl=p2_pnl, next_url="/rogue/menu", show_reward_choice=True, is_syndicate=True, boss_token_name=syndicate['token_name'])
            else:
                data['syndicate_data']['current_tournament'] = None
                save_player_data(data)
                return render_template('round_results.html', winner="SYNDICATE DEFEATED!", player_pnl=p1_pnl, ai_pnl=p2_pnl, next_url="/rogue/menu")
        elif tourney['losses'] >= needed_wins:
            # Lose Series
            data['syndicate_data']['current_tournament'] = None # Reset
            save_player_data(data)
            return render_template('round_results.html', winner="ELIMINATED FROM TOURNAMENT", player_pnl=p1_pnl, ai_pnl=p2_pnl, next_url="/rogue/menu")
        else:
            # Continue
            return render_template('round_results.html', winner="ROUND COMPLETE", player_pnl=p1_pnl, ai_pnl=p2_pnl, next_url=f"/syndicate/lobby/{syn_id}")

    # Regular match (non-boss, non-syndicate) - Calculate rewards
    if g.get('game_type') not in ['rogue', 'syndicate']:
        winner = g.get('winner', 'Unknown')
        wager = g.get('wager', 0)
        is_multiplayer = g.get('is_multiplayer', False)
        game_mode = g.get('game_mode', 'one_v_one')
        num_rounds = g.get('num_rounds', 1)
        current_round = g.get('current_round', 0)
        
        # Determine if player won based on total cash
        p1_total_cash = g.get('p1_total_cash', 0)
        p2_total_cash = g.get('p2_total_cash', 0)
        
        # For coop mode, calculate team totals
        if game_mode == 'coop' and is_multiplayer:
            # Team 1: host + player 3, Team 2: guest + player 4
            # For now, assume 2v2 (will need to extend for 4 players)
            team1_total = p1_total_cash  # Host team
            team2_total = p2_total_cash  # Guest team
            player_won = (session.get('role') == 'host' and team1_total > team2_total) or \
                        (session.get('role') == 'guest' and team2_total > team1_total)
        else:
            # Adjust for guest role (swap values)
            if session.get('role') == 'guest':
                p1_total_cash, p2_total_cash = p2_total_cash, p1_total_cash
            
            player_won = False
            if winner == 'Player':
                player_won = True
            elif session.get('role') == 'host' and p1_total_cash > p2_total_cash:
                player_won = True
            elif session.get('role') == 'guest' and p2_total_cash > p1_total_cash:
                player_won = True
        
        actual_pnl = p1_pnl if session.get('role') != 'guest' else p2_pnl
        
        # Handle rounds system
        if num_rounds > 1 and is_multiplayer:
            # Update round wins
            round_wins = g.get('round_wins', {"host": 0, "guest": 0})
            if player_won:
                round_wins[session.get('role', 'host')] = round_wins.get(session.get('role', 'host'), 0) + 1
            else:
                opponent_role = 'guest' if session.get('role') == 'host' else 'host'
                round_wins[opponent_role] = round_wins.get(opponent_role, 0) + 1
            
            g['round_wins'] = round_wins
            g['current_round'] = current_round + 1
            
            # Check if match is complete
            if current_round + 1 >= num_rounds:
                # Match complete - determine overall winner
                host_wins = round_wins.get('host', 0)
                guest_wins = round_wins.get('guest', 0)
                overall_winner = 'host' if host_wins > guest_wins else 'guest'
                player_won_match = (session.get('role') == overall_winner)
                
                # Get opponent info for match history
                host_username = g.get('host_username', 'Host')
                guest_username = g.get('guest_username', 'Guest')
                
                # Apply wager (x2 for coop)
                wager_multiplier = 2 if game_mode == 'coop' else 1
                if player_won_match:
                    if wager > 0:
                        data['net_worth'] += wager * wager_multiplier
                    # Only track wins/losses for multiplayer matches
                    if is_multiplayer:
                        data['wins'] = data.get('wins', 0) + 1
                        # Store match history with opponent info
                        if 'match_history' not in data:
                            data['match_history'] = []
                        opponent_username = guest_username if session.get('role') == 'host' else host_username
                        opponent_id = g.get('guest_player_id') if session.get('role') == 'host' else g.get('host_player_id')
                        data['match_history'].append({
                            "result": "win",
                            "opponent_username": opponent_username,
                            "opponent_id": opponent_id,
                            "timestamp": time.time(),
                            "wager": wager * wager_multiplier
                        })
                else:
                    if wager > 0:
                        pnl_reduction = max(0, actual_pnl) * 0.5
                        loss_amount = max(0, (wager * wager_multiplier) - pnl_reduction)
                        # Deduct from capital (cash) in game state for the losing player
                        if session.get('role') == 'host':
                            if 'capital' in g.get('player', {}):
                                g['player']['capital'] = max(0, g['player']['capital'] - loss_amount)
                        else:  # guest
                            if 'capital' in g.get('ai_bot', {}):
                                g['ai_bot']['capital'] = max(0, g['ai_bot']['capital'] - loss_amount)
                        data['net_worth'] -= loss_amount
                    # Only track wins/losses for multiplayer matches
                    if is_multiplayer:
                        data['losses'] = data.get('losses', 0) + 1
                        # Store match history with opponent info
                        if 'match_history' not in data:
                            data['match_history'] = []
                        opponent_username = guest_username if session.get('role') == 'host' else host_username
                        opponent_id = g.get('guest_player_id') if session.get('role') == 'host' else g.get('host_player_id')
                        data['match_history'].append({
                            "result": "loss",
                            "opponent_username": opponent_username,
                            "opponent_id": opponent_id,
                            "timestamp": time.time(),
                            "wager": wager * wager_multiplier
                        })
                save_player_data(data)
                
                # Store match complete flag for round_results page
                session['match_complete'] = True
                session['round_wins'] = round_wins
                session['current_round'] = current_round + 1
                session['num_rounds'] = num_rounds
            else:
                # More rounds to go - reset game state for next round
                # Reset the match state but keep round wins
                with game_state_lock:
                    # Reset round_over and winner for next round
                    g['round_over'] = False
                    g['winner'] = None
                    g['current_tick'] = 0
                    g['current_stock_price'] = 100.00
                    g['price_history'] = [{"tick":0, "price":100.0, "open":100, "close":100, "high":100, "low":100}]
                    g['game_log'] = deque(["Market Open! Round " + str(current_round + 2)], maxlen=20)
                    
                    # Reset players to starting state
                    p1 = Trader("Host", is_ai=False)
                    host_abs = g.get('host_abilities', [])
                    if host_abs:
                        p1.abilities_equipped = [Ability(**next((a for a in ALL_POSSIBLE_ABILITIES if a['id']==id), {})) for id in host_abs]
                    p2 = Trader("Guest", is_ai=False)
                    guest_abs = g.get('guest_abilities', [])
                    if guest_abs:
                        p2.abilities_equipped = [Ability(**next((a for a in ALL_POSSIBLE_ABILITIES if a['id']==id), {})) for id in guest_abs]
                    g['player'] = p1.to_dict()
                    g['ai_bot'] = p2.to_dict()
                    g['player_action_queue'] = deque()
                    g['ai_action_queue'] = deque()
                    g['market_info'] = {}
                
                save_player_data(data)
                # Store round info for round_results page
                session['match_complete'] = False
                session['round_wins'] = round_wins
                session['current_round'] = current_round + 1
                session['num_rounds'] = num_rounds
        else:
                # Single round or non-multiplayer
            if player_won:
                # Player won - gets wager amount (x2 for coop)
                wager_multiplier = 2 if game_mode == 'coop' else 1
                if wager > 0:
                    data['net_worth'] += wager * wager_multiplier
                # Only track wins/losses for multiplayer matches
                if is_multiplayer:
                    data['wins'] = data.get('wins', 0) + 1
                    # Store match history with opponent info
                    if 'match_history' not in data:
                        data['match_history'] = []
                    host_username = g.get('host_username', 'Host')
                    guest_username = g.get('guest_username', 'Guest')
                    opponent_username = guest_username if session.get('role') == 'host' else host_username
                    opponent_id = g.get('guest_player_id') if session.get('role') == 'host' else g.get('host_player_id')
                    data['match_history'].append({
                        "result": "win",
                        "opponent_username": opponent_username,
                        "opponent_id": opponent_id,
                        "timestamp": time.time(),
                        "wager": wager * wager_multiplier
                    })
                save_player_data(data)
            else:
                # Player lost - loses wager amount, but positive PnL reduces the loss
                wager_multiplier = 2 if game_mode == 'coop' else 1
                if wager > 0:
                    # Positive PnL reduces loss (up to 50% reduction)
                    pnl_reduction = max(0, actual_pnl) * 0.5  # 50% of positive PnL reduces loss
                    loss_amount = max(0, (wager * wager_multiplier) - pnl_reduction)
                    # Deduct from capital (cash) first, then net_worth
                    if session.get('role') == 'host':
                        if 'capital' in g.get('player', {}):
                            g['player']['capital'] = max(0, g['player']['capital'] - loss_amount)
                    else:  # guest
                        if 'capital' in g.get('ai_bot', {}):
                            g['ai_bot']['capital'] = max(0, g['ai_bot']['capital'] - loss_amount)
                    data['net_worth'] -= loss_amount
                # Only track wins/losses for multiplayer matches
                if is_multiplayer:
                    data['losses'] = data.get('losses', 0) + 1
                    # Store match history with opponent info
                    if 'match_history' not in data:
                        data['match_history'] = []
                    host_username = g.get('host_username', 'Host')
                    guest_username = g.get('guest_username', 'Guest')
                    opponent_username = guest_username if session.get('role') == 'host' else host_username
                    opponent_id = g.get('guest_player_id') if session.get('role') == 'host' else g.get('host_player_id')
                    data['match_history'].append({
                        "result": "loss",
                        "opponent_username": opponent_username,
                        "opponent_id": opponent_id,
                        "timestamp": time.time(),
                        "wager": wager * wager_multiplier
                    })
                save_player_data(data)
        
        # Store winner/loser usernames for display
        if is_multiplayer:
            host_username = g.get('host_username', 'Host')
            guest_username = g.get('guest_username', 'Guest')
            if player_won:
                winner_username = host_username if session.get('role') == 'host' else guest_username
                loser_username = guest_username if session.get('role') == 'host' else host_username
            else:
                winner_username = guest_username if session.get('role') == 'host' else host_username
                loser_username = host_username if session.get('role') == 'host' else guest_username
            session['winner_username'] = winner_username
            session['loser_username'] = loser_username
        else:
            session['winner_username'] = 'Player' if player_won else 'AI Opponent'
            session['loser_username'] = 'AI Opponent' if player_won else 'Player'
    
    # Get winner/loser usernames from session (set above)
    winner_username = session.get('winner_username', 'Winner')
    loser_username = session.get('loser_username', 'Loser')
    
    # Get round information for template
    num_rounds = session.get('num_rounds', 1)
    current_round = session.get('current_round', 1)
    match_complete = session.get('match_complete', True)
    round_wins = session.get('round_wins', {})
    
    if session.get('role') == 'guest': p1_pnl, p2_pnl = p2_pnl, p1_pnl
    
    # Trading Buddy Tips (Tier 3+ or Admin)
    trading_buddy_tip = None
    admin_user = is_admin_user()
    ft_data = data.get('founding_trader', {})
    effective_tier = 5 if admin_user else ft_data.get('tier', 0)
    if effective_tier >= 3 and (ft_data.get('trading_buddy_enabled', False) or admin_user):
        import random
        player_won = p1_pnl > p2_pnl
        if player_won:
            tips = [
                "Great trade! You managed your risk well. Remember: consistency beats big wins.",
                "Well executed! Consider taking partial profits next time to lock in gains.",
                "Nice work! Your timing was spot on. Keep an eye on market volatility.",
                "Excellent performance! Don't forget to review what worked in this match.",
                "Outstanding! Your ability usage was strategic. Keep building on this success."
            ]
        else:
            tips = [
                "Tough loss, but every trade is a learning opportunity. Review your entry and exit points.",
                "Don't let this discourage you. Consider using stop-loss strategies to limit downside.",
                "Losses happen to everyone. Focus on risk management and position sizing.",
                "Analyze what went wrong - was it timing, ability usage, or market conditions?",
                "Remember: cutting losses early is often better than holding and hoping."
            ]
        trading_buddy_tip = random.choice(tips)
    
    return render_template('round_results.html', 
                          winner=g.get('winner', 'Unknown'), 
                          player_pnl=p1_pnl, 
                          ai_pnl=p2_pnl, 
                          winner_username=winner_username, 
                          loser_username=loser_username,
                          num_rounds=num_rounds,
                          current_round=current_round,
                          match_complete=match_complete,
                          round_wins=round_wins,
                          trading_buddy_tip=trading_buddy_tip)

@app.route('/choose_reward', methods=['POST'])
@login_required
def choose_reward():
    choice = request.form.get('choice')
    data = load_player_data()
    
    if choice == 'heart':
        # Restore heart (for rogue bosses) or add heart to rogue run (for syndicates)
        run = data.get('rogue_run', {})
        if run.get('hearts', 0) < 4:
            run['hearts'] = min(4, run.get('hearts', 0) + 1)
        save_player_data(data)
        session.pop('boss_reward_choice', None)
        session.pop('syndicate_reward_choice', None)
        session.pop('boss_token_id', None)
        session.pop('boss_token_name', None)
        session.pop('syndicate_token_id', None)
        session.pop('syndicate_token_name', None)
        return redirect(url_for('rogue_menu'))
    elif choice == 'token':
        # Take token/emblem
        if session.get('boss_token_id'):
            # Rogue boss reward - ensure rogue_run exists and add token
            if 'rogue_run' not in data:
                data['rogue_run'] = {"active": True, "hearts": 4, "tokens": [], "defeated_bosses": []}
            token_id = session.get('boss_token_id')
            if 'tokens' not in data['rogue_run']:
                data['rogue_run']['tokens'] = []
            if token_id not in data['rogue_run']['tokens']:
                data['rogue_run']['tokens'].append(token_id)
            save_player_data(data)
            session.pop('boss_token_id', None)
            session.pop('boss_token_name', None)
            session.pop('boss_reward_choice', None)
        elif session.get('syndicate_token_id'):
            # Syndicate reward - ensure syndicate_data exists and add emblem
            if 'syndicate_data' not in data:
                data['syndicate_data'] = {"active": False, "recruited_mercs": [], "emblems": [], "current_tournament": None}
            token_id = session.get('syndicate_token_id')
            if 'emblems' not in data['syndicate_data']:
                data['syndicate_data']['emblems'] = []
            if token_id not in data['syndicate_data']['emblems']:
                data['syndicate_data']['emblems'].append(token_id)
            save_player_data(data)
            session.pop('syndicate_token_id', None)
            session.pop('syndicate_token_name', None)
            session.pop('syndicate_reward_choice', None)
        return redirect(url_for('rogue_menu'))
    
    return redirect(url_for('rogue_menu'))

# --- PREMISE SLIDESHOW ROUTES ---

CHAPTER_PREMISES = {
    1: [
        "In the shadows of Wall Street, a new breed of trader emerged.",
        "They didn't play by the rules—they made their own.",
        "Welcome to the Black Market Blitz.",
        "Six bosses control the underground markets.",
        "Defeat them all to claim your place at the top.",
        "But beware: one wrong trade could end your run forever."
    ],
    2: [
        "With the bosses defeated, a new threat emerges.",
        "The Syndicates—organized crime families of finance.",
        "They control entire market sectors through manipulation.",
        "Four powerful organizations await your challenge.",
        "Each requires a different strategy to conquer.",
        "Prove you're more than just a rogue trader."
    ],
    3: [
        "The final layer of corruption reveals itself.",
        "Global institutions that control systemic risk itself.",
        "These are the puppet masters of the entire financial system.",
        "Four legendary institutions stand between you and true dominance.",
        "They don't just control markets—they create them.",
        "This is where legends are made... or broken."
    ]
}

@app.route('/premise/<int:chapter>')
@login_required
def premise_slideshow(chapter):
    data = load_player_data()
    premises_shown = data.get('premises_shown', {})
    
    # Check if already shown
    key = f'chapter_{chapter}'
    if premises_shown.get(key, False):
        # Already shown, skip to menu
        if not data.get('rogue_run', {}).get('active'):
            data['rogue_run'] = {"active": True, "hearts": 4, "tokens": [], "defeated_bosses": []}
            save_player_data(data)
        return redirect(url_for('rogue_menu'))
    
    premises = CHAPTER_PREMISES.get(chapter, [])
    return render_template('premise_slideshow.html', chapter=chapter, premises=premises)

@app.route('/premise/complete/<int:chapter>', methods=['POST'])
@login_required
def premise_complete(chapter):
    data = load_player_data()
    premises_shown = data.get('premises_shown', {})
    premises_shown[f'chapter_{chapter}'] = True
    data['premises_shown'] = premises_shown
    
    # Start run if not active
    if not data.get('rogue_run', {}).get('active'):
        data['rogue_run'] = {"active": True, "hearts": 4, "tokens": [], "defeated_bosses": []}
    
    save_player_data(data)
    return redirect(url_for('rogue_menu'))

# --- TRADER ACADEMY ROUTES ---

@app.route('/trader_academy')
@login_required
def trader_academy():
    return render_template('trader_academy.html')

@app.route('/academy/demo/<feature>')
@login_required
def academy_demo(feature):
    user_email = session.get('user_email')
    room_code = f"demo_{user_email}"
    
    # Pre-select abilities based on feature
    abilities = []
    # Default set
    default_abs = [
        next((a for a in ALL_POSSIBLE_ABILITIES if a['id'] == 'pump'), None),
        next((a for a in ALL_POSSIBLE_ABILITIES if a['id'] == 'dump'), None),
        next((a for a in ALL_POSSIBLE_ABILITIES if a['id'] == 'rumor'), None)
    ]
    abilities = [a for a in default_abs if a]

    # Initialize a specific demo match
    with game_state_lock:
        GAMES[room_code] = _initialize_match_state(room_code, "Player (Student)", "AI Instructor", abilities, [], 0, market_id=None, systemic_risk_mode=False)
        GAMES[room_code]['status'] = 'active'
        GAMES[room_code]['is_tutorial'] = True
    
    session['room_code'] = room_code
    session['role'] = 'host'
    start_thread()
    
    return redirect(url_for('mock_battle', highlight=feature))

@app.route('/academy/practice_match')
@login_required
def academy_practice_match():
    """Start a practice match from the trader academy"""
    user_email = session.get('user_email')
    room_code = f"practice_{user_email}"
    
    data = load_player_data()
    
    # Use default abilities for practice
    default_abs = [
        next((a for a in ALL_POSSIBLE_ABILITIES if a['id'] == 'pump'), None),
        next((a for a in ALL_POSSIBLE_ABILITIES if a['id'] == 'dump'), None),
        next((a for a in ALL_POSSIBLE_ABILITIES if a['id'] == 'rumor'), None)
    ]
    abilities = [a for a in default_abs if a]
    
    # Initialize practice match
    with game_state_lock:
        GAMES[room_code] = _initialize_match_state(room_code, "Player (Student)", "AI Instructor", abilities, [], 0, market_id=None, systemic_risk_mode=False)
        GAMES[room_code]['status'] = 'active'
        GAMES[room_code]['is_tutorial'] = True
    
    session['room_code'] = room_code
    session['role'] = 'host'
    session['is_practice_match'] = True  # Mark as practice match
    session['practice_match_id'] = str(int(time.time() * 1000))  # Unique ID for this practice match
    start_thread()
    
    return redirect(url_for('mock_battle'))

@app.route('/mock_battle')
@login_required
def mock_battle():
    highlight = request.args.get('highlight')
    is_practice = session.get('is_practice_match', False)
    practice_match_id = session.get('practice_match_id', '')
    return render_template('mock_battle.html', highlight=highlight, is_practice_match=is_practice, practice_match_id=practice_match_id)

@app.route('/reset_account', methods=['POST'])
@login_required
def reset_account():
    email = session.get('user_email')
    if not email:
        return redirect(url_for('vault'))
    
    users = load_all_users()
    if email not in users:
        return redirect(url_for('vault'))
    
    # Get current login info (username/password) - DO NOT RESET
    current_username = users[email].get('username', 'Player')
    current_password = users[email].get('password', '')
    
    # Get current player data to preserve username
    data = users[email].get('data', {})
    current_codename = data.get('username', 'Player')
    
    # Reset only the game data, keep login credentials and codename
    # Bankruptcy: Start with $75,000 instead of $100,000
    default_data = get_default_player_data(current_codename)
    default_data['username'] = current_codename  # Keep codename
    default_data['net_worth'] = 75000  # Bankruptcy penalty: reduced starting amount
    
    # Update users dict - preserve login info, reset only data
    users[email]['data'] = default_data
    # Keep username and password unchanged
    users[email]['username'] = current_username
    users[email]['password'] = current_password
    
    save_all_users(users)
    return redirect(url_for('vault'))

@app.route('/add_friend', methods=['POST'])
@login_required
def add_friend():
    user_email = session.get('user_email')
    if not user_email:
        flash('Not logged in', 'error')
        return redirect(url_for('vault'))
    
    data = load_player_data()
    if not data:
        flash('Player data not found', 'error')
        return redirect(url_for('vault'))
    
    friend_identifier = request.form.get('friend_identifier', '').strip()
    if not friend_identifier:
        flash('Please enter a Username or Player ID', 'error')
        return redirect(url_for('vault'))
    
    # Try to find player by username or player_id
    all_users = load_all_users()
    friend_id = None
    friend_username = None
    friend_email = None
    
    # First try as player_id (8 character code)
    if len(friend_identifier) == 8 and friend_identifier.isalnum():
        friend_id = friend_identifier.upper()
        # Verify it exists
        for email, user_data in all_users.items():
            if user_data.get('data', {}).get('player_id') == friend_id:
                friend_username = user_data.get('username', 'Unknown')
                friend_email = email
                break
        if not friend_email:
            flash(f'Player ID {friend_id} not found', 'error')
            return redirect(url_for('vault'))
    else:
        # Try as username
        for email, user_data in all_users.items():
            if user_data.get('username', '').lower() == friend_identifier.lower():
                friend_id = user_data.get('data', {}).get('player_id')
                friend_username = user_data.get('username', 'Unknown')
                friend_email = email
                break
        
        if not friend_id:
            flash(f'Username "{friend_identifier}" not found', 'error')
            return redirect(url_for('vault'))
    
    my_player_id = data.get('player_id', '')
    
    # Can't add yourself
    if friend_id == my_player_id:
        flash('You cannot add yourself as a friend', 'error')
        return redirect(url_for('vault'))
    
    # Check if already a friend
    friends = data.get('friends', [])
    if friend_id in friends:
        flash('This player is already your friend', 'error')
        return redirect(url_for('vault'))
    
    # Check if request already sent
    sent_requests = data.get('friend_requests_sent', [])
    if friend_id in sent_requests:
        flash('Friend request already sent to this player', 'error')
        return redirect(url_for('vault'))
    
    # Check if they already sent us a request (auto-accept)
    received_requests = data.get('friend_requests_received', [])
    if friend_id in received_requests:
        # Auto-accept: both become friends
        if 'friends' not in data:
            data['friends'] = []
        data['friends'].append(friend_id)
        data['friend_requests_received'].remove(friend_id)
        save_player_data(data)
        
        # Add to friend's friends list too
        if friend_email and friend_email in all_users:
            friend_data = all_users[friend_email].get('data', {})
            if 'friends' not in friend_data:
                friend_data['friends'] = []
            if my_player_id not in friend_data['friends']:
                friend_data['friends'].append(my_player_id)
            # Remove from their sent requests
            if 'friend_requests_sent' in friend_data and my_player_id in friend_data['friend_requests_sent']:
                friend_data['friend_requests_sent'].remove(my_player_id)
            all_users[friend_email]['data'] = friend_data
            save_all_users(all_users)
        
        flash(f'You are now friends with {friend_username}!', 'success')
        return redirect(url_for('vault'))
    
    # Send friend request
    if 'friend_requests_sent' not in data:
        data['friend_requests_sent'] = []
    data['friend_requests_sent'].append(friend_id)
    save_player_data(data)
    
    # Add to friend's received requests
    if friend_email and friend_email in all_users:
        friend_data = all_users[friend_email].get('data', {})
        if 'friend_requests_received' not in friend_data:
            friend_data['friend_requests_received'] = []
        if my_player_id not in friend_data['friend_requests_received']:
            friend_data['friend_requests_received'].append(my_player_id)
        all_users[friend_email]['data'] = friend_data
        save_all_users(all_users)
    
    flash(f'Friend request sent to {friend_username}!', 'success')
    return redirect(url_for('vault'))

@app.route('/accept_friend_request', methods=['POST'])
@login_required
def accept_friend_request():
    user_email = session.get('user_email')
    if not user_email:
        flash('Not logged in', 'error')
        return redirect(url_for('vault'))
    
    data = load_player_data()
    if not data:
        flash('Player data not found', 'error')
        return redirect(url_for('vault'))
    
    requester_id = request.form.get('requester_id', '').strip()
    if not requester_id:
        flash('Invalid request', 'error')
        return redirect(url_for('vault'))
    
    # Check if this request exists
    received_requests = data.get('friend_requests_received', [])
    if requester_id not in received_requests:
        flash('Friend request not found', 'error')
        return redirect(url_for('vault'))
    
    my_player_id = data.get('player_id', '')
    
    # Add to friends list
    if 'friends' not in data:
        data['friends'] = []
    if requester_id not in data['friends']:
        data['friends'].append(requester_id)
    
    # Remove from received requests
    data['friend_requests_received'].remove(requester_id)
    save_player_data(data)
    
    # Add to requester's friends list and remove from their sent requests
    all_users = load_all_users()
    for email, user_data in all_users.items():
        if user_data.get('data', {}).get('player_id') == requester_id:
            requester_data = user_data.get('data', {})
            if 'friends' not in requester_data:
                requester_data['friends'] = []
            if my_player_id not in requester_data['friends']:
                requester_data['friends'].append(my_player_id)
            # Remove from their sent requests
            if 'friend_requests_sent' in requester_data and my_player_id in requester_data['friend_requests_sent']:
                requester_data['friend_requests_sent'].remove(my_player_id)
            all_users[email]['data'] = requester_data
            save_all_users(all_users)
            break
    
    flash('Friend request accepted!', 'success')
    return redirect(url_for('vault'))

@app.route('/decline_friend_request', methods=['POST'])
@login_required
def decline_friend_request():
    user_email = session.get('user_email')
    if not user_email:
        flash('Not logged in', 'error')
        return redirect(url_for('vault'))
    
    data = load_player_data()
    if not data:
        flash('Player data not found', 'error')
        return redirect(url_for('vault'))
    
    requester_id = request.form.get('requester_id', '').strip()
    if not requester_id:
        flash('Invalid request', 'error')
        return redirect(url_for('vault'))
    
    # Check if this request exists
    received_requests = data.get('friend_requests_received', [])
    if requester_id not in received_requests:
        flash('Friend request not found', 'error')
        return redirect(url_for('vault'))
    
    my_player_id = data.get('player_id', '')
    
    # Remove from received requests
    data['friend_requests_received'].remove(requester_id)
    save_player_data(data)
    
    # Remove from requester's sent requests
    all_users = load_all_users()
    for email, user_data in all_users.items():
        if user_data.get('data', {}).get('player_id') == requester_id:
            requester_data = user_data.get('data', {})
            if 'friend_requests_sent' in requester_data and my_player_id in requester_data['friend_requests_sent']:
                requester_data['friend_requests_sent'].remove(my_player_id)
            all_users[email]['data'] = requester_data
            save_all_users(all_users)
            break
    
    flash('Friend request declined', 'info')
    return redirect(url_for('vault'))

@app.route('/lend_money', methods=['POST'])
@login_required
def lend_money():
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({"success": False, "message": "Not logged in"})
    
    data = request.get_json()
    friend_id = data.get('friend_id')
    amount = data.get('amount', 0)
    lend_type = data.get('lend_type', 'gift')
    interest_rate = data.get('interest_rate', 0)
    
    if not friend_id or amount <= 0:
        return jsonify({"success": False, "message": "Invalid amount or friend"})
    
    # Load current user data
    users = load_all_users()
    if user_email not in users:
        return jsonify({"success": False, "message": "User not found"})
    
    lender_data = users[user_email]['data']
    
    # Check if user has enough money
    if lender_data.get('net_worth', 0) < amount:
        return jsonify({"success": False, "message": "Insufficient funds"})
    
    # Find friend
    friend_email = None
    friend_username = None
    for email, user_data in users.items():
        if user_data.get('data', {}).get('player_id') == friend_id:
            friend_email = email
            friend_username = user_data.get('username', 'Unknown')
            break
    
    if not friend_email:
        return jsonify({"success": False, "message": "Friend not found"})
    
    # Deduct from lender
    lender_data['net_worth'] -= amount
    
    # Add to borrower
    borrower_data = users[friend_email]['data']
    if lend_type == 'gift':
        # Gift - just add money
        borrower_data['net_worth'] += amount
        save_all_users(users)
        return jsonify({"success": True, "message": f"Gifted ${amount:,.2f} to {friend_username}!"})
    else:
        # Loan - create loan record for borrower
        if 'loans_received' not in borrower_data:
            borrower_data['loans_received'] = []
        
        borrower_data['loans_received'].append({
            'lender_id': lender_data.get('player_id'),
            'lender_username': lender_data.get('username', 'Unknown'),
            'amount': amount,
            'interest_rate': interest_rate,
            'total_due': amount * (1 + interest_rate / 100),
            'paid': False,
            'timestamp': time.time()
        })
        
        # Track loan given for lender
        if 'loans_given' not in lender_data:
            lender_data['loans_given'] = []
        
        lender_data['loans_given'].append({
            'borrower_id': friend_id,
            'borrower_username': friend_username,
            'amount': amount,
            'interest_rate': interest_rate,
            'total_due': amount * (1 + interest_rate / 100),
            'paid': False,
            'timestamp': time.time()
        })
        
        borrower_data['net_worth'] += amount
        save_all_users(users)
        return jsonify({"success": True, "message": f"Loaned ${amount:,.2f} to {friend_username} at {interest_rate}% interest!"})

# Chat System Storage (in-memory for now, can be moved to database)
CHAT_MESSAGES = {
    'global': deque(maxlen=100),  # Last 100 global messages
    'private': {}  # {friend_id: deque(maxlen=50)}
}
CHAT_UNREAD = {}  # {user_email: count}

# Feedback Storage (persistent file-based)
FEEDBACK_FILE = "feedback_data.json"

def load_feedback():
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_feedback(feedback_list):
    with open(FEEDBACK_FILE, 'w') as f:
        json.dump(feedback_list, f, indent=4)

@app.route('/chat/send', methods=['POST'])
@login_required
def chat_send():
    data = request.get_json()
    msg_type = data.get('type', 'global')
    message = data.get('message', '').strip()
    user_email = session.get('user_email')
    
    if not message or not user_email:
        return jsonify({"success": False})
    
    user_data = load_all_users().get(user_email, {})
    username = user_data.get('username', 'Unknown')
    
    if msg_type == 'global':
        CHAT_MESSAGES['global'].append({
            'sender': username,
            'message': message,
            'timestamp': time.time()
        })
        # Increment unread for all other users
        for email in load_all_users().keys():
            if email != user_email:
                CHAT_UNREAD[email] = CHAT_UNREAD.get(email, 0) + 1
    elif msg_type == 'private':
        friend_id = data.get('friend_id')
        if friend_id:
            # Find friend's email
            friend_email = None
            for email, u_data in load_all_users().items():
                if u_data.get('data', {}).get('player_id') == friend_id:
                    friend_email = email
                    break
            
            if friend_email:
                key = f"{min(user_email, friend_email)}_{max(user_email, friend_email)}"
                if key not in CHAT_MESSAGES['private']:
                    CHAT_MESSAGES['private'][key] = deque(maxlen=50)
                CHAT_MESSAGES['private'][key].append({
                    'sender': username,
                    'message': message,
                    'timestamp': time.time()
                })
                # Increment unread for friend
                CHAT_UNREAD[friend_email] = CHAT_UNREAD.get(friend_email, 0) + 1
    
    return jsonify({"success": True})

@app.route('/chat/messages')
@login_required
def chat_messages():
    user_email = session.get('user_email')
    return jsonify({
        'global': list(CHAT_MESSAGES['global'])
    })

@app.route('/chat/private/<friend_id>')
@login_required
def chat_private(friend_id):
    user_email = session.get('user_email')
    # Find friend's email
    friend_email = None
    for email, u_data in load_all_users().items():
        if u_data.get('data', {}).get('player_id') == friend_id:
            friend_email = email
            break
    
    if friend_email:
        key = f"{min(user_email, friend_email)}_{max(user_email, friend_email)}"
        messages = list(CHAT_MESSAGES['private'].get(key, []))
        return jsonify({'messages': messages})
    return jsonify({'messages': []})

@app.route('/chat/friends')
@login_required
def chat_friends():
    data = load_player_data()
    friends = data.get('friends', [])
    all_users = load_all_users()
    friend_list = []
    
    for friend_id in friends:
        for email, user_data in all_users.items():
            if user_data.get('data', {}).get('player_id') == friend_id:
                friend_list.append({
                    'player_id': friend_id,
                    'username': user_data.get('username', 'Unknown')
                })
                break
    
    return jsonify({'friends': friend_list})

@app.route('/chat/unread')
@login_required
def chat_unread():
    user_email = session.get('user_email')
    count = CHAT_UNREAD.get(user_email, 0)
    CHAT_UNREAD[user_email] = 0  # Reset after reading
    return jsonify({'count': count})

# --- Feedback System ---
@app.route('/feedback/send', methods=['POST'])
@login_required
def feedback_send():
    data = request.get_json()
    feedback_type = data.get('type', 'other')
    message = data.get('message', '').strip()
    user_email = session.get('user_email')
    
    if not message or not user_email:
        return jsonify({"success": False, "message": "Please enter a message"})
    
    user_data = load_all_users().get(user_email, {})
    username = user_data.get('username', 'Unknown')
    player_id = user_data.get('data', {}).get('player_id', 'Unknown')
    
    feedback_list = load_feedback()
    feedback_list.append({
        'id': len(feedback_list) + 1,
        'type': feedback_type,
        'message': message,
        'username': username,
        'player_id': player_id,
        'email': user_email,
        'timestamp': time.time(),
        'read': False,
        'resolved': False
    })
    save_feedback(feedback_list)
    
    return jsonify({"success": True, "message": "Feedback sent successfully!"})

@app.route('/admin/feedback')
@login_required
def admin_feedback():
    # Only admin can view feedback
    if session.get('user_email') != 'rennelldenton2495@gmail.com':
        flash('Admin access required', 'error')
        return redirect(url_for('index'))
    
    feedback_list = load_feedback()
    # Sort by timestamp (newest first)
    feedback_list.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    
    return render_template('admin_feedback.html', feedback=feedback_list)

@app.route('/admin/feedback/mark_read/<int:feedback_id>', methods=['POST'])
@login_required
def admin_feedback_mark_read(feedback_id):
    if session.get('user_email') != 'rennelldenton2495@gmail.com':
        return jsonify({"success": False})
    
    feedback_list = load_feedback()
    for fb in feedback_list:
        if fb.get('id') == feedback_id:
            fb['read'] = True
            break
    save_feedback(feedback_list)
    return jsonify({"success": True})

@app.route('/admin/feedback/mark_resolved/<int:feedback_id>', methods=['POST'])
@login_required
def admin_feedback_mark_resolved(feedback_id):
    if session.get('user_email') != 'rennelldenton2495@gmail.com':
        return jsonify({"success": False})
    
    feedback_list = load_feedback()
    for fb in feedback_list:
        if fb.get('id') == feedback_id:
            fb['resolved'] = True
            break
    save_feedback(feedback_list)
    return jsonify({"success": True})

@app.route('/admin/feedback/delete/<int:feedback_id>', methods=['POST'])
@login_required
def admin_feedback_delete(feedback_id):
    if session.get('user_email') != 'rennelldenton2495@gmail.com':
        return jsonify({"success": False})
    
    feedback_list = load_feedback()
    feedback_list = [fb for fb in feedback_list if fb.get('id') != feedback_id]
    save_feedback(feedback_list)
    return jsonify({"success": True})

if __name__ == '__main__':
    start_thread()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug, use_reloader=False, host='0.0.0.0', port=port)
