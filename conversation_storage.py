import json
import boto3
from datetime import datetime
from botocore.exceptions import ClientError

# --- s3 bucket configuration ---
BUCKET_NAME = "man-vehicle-knowledge-base"
OBJECT_KEY = f"conversations/{datetime.now().strftime('%Y-%m-%d')}.json"

# Create the S3 client
s3 = boto3.client("s3")


def load_conversations():
    """Loads previous conversations from S3 (for the same day)."""
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY)
        content = response["Body"].read().decode("utf-8")
        data = json.loads(content)
        return data
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            # No file yet
            return []
        else:
            raise e


def save_conversation(entry):
    """
    Saves a single user-assistant exchange to the S3 bucket.
    Each entry includes username, timestamp, question, and answer.
    """
    data = load_conversations()
    data.append(entry)

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=OBJECT_KEY,
        Body=json.dumps(data, indent=4, ensure_ascii=False),
        ContentType="application/json"
    )

    print(f"[INFO] Conversation saved to S3 at {datetime.now()}")