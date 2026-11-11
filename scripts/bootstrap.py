"""Creates both DynamoDB tables and loads the seed problem bank (safe to re-run).
Run: DYNAMODB_ENDPOINT=http://localhost:8001 python -m scripts.bootstrap"""

import json
from pathlib import Path

from botocore.exceptions import ClientError

from content_service.repository import ContentRepository
from mathpath_common.dynamo import create_tables, resource

SEED = Path(__file__).resolve().parent.parent / "seed"


def load_seed(ddb) -> tuple[int, int]:
    create_tables(ddb)
    repo = ContentRepository(ddb)
    topics = json.loads((SEED / "topics.json").read_text(encoding="utf-8"))
    problems = json.loads((SEED / "problems.json").read_text(encoding="utf-8"))
    for t in topics:
        repo.put_topic(t)
    added = 0
    for p in problems:
        try:
            repo.put_problem(p)
            added += 1
        except ClientError as e:
            if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise
    return len(topics), added


if __name__ == "__main__":
    print("topics=%d problems added=%d" % load_seed(resource()))
