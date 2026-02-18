"""
Celery tasks for async webhook delivery
"""
from celery import shared_task
from django.utils import timezone
import requests
from messages.models import DeviceInbox, InboxStatus
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=None)
def deliver_webhook(self, inbox_id):
    """
    Deliver message to device via webhook with retry logic
    
    Args:
        inbox_id: ID of the DeviceInbox entry
    """
    try:
        inbox = DeviceInbox.objects.get(id=inbox_id)
        device = inbox.device
        message = inbox.message
        
        if not device.webhook_url:
            logger.info(f"No webhook URL configured for device {device.hid}")
            return {'status': 'skipped', 'reason': 'no_webhook_url'}
        
        # Prepare payload
        payload = {
            'message_id': message.message_id,
            'type': message.type,
            'alert_type': message.alert_type,
            'alarm_type': message.alarm_type,
            'payload': message.payload,
            'timestamp': message.timestamp.isoformat(),
            'source_device_hid': message.source_device.hid,
            'user': message.user,
        }
        
        # Attempt delivery
        try:
            response = requests.post(
                device.webhook_url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            
            # Mark as delivered
            inbox.status = InboxStatus.DELIVERED
            inbox.delivered_at = timezone.now()
            inbox.save()
            
            logger.info(f"Webhook delivered successfully for inbox {inbox_id}")
            return {'status': 'delivered', 'inbox_id': inbox_id}
            
        except requests.RequestException as e:
            # Increment attempts
            inbox.delivery_attempts += 1
            
            if inbox.delivery_attempts >= device.retry_limit:
                # Max retries reached
                inbox.status = InboxStatus.FAILED
                inbox.save()
                logger.error(f"Webhook delivery failed after {inbox.delivery_attempts} attempts for inbox {inbox_id}")
                return {'status': 'failed', 'inbox_id': inbox_id, 'reason': 'max_retries'}
            else:
                # Retry with exponential backoff
                retry_delay = 2 ** inbox.delivery_attempts  # 2, 4, 8, 16 seconds...
                logger.warning(f"Webhook delivery failed for inbox {inbox_id}, retrying in {retry_delay}s (attempt {inbox.delivery_attempts}/{device.retry_limit})")
                inbox.save()
                
                # Schedule retry
                deliver_webhook.apply_async(
                    args=[inbox_id],
                    countdown=retry_delay
                )
                return {'status': 'retrying', 'inbox_id': inbox_id, 'attempt': inbox.delivery_attempts}
                
    except DeviceInbox.DoesNotExist:
        logger.error(f"DeviceInbox {inbox_id} not found")
        return {'status': 'error', 'reason': 'not_found'}
    except Exception as e:
        logger.error(f"Unexpected error in webhook delivery for inbox {inbox_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)  # Retry after 60 seconds on unexpected errors

