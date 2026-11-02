# Test suite

Every case has an ID. A case marked `PASS` has a test method named for it (`test_S04_...`),
and `tests/test_backlog.py` fails the build if one goes missing, if a test claims an ID this
page does not list, or if a documented case is dropped. A case marked `FIELD` has
no proof in CI yet. F-01 to F-03 need a real cohort, corpus or host and are a checklist for the
first real use, recorded in the field-run record. G-08 runs in CI on three operating systems, and
stays `FIELD` until a recorded run exists. A case marked
`ACCEPTED` is a limit, written down so nobody mistakes it for work.

Run:

```sh
TZ=UTC PYTHONPATH=src:tests python3 -m unittest discover -s tests -t tests -v
```

Then once more without a UTF-8 locale, which catches the encoding assumptions Windows would hit:

```sh
LC_ALL=C LANG=C PYTHONCOERCECLOCALE=0 PYTHONUTF8=0 TZ=UTC PYTHONPATH=src:tests \
  python3 -m unittest discover -s tests -t tests
```

Both end `OK (skipped=1)`. The one skip is F-01, which needs a real cohort.

Columns: Given is the state, When the action, Then what can be observed, and Proof the test or
the field step; Status is the last.

## What "generic" means here, and how the suite enforces it

The tool is for anyone judging agent work: an event organiser with a hundred submissions, a
platform team reviewing a harness before adopting it, a maintainer checking their own release.
Nothing in the public tree may assume a person, an organisation, a forge host, a model, a
directory layout or an operating system.

Suite G is the mandatory guard. It fails the build if a machine path, a private e-mail domain or
an internal host name appears anywhere public, and it proves the tool runs from a fresh
directory with nothing but Python. An organisation adds its own forbidden names through
`QUIET_COUNSEL_FORBIDDEN_TOKENS` or a file named by `QUIET_COUNSEL_FORBIDDEN_FILE`, kept outside the repository, so
even the list of what must not appear does not bind the repository.

| who | what they use | suites that protect them |
|---|---|---|
| a hackathon judge with a cohort | `screen`, `dashboard`, the `screen-cohort` skill | B, I, S, C, V, H |
| a platform team adopting a harness | `classify`, `screen`, a deep pass on the rubric | A, S, I, G |
| a maintainer checking a release | `screen`, `check`, `dashboard --strict` | B, C, V, K |
| a security or legal reviewer | the flags and their evidence | S, I, T, M |
| an agent doing any of the above | the skills in `skills/`, the roles in `agents/` | H |
| anyone reading the result | the HTML page | V, E, D |

## Suite G · Generic and portable (mandatory)

| ID | Given | When | Then | Proof | Status |
|---|---|---|---|---|---|
| G-01 | the public tree | the suite runs | no home-directory path, private e-mail domain or internal host; plus every token in `QUIET_COUNSEL_FORBIDDEN_FILE` when set | `test_G01_public_tree_names_no_person_org_or_machine` | PASS |
| G-02 | an empty directory and Python | `sample`, `screen`, `check`, `dashboard` | all exit 0 and a page exists | `test_G02_fresh_directory_stdlib_only_end_to_end` | PASS |
| G-03 | every module in `src` | imports are read | none can reach the network | `test_G03_no_module_can_reach_the_network` | PASS |
| G-04 | the help text and every refusal | read | no product, organisation or person is named | `test_G04_help_and_refusals_name_no_product_org_or_person` | PASS |
| G-05 | a project screened by a relative path | the card is written | the path stays relative and no absolute path of this machine appears | `test_G05_scorecard_carries_no_absolute_path_of_this_machine` | PASS |
| G-06 | a fixed clock | the same tree is screened twice | the cards are identical byte for byte | `test_G06_same_tree_same_scorecard_byte_for_byte` | PASS |
| G-07 | a directory that is not a git repository | screened | history is reported unavailable with a reason, and the run continues | `test_G07_a_directory_that_is_not_a_repository_still_screens` | PASS |
| G-08 | Windows and macOS | the suite runs on each | green on all three operating systems | the `suite` job of the `gate` workflow runs the tests on Ubuntu, Windows and macOS, each with Python 3.11 and 3.13; a recorded run is the evidence, and none is recorded yet | FIELD |
| G-09 | a fixture screened in a process where creating a socket raises, with a fixed clock | the card is compared with a normal run's | identical byte for byte, so the screen needs no network | `test_G09_a_screen_with_every_socket_refused_matches_a_normal_run_byte_for_byte` | PASS |

## Suite A · Classify before scoring

| ID | Given | When | Then | Proof | Status |
|---|---|---|---|---|---|
| A-01 | a skill definition nested three levels down and an install script | classify | catalogue, with the evidence printed | `test_A01_skill_definitions_anywhere_make_a_catalogue` | PASS |
| A-02 | definitions only under `.claude/skills` and `.claude/agents` | classify | both are found | `test_A02_definitions_in_hidden_host_directories_are_found` | PASS |
| A-03 | one skill, plus translations and an installed copy | screen | one distinct skill; three copies reported | `test_A03_translations_and_copies_are_counted_once` | PASS |
| A-04 | checkers and governance documents but no catalogue | classify | the harness score is zero | `test_A04_checkers_without_a_catalogue_do_not_make_a_harness` | PASS |
| A-05 | a catalogue, a checker and release notes | classify | harness | `test_A05_catalogue_plus_checkers_plus_governance_is_a_harness` | PASS |
| A-06 | web sources and a Dockerfile | classify | application | `test_A06_web_sources_make_an_application` | PASS |
| A-07 | an application in a directory named like a harness | classify | application | `test_A07_the_repository_name_is_never_read` | PASS |
| A-08 | an agent, a role with a description, and a command declaring tools | classify | two agents and one command; the command is not an agent | `test_A08_agents_are_found_by_shape_and_commands_are_not_agents` | PASS |
| A-09 | a README and a licence only | classify | unknown | `test_A09_thin_evidence_is_unknown_rather_than_a_guess` | PASS |
| A-10 | an application | screen | A1 and A2 skipped with a written reason; A3 kept | `test_A10_skipped_dimensions_carry_a_reason_and_A3_is_never_skipped` | PASS |
| A-11 | a `pyproject.toml` with `"main"` in a quoted array, and the same file without it | classify | the tool score is the same for both | `test_A11_a_main_string_in_a_python_manifest_is_not_a_package_json_entry` | PASS |

## Suite S · Safety signals

