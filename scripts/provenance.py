"""Record where and when each data set was fetched: data/provenance.json."""
import json, pathlib, datetime
ROOT = pathlib.Path(__file__).resolve().parent.parent
PATH = ROOT / "data" / "provenance.json"
def record(dataset, **info):
    data = json.load(open(PATH)) if PATH.exists() else {}
    data[dataset] = {"fetched": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), **info}
    PATH.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
