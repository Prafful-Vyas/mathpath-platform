"""Practice table access patterns (single table):

  skill per topic   PK=STUDENT#<id>  SK=SKILL#<topic>                       rating, attempts, correct, version
  attempt log       PK=STUDENT#<id>  SK=ATTEMPT#<topic>#<iso ts>#<attempt>  newest-first query for recent problems
  idempotency key   PK=STUDENT#<id>  SK=IDEMP#<attempt id>                  stored response for replays

One answer submission is a single TransactWriteItems call: the idempotency key must not
exist yet and the skill item must still have the version that was read (optimistic locking),
so a retried request or two tabs submitting at once can never double-count an attempt."""

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from mathpath_common.dynamo import PRACTICE_TABLE, to_ddb, to_plain


class DuplicateAttempt(Exception):
    pass


class VersionConflict(Exception):
    pass


class PracticeRepository:
    def __init__(self, ddb):
        self.table = ddb.Table(PRACTICE_TABLE)
        self.client = ddb.meta.client  # resource-backed client: takes plain Python values, not {"S": ...}

    def get_skill(self, student: str, topic: str) -> dict | None:
        item = self.table.get_item(Key={"PK": f"STUDENT#{student}", "SK": f"SKILL#{topic}"}, ConsistentRead=True)
        return to_plain(item["Item"]) if "Item" in item else None

    def list_skills(self, student: str) -> list[dict]:
        items = self.table.query(
            KeyConditionExpression=Key("PK").eq(f"STUDENT#{student}") & Key("SK").begins_with("SKILL#"),
        )["Items"]
        return [to_plain(i) for i in items]

    def recent_problem_ids(self, student: str, topic: str, n: int = 15) -> list[str]:
        items = self.table.query(
            KeyConditionExpression=Key("PK").eq(f"STUDENT#{student}") & Key("SK").begins_with(f"ATTEMPT#{topic}#"),
            ScanIndexForward=False, Limit=n, ProjectionExpression="problem_id",
        )["Items"]
        return [i["problem_id"] for i in items]

    def get_replay(self, student: str, attempt_id: str) -> dict | None:
        item = self.table.get_item(Key={"PK": f"STUDENT#{student}", "SK": f"IDEMP#{attempt_id}"}, ConsistentRead=True)
        return to_plain(item["Item"])["response"] if "Item" in item else None

    def record_attempt(self, student: str, attempt: dict, skill: dict, read_version: int, response: dict) -> None:
        pk = f"STUDENT#{student}"
        skill_cond = ({"ConditionExpression": "attribute_not_exists(PK)"} if read_version == 0 else
                      {"ConditionExpression": "version = :v", "ExpressionAttributeValues": {":v": read_version}})
        items = [
            {"Put": {"TableName": PRACTICE_TABLE, "ConditionExpression": "attribute_not_exists(PK)",
                     "Item": to_ddb({"PK": pk, "SK": f"IDEMP#{attempt['attempt_id']}", "response": response})}},
            {"Put": {"TableName": PRACTICE_TABLE,
                     "Item": to_ddb({"PK": pk, "SK": f"ATTEMPT#{attempt['topic']}#{attempt['at']}#{attempt['attempt_id']}",
                                     **attempt})}},
            {"Put": {"TableName": PRACTICE_TABLE, **skill_cond,
                     "Item": to_ddb({"PK": pk, "SK": f"SKILL#{skill['topic']}", **skill})}},
        ]
        try:
            self.client.transact_write_items(TransactItems=items)
        except ClientError as e:
            if e.response["Error"]["Code"] != "TransactionCanceledException":
                raise
            reasons = [r.get("Code") for r in e.response.get("CancellationReasons", [])]
            if reasons and reasons[0] == "ConditionalCheckFailed":
                raise DuplicateAttempt from e
            if len(reasons) > 2 and reasons[2] == "ConditionalCheckFailed":
                raise VersionConflict from e
            raise
