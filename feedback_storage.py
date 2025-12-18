import json
import boto3
from datetime import datetime
from botocore.exceptions import ClientError

# --- s3 bucket configuration ---
BUCKET_NAME = "man-vehicle-knowledge-base"
OBJECT_KEY = "feedback/feedback.json"

# Create the S3 client
s3 = boto3.client("s3")


def load_feedback():
    """
    Load feedback data from the S3 feedback file.

    Attempts to retrieve the JSON feedback file from S3, parse it into a list
    of entries, and perform backward-compatibility key normalization for
    older feedback shapes.

    Args:
        None

    Returns:
        list: A list of feedback entries. Returns an empty list if the S3 key
              does not exist yet.

    Raises:
        botocore.exceptions.ClientError: If the S3 get_object call fails for
                                         reasons other than the key missing.

    Example:
        >>> load_feedback()
        []
    """
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY)
        content = response["Body"].read().decode("utf-8")
        data = json.loads(content)

        # ✅ Backward compatibility: convert old keys if necessary
        for entry in data:
            if "relevance_score" in entry and "tone_style_score" not in entry:
                entry["tone_style_score"] = entry.pop("relevance_score")
            if "relevance_notes" in entry and "tone_style_notes" not in entry:
                entry["tone_style_notes"] = entry.pop("relevance_notes")

        return data

    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            # No feedback file yet, return empty list
            return []
        else:
            raise e


def save_feedback(entry):
    """
    Append a new feedback entry to the S3 feedback file.

    Loads the existing feedback list, appends the provided entry, and writes
    the updated JSON back to the configured S3 key.

    Args:
        entry (dict): Feedback entry to append. Expected keys may include
                      'username', 'timestamp', 'tone_style_score', and notes.

    Returns:
        None

    Raises:
        botocore.exceptions.ClientError: If the S3 put_object call fails.
        ValueError: If the entry or resulting data cannot be serialized to JSON.

    Example:
        >>> save_feedback({
        ...     "username": "alice",
        ...     "timestamp": "2025-12-18T12:00:00",
        ...     "tone_style_score": 4,
        ...     "tone_style_notes": "Helpful response"
        ... })
    """
    # Load existing feedback
    data = load_feedback()

    # Add new entry
    data.append(entry)

    # Upload updated data back to S3
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=OBJECT_KEY,
        Body=json.dumps(data, indent=4, ensure_ascii=False),
        ContentType="application/json"
    )

    print(f"[INFO] Feedback saved to S3 at {datetime.now()}")