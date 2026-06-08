f = "src/generate/games_carousel.py"
s = open(f).read()

old_top10 = s[s.index("def build_games_top10"): s.index("# SLIDE 3 - YOUR PICKS")]
new_top10 = (
'def build_games_top10(games: list, month_date: date,\n'
'                      get_title, get_poster_url) -> Path:\n'
'    canvas = _base()\n'
'    header_bottom = _header(canvas, "TOP 10 RELEASES")\n'
'\n'
'    pad = 10\n'
'    gt = header_bottom + 14\n'
'    gb = H - 78\n'
'\n'
'    count = min(len(games), 10)\n'
'    if count == 0:\n'
'        _footer(canvas, month_date.strftime("%B %Y").upper())\n'
'        return _save(canvas, "games_02_top10")\n'
'\n'
'    cols = 4 if count >= 5 else max(count, 1)\n'
'    rows = (count + cols - 1) // cols\n'
'    cw = (W - pad*(cols+1)) // cols\n'
'    ch = (gb - gt - pad*(rows-1)) // rows\n'
'\n'
'    for idx in range(count):\n'
'        row = idx // cols\n'
'        items_in_row = min(cols, count - row*cols)\n'
'        total_w = items_in_row*cw + (items_in_row-1)*pad\n'
'        start_x = (W - total_w) // 2\n'
'        col_in_row = idx - row*cols\n'
'        x1 = start_x + col_in_row*(cw+pad)\n'
'        y1 = gt + row*(ch+pad)\n'
'        game = games[idx]\n'
'        _place_poster(canvas, get_poster_url(game),\n'
'                     (x1, y1, x1+cw, y1+ch),\n'
'                     ACCENT, idx+1, get_title(game))\n'
'\n'
'    _footer(canvas, month_date.strftime("%B %Y").upper())\n'
'    return _save(canvas, "games_02_top10")\n'
'\n'
'\n'
)
assert old_top10 in s
s = s.replace(old_top10, new_top10, 1)

old_rated = s[s.index("# SLIDE 4 - TOP RATED LAST MONTH"):]
new_rated = (
'# SLIDE 4 - MOST PLAYED\n'
'def build_games_most_played(games: list, month_date: date,\n'
'                            get_title, get_poster_url,\n'
'                            get_added, format_added) -> Path:\n'
'    canvas = _base()\n'
'    header_bottom = _header(canvas, "MOST PLAYED")\n'
'    draw = ImageDraw.Draw(canvas)\n'
'\n'
'    sf = _font("small", 30)\n'
'    draw.text((W//2, header_bottom+22), "BIGGEST PLAYER BASES",\n'
'              font=sf, fill=GOLD+(160,), anchor="mm")\n'
'\n'
'    pad = 20\n'
'    gt = header_bottom + 52\n'
'    gb = H - 78\n'
'    games = games[:3]\n'
'    n = max(len(games), 1)\n'
'    cw = (W - pad*(n+1)) // n\n'
'    ch = gb - gt\n'
'\n'
'    for idx, game in enumerate(games):\n'
'        x1 = pad + idx*(cw+pad)\n'
'        y1 = gt\n'
'\n'
'        rank_colors = [GOLD, (192,192,192), (205,127,50)]\n'
'        border_color = rank_colors[idx] if idx < len(rank_colors) else GRAY_DIM\n'
'\n'
'        _place_poster(canvas, get_poster_url(game),\n'
'                     (x1, y1, x1+cw, y1+ch),\n'
'                     border_color, idx+1, get_title(game))\n'
'\n'
'        n_added = get_added(game)\n'
'        if n_added:\n'
'            _pill_overlay(canvas, (x1, y1, x1+cw, y1+ch),\n'
'                         f"{format_added(n_added)} players", border_color, subfont_size=28)\n'
'\n'
'    _footer(canvas, month_date.strftime("%B %Y").upper())\n'
'    return _save(canvas, "games_04_most_played")\n'
)
assert old_rated in s
s = s.replace(old_rated, new_rated, 1)

open(f, "w").write(s)
import py_compile; py_compile.compile(f, doraise=True)
print("games_carousel.py patched + compiles")
