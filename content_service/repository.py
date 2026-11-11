"""Content table access patterns (single table, PK/SK + GSI1):

  topic catalogue   PK=CATALOG          SK=TOPIC#<order>#<slug>   (list topics in order)
  topic by slug     GSI1PK=TOPIC#<slug>  GSI1SK=META
  problems by topic PK=TOPIC#<slug>     SK=P#<rating:04d>#<id>    (range query by difficulty)
  problem by id     GSI1PK=PROBLEM#<id>  GSI1SK=PROBLEM
"""

from boto3.dynamodb.conditions import Key

from mathpath_common.dynamo import CONTENT_TABLE, to_ddb, to_plain

INTERNAL = ("PK", "SK", "GSI1PK", "GSI1SK")


def _clean(item):
    return {k: v for k, v in to_plain(item).items() if k not in INTERNAL}


def _query_all(table, **kwargs):
    items, start = [], None
    while True:
        page = table.query(**kwargs, **({"ExclusiveStartKey": start} if start else {}))
        items += page["Items"]
        if not (start := page.get("LastEvaluatedKey")):
            return items


class ContentRepository:
    def __init__(self, ddb):
        self.table = ddb.Table(CONTENT_TABLE)

    def put_topic(self, topic: dict) -> None:
        self.table.put_item(Item=to_ddb({
            "PK": "CATALOG", "SK": f"TOPIC#{topic['order']:03d}#{topic['slug']}",
            "GSI1PK": f"TOPIC#{topic['slug']}", "GSI1SK": "META", **topic,
        }))

    def list_topics(self) -> list[dict]:
        items = _query_all(self.table, KeyConditionExpression=Key("PK").eq("CATALOG") & Key("SK").begins_with("TOPIC#"))
        return [_clean(i) for i in items]

    def get_topic(self, slug: str) -> dict | None:
        items = self.table.query(
            IndexName="GSI1", KeyConditionExpression=Key("GSI1PK").eq(f"TOPIC#{slug}") & Key("GSI1SK").eq("META"),
        )["Items"]
        return _clean(items[0]) if items else None

    def put_problem(self, problem: dict) -> None:
        self.table.put_item(
            Item=to_ddb({
                "PK": f"TOPIC#{problem['topic']}", "SK": f"P#{problem['rating']:04d}#{problem['id']}",
                "GSI1PK": f"PROBLEM#{problem['id']}", "GSI1SK": "PROBLEM", **problem,
            }),
            ConditionExpression="attribute_not_exists(PK)",
        )

    def get_problem(self, problem_id: str) -> dict | None:
        items = self.table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq(f"PROBLEM#{problem_id}") & Key("GSI1SK").eq("PROBLEM"),
        )["Items"]
        return _clean(items[0]) if items else None

    def problems_near(self, slug: str, rating: int, exclude: set[str], limit: int, window: int = 250) -> list[dict]:
        """Problems closest in difficulty to `rating`. Reads only the SK range around the
        target first and falls back to the whole topic when that window is exhausted."""
        lo, hi = max(rating - window, 0), min(rating + window, 9999)
        cond = Key("PK").eq(f"TOPIC#{slug}") & Key("SK").between(f"P#{lo:04d}", f"P#{hi:04d}~")
        found = [p for p in map(_clean, _query_all(self.table, KeyConditionExpression=cond)) if p["id"] not in exclude]
        if len(found) < limit:
            cond = Key("PK").eq(f"TOPIC#{slug}") & Key("SK").begins_with("P#")
            found = [p for p in map(_clean, _query_all(self.table, KeyConditionExpression=cond))
                     if p["id"] not in exclude]
        found.sort(key=lambda p: (abs(p["rating"] - rating), p["id"]))
        return found[:limit]
