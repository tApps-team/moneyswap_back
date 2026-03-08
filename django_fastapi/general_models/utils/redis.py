import json
import redis

from config import (SUB_REDIS_HOST,
                    SUB_REDIS_PASSWORD,
                    SUB_REDIS_PORT)

redis_client = redis.Redis(host=SUB_REDIS_HOST,
                           password=SUB_REDIS_PASSWORD,
                           port=SUB_REDIS_PORT)


def publish_review_notification(user_id,
                                exchange_id,
                                review_id):
    redis_client.publish(
        "review_notifications",
        json.dumps({
            "user_id": user_id,
            "exchange_id": exchange_id,
            "review_id": review_id,
        })
    )