| ID | Given | When | Then | Proof | Status |
|---|---|---|---|---|---|
| S-01 | a cloud-key shape in a deploy script | screen | critical, caps safety at 3, band blocked | `test_S01_a_credential_shape_outside_tests_is_critical_and_caps_safety` | PASS |
| S-02 | the same shape under `tests/` | screen | information only | `test_S02_the_same_shape_in_a_test_path_is_information_only` | PASS |
| S-03 | a placeholder value in config | screen | not critical | `test_S03_a_documented_placeholder_is_not_a_finding` | PASS |
| S-04 | a credential in the tree | the card is written | the value never appears in it; the evidence reads `<line withheld>` and keeps its file and line. Rewritten for the withheld-line rule (2 Nov 2026). | `test_S04_the_credential_value_never_appears_in_the_scorecard` | PASS |
| S-05 | a private-key block in source | screen | critical | `test_S05_a_private_key_block_in_source_is_critical` | PASS |
| S-06 | the project's own script pipes a download into a shell | screen | serious | `test_S06_the_projects_own_script_piping_a_download_into_a_shell_is_serious` | PASS |
| S-07 | the same line in a README | screen | warning | `test_S07_the_same_line_in_a_readme_is_a_warning` | PASS |
| S-08 | a denylist and a test string naming the pattern | screen | no flag | `test_S08_a_denylist_that_names_the_pattern_is_not_a_finding` | PASS |
| S-09 | `verify=False` in a client | screen | serious | `test_S09_disabled_certificate_verification_is_serious` | PASS |
| S-10 | `git commit --no-verify` in a script | screen | warning | `test_S10_a_hook_bypass_is_a_warning` | PASS |
| S-11 | a zero-width space in source | screen | serious, with the code point named | `test_S11_a_zero_width_space_in_source_is_serious_and_named` | PASS |
| S-12 | a Persian README using zero-width non-joiners | screen | no flag | `test_S12_persian_typography_is_not_an_attack` | PASS |
| S-13 | a byte-order mark at the start of a file | screen | no flag | `test_S13_a_byte_order_mark_at_the_start_is_an_encoding_artifact` | PASS |
| S-14 | a sanitiser that inserts a zero-width space on purpose | screen | no flag | `test_S14_a_sanitiser_that_inserts_the_character_on_purpose_is_the_defence` | PASS |
| S-15 | three CI actions, two pinned by digest | screen | `2/3` | `test_S15_ci_actions_pinned_by_digest_are_counted` | PASS |
| S-16 | a credential-shaped key inside an installer line that pipes a download into a shell | screen | the `curl-pipe-shell` flag keeps its file and line and its excerpt reads `<line withheld>`, and the key is in no other part of the card. Rewritten for the withheld-line rule (2 Nov 2026). | `test_S16_a_key_on_a_line_another_flag_quotes_is_withheld_there_too` | PASS |
| S-17 | six credential shapes planted in an installer, a README and an instruction file; a key crossing the 200-character cut of a line; two keys used as frontmatter keys | screen | none of the planted values, and no prefix of the cut key, appears anywhere in the card; the two keys stay two entries | `test_S17_no_planted_key_shape_appears_anywhere_in_a_card` | PASS |
| S-18 | a file named like a cloud key, and a project directory named like one | screen | the reference reads `<redacted>.sh:1` and no longer resolves; the key is in no part of the card (a recorded limit, in `docs/INTEGRITY.md`) | `test_S18_a_credential_shaped_file_or_directory_name_is_redacted_so_the_reference_no_longer_resolves` | PASS |
| S-19 | an installer line with a recognised key and an adjacent unquoted `AWS_SECRET_ACCESS_KEY=` value; lines such as `$AWS_SECRET_ACCESS_KEY` and `${{ secrets.DEPLOY_TOKEN }}`; and a line holding only `${{ secrets.DEPLOY }}` | screen, and `clip()` alone | the card holds neither the value nor the variable name, only `<line withheld>`; every line with a listed word is withheld whether it holds a literal or a reference; `secrets.NAME` alone is not a trigger and is quoted. Rewritten for the withheld-line rule (2 Nov 2026). | `test_S19_a_line_with_a_secret_assignment_is_withheld_whole_and_secrets_dot_name_is_not_a_trigger` | PASS |
| S-20 | fake credentials (a cloud key, a GitHub token, a JWT, an unquoted `AWS_SECRET_ACCESS_KEY=` value, a quoted `password="..."` value and a bracketed `TOKEN=` value) planted in Markdown, shell, a workflow step, `package.json`, `.claude/settings.json`, frontmatter and a licence line, straddling each line limit (40, 100, 120, 200, 400), longer than each long limit (2,000 to 500,000) and straddling each file-read limit (4,000, 20,000, 200,000, 500,000) | screen, then walk the whole card, keys included | each planted file emits an excerpt (a workflow past its 200,000-character read emits none), and no run of 8 or more characters of any planted credential appears anywhere | `test_S20_no_planted_credential_survives_at_any_size_limit` | PASS |
| S-21 | `os.environ[...]`, `os.getenv(`, `getpass.getpass()`, `%NAME%`, `process.env.`, `$(...)` and `${NAME}` assigned to `TOKEN` or `password`; a plain literal, `Abcd1234[Efgh5678]`, `abc(def)xyz`, `get_password()`; the words `api-key`, `_key`, `_pass`, `pwd`, `credentials`, `Authorization`, `Bearer` and a URL with a user and password; and `export_key_file`, `hotkey`, `secrets.X` and plain text as lines that must stay readable | `clip()`, and a screen of the bracketed one | every line with a listed word is withheld whatever the value looks like; the lines without one are quoted as written. Rewritten for the withheld-line rule (2 Nov 2026). | `test_S21_a_listed_word_withholds_the_line_whatever_the_value_looks_like` | PASS |
| S-22 | a source line whose licence name is 29 characters long and followed by a recognised key | screen | the licence flag shows no part of the key | `test_S22_a_licence_name_cut_from_a_line_holding_a_key_shows_no_part_of_it` | PASS |
| S-23 | a workflow whose last line the 200,000-character read limit cuts in two, holding a `token="` value | screen | the cut line is not read: no data-out flag from it, and no part of the value is in the card | `test_S23_text_past_the_file_read_limit_including_a_cut_final_line_is_not_read` | PASS |
| S-24 | U+FDD0 in a file name, at the end of a licence line and at the end of an installer line | screen | the citation keeps its file name and line, the licence flag still fires and the excerpt is unchanged | `test_S24_the_character_u_fdd0_in_a_file_name_or_a_line_has_no_special_effect` | PASS |
| S-25 | two copies of a test tree, a control without a listed word and a trial with `TOKEN=` beside a marker; the marker sits in each place a card can quote project text: lines of a README, instruction files, an installer, source, Markdown (including a quoted example), a workflow, `package.json` and `.claude/settings.json`; a stale path inside an instruction file, one of them beside a fenced span that holds the word; a source-line URL; a `.scanignore` pattern; a hook event name; a stale path in an instruction file whose fence holds U+2028; a hook event spelled with a JSON escape; and a copied file whose source line and licence carry the marker and a key, screened against a corpus holding the same file | screen, `quiet-counsel integrity`, and the dashboard built from the card, on both trees | in the control every route quotes the marker, so a planted file that exercises nothing fails (15 routes counting the archetype evidence of `package.json` apart from its flags, plus the integrity fields, the dashboard and the corpus match; the escaped event name is left out of the detail in both trees, because no line can be matched to it); in the trial the marker is in no string or key of the card, in no `integrity` output and not on the dashboard, no prefix of the key appears, and the flags and their citations are the same as in the control. It fails against the scanner of commit d6ceec1, against b3b53c9 (the `.scanignore` pattern, the hook event name, a stale path beside a fence) and against 94c3199 (the U+2028 fence and the escaped event name) | `test_S25_a_marker_on_every_line_of_a_tree_beside_a_listed_word_reaches_no_card_dashboard_or_integrity_output` | PASS |

