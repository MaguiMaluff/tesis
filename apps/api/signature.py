import hmac
import hashlib

def verify_x_hub_signature_256(app_secret: str, raw_body: bytes, header_value: str | None) -> bool:
    """
    Meta sends: X-Hub-Signature-256: sha256=<hex>
    We compute HMAC SHA256 of raw request body using app secret.
    """
    if not header_value:
        return False

    header_value = header_value.strip()
    if not header_value.startswith("sha256="):
        return False

    their_sig = header_value.split("sha256=", 1)[1].strip()
    mac = hmac.new(app_secret.encode("utf-8"), msg=raw_body, digestmod=hashlib.sha256)
    our_sig = mac.hexdigest()

    return hmac.compare_digest(our_sig, their_sig)