# data.json format (compact). See examples/ for working files of every slide type.
Top: slot, snap, cover{k,big,bc,sub,h,seed,gp}, slides[], cta{extra[title,text]}, refs{key:[source name,url]}, claims[[claim,value,ref_key,as_of,confidence]], caption.
Slide: {t, k (kicker), h (title with markup), src (sources text) or f (full footer), ...}
board: rows ["name|value|sub|color|ratio"]   cards: cards ["n|title|text"]   bignum: big, bc, sub, bullets[]
movers: rows ["TICK|pct|reason|time"]   movers2: gain/lose ["TICK|name|pct"]   chipbars: rows ["TICK|gain|share"], avg   linechart: pts ["label|value"], note
Colors: white amber red green cyan slate. Cover gp = share of green tiles (0-1). CTA sources default to the refs used in claims.