## Suite I · Integrity

| ID | Given | When | Then | Proof | Status |
|---|---|---|---|---|---|
| I-01 | a skill telling the reviewer to award a perfect score | screen | critical, not scored, band blocked | `test_I01_text_addressed_to_the_evaluator_blocks_scoring` | PASS |
| I-02 | security guidance quoting the same attack | screen | no flag | `test_I02_security_guidance_quoting_the_attack_is_not_the_attack` | PASS |
| I-03 | a GPL licence file vendored into an MIT tree | screen | critical, sets D1 to 0 | `test_I03_a_gpl_licence_file_inside_an_mit_tree_is_critical` | PASS |
| I-04 | a setup wizard that names the GPL as an option | screen | no flag | `test_I04_naming_the_gpl_in_prose_is_not_redistributing_it` | PASS |
| I-05 | an SPDX GPL header in source under an MIT root | screen | critical | `test_I05_an_spdx_gpl_header_in_source_under_mit_is_critical` | PASS |
| I-06 | no licence at the root | screen | serious; declared licence `none` | `test_I06_no_licence_at_the_root_is_serious` | PASS |
| I-07 | a file identical to one in the corpus | screen with a corpus | flagged, naming both paths | `test_I07_a_file_identical_to_a_corpus_file_is_flagged_with_both_paths` | PASS |
| I-08 | a tiny file identical to one in the corpus | screen with a corpus | not compared | `test_I08_files_under_the_size_floor_are_not_compared` | PASS |
| I-09 | no corpus | screen | recorded as a limit | `test_I09_no_corpus_is_recorded_as_a_limit` | PASS |
| I-10 | a shallow clone of a large import | screen | no provenance reported, no provenance flag, a limit recorded | `test_I10_a_shallow_clone_reports_no_provenance_at_all` | PASS |
| I-11 | full history whose first commit holds 212 files | screen | warning, with the count | `test_I11_a_first_commit_holding_the_finished_project_is_a_warning` | PASS |
| I-12 | history that begins before the event window | screen with the window | warning | `test_I12_history_that_begins_before_the_event_is_a_warning` | PASS |
| I-13 | a credential shape under a path the project's `.scanignore` excludes | screen | still shown, as information marked excluded, with its original severity; the band is not blocked | `test_I13_a_finding_in_an_excluded_path_stays_visible_as_information` | PASS |
| I-14 | the same project | screen with `--no-ignore` | the original severity is restored | `test_I14_ignoring_the_exclusions_restores_the_original_severity` | PASS |
| I-15 | the evaluator-directed phrase only under `tests/`, `testdata/`, `fixtures/`, `__tests__/`, a `test_*` file and a `*_test.*` file | screen | serious, every hit listed with its file and line, no `do-not-score` cap, band not blocked | `test_I15_directed_text_only_under_a_test_path_is_serious_listed_and_does_not_stop_scoring` | PASS |
| I-16 | the same phrase in a skill file and in a test file | screen | critical, `do-not-score`, band blocked, the skill file listed first | `test_I16_the_same_text_in_skills_still_blocks_even_beside_a_test_string` | PASS |
| I-17 | GPL text only in a test file, then also in source | screen | a warning with no cap and band not blocked; then critical with `D1=0` and the source file listed first | `test_I17_copyleft_text_only_in_a_test_file_is_a_warning_and_elsewhere_is_critical` | PASS |
| I-18 | the evaluator-directed phrase in `README.md`, which `.scanignore` lists | screen, and screen with `--no-ignore` | critical with `do-not-score` and band blocked both times | `test_I18_a_scanignore_entry_cannot_lift_the_evaluator_directed_block` | PASS |
| I-19 | seventy test files holding the phrase, listed before a skill file that holds it; then thirty skill files | screen | the skill file is listed first and the flag is critical; past 25 hits outside test paths a note in the evidence states the limit | `test_I19_sixty_early_test_path_hits_cannot_hide_a_later_instruction_outside_a_test` | PASS |
| I-20 | a JSON file in the project with a `ref` line and an `excerpt` line holding the phrase, shaped like the tool's own quotation | screen | critical, `do-not-score`, band blocked: the shape earns no exemption | `test_I20_a_json_file_shaped_like_a_scorecard_quotation_still_blocks` | PASS |
| I-21 | a Markdown file with a `# Example` heading two lines above the evaluator-directed phrase, and a JSON file with the phrase as the value of a `"score"` key | screen | no `evaluator-directed-text`; one `quoted-evaluator-text` flag at information level, with no cap, whose title counts both lines and whose evidence names each file and line; the band is not blocked | `test_I21_text_judged_quoted_is_listed_at_information_level_with_file_line_and_count` | PASS |
| I-22 | a project with no such text; then the phrase in a skill file | screen | no `quoted-evaluator-text` in either; the second is critical `evaluator-directed-text` | `test_I22_the_listing_is_quiet_without_such_text_and_a_real_hit_is_not_moved_into_it` | PASS |

## Suite P · Third-party text

A project that copies someone else's text should carry that text's licence and a line saying where it came from. The check reads what the tree declares about its own files and, given a corpus, where its copies came from.

