"""Settings and Controls for the simulation and security part"""
from datetime import timedelta
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

# Security Parameters
CERT_VALIDITY = timedelta(minutes=10)
KEY_CURVE = ec.SECP256R1()
HASH_ALGORITHM = hashes.SHA256()
SIGNATURE_ALGORITHM = ec.ECDSA(HASH_ALGORITHM)
CA_PRIVATE_KEY_PASSWORD = b"v2x_ca_pvt_key"

# Controls
MAX_V2I_RANGE = 150         # Distance range to find nearest infrastructure
NO_OF_VEH_CERTS = 100       # Number of certificates to generate for vehicle
NO_OF_MSG_CERT_ROT = 10     # To rotate the certificate after this count of messages sent
BSM_DISTANCE = 15           # <= Distance to trigger message sharing
PSM_DISTANCE = 5            # <= Distance to trigger message sharing