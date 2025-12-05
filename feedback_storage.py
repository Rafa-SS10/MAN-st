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
    """Loads feedback data from S3 bucket"""
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
    """Appends a new feedback entry to the S3 feedback file"""
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