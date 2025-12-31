#!/bin/bash
# Setup persistent private key for hosted backend on Fly.io
# This ensures the backend_id remains stable across restarts

echo "Setting up persistent private key for hosted backend..."

# Generate a new private key specifically for hosted backend
python3 << 'EOF'
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# Generate RSA-2048 keypair
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)

# Serialize to PEM format
private_key_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
).decode()

# Save to temporary file (will be read by flyctl)
with open('/tmp/hosted_backend_key.pem', 'w') as f:
    f.write(private_key_pem)

print("✓ Generated new private key for hosted backend")
EOF

# Set as Fly.io secret
echo "Setting Fly.io secret..."
flyctl secrets set BACKEND_PRIVATE_KEY="$(cat /tmp/hosted_backend_key.pem)" --app maestra-backend-8825-systems

# Clean up
rm /tmp/hosted_backend_key.pem

echo "✓ Hosted backend private key configured"
echo "✓ Backend will use same key across restarts"
