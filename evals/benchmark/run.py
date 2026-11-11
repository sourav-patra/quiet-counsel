"""Track B runner: manifest, split, scoring, and blind-labeller export.

    py -3 -I evals/benchmark/run.py manifest
    py -3 -I evals/benchmark/run.py run --split dev
    py -3 -I evals/benchmark/run.py run --split test --manifest-hash <sha256 of manifest.json>
    py -3 -I evals/benchmark/run.py materialise --ids ids.txt --out DIR

Standard library only; no network. Fixtures are written to a temporary folder and only read by the
screen; nothing in them runs.
"""

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "src"))

import fixtures as fx  # noqa: E402

MANIFEST = os.path.join(HERE, "manifest.json")
SEED = "qc-bench-2026-11-03"
DEV_PER_GROUP = 5  # 25% of the 20 fixtures in each check and label group


def write_files(files, dest):
    for rel, text in files.items():
        p = os.path.join(dest, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)


def split_of(fids):
    """Per group, the five ids with the smallest sha256(seed:id) are dev; the rest are test."""
    order = sorted(fids, key=lambda f: hashlib.sha256((SEED + ":" + f).encode()).hexdigest())
    return {f: ("dev" if k < DEV_PER_GROUP else "test") for k, f in enumerate(order)}


def build_manifest():
    rows = []
    for check in fx.CHECKS:
        for label in ("positive", "negative"):
            group = [fx.build(check, label, i) for i in range(fx.N)]
            sp = split_of([g[0] for g in group])
            for fid, prop, files in group:
                rows.append({"id": fid, "check": check, "label": label, "split": sp[fid],
                             "property": prop, "sha256": fx.content_hash(files)})
    return {"seed": SEED, "fixtures": rows}


def manifest_bytes(m):
    return (json.dumps(m, indent=1, ensure_ascii=True, sort_keys=True) + "\n").encode("utf-8")


def file_hash(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def by_id():
    return {fx.build(c, lab, i)[0]: (c, lab, i) for c, lab, i in fx.all_ids()}


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def fmt(k, n):
    if n == 0:
        return "n/a"
    lo, hi = wilson(k, n)
    return "%d/%d = %.2f (%.2f to %.2f)" % (k, n, k / n, lo, hi)


def screen_fixture(check, label, i, scan, tmp):
    fid, _, files = fx.build(check, label, i)
    d = os.path.join(tmp, fid)
    write_files(files, d)
    card = scan.screen(d)
    shutil.rmtree(d, ignore_errors=True)
    return check in {f["id"] for f in card["flags"]}


def run(split, manifest_hash):
    m = json.load(open(MANIFEST, encoding="utf-8"))
    if file_hash(MANIFEST) != (manifest_hash or file_hash(MANIFEST)):
        sys.exit("manifest.json does not match --manifest-hash")
    if split == "test" and not manifest_hash:
        sys.exit("the test split needs --manifest-hash, the hash recorded before the first test run")
    if manifest_bytes(build_manifest()) != open(MANIFEST, "rb").read():
        sys.exit("the generator no longer reproduces manifest.json; refusing to run")
    os.environ.setdefault("QUIET_COUNSEL_NOW", "2026-11-03T00:00:00Z")
    from quiet_counsel import scan
    ids = by_id()
    tmp = tempfile.mkdtemp(prefix="qc-bench-")
    counts = {c: {"TP": 0, "FN": 0, "FP": 0, "TN": 0} for c in fx.CHECKS}
    wrong = []
    try:
        for row in m["fixtures"]:
            if row["split"] != split:
                continue
            c, lab, i = ids[row["id"]]
            hit = screen_fixture(c, lab, i, scan, tmp)
            key = ("TP" if hit else "FN") if lab == "positive" else ("FP" if hit else "TN")
            counts[c][key] += 1
            if key in ("FN", "FP"):
                wrong.append((key, row["id"], row["property"]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return counts, wrong


def table(counts):
    out = ["| check | TP | FN | FP | TN | recall (Wilson 95%) | false positive rate (Wilson 95%) |",
           "|---|---|---|---|---|---|---|"]
    tot = {"TP": 0, "FN": 0, "FP": 0, "TN": 0}
    for c in fx.CHECKS:
        k = counts[c]
        for x in tot:
            tot[x] += k[x]
        out.append("| `%s` | %d | %d | %d | %d | %s | %s |" % (
            c, k["TP"], k["FN"], k["FP"], k["TN"], fmt(k["TP"], k["TP"] + k["FN"]), fmt(k["FP"], k["FP"] + k["TN"])))
    P, Nn = tot["TP"] + tot["FN"], tot["FP"] + tot["TN"]
    out.append("")
    out.append("Baselines on the same fixtures, each check taken alone: flag-all has recall %s and false positive "
               "rate %s; flag-none has recall %s and false positive rate %s." % (
                   fmt(P, P), fmt(Nn, Nn), fmt(0, P), fmt(0, Nn)))
    return "\n".join(out)


def materialise(ids_file, out):
    """Write the listed fixtures as item-NN folders and a blank sheet; the key stays with the seat."""
    ids = [ln.strip() for ln in open(ids_file, encoding="utf-8") if ln.strip()]
    idx = by_id()
    order = sorted(ids, key=lambda f: hashlib.sha256(("order:" + f).encode()).hexdigest())
    os.makedirs(out, exist_ok=True)
    sheet, key = ["item\tcheck\tlabel"], ["item\tfixture_id"]
    for n, fid in enumerate(order, 1):
        c, lab, i = idx[fid]
        write_files(fx.build(c, lab, i)[2], os.path.join(out, "item-%02d" % n))
        sheet.append("%02d\t%s\t" % (n, c))
        key.append("%02d\t%s" % (n, fid))
    with open(os.path.join(out, "sheet.tsv"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(sheet) + "\n")
    with open(os.path.join(out, "KEY-do-not-give-to-labeller.tsv"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(key) + "\n")
    print("%d items in %s" % (len(order), out))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="run.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("manifest")
    r = sub.add_parser("run")
    r.add_argument("--split", choices=("dev", "test"), required=True)
    r.add_argument("--manifest-hash")
    m = sub.add_parser("materialise")
    m.add_argument("--ids", required=True)
    m.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "manifest":
        with open(MANIFEST, "wb") as fh:
            fh.write(manifest_bytes(build_manifest()))
        print("manifest.json sha256 " + file_hash(MANIFEST))
    elif a.cmd == "run":
        counts, wrong = run(a.split, a.manifest_hash)
        print(table(counts))
        print("\nraw counts: " + json.dumps(counts, sort_keys=True))
        print("\nwrong calls (%d):" % len(wrong))
        for k, fid, prop in wrong:
            print("  %s %s: %s" % (k, fid, prop))
    else:
        materialise(a.ids, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
