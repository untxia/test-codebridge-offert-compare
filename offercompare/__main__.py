import json
import sys

from .diff import compare_files
from .extract import extract_offer
from .models import to_jsonable

USAGE = "usage: python -m offercompare extract <a.pdf> | compare <original.pdf> <revised.pdf>"

if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == "extract":
        print(json.dumps(to_jsonable(extract_offer(a[1])), ensure_ascii=False, indent=2))
    elif len(a) == 3 and a[0] == "compare":
        print(json.dumps(compare_files(a[1], a[2]), ensure_ascii=False, indent=2))
    else:
        sys.exit(USAGE)
