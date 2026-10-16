cd /tmp/claude-0/-home-claude/cfd36e3b-6336-59bd-8793-440a2c26d284/scratchpad/overlap/kalshi
date -u +%s > /tmp/claude-0/-home-claude/cfd36e3b-6336-59bd-8793-440a2c26d284/scratchpad/overlap/refresh_start.txt
python3 -I /tmp/claude-0/-home-claude/cfd36e3b-6336-59bd-8793-440a2c26d284/scratchpad/scripts/kget.py series k_games_q.json KXNFLGAME,KXNHLGAME,KXMLBGAME,KXNCAAFGAME,KXEPLGAME,KXUCLGAME,KXLALIGAGAME,KXSERIEAGAME,KXBUNDESLIGAGAME,KXLIGUE1GAME,KXMLSGAME,KXUFCFIGHT > /dev/null 2>&1 &
python3 -I /tmp/claude-0/-home-claude/cfd36e3b-6336-59bd-8793-440a2c26d284/scratchpad/scripts/kget.py series k_futures_q.json KXMLB,KXSB,KXF1,KXF1CONSTRUCTORS,KXPRESNOMR,KXPRESNOMD,KXPRESPERSON,KXBTCMAXY,KXBTCMINY,CONTROLH,CONTROLS,KXWTIMAX,KXNASDAQ100Y,KXINXY,KXINXPOS,KXLAYOFFSYINFO,KXRATECUTCOUNT,KXAAAGASMAX,KXLEADERSOUT,KXMUSKNW,KXGOVCA,KXFRENCHPRES,KXARREST,KXOSCARPIC,KXVENEZUELALEADER,KXMAYORLA,SENATEME,SENATENC,SENATETX,KXU3MAX > /dev/null 2>&1 &
cd /tmp/claude-0/-home-claude/cfd36e3b-6336-59bd-8793-440a2c26d284/scratchpad/overlap/poly && python3 -I /tmp/claude-0/-home-claude/cfd36e3b-6336-59bd-8793-440a2c26d284/scratchpad/scripts/pget.py slugs p_quotes.json quote_slugs.json > /dev/null 2>&1 &
wait
date -u +%s > /tmp/claude-0/-home-claude/cfd36e3b-6336-59bd-8793-440a2c26d284/scratchpad/overlap/refresh_end.txt