| ID | Given | When | Then | Proof | Status |
|---|---|---|---|---|---|
| P-01 | a skill whose frontmatter declares CC-BY-SA-4.0, in an MIT tree | screen | critical, sets D1 to 0, naming the file and line | `test_P01_a_skill_declaring_a_share_alike_licence_in_an_mit_tree_is_critical` | PASS |
| P-02 | a source line naming CC-BY-4.0, and a source line with no licence | screen | a warning for each, and no share-alike flag | `test_P02_terms_a_person_should_read_are_a_warning_and_a_bare_source_line_is_one` | PASS |
| P-03 | a non-commercial skill and a BUSL SPDX header | screen | serious, caps D1 at 3, both files named | `test_P03_restricted_or_proprietary_terms_are_serious_and_cap_licence_compliance` | PASS |
| P-04 | an MIT skill with its licence and source line, in an Apache tree | screen | no flag; both declarations counted | `test_P04_a_permissive_skill_carrying_its_licence_and_source_is_quiet` | PASS |
| P-05 | a guide showing the source-line template with placeholders | screen | nothing declared, no flag | `test_P05_a_template_with_placeholders_in_a_guide_declares_nothing` | PASS |
| P-06 | a GPL file inside a GPL project | screen | no share-alike flag | `test_P06_a_file_under_the_projects_own_share_alike_licence_is_not_a_finding` | PASS |
| P-07 | a file copied byte for byte from an MIT corpus project, credited nowhere | screen with a corpus | serious, caps D2 at 3; `0 of 1` credited | `test_P07_a_permissive_file_copied_with_no_credit_is_serious_and_caps_provenance` | PASS |
| P-08 | the same copy with a source line added at the top | screen with a corpus | still matched, credited, no licence flag; `1 of 1` | `test_P08_a_copy_that_gained_a_source_line_still_matches_and_is_credited` | PASS |
| P-09 | the copy with a licence beside it, or named in a third-party notices file | screen with a corpus | credited, no flag | `test_P09_a_licence_beside_the_copy_or_a_notice_naming_the_source_is_credit` | PASS |
| P-10 | a copy from a corpus project with no licence | screen with a corpus | serious, saying no licence was found | `test_P10_a_copy_from_a_source_with_no_licence_is_restricted` | PASS |
| P-11 | a copy from a CC-BY-SA corpus project | screen with a corpus | critical, naming the source licence | `test_P11_a_copy_from_a_share_alike_source_is_critical` | PASS |
| P-12 | twenty licence names | classified | each lands in its class, with non-commercial ahead of share-alike and BSL-1.0 kept apart from BUSL | `test_P12_licence_names_sort_into_the_classes_the_check_acts_on` | PASS |
| P-13 | a restricted skill, every dimension scored 9 | `review_project.py finalize` | D1 capped to 3; `D2<=3` and `safety<=3` read the same way | `test_P13_finalize_applies_the_licence_and_provenance_caps` | PASS |
| P-14 | a closed project marking its own skills proprietary, and the same skill under an MIT root | screen | quiet in the closed project; serious in the open one | `test_P14_a_closed_project_marking_its_own_skills_proprietary_is_quiet` | PASS |
| P-15 | a `source:` field in a YAML registry, and one twenty lines into a document | screen | nothing declared, no flag | `test_P15_a_source_field_in_data_or_deep_in_a_document_is_not_a_declaration` | PASS |
| P-16 | share-alike text in a fixture-named file, and the same file under `.scanignore` | screen | critical and band blocked; with exclusion, info, excluded, original severity critical, band not blocked | `test_P16_share_alike_text_in_a_fixture_named_file_is_critical_unless_the_project_excludes_it` | PASS |

## Suite C · Claims against measurement

| ID | Given | When | Then | Proof | Status |
|---|---|---|---|---|---|
| C-01 | a README claiming 12 skills, one shipped | screen | contradicted; claim accuracy capped at 2 | `test_C01_an_inflated_count_is_contradicted_and_caps_claim_accuracy` | PASS |
| C-02 | a README claiming 2 skills, five shipped | screen | not contradicted | `test_C02_finding_more_than_claimed_is_never_a_contradiction` | PASS |
| C-03 | a claim of 340 tests | screen | unchecked, because cases are not files | `test_C03_a_test_count_is_unchecked_because_cases_are_not_files` | PASS |
| C-04 | "works with 15 agents" | screen | a compatibility claim, not an inventory one | `test_C04_works_with_n_agents_is_a_compatibility_claim` | PASS |
| C-05 | "SOC 2 compliant and production-ready" | screen | both unsupported | `test_C05_a_compliance_claim_with_nothing_behind_it_is_unsupported` | PASS |
| C-06 | a claim of 20 skills, 19 shipped | screen | confirmed | `test_C06_a_count_within_fifteen_percent_is_confirmed` | PASS |

## Suite B · Bands, and what a screen may claim

| ID | Given | When | Then | Proof | Status |
|---|---|---|---|---|---|
| B-01 | a critical flag | screen | blocked | `test_B01_a_critical_flag_blocks` | PASS |
| B-02 | a serious flag and no critical one | screen | review | `test_B02_serious_flags_without_a_critical_one_mean_review` | PASS |
| B-03 | clean, with tests, a licence and CI | screen | shortlist | `test_B03_a_clean_screen_with_tests_licence_and_ci_is_shortlisted` | PASS |
| B-04 | clean, with none of those | screen | screened | `test_B04_a_clean_but_thin_screen_is_screened` | PASS |
| B-05 | any project | screen | no dimension is scored; all are unverified | `test_B05_a_screen_never_scores` | PASS |
| B-06 | any project | screen | every signal names how it was measured; the card passes `check` | `test_B06_every_signal_says_how_it_was_measured` | PASS |
| B-07 | several flags | screen | every flag carries evidence | `test_B07_every_flag_carries_evidence` | PASS |
| B-08 | a screen card edited to score, and a skip with no reason | `check` | each is named as a problem | `test_B08_the_contract_rejects_a_screen_that_scores_or_a_skip_with_no_reason` | PASS |
| B-09 | an eval set stored as JSON lines | screen | its directory is counted as evals (found when the tool screened itself and missed its own) | `test_B09_eval_sets_in_jsonl_are_counted` | PASS |

## Suite V · The dashboard

| ID | Given | When | Then | Proof | Status |
|---|---|---|---|---|---|
| V-01 | a clean project and a blocked one | render | both appear; the blocked one first | `test_V01_every_project_appears_and_blocked_ones_come_first` | PASS |
| V-02 | a dimension scored with no evidence | render | a warning bar, and the cell says so | `test_V02_a_score_with_no_evidence_raises_a_visible_warning` | PASS |
| V-03 | the same | render with strict | refused; a fully evidenced card still builds | `test_V03_strict_mode_refuses_to_build_that_page` | PASS |
| V-04 | any cohort | render | nothing is loaded from any host | `test_V04_the_page_loads_nothing_from_anywhere` | PASS |
| V-05 | a submission whose name, claim and flag text contain a script tag | render | escaped, never executed | `test_V05_hostile_text_in_a_submission_is_escaped_not_rendered` | PASS |
| V-06 | critical and serious flags | render | each status carries its word | `test_V06_every_status_is_carried_by_a_word_not_only_a_colour` | PASS |
| V-07 | any cohort | render | dark mode follows the system and the explicit toggle | `test_V07_dark_mode_follows_the_system_and_the_explicit_toggle` | PASS |
| V-08 | an application | render | skipped dimensions show their reason, never a zero | `test_V08_a_skipped_dimension_shows_its_reason_never_a_zero` | PASS |
| V-09 | any cohort | render | the page says what it does not show, and each card what its run did not establish | `test_V09_what_the_run_did_not_establish_is_always_on_the_page` | PASS |
| V-10 | the sample project, screened and rendered | render | every flag carries at least one evidence item with a reference, and the page says every flag names its evidence (a file and line, or a command or commit) | `test_V10_the_page_claims_evidence_for_every_flag_and_the_sample_card_holds_it` | PASS |
| V-11 | a dimension scored 10 and capped to 3 | render | the page shows 3 and says it was scored 10 and capped to 3 | `test_V11_a_capped_dimension_shows_its_effective_score_and_the_cap` | PASS |

