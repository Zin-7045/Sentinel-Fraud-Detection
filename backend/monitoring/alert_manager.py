import json
import smtplib
import requests
from datetime import datetime
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, field
from collections import deque


@dataclass
class AlertEvent:
    alert_id: str
    transaction_id: str
    fraud_type: str
    risk_score: int
    merchant: str
    user_id: str
    region: str
    message: str
    timestamp: str
    acknowledged: bool = False


class AlertManager:
    def __init__(self, max_alerts: int = 100):
        self.alerts: deque = deque(maxlen=max_alerts)
        self.handlers: List[Callable] = []
        self.thresholds = {
            "risk_high": 80,
            "risk_critical": 95,
            "fraud_burst": 10,
            "latency_high": 200,
        }

    def register_handler(self, handler: Callable):
        self.handlers.append(handler)

    def create_alert(self, txn: Dict, risk_score: int) -> AlertEvent:
        event = AlertEvent(
            alert_id=str(hash(f"{txn.get('transaction_id')}{datetime.utcnow()}"))[:8],
            transaction_id=txn.get("transaction_id", "unknown"),
            fraud_type=txn.get("fraud_type", "unknown"),
            risk_score=risk_score,
            merchant=txn.get("merchant", "unknown"),
            user_id=txn.get("user_id", "unknown"),
            region=txn.get("region", "unknown"),
            message=f"HIGH RISK: {txn.get('fraud_type')} detected on {txn.get('merchant')}",
            timestamp=datetime.utcnow().isoformat(),
        )
        self.alerts.appendleft(event)
        self._notify(event)
        return event

    def _notify(self, alert: AlertEvent):
        for handler in self.handlers:
            try:
                handler(alert)
            except Exception as e:
                print(f"Alert handler error: {e}")

    def get_recent(self, count: int = 10) -> List[AlertEvent]:
        return list(self.alerts)[:count]

    def acknowledge(self, alert_id: str) -> bool:
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def check_fraud_burst(self, recent_frauds: int) -> bool:
        return recent_frauds >= self.thresholds["fraud_burst"]


class WebhookNotifier:
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url

    def send(self, alert: AlertEvent):
        if not self.webhook_url:
            return
        try:
            requests.post(
                self.webhook_url,
                json={
                    "text": f"🚨 *Fraud Alert*\n{alert.message}\n"
                            f"Risk: {alert.risk_score}/99\n"
                            f"Transaction: {alert.transaction_id}\n"
                            f"Merchant: {alert.merchant}",
                },
                timeout=5,
            )
        except requests.RequestException as e:
            print(f"Webhook error: {e}")


class EmailNotifier:
    def __init__(self, smtp_host: str, smtp_port: int,
                 sender: str, password: str, recipients: List[str]):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender = sender
        self.password = password
        self.recipients = recipients

    def send(self, alert: AlertEvent):
        try:
            msg = (
                f"Subject: FRAUD ALERT - {alert.risk_score}/99\n\n"
                f"Alert ID: {alert.alert_id}\n"
                f"Transaction: {alert.transaction_id}\n"
                f"Fraud Type: {alert.fraud_type}\n"
                f"Risk Score: {alert.risk_score}\n"
                f"Merchant: {alert.merchant}\n"
                f"User: {alert.user_id}\n"
                f"Region: {alert.region}\n"
                f"Time: {alert.timestamp}\n"
            )
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender, self.password)
                server.sendmail(self.sender, self.recipients, msg)
        except Exception as e:
            print(f"Email error: {e}")
