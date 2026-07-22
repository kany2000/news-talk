#!/usr/bin/env python3
"""News Talk Episode 3 — English version: Why stocks drop when you buy? Why your team loses when you bet?"""

SCENE = [
    # (speaker, text, topic_idx)
    # speaker: 'female' or 'male'
    # topic_idx: 0=intro, 1-7=topic, 8=outro

    # ===== Intro =====
    ("female", "Welcome to News Talk, Episode 3. I'm Xiao Xiao. Today we're talking about something painfully relatable — why does a stock always drop the moment you buy it?", 0),
    ("male",   "And I'm Yun Yang. This hits close to home. Or the World Cup — you bet on your favorite team, and they lose for sure, like clockwork.", 0),
    ("female", "Right! Today we're breaking this down through behavioral economics and psychology.", 0),

    # ===== Topic 1: Confirmation Bias =====
    ("female", "First up — confirmation bias. You remember losses way more vividly than wins.", 1),
    ("male",   "Exactly. You buy a stock, it drops — that memory sticks. But you've also bought stocks that went up — those just get filtered out.", 1),
    ("female", "The story 'I buy, it drops' fits your emotional memory better. You tell your friends, you reinforce the narrative, and eventually you believe it's the universal truth.", 1),
    ("male",   "Statistically, this is selective memory. You ignore the times you didn't buy and it went up, or you bought and it didn't drop. You only focus on the losing cases.", 1),

    # ===== Topic 2: Loss Aversion =====
    ("female", "Number two — loss aversion. This is one of the most famous findings in behavioral economics.", 2),
    ("male",   "Kahneman and Tversky showed that the pain of losing is about two to three times stronger than the pleasure of an equal gain.", 2),
    ("female", "So when your stock drops one percent, it hurts as much as a two to three percent gain feels good. That's why you panic-sell on a dip.", 2),
    ("male",   "And then it rebounds. That's your 'I sell, it goes up' moment. It's not the universe mocking you — it's loss aversion driving your behavior.", 2),
    ("female", "And when it's going up, you FOMO in at the top, then it corrects — 'I buy, it drops.' Classic pattern.", 2),

    # ===== Topic 3: Availability Heuristic =====
    ("female", "Number three — the availability heuristic. The easier something is to recall, the more likely you think it is.", 3),
    ("male",   "The media loves reporting 'retail investors wiped out' or 'market crash incoming' — it gets clicks. You see this every day and start believing losses are the norm.", 3),
    ("female", "The stock market trends upward over the long term, but media amplification makes risk feel omnipresent. The more anxious you are, the worse your decisions get.", 3),
    ("male",   "Lesson one of investing: learn to tune out the noise.", 3),

    # ===== Topic 4: Gambler's Fallacy =====
    ("female", "Number four — the gambler's fallacy. If a stock goes up three days in a row, you think it has to drop on day four.", 4),
    ("male",   "That's a classic probability mistake. Each move in an efficient market is independent — like a coin flip. Five heads in a row, the sixth is still fifty-fifty.", 4),
    ("female", "But our brains are pattern-seekers. We feel 'it's due for a correction' — so we sell, and then it keeps going up.", 4),
    ("male",   "A lot of people who missed the big bull runs were victims of the gambler's fallacy.", 4),

    # ===== Topic 5: World Cup Betting =====
    ("female", "World Cup betting adds another layer. When you bet on your favorite team, it's no longer about probability.", 5),
    ("male",   "That's emotional bias. As a fan, your evaluation is anything but objective. You overestimate their strength and underestimate the opponent.", 5),
    ("female", "You tell yourself, 'I've supported them for years, they've got this' — but the team has no idea who you are and doesn't care if you bet on them.", 5),
    ("male",   "There's also the illusion of control — you read the stats, analyzed the lineup, studied the odds, and convinced yourself you can predict the outcome. But soccer has massive randomness.", 5),
    ("female", "And remember, the house always wins. The bookmaker has the information advantage and the probability edge. Retail investors and gamblers are playing a rigged game.", 5),

    # ===== Topic 6: Hot Hand Fallacy vs Gambler's Fallacy =====
    ("female", "Here's the funny part — your brain holds two contradictory biases at the same time.", 6),
    ("male",   "You mean the hot hand fallacy and the gambler's fallacy? One says 'winning streak means you'll keep winning,' the other says 'winning streak means you're due for a loss.'", 6),
    ("female", "Exactly. Two opposite beliefs, and the same person can fall for both in different contexts. One makes you chase gains, the other makes you sell too early.", 6),
    ("male",   "Plain and simple: human decisions are often driven by emotion and mental shortcuts, not rationality.", 6),

    # ===== Topic 7: How to Break the Cycle =====
    ("female", "So how do we break free from all these biases?", 7),
    ("male",   "First — admit you're irrational. Knowing you have these biases is already a defense.", 7),
    ("female", "Second — use systems, not gut feelings. Dollar-cost averaging is a great example — buy at regular intervals regardless of market conditions.", 7),
    ("male",   "Third — reduce decision frequency. The more you trade, the more chances you have to make mistakes. Buffett says the best strategy is buy and hold.", 7),
    ("female", "Fourth — stay away from leverage and gambling. Don't invest or bet money you can't afford to lose. Fear will hijack your judgment.", 7),
    ("male",   "Finally — zoom out. Over a five or ten year horizon, most short-term noise fades into background.", 7),
    ("female", "Bottom line: 'I buy, it drops' isn't your fault — it's how the human brain evolved. But understanding these biases is the first step to change.", 7),

    # ===== Outro =====
    ("male",   "That's all for this episode of News Talk. Whether you're investing or watching the game, stay rational and stay relaxed.", 8),
    ("female", "Hope your stocks go up and your teams win. See you next time!", 8),
]