## Suite K · Command line

| ID | Given | When | Then | Proof | Status |
|---|---|---|---|---|---|
| K-01 | an install | `--version` | the name and version | `test_K01_version_prints_the_name_and_version` | PASS |
| K-02 | a catalogue | `classify --json` | archetype and evidence | `test_K02_classify_json_names_the_archetype_and_its_evidence` | PASS |
| K-03 | two projects | `screen --out` | one card each and a summary line each | `test_K03_screen_writes_one_card_per_project_and_a_line_each` | PASS |
| K-04 | a path that is not a directory | `screen` | skipped with a message; exit 2 when nothing is left | `test_K04_a_path_that_is_not_a_directory_is_skipped_and_all_bad_is_exit_2` | PASS |
| K-05 | a project | `integrity` | JSON with history, licence, claims, both text sweeps and the evaluator-directed lines judged quoted | `test_K05_integrity_prints_history_licence_and_claims` | PASS |
| K-06 | a good card and a broken one | `check` | exit 0, then exit 1 naming the problem | `test_K06_check_exits_1_on_a_broken_card_and_0_on_a_good_one` | PASS |

## Suite E · The shipped example

| ID | Given | When | Then | Proof | Status |
|---|---|---|---|---|---|
| E-01 | the synthetic sample project | screen | every planted flag is raised | `test_E01_the_sample_project_raises_every_planted_flag` | PASS |
| E-02 | the committed example | regenerated with the fixed clock | identical to what is committed; regenerated with `tools/gen_example.py` for the withheld-line rule (2 Nov 2026) | `test_E02_the_committed_example_is_current` | PASS |
| E-03 | the whole tree | the release preflight's secret expression runs over it | nothing matches, so the forge's push protection has nothing to block | `test_E03_no_complete_credential_shape_exists_anywhere_in_the_tree` | PASS |
| E-04 | the synthetic sample project | screened, then screened again with every directory listed in reverse | the two cards are identical, so evidence order comes from the tool and not the filesystem | `test_E04_evidence_order_does_not_depend_on_the_order_the_filesystem_lists` | PASS |
| E-05 | the committed example | read | neither file holds the planted instruction (this repository commits no complete attack phrase); the live sample still raises it as critical with `do-not-score` | `test_E05_the_committed_example_withholds_the_planted_phrase_and_the_live_sample_still_blocks` | PASS |

## Suite D · Documentation

| ID | Given | When | Then | Proof | Status |
|---|---|---|---|---|---|
| D-01 | every human-facing document | read | it names only subcommands that exist | `test_D01_docs_name_only_subcommands_that_exist` | PASS |
| D-02 | `docs/cli.md` | regenerated from the parser | identical | `test_D02_the_command_reference_is_current` | PASS |
| D-03 | `docs/RUBRIC.md` and the code | compared | the same sixteen dimensions | `test_D03_the_rubric_and_the_code_name_the_same_sixteen_dimensions` | PASS |
| D-04 | every human-facing document | prose outside code is read | no em or en dashes | `test_D04_human_facing_prose_carries_no_em_or_en_dashes` | PASS |
| D-05 | the shipped skill | its frontmatter is read | only specification keys, and a name matching its folder | `test_D05_the_shipped_skill_uses_only_specification_keys_and_its_own_name` | PASS |

## Suite H · The agent interface, held to the tool's own standard

| ID | Given | When | Then | Proof | Status |
|---|---|---|---|---|---|
| H-01 | `AGENTS.md` | read | under 4,000 bytes, and every skill and path it names exists | `test_H01_agents_md_is_short_and_names_only_what_exists` | PASS |
| H-02 | `CLAUDE.md` | read | a pointer to `AGENTS.md`, under 300 characters | `test_H02_claude_md_is_only_a_pointer` | PASS |
| H-03 | every skill | its frontmatter is read | specification keys only, name matches the folder, the description says when to use it, tools declared | `test_H03_every_skill_meets_the_specification_and_says_when` | PASS |
| H-04 | every skill | the files it names are looked up | each is inside the skill, one level deep | `test_H04_every_file_a_skill_names_is_inside_it_one_level_deep` | PASS |
| H-05 | every skill script | run with `--help`, with nothing installed | exits 0, and imports only the standard library and the package | `test_H05_every_script_answers_help_and_imports_only_the_standard_library` | PASS |
| H-06 | two projects, one blocked | `screen_cohort.py --json` | both screened, blocked first, a dashboard built | `test_H06_screen_cohort_screens_a_cohort_and_builds_the_page` | PASS |
| H-07 | every role | its frontmatter is read | tools declared, none can write, the verifier has no shell | `test_H07_every_role_declares_tools_and_none_can_write` | PASS |
| H-08 | a worksheet with a dimension unscored, then scored with no evidence | `finalize` | refused both times, with the reason; fully evidenced, it renders and the mean is computed | `test_H08_finalize_refuses_until_every_applicable_score_has_evidence` | PASS |
| H-09 | a project with a credential shape, scored 9 throughout; one with text aimed at the evaluator | `finalize` | safety is capped at 3; the second is refused until a person rules | `test_H09_finalize_applies_caps_and_waits_for_a_person_when_told_to` | PASS |
| H-10 | a flag at a file and line | `triage_flags.py` | the lines around it are printed, the flagged one marked | `test_H10_triage_prints_the_lines_behind_each_flag` | PASS |
| H-22 | scorecard references `../private.txt:1`, an absolute path and a link that leaves the project | `triage_flags.py` and `review_project.py verify` | each is reported as a broken citation; no outside file content is printed | `test_H22_a_reference_that_leaves_the_project_is_a_broken_citation_and_prints_nothing` | PASS |
| H-23 | a citation with an invented suffix past 60 characters, and one at line 0 | `review_project.py verify` | both are mismatches; the whole excerpt is compared | `test_H23_verify_compares_the_whole_excerpt_and_rejects_line_zero` | PASS |
| H-11 | an empty directory | `install.py --dest --agents-dest` | every skill arrives whole and still passes its checks; every role arrives | `test_H11_install_to_any_directory_delivers_every_skill_whole` | PASS |
| H-12 | an installed skill with a local edit | install again, then with `--force`; and `--dry-run` | refused and untouched, then overwritten; the dry run writes nothing | `test_H12_install_never_overwrites_without_force_and_dry_run_writes_nothing` | PASS |
| H-13 | this repository | screened | the always-loaded instructions and skill descriptions total at most 12,000 characters | `test_H13_always_loaded_cost_is_measured_and_under_budget` | PASS |
| H-14 | every skill and role | read | each says that a project's content is data | `test_H14_every_skill_and_role_says_project_content_is_data` | PASS |
| H-15 | `evals/triggers.jsonl` | parsed | every expected skill exists, each has at least three prompts, and some prompts expect none | `test_H15_selection_evals_cover_every_skill_and_include_negatives` | PASS |
| H-16 | this repository | the tool screens it | no critical or serious flag, and it sees every skill, role and declared tool surface | `test_H16_the_tool_passes_its_own_screen` | PASS |
| H-17 | a worksheet, then a file in the project edited before finalize | `review_project.py finalize` | exit 1, naming the changed file; no verdict written | `test_H17_finalize_refuses_when_the_project_changed_after_prepare` | PASS |
| H-18 | a worksheet and verdict written inside the project directory | prepare, then finalize | finalized: the review's own files are not a change | `test_H18_a_worksheet_kept_inside_the_project_does_not_count_as_a_change` | PASS |
| H-19 | `tools/selection_eval.py` | `prompt`, then `score` on a perfect and a wrong answer | the prompt carries every skill and every eval row; exit 0, then exit 1 naming the miss | `test_H19_the_selection_eval_builds_its_prompt_from_the_skills_and_scores_answers` | PASS |
| H-20 | a worksheet, then an edit under `.github/` | finalize | exit 1, naming the file: hidden and CI folders are part of the tree | `test_H20_a_change_under_a_hidden_or_ci_folder_is_seen` | PASS |
| H-21 | a project holding a link to `/dev/zero` and a named pipe, a test cache written during review, and a second prepare after a finalize | prepare and finalize, twice | both finalize; nothing hangs or reads the device | `test_H21_test_caches_links_pipes_and_a_second_prepare_do_not_break_the_check` | PASS |

