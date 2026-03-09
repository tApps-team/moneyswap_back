import json
import redis

from config import (SUB_REDIS_HOST,
                    SUB_REDIS_PASSWORD,
                    SUB_REDIS_PORT)

from general_models.utils.base import EventNotificatonEnum


redis_client = redis.Redis(host=SUB_REDIS_HOST,
                           password=SUB_REDIS_PASSWORD,
                           port=SUB_REDIS_PORT)


def publish_review_notification_to_exchange_admin(user_id,
                                                  exchange_id,
                                                  review_id):
    redis_client.publish(
        "notitication_events",
        json.dumps({
            "event": f"{EventNotificatonEnum.REVIEW_EXCHANGE_ADMIN}",
            "user_id": user_id,
            "exchange_id": exchange_id,
            "review_id": review_id,
        })
    )


def publish_comment_notification_to_exchange_admin(user_id,
                                                   exchange_id,
                                                   review_id):
    redis_client.publish(
        "notitication_events",
        json.dumps({
            "event": f"{EventNotificatonEnum.COMMENT_EXCHANGE_ADMIN}",
            "user_id": user_id,
            "exchange_id": exchange_id,
            "review_id": review_id,
        })
    )


def publish_comment_notification_to_review_owner(user_id,
                                                 exchange_id,
                                                 review_id):
    redis_client.publish(
        "notitication_events",
        json.dumps({
            "event": f"{EventNotificatonEnum.COMMENT_OWNER}",
            "user_id": user_id,
            "exchange_id": exchange_id,
            "review_id": review_id,
        })
    )