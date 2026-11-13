# Security

This tool reads untrusted repositories by design. Two properties matter most, and each has a
test.

Nothing in a scanned repository is ever executed. It only opens files and reads the history through the git program, which it starts with the project's own settings that can start another program (signature checkers, pager, hooks, file-system monitor, external diff) overridden on every call, and only from a `.git` directory inside the scanned folder: git is told that directory and may not search parent folders, and a repository whose configuration includes another file or whose pointers lead outside the folder is not read (cases S-35 to S-37). It never runs a project's own scripts, tests or installers. Case S-26 plants such a setting and checks that it starts nothing.

Nothing from a scanned repository reaches the dashboard unescaped. A submission cannot inject
script into the page a judge opens (case V-05).

The scanner decides line by line what a scorecard may quote. If a line holds a credential shape from `SECRET_PATTERNS` in `src/quiet_counsel/scan.py`, or a word from `SECRET_WORD_RE` beside it (such as `secret`, `token`, `password` or `api_key`), the card quotes none of it: the flag keeps its file and line, the excerpt reads `<line withheld>`, and you open the line to read it. `secrets.NAME` does not count as such a word. A repository can add such a word to keep a line's text off the card; the flag still fires and cites the line. A `.scanignore` pattern shown in the card is withheld the same way, and a hook event name is left out of the `agent-hook` detail when its line would be withheld or cannot be found.

Every other line is quoted as written, so a credential in a format on neither list, such as a bare value or a private-key body, can appear in a card. File and directory names, frontmatter keys and README claim phrases such as `40 skills` are not quoted lines: a credential shape in one is replaced with `<redacted>`, and a citation through such a name reads as broken (case S-18). Text beyond a file-read limit, including a final line the limit cuts in two, is not read, so it cannot appear in a card and cannot raise a flag. A repository written to defeat this, for example with unusual line separators or escaped spellings, can still get text from such a line onto a card; the rule protects against accidents and gives no protection against a hostile author's own text.

This is an aid, with no guarantee that a scorecard holds no secret. Case S-25 puts a marker in each place of a test tree that a card can quote, beside a listed word, and fails if the marker reaches the card, the dashboard or `integrity` output; a control tree without the word must quote the marker in each of those places; case S-20 plants fake credentials at the length limits listed in its test. Read a scorecard before you share it.

Report security problems through GitHub private vulnerability reporting: on the repository page,
open the Security tab and choose "Report a vulnerability". Do not open a public issue for a
security problem.