## Suite Q · Standing instructions and host configuration

What a project does to the agent host it installs into, and whether the instruction files every session loads still describe the tree.

| ID | Given | When | Then | Proof | Status |
|---|---|---|---|---|---|
| Q-01 | an installer that writes a host settings file with no confirmation | screen | serious, naming the line | `test_Q01_an_installer_that_writes_hooks_without_asking_is_serious` | PASS |
| Q-02 | the same write behind a `read -p` confirmation | screen | a warning | `test_Q02_the_same_write_behind_a_confirmation_is_a_warning` | PASS |
| Q-03 | a script appending to the project's `AGENTS.md` | screen | flagged | `test_Q03_a_script_appending_to_the_projects_standing_instructions_is_caught` | PASS |
| Q-04 | a script that reads `CLAUDE.md`, a doc comment naming `AGENTS.md`, a guide showing the manual edit, a test | screen | no flag | `test_Q04_reading_naming_or_documenting_those_files_is_quiet` | PASS |
| Q-05 | an `AGENTS.md` naming one script that exists and one that does not | screen | a warning naming the missing one and its line | `test_Q05_an_instruction_file_naming_a_missing_path_is_a_warning` | PASS |
| Q-06 | a `CLAUDE.md` naming an owner/repo, a placeholder, a URL, a glob that matches, a bare file name that exists in a subfolder, and a path inside a code block | screen | no flag, nothing counted | `test_Q06_repository_names_placeholders_urls_and_code_blocks_are_not_paths` | PASS |
| Q-07 | a `CLAUDE.md` naming a file path and a bare file name, neither of which exists anywhere | screen | both named | `test_Q07_a_renamed_file_that_kept_its_extension_is_still_caught` | PASS |
| Q-08 | code that measures, prints or copies `CLAUDE.md`, `AGENTS.md` or a settings file | screen | no flag: reading is not writing | `test_Q08_reading_a_host_file_is_not_writing_it` | PASS |
| Q-09 | a settings path held in a variable and written a few lines later, in Node, Python and shell | screen | flagged in each | `test_Q09_a_write_through_a_variable_is_caught_in_node_python_and_shell` | PASS |
| Q-10 | an installer with `--yes` and a comment saying "confirm", copying a hook and writing `.mcp.json` | screen | serious, both writes named | `test_Q10_an_option_that_skips_the_prompt_is_not_a_gate` | PASS |
| Q-11 | an `AGENTS.md` naming a product, a recursive glob, an ignored build output, a hidden file by bare name, and a path in a `~~~` block | screen | no flag | `test_Q11_products_recursive_globs_tilde_fences_ignored_outputs_and_hidden_files_are_quiet` | PASS |
| Q-12 | an `AGENTS.md` naming `deploy.yml` bare, with that file under `.github/workflows/` | screen | no flag, nothing counted | `test_Q12_a_workflow_named_bare_that_exists_under_dot_github_is_not_missing` | PASS |
| Q-13 | an `AGENTS.md` naming `gate.yml`, which exists under `.github/workflows/`, and `deploy.yml`, which exists nowhere | screen | a warning naming only `deploy.yml` | `test_Q13_a_workflow_named_bare_that_exists_nowhere_is_still_a_warning` | PASS |

## Suite R · The release gate

`tools/gate.py` is the gate between a release branch and a tag, run by hand and by the `gate` workflow, so it gets its own cases.

| ID | Given | When | Then | Proof | Status |
|---|---|---|---|---|---|
| R-01 | a tree whose version, package, changelog and README agree | `gate.py --release` | passes | `test_R01_a_tree_whose_versions_agree_passes_the_release_checks` | PASS |
| R-02 | a release version the tree does not carry | `gate.py --release` | exit 1, naming the file and the version it carries | `test_R02_a_version_the_tree_does_not_carry_is_refused_by_name` | PASS |
| R-03 | a changelog still headed Unreleased, or a README naming two versions | `gate.py --release` | exit 1, naming the file | `test_R03_an_unreleased_changelog_or_a_stale_readme_is_refused` | PASS |
| R-04 | a workflow that does not run `tools/gate.py` | `gate.py --release` | exit 1, naming the workflow; a workflow that runs it passes | `test_R04_a_workflow_that_skips_the_gate_is_refused` | PASS |
| R-05 | this repository | read | each workflow runs `tools/gate.py` | `test_R05_build_workflows_in_this_repository_run_the_gate` | PASS |
| R-06 | a version that is not X.Y.Z | `gate.py --release` | exit 2 | `test_R06_a_malformed_version_is_bad_input` | PASS |
| R-07 | `tools/gate.py` | its imports are read | the standard library only, and no network address | `test_R07_the_gate_uses_the_standard_library_and_names_no_host_or_person` | PASS |

