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
    """
    Load previous conversations from S3 for the current day.

    Attempts to retrieve the JSON file at the configured bucket/key and parse
    it as a list of conversation entries.

    Args:
        None

    Returns:
        list: A list of conversation entries. Returns an empty list if no file
              exists for the current day.

    Raises:
        botocore.exceptions.ClientError: Propagated if the S3 get_object call
                                         fails for reasons other than a missing key.

    Example:
        >>> load_conversations()
        []
    """
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
    Save a single user-assistant exchange to the S3 bucket.

    Loads the current day's conversations, appends the provided entry, and
    writes the updated list back to S3 as a JSON file.

    Args:
        entry (dict): Conversation entry to append. Expected keys typically
                      include 'username', 'timestamp', 'question', and 'answer'.

    Returns:
        None

    Raises:
        botocore.exceptions.ClientError: If the S3 put_object call fails.
        ValueError: If the entry or resulting data cannot be serialized to JSON.

    Example:
        >>> save_conversation({
        ...     "username": "alice",
        ...     "timestamp": "2025-12-18T12:00:00",
        ...     "question": "Hi",
        ...     "answer": "Hello"
        ... })
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