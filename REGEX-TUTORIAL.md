# Regex Tutorial for YaRSS2

A practical guide to regular expressions, from the basics through to
production-quality subscription filters. Written for YaRSS2 users, but the
fundamentals carry over to any tool that uses Python-style or
JavaScript-style regex.

## Contents

1. [Why regex](#why-regex)
2. [How YaRSS2 uses regex](#how-yarss2-uses-regex)
3. [Literal matching](#literal-matching)
4. [Metacharacters — the special ones](#metacharacters--the-special-ones)
5. [Character classes](#character-classes)
6. [Quantifiers](#quantifiers)
7. [Anchors](#anchors)
8. [Alternation](#alternation)
9. [Groups and capture](#groups-and-capture)
10. [Greedy vs lazy](#greedy-vs-lazy)
11. [Escaping special characters](#escaping-special-characters)
12. [Case sensitivity](#case-sensitivity)
13. [Common mistakes](#common-mistakes)
14. [Testing your regex](#testing-your-regex)
15. [Cookbook — real-world recipes](#cookbook--real-world-recipes)
16. [The `last_match` trap](#the-last_match-trap)
17. [Python vs JavaScript differences](#python-vs-javascript-differences)
18. [Further reading](#further-reading)

---

## Why regex

An RSS feed might contain hundreds of torrent titles per day. You want
to download some and ignore the rest. A regex (regular expression) is a
compact pattern that says "match titles that look like this."

Instead of writing logic like "if the title contains 'Breaking Bad' and
'1080p' and 'S05' and doesn't contain 'x265'...", you write a single
pattern:

```
^Breaking Bad S05E\d+ 1080p
```

One line, clear intent. That's regex.

## How YaRSS2 uses regex

In the Subscription editor there are two regex fields:

- **Regex include** — titles matching this are considered for download
- **Regex exclude** — titles matching this are filtered out even if
  they matched the include rule

Both fields are optional. Leaving include empty means "match everything."
Leaving exclude empty means "filter out nothing."

YaRSS2's backend uses **Python's `re` module**, which is close to but not
identical to JavaScript's regex. The v2.2.2+ live preview uses JavaScript
RegExp for speed, so in very rare edge cases a pattern might behave
slightly differently in preview vs production. For 99% of patterns used
to filter torrent titles, they're identical.

A match uses `re.search()`, not `re.match()` — meaning the pattern can
match **anywhere** in the title, not just from the start. Use anchors
(`^` and `$`) if you need to pin the pattern to the beginning or end.

## Literal matching

The simplest regex is just plain text. It matches anywhere in the
string.

```
Breaking Bad
```

This matches any title containing the text `Breaking Bad`. Case-sensitive
by default, but YaRSS2 has an "Ignore case" checkbox that makes matching
case-insensitive.

Most characters in regex are **literals** — they match themselves.
`abc123` matches the literal text `abc123`.

A handful of characters are **metacharacters** — they have special
meaning and don't match themselves directly. These are:

```
.  ^  $  *  +  ?  (  )  [  ]  {  }  |  \
```

To match a literal metacharacter, put a backslash before it: `\.` matches
a literal period, `\+` matches a literal plus sign, and so on.

## Metacharacters — the special ones

### `.` — any character

Matches exactly one character, any character. Doesn't match a newline
by default.

```
.ing
```

Matches `ring`, `king`, `sing`, `Xing` — anything with one character
followed by `ing`.

Think of `.` as a wildcard for a single character.

### `\` — escape

Turns a special character into a literal, or a letter into a special
class (see below).

```
\.
```

Matches a literal period — which is useful because torrent titles often
have a lot of periods: `Breaking.Bad.S01E01.1080p`.

### `|` — alternation ("or")

Matches one side or the other.

```
cat|dog
```

Matches titles containing either `cat` or `dog`.

## Character classes

A character class is a set of characters enclosed in square brackets.
It matches exactly one character from the set.

### Basic classes

```
[abc]
```

Matches one character that's `a`, `b`, or `c`.

```
[0-9]
```

Matches one digit. The `-` inside brackets creates a range.

```
[a-z]
```

Matches one lowercase letter.

```
[A-Za-z0-9]
```

Matches one alphanumeric character. You can combine multiple ranges and
individual characters in one class.

### Negated classes

A `^` at the start of a class *inverts* it:

```
[^0-9]
```

Matches one character that is **not** a digit.

```
[^aeiou]
```

Matches one non-vowel character.

### Shortcut classes

Regex provides shortcuts for common character classes. The most useful
ones:

| Pattern | Matches                                    |
|---------|--------------------------------------------|
| `\d`    | Any digit — same as `[0-9]`                |
| `\D`    | Any non-digit — same as `[^0-9]`           |
| `\w`    | Any "word" char — letters, digits, `_`     |
| `\W`    | Any non-word char                          |
| `\s`    | Any whitespace — space, tab, newline       |
| `\S`    | Any non-whitespace                         |

So `S\d+E\d+` is shorthand for "the letter S, then one or more digits,
then the letter E, then one or more digits" — matching `S01E01`,
`S11E27`, `S21E02`, etc.

## Quantifiers

A quantifier tells the regex engine **how many times** to match the
preceding element.

| Quantifier | Meaning              |
|------------|----------------------|
| `?`        | Zero or one          |
| `*`        | Zero or more         |
| `+`        | One or more          |
| `{n}`      | Exactly `n` times    |
| `{n,}`     | At least `n` times   |
| `{n,m}`    | Between `n` and `m`  |

### Examples

```
colou?r
```

Matches both `color` and `colour` — the `u` is optional.

```
a+
```

Matches `a`, `aa`, `aaa`, etc. — one or more `a`'s.

```
\d{4}
```

Matches exactly 4 digits — useful for years: `2024`, `2026`.

```
S\d{1,2}E\d{1,3}
```

Matches `S1E1` through `S99E999`. Overkill for TV but shows the syntax.

### The single-char trap

Quantifiers only apply to the preceding element. In `abc+`, the `+` only
applies to `c`, not to the whole word.

```
abc+
```

Matches `abc`, `abcc`, `abccc`, but not `abcabc`.

To repeat a multi-character sequence, wrap it in a group:

```
(abc)+
```

Matches `abc`, `abcabc`, `abcabcabc`.

## Anchors

Anchors don't match characters — they match **positions**.

| Anchor | Meaning                        |
|--------|--------------------------------|
| `^`    | Start of the string (or line)  |
| `$`    | End of the string (or line)    |
| `\b`   | Word boundary                  |
| `\B`   | Non-word-boundary              |

### `^` — start anchor

```
^Breaking Bad
```

Matches only titles that **start with** `Breaking Bad`. Titles like
`The Story of Breaking Bad` won't match.

This is the most useful anchor for feed filtering because titles are
almost always structured as `ShowName SxxExx Resolution ReleaseInfo`,
with the show name at the start.

### `$` — end anchor

```
1080p$
```

Matches titles that **end with** `1080p`. Rarely useful for torrent
titles because they usually have a release group suffix, but handy for
precise matching when needed.

### `\b` — word boundary

`\b` matches the position between a word character (`\w`) and a
non-word character (`\W`). Useful for "match this word, not as part of
another word."

```
\bCat\b
```

Matches `Cat` but not `Category` or `Catastrophe`.

In torrent titles, spaces and periods both create word boundaries, so
`\bBreaking Bad\b` works equivalently to just `Breaking Bad` in practice.

## Alternation

`|` lets you match one of several alternatives.

```
720p|1080p|2160p
```

Matches any of those three resolutions.

Alternation has **low precedence** — it splits the entire regex at the
`|`. To limit its scope, use a group:

```
^(Breaking Bad|Better Call Saul) S\d+E\d+
```

This matches either show name followed by an episode pattern. Without
the group, the `|` would split the whole regex and you'd get strange
results.

## Groups and capture

Parentheses `(...)` do two things:

1. **Group** a sequence so quantifiers or alternation apply to the whole
   thing.
2. **Capture** the matched text for later reference.

For YaRSS2 subscription filters, you almost always want grouping
without needing the capture. Still, it's worth knowing both exist.

### Non-capturing groups

If you only want grouping, use `(?:...)`:

```
^(?:Breaking Bad|Better Call Saul) S\d+E\d+
```

Functionally identical to `(Breaking Bad|Better Call Saul)` for
filtering purposes but slightly more efficient and explicit.

### Back-references

Captured groups can be referenced later with `\1`, `\2`, etc. Useful
occasionally — e.g. matching duplicated words:

```
\b(\w+) \1\b
```

Matches `the the`, `is is`, etc. Rarely needed for feed filtering.

## Greedy vs lazy

Quantifiers default to **greedy** — they match as much as possible.

```
.*p
```

Applied to `1080p WEB DL 720p`, the `.*` greedily matches as much as
it can, so the whole string gets consumed up to the last `p`.

Adding `?` after a quantifier makes it **lazy** — it matches as little
as possible.

```
.*?p
```

Applied to the same string, `.*?` matches as little as possible, so
it stops at the first `p` it can — matching just `1080p`.

Torrent titles usually don't need lazy matching, but it's good to know
the difference when debugging.

## Escaping special characters

If you want to match a character that's special in regex, precede it
with a backslash.

```
1\.2\.3
```

Matches the literal string `1.2.3` (without escaping, `.` would match
any character).

Common cases in torrent titles:

- `.` → `\.` (periods between words in dot-separated titles)
- `+` → `\+` (release tags like `HDR10+`)
- `(` `)` → `\(` `\)` (year in parentheses: `\(2024\)`)
- `[` `]` → `\[` `\]` (group tags like `[EZTVx.to]`)

Inside a character class `[...]`, most metacharacters lose their special
meaning and don't need escaping. But `]`, `\`, and `^` (at the start) do.

## Case sensitivity

By default, regex is case-sensitive. `breaking` doesn't match
`Breaking`.

YaRSS2 has two checkboxes in the Subscription editor — **Ignore case
(include)** and **Ignore case (exclude)** — both ticked by default.
With these on, `breaking bad` matches `Breaking Bad`, `BREAKING BAD`,
and `Breaking bad`.

Leave them ticked unless you have a specific reason to be strict.

## Common mistakes

### Forgetting to escape the period

```
Breaking.Bad
```

You might think this matches `Breaking.Bad` but it actually matches
`Breaking` + any character + `Bad`. So it matches `Breaking.Bad`,
`Breaking Bad`, `Breaking_Bad`, even `BreakingXBad`.

Usually fine for feed matching (you *want* to match both dots and
spaces), but be aware of it.

### Using `.` when you mean a literal dot

Same as above. Escape it: `\.` — or use `\s` if you specifically want
whitespace.

### Quantifier after a single char when you meant a group

```
abc+
```

This matches `ab` plus one or more `c`s. It does **not** match `abcabc`.
Use `(abc)+` or `(?:abc)+` if you want to repeat the whole sequence.

### Using `.*` when you don't need it

```
.*Breaking Bad.*
```

Unnecessary. YaRSS2 uses `re.search()`, which finds the pattern
anywhere in the string. `Breaking Bad` alone is equivalent and faster.

### Not anchoring when you should

```
Breaking Bad
```

This matches titles containing `Breaking Bad` anywhere — including
`A Documentary About Breaking Bad`. If you only want actual Breaking Bad
episodes, anchor it:

```
^Breaking Bad S\d+E\d+
```

### Matching too permissively

```
S\d+E\d+
```

Matches S01E01, but also matches titles like `TheSearch01Episode01`
because those characters appear in sequence. The first `\d+` will grab
digits from `TheSearch01` and the next `E` won't match what follows.

Usually fine in practice because most real titles that contain `SxxExx`
really are TV episodes, but be aware. If you need stricter matching, use
word boundaries:

```
\bS\d+E\d+\b
```

### Season range mistake

```
S0[0-9]E\d+
```

This only matches S00-S09. For S00-S99 use:

```
S\d{1,2}E\d+
```

Or for S00-S29 specifically:

```
S[0-2]\d E\d+  ← WRONG, this adds a literal space

S[0-2]\dE\d+   ← correct
```

## Testing your regex

YaRSS2 v2.2.2+ has a **live preview panel** in the Subscription editor.
As you type a regex, matching feed items turn green, excluded items
turn red with strike-through, and a count updates in real time. Use it.

For regex testing outside YaRSS2:

- **[regex101.com](https://regex101.com)** — excellent interactive tester.
  Set the flavor to "Python" for exact parity with YaRSS2's backend.
- **[regexr.com](https://regexr.com)** — another good online tool.
- `python3 -c "import re; print(re.search(r'YOUR_REGEX', 'TEST_TITLE'))"`
  on the command line.

## Cookbook — real-world recipes

All of these assume case-insensitive matching (the default).

### Specific show, all episodes, 1080p only

```
^Breaking Bad S\d+E\d+ 1080p
```

Locked to 1080p, no other resolution will match. `^` ensures the show
name is at the start of the title (prevents matching "Documentary About
Breaking Bad").

### Specific show, new seasons only

Say you want to match S05 and everything going forward:

```
^Breaking Bad S(0[5-9]|[1-9]\d)E\d+
```

Matches S05-S99. When S10 airs it's still matched by the `[1-9]\d` alternative.

### Specific show, exact resolution, exclude x265

Some people avoid x265 because of playback compatibility:

**Include:** `^Breaking Bad S\d+E\d+ 1080p`
**Exclude:** `x265|HEVC`

### Weekly talk show — all episodes

Talk shows use dates in their titles:

```
^(The Daily Show|Jimmy Kimmel|Stephen Colbert) \d{4} \d{2} \d{2}.*1080p
```

Matches any of three shows with a date pattern and 1080p quality.

### Exclude low-quality releases

Shorter release-group tags often correlate with poor encodes:

**Exclude:** `CAM|HDCAM|HDTS|TS|SCREENER`

Use as a global exclude on subscriptions for new movies.

### Match from specific release groups only

If you trust particular groups:

**Include:** `^Show Name S\d+E\d+ 1080p.*(SPARKS|KOGi|CAKES|NTb)$`

Matches 1080p from any of those groups. The `$` anchors to end of
title.

### Match specific season numerically

S07 through S10 only:

```
^Taskmaster S(0[7-9]|10)E\d+ 1080p
```

This is the pattern used to handle "catching up on back-catalog while
skipping the very oldest seasons."

### Movie regex

Movies typically have a year in parens or brackets:

```
^Movie Name \(?\d{4}\)?.*(1080p|2160p).*BluRay
```

The `\(?` and `\)?` make the parens optional (some releases use them,
some don't). `.*` fillers allow arbitrary text between known tokens.

## The `last_match` trap

This isn't about regex, but it confuses everyone at least once — so
it belongs here.

YaRSS2 tracks a `last_match` timestamp per subscription. The behavior
depends on the **Ignore timestamps** checkbox:

- **Unticked (default):** Only match items published after `last_match`.
  Good for "download new episodes going forward."
- **Ticked:** Match every item regardless of publish date. Good for
  one-time back-catalog grabs or when the feed doesn't provide reliable
  publish times.

**The trap:** if you create a new subscription and set `last_match`
accidentally to "now" before fetching, every current item in the feed
has a publish date *older* than "now", so nothing matches. This confused
several users on the original bendikro YaRSS2.

To fix: untick "Ignore timestamps" only *after* the first successful
match, or clear `last_match` manually (edit `yarss2.conf` when the
daemon is stopped and set `"last_match": ""` on the subscription).

For the **first ever run** of a brand-new subscription, ticking "Ignore
timestamps" is often the right move, so historical items in the feed can
be matched. Then untick it after you've got what you want.

## Python vs JavaScript differences

YaRSS2 v2.2.2+ previews regex in JavaScript (in your browser) for speed,
while the daemon matches with Python. For 99% of feed-filtering patterns
they behave identically. Known differences:

| Feature               | Python re       | JavaScript RegExp |
|-----------------------|-----------------|-------------------|
| `\d`, `\w`, `\s`      | ASCII by default in Python 3. | ASCII by default. Use `u` flag for Unicode. |
| Named groups          | `(?P<name>...)` | `(?<name>...)` (ES2018+) |
| Lookbehinds           | `(?<=...)` `(?<!...)` | ES2018+ only, recent browsers |
| Back-references       | `\1` — `\9`, or `\g<name>` | `\1` — `\9` or `\k<name>` |
| `\A` / `\Z`           | Supported        | Not supported — use `^` / `$` |
| Unicode property `\p{...}` | Not in stdlib, use `regex` module | ES2018+ with `u` flag |

For practical torrent-title filtering — anchors, digit classes, literal
matches, alternation, quantifiers, optional groups — the two flavors are
interchangeable.

## Further reading

- **[regex101.com](https://regex101.com)** — interactive tester with
  explanations for every part of your pattern
- **Python's `re` module docs** —
  https://docs.python.org/3/library/re.html — authoritative reference
  for the exact flavor YaRSS2's daemon uses
- **Regex Golf** — https://regex.alf.nu — puzzles that sharpen your
  regex instincts
- **"Mastering Regular Expressions" by Jeffrey Friedl** — the definitive
  deep dive if you want to truly understand the engine

---

**A closing note:** regex is a deep topic with decades of theory behind
it. You don't need any of that theory to write good subscription
filters. Learn the ~15 concepts on this page, test patterns with the
live preview, and you'll be fluent enough for every real-world scenario
you'll hit.