## Suite W · Release verdict

A release-review workflow is not in 0.1; the `verdict` command below stays.

| ID | Given | When | Then | Proof | Status |
|---|---|---|---|---|---|
| W-01 | a scorecard with a critical flag | `verdict` | MAJOR with file and line | `test_W01_critical_flag_gives_major` | PASS |
| W-02 | a scorecard with a serious flag | `verdict` | MINOR | `test_W02_serious_flag_gives_minor` | PASS |
| W-03 | a scorecard with warnings only | `verdict` | PATCH | `test_W03_warnings_only_give_patch` | PASS |
| W-04 | a scorecard without flags | `verdict` | PASS | `test_W04_no_flags_give_pass` | PASS |
| W-05 | a scorecard and a failed gate | `verdict --gate-status failed` | MAJOR | `test_W05_failed_gate_forces_major` | PASS |
| W-06 | the same scorecard twice | `verdict` twice | identical verdict bytes | `test_W06_same_scorecard_gives_same_verdict_bytes` | PASS |
| W-07 | a scorecard | `verdict` | scorer version and SHA-256 of the scorecard bytes | `test_W07_verdict_names_scorer_version_and_scorecard_hash` | PASS |
| W-10 | the directed-text and copyleft flags at information, warning and critical | `verdict` | PASS, PATCH and MAJOR | `test_W10_a_lowered_flag_never_blocks_more_than_a_warning_does` | PASS |
| W-11 | directed text outside a test path, with its file listed in `.scanignore` | screen, then verdict | MAJOR | `test_W11_directed_text_outside_a_test_path_blocks_even_when_the_ignore_file_lists_it` | PASS |
| W-12 | a copyleft flag the project's `.scanignore` lowered from critical to information | `verdict` | MAJOR, the reason saying the project excluded it | `test_W12_a_critical_flag_the_project_excluded_still_gives_major_with_that_reason` | PASS |
| W-13 | the same flag under a test path | `verdict` | PATCH: it has its own lower severity and no original severity | `test_W13_the_test_path_version_keeps_its_lower_verdict` | PASS |
| W-14 | a critical, a serious and a warning flag, each excluded by `.scanignore` | screen, then verdict | MAJOR, MINOR and PATCH, each reason saying the project excluded it | `test_W14_a_project_excluded_flag_keeps_its_original_severity_at_every_level` | PASS |
| W-09 | the test-path versions of the directed-text and copyleft flags, and the critical directed-text flag | `verdict` | MINOR, PATCH and MAJOR | `test_W09_a_test_path_flag_lowered_on_purpose_does_not_block_the_release` | PASS |

## Suite T · Checks derived from public incident reports

Four checks, each written from the public reports named in `docs/NOTICES.md` and nothing else. A flag asks a person to look at a file and line; it says nothing about who wrote it or why. Workflows are read line by line, not with a YAML parser, so anchors, flow-style maps, merge keys and values built in variables are not followed. A command that sends data through a variable holding the address, or from a composite action, is not seen.

| ID | Given | When | Then | Proof | Status |
|---|---|---|---|---|---|
| T-01 | a session-start hook in `.claude/settings.json`, and a `.vscode/tasks.json` task set to run on folder open | screen | `open-time-hook`: a warning, naming the file, the line and the event; serious cases are T-09 | `test_T01_a_command_that_runs_on_open_is_a_warning_and_a_hidden_script_is_serious` | PASS |
| T-02 | a settings file with no hooks, and a task that does not run on open | screen | no flag | `test_T02_settings_without_hooks_and_a_task_that_does_not_run_on_open_are_quiet` | PASS |
| T-03 | a `package.json` with `preinstall`, `install` or `postinstall` | screen | `install-time-script`: a warning, serious on the same two conditions | `test_T03_install_scripts_fire_and_a_hidden_folder_script_is_serious` | PASS |
| T-04 | `test`, `build` and `prepare` scripts, and a `postinstall` string outside `scripts` | screen | no flag | `test_T04_other_scripts_and_a_postinstall_string_outside_scripts_are_quiet` | PASS |
| T-05 | a workflow step that sends a secret, a secret held in an environment variable, or `git log -p` output to a numeric address or a plain `http://` host | screen | `workflow-data-out`, serious, whatever the workflow file is called | `test_T05_a_step_sending_secrets_or_history_to_a_bare_address_is_serious` | PASS |
| T-06 | a secret in a header sent to a named `https://` host, `git log -p` with no send, and a send to a bare address that carries no data | screen | no flag | `test_T06_a_secret_in_a_header_to_a_named_https_host_and_a_log_with_no_send_are_quiet` | PASS |
| T-07 | a `pull_request_target` or `issue_comment` workflow that checks out the pull request head or substitutes its text in a `run:` step, with secrets in the workflow, or an agent action with write access | screen | `untrusted-code-with-power`: serious, critical when an agent action is present, band blocked | `test_T07_pull_request_content_with_secrets_is_serious_and_with_an_agent_critical` | PASS |
| T-08 | `pull_request_target` with no head checkout and no substitution; a plain `pull_request` trigger | screen | no flag | `test_T08_a_target_trigger_with_no_head_checkout_and_a_plain_pull_request_are_quiet` | PASS |
| T-09 | a session-start hook or a folder-open task that pipes a download into a shell, a `.claude` hook that runs a script inside `.vscode`, and the reverse | screen | `open-time-hook`, serious | `test_T09_a_download_piped_to_a_shell_or_a_script_in_another_host_folder_is_serious` | PASS |
| T-10 | a session-start hook running `.claude/hooks/session-start.sh`, a folder-open task running `.vscode/setup.sh`, and a hook running a script in `.husky` | screen | `open-time-hook`, still a warning | `test_T10_a_script_in_its_own_host_folder_or_any_other_hidden_folder_stays_a_warning` | PASS |
| T-11 | hooks on the post-tool, stop and notification events, and one on session start | screen | `agent-hook` at information level for the first three, naming the event and no `open-time-hook`; the session-start hook raises `open-time-hook` naming `SessionStart` and no `agent-hook` | `test_T11_hooks_on_other_events_are_information_and_the_detail_names_the_event` | PASS |
| T-12 | a settings file, a manifest and a tasks file nested 1,500 levels deep; commands of 300,000 characters; a task list of 20,000 entries; workflows with one 180,000-character line; invalid JSON; invalid UTF-8 | screen | no error and no stall; the two nested files that were refused raise `unreadable-configuration` naming the file | `test_T12_deep_nesting_long_lines_invalid_json_and_invalid_utf8_do_not_stop_the_screen` | PASS |
| T-13 | `runOn` set to `folderOpen` inside a block comment, inside a string, and outside any task; then on a real task | screen | no `open-time-hook` for the first three; the real task is reported at its line | `test_T13_a_runon_inside_a_comment_or_a_string_is_not_a_task_but_a_real_one_still_is` | PASS |
| T-14 | a secret sent to `http://localhost.attacker.invalid`, `http://127.0.0.1.attacker.invalid`, `http://localhost@attacker.invalid`; and to `localhost`, `127.0.0.1`, `[::1]` and `0.0.0.0` with ports | screen | `workflow-data-out` for the first group, none for the second | `test_T14_only_the_complete_local_hostname_counts_as_local` | PASS |
| T-15 | a pull request head checked out in one job and a secret used in another; the same with the secret, an agent action or `permissions: write-all` placed in the workflow or in the checking-out job | screen | no flag when the secret is only in the other job; serious when it is in the same job or in workflow-level `env:`; critical with an agent action in the same job; none for workflow-level permissions alone | `test_T15_trigger_untrusted_input_and_secrets_are_paired_inside_one_job` | PASS |
| T-16 | a `pull_request_target` job that calls a reusable workflow with `secrets: inherit` and passes the pull request head in `with:`; a job with a head checkout step and `secrets: inherit` | screen | `untrusted-code-with-power`, serious, citing the trigger, the passed value and the `secrets: inherit` line | `test_T16_a_job_calling_a_reusable_workflow_with_inherited_secrets_holds_secrets` | PASS |
| T-17 | `secrets: inherit` under `pull_request_target` with nothing from the pull request passed; the same call with the head passed under a plain `pull_request` trigger | screen | no flag | `test_T17_inherited_secrets_with_nothing_from_the_pull_request_or_another_trigger_are_quiet` | PASS |
| T-18 | a workflow line past 2,000 characters holding a `token="..."` value whose closing quote lies beyond the detection limit, on a step that sends a secret to a bare address | screen | the data-out flag fires, its evidence reads `<line withheld>` and holds no part of the value. Rewritten for the withheld-line rule (2 Nov 2026). | `test_T18_a_key_crossing_the_workflow_detection_cut_is_withheld_whole_in_the_evidence` | PASS |

