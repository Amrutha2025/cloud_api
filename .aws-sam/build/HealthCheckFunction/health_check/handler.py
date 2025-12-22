import json


def lambda_handler(event, context):
    """Simple health check Lambda for API Gateway REST proxy integration."""
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "OPTIONS,GET,POST,PATCH,PUT,DELETE",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps({"status": "ok"}),
        "isBase64Encoded": False,
    }
