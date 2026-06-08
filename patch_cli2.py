f = "src/cli.py"
s = open(f).read()

a = s.replace("        fetch_top_rated_last_month,\n", "        fetch_most_played,\n", 1)
assert a != s; s = a
a = s.replace(
"""        get_game_metacritic,
        get_game_rating,
        format_metacritic,
        format_rating,
    )""",
"""        get_game_added,
        format_added,
    )""", 1)
assert a != s; s = a
a = s.replace("        build_games_rated,\n", "        build_games_most_played,\n", 1)
assert a != s; s = a

a = s.replace(
'''    console.log("\\nFetching top rated games from last month...")
    rated = fetch_top_rated_last_month(limit=3)
    if rated:
        console.print(f"[bold gold1]Top {len(rated)} rated last month:[/bold gold1]")
        for g in rated:
            mc = get_game_metacritic(g)
            score = format_metacritic(mc) if mc else format_rating(get_game_rating(g))
            console.print(f"  [gold1]*[/gold1] {get_game_title(g)} - {score}")''',
'''    console.log("\\nFetching most played games...")
    most_played = fetch_most_played(limit=3)
    if most_played:
        console.print(f"[bold gold1]Top {len(most_played)} most played:[/bold gold1]")
        for g in most_played:
            console.print(f"  [gold1]*[/gold1] {get_game_title(g)} - {format_added(get_game_added(g))} players")''',
1)
assert a != s; s = a

a = s.replace(
'''    if rated:
        console.log("Slide 4: Top rated last month...")
        slides.append(str(build_games_rated(
            rated, today, get_game_title, get_game_poster_url,
            get_game_metacritic, format_metacritic,
            get_game_rating, format_rating
        )))
        console.log(f"[green]ok[/green] {slides[-1]}")''',
'''    if most_played:
        console.log("Slide 4: Most played...")
        slides.append(str(build_games_most_played(
            most_played, today, get_game_title, get_game_poster_url,
            get_game_added, format_added
        )))
        console.log(f"[green]ok[/green] {slides[-1]}")''',
1)
assert a != s; s = a

open(f, "w").write(s)
import py_compile; py_compile.compile(f, doraise=True)
print("cli.py patched + compiles")