## Suite M · Measured evidence

`tools/check_evidence.py` screens a tree and counts, for every flag and every numeric signal, whether it cites a file and line that exist and whether the cited line contains the excerpt the card claims. It changes no card and no document.

| ID | Given | When | Then | Proof | Status |
|---|---|---|---|---|---|
| M-01 | a fixture with a flag citing a line, a flag whose line is withheld, and flags citing a command | the tool measures it | each flag lands in the class its evidence earns, a withheld line counts as `withheld` (2 matches, 1 withheld), signals are counted as command only, and no citation is broken. Rewritten for the withheld-line rule (2 Nov 2026). | `test_M01_a_fixture_is_counted_by_what_each_flag_and_signal_cites` | PASS |
| M-02 | a citation to a missing file, a line past the end, and a line whose text differs from the excerpt | the tool checks each | broken, broken and differs | `test_M02_a_citation_that_points_at_nothing_is_broken_and_a_changed_line_differs` | PASS |
| M-06 | a reference with `..` and an absolute reference to a file outside the project | the tool checks each | broken | `test_M06_a_reference_that_leaves_the_project_is_broken` | PASS |
| M-07 | the excerpts `<line withheld>` and `<redacted>` against the line `harmlessidentifier012345`, and `<line withheld>` and the quoted text against the line `token="..."` | the tool compares each | differs, differs, withheld, differs. Rewritten for the withheld-line rule (2 Nov 2026). | `test_M07_withheld_is_not_a_wildcard_and_quoted_text_never_matches_a_line_the_scanner_withholds` | PASS |
| M-08 | the excerpt of that long workflow line, and of a line with an adjacent secret assignment | the tool compares each with its source | withheld for both; text from the start of the line differs. Rewritten for the withheld-line rule (2 Nov 2026). | `test_M08_a_long_workflow_line_and_an_adjacent_secret_assignment_are_confirmed_as_withheld` | PASS |
| M-03 | this repository | the tool measures it | every cited file and line exists and no flag lacks evidence | `test_M03_the_tools_own_tree_cites_only_lines_that_exist` | PASS |
| M-04 | an excerpt with the card's `[label] ` prefix, a gate note, a `U+200B in: ` prefix or `<line withheld>` | the tool compares it with the line | match for the decorations and `withheld` for a line the scanner withholds; a changed line, quoted text from a withheld line, or `<line withheld>` on a line the scanner would quote, still differs. Rewritten for the withheld-line rule (2 Nov 2026). | `test_M04_the_cards_own_prefix_and_a_withheld_line_are_not_a_difference` | PASS |
| M-05 | an excerpt that begins `[invented]`, a label from another kind of flag, a label with nothing after it, an empty excerpt, and a gate note on a flag that does not make one, and `<line withheld>` standing for a line the scanner would quote | the tool compares each with the line | differs every time; the decorations made for that flag, and a correctly withheld line (counted as withheld), still match. Rewritten for the withheld-line rule (2 Nov 2026). | `test_M05_only_the_decorations_made_for_that_kind_of_flag_are_set_aside` | PASS |

## Suite F · Field checks

| ID | Given | When | Then | Proof | Status |
|---|---|---|---|---|---|
| F-01 | a real cohort of at least 50 submissions | screened, and every flag read by a person | the false-positive rate per detector is recorded in the field-run record | `test_backlog.Field.test_F01_a_real_cohort_is_screened_and_every_flag_reviewed` | FIELD |
| F-02 | a corpus of at least 30 public repositories and one known fork | screen the fork | the duplication flag names the upstream | recorded in the field-run record | FIELD |
| F-03 | a real host with the skills installed | each prompt in `evals/triggers.jsonl` is given to it | the selection rate per skill is recorded in the field-run record | recorded in the field-run record | FIELD |

## Limits, accepted

| ID | Given | When | Then | Proof | Status |
|---|---|---|---|---|---|
| N-01 | a file copied and reworded | screen with a corpus | not detected: hashing finds identical files only | none | ACCEPTED |
| N-02 | a claim of partnership or user base in prose | screen | not settled by any repository scan | none | ACCEPTED |
| N-03 | the question of whether a person or a model wrote the code | screen | deliberately not answered; there is no reliable detector | none | ACCEPTED |
| N-04 | a licence conflict | screen | reported as facts for a person, never as a legal ruling | none | ACCEPTED |
