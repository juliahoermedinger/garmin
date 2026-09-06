"""One-time helper to generate a VAPID keypair for Web Push notifications.

Run with: python -m app.generate_vapid_keys

Prints VAPID_PRIVATE_KEY and VAPID_PUBLIC_KEY as the raw base64url strings
`pywebpush`/the browser's PushManager expect (not PEM) - copy both into your
.env / Render environment variables, along with VAPID_CONTACT_EMAIL.
"""

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid02
from py_vapid.utils import b64urlencode


def main() -> None:
    vapid = Vapid02()
    vapid.generate_keys()

    private_raw = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
    public_raw = vapid.public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )

    print(f"VAPID_PRIVATE_KEY={b64urlencode(private_raw)}")
    print(f"VAPID_PUBLIC_KEY={b64urlencode(public_raw)}")


if __name__ == "__main__":
    main()
