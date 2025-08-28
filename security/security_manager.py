import json
import base64
from security import settings
from datetime import datetime, timezone
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import CertificateBuilder, NameOID, Name, NameAttribute, random_serial_number

def load_ca_private_key(path):
    """
    Loads Certifying Authority's private key from the disk
    Input: Path to the key
    Ouput: CA private key
    """
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=settings.CA_PRIVATE_KEY_PASSWORD)

def load_ca_public_key(path):
    """
    Loads Certifying Authority's public key from the disk
    Input: Path to the key
    Ouput: CA public key
    """
    with open(path, "rb") as f:
        return serialization.load_pem_public_key(f.read())

def message_verifier(payload, ca):
    """
    Verifies the received payload
    Input: Payload, CA
    Output: Verification Status
    """

    # Load certificate (support both bytes and text)
    cert_pem = payload['certificate']
    if isinstance(cert_pem, str):
        cert_pem = cert_pem.encode("utf-8")
    cert = load_pem_x509_certificate(cert_pem)

    # Step 1: Verify certificate signature by CA
    try:
        ca.ca_pub_key.verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            settings.SIGNATURE_ALGORITHM
        )
    except Exception as e:
        return f"Certificate not signed by Root CA: {e}"

    # Step 2: Time validity
    now = datetime.now(timezone.utc)
    try:
        not_before = cert.not_valid_before_utc
        not_after = cert.not_valid_after_utc
    except AttributeError:
        # fallback for older cryptography versions
        not_before = cert.not_valid_before.replace(tzinfo=timezone.utc)
        not_after = cert.not_valid_after.replace(tzinfo=timezone.utc)

    if not_before > now or not_after < now:
        return "Certificate expired or not yet valid"

    # Step 3: CRL check (ca.crl stores revoked serials)
    if cert.serial_number in ca.crl:
        date = ca.crl[cert.serial_number]["date"]
        reason = ca.crl[cert.serial_number]["reason"]
        return f"Certificate {cert.serial_number} is revoked on the date {date}. Reason: {reason}"

    # Step 4: Validating the signatures in payload / Reconstruct message bytes
    message = payload["message"]
    try:
        cert.public_key().verify(
            base64.b64decode(payload['signature']),
            message,
            settings.SIGNATURE_ALGORITHM
        )
    except Exception as e:
        return f"Signatures were not verified: {e}"
    
    # Result: If everything goes right, we will execute this.
    return "Message Verified!"

class CertifyingAuthority:
    """
    All the properties and functions related to certifying authority lies here.

    Properties:
    - public_key of CA
    - private_key of CA
    - certificate revocation list (CRL)
    - list to maintain vehicles whose certificates have been issued
    - list to maintain infrastructure whose certificates have been issued

    Functions:
    - Creating certificates
    - Adding to CRL
    """

    def __init__(self):
        self.ca_pvt_key = load_ca_private_key("keys/ca_pvt_key.pem")
        self.ca_pub_key = load_ca_public_key("keys/ca_pub_key.pem")
        self.ca_vehicles = {}
        self.ca_infrastructures = {}
        self.crl = {}

    def build_certificate(self, entity_id, entity_type, entity_pub_key):
        """Generic certificate issuance for both vehicles and infrastructure"""

        certificate_number = random_serial_number()
        builder = (
            CertificateBuilder().subject_name(Name([
                NameAttribute(NameOID.COMMON_NAME, f"{entity_type}-{entity_id}"),
                NameAttribute(NameOID.ORGANIZATION_NAME, "V2X-CP")
            ]))
            .issuer_name(Name([
                NameAttribute(NameOID.COMMON_NAME, "V2X-Root-CA")
            ]))
            .public_key(entity_pub_key)
            .serial_number(certificate_number)
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + settings.CERT_VALIDITY)
        )

        cert = builder.sign(self.ca_pvt_key, settings.HASH_ALGORITHM)
        cert = cert.public_bytes(serialization.Encoding.PEM)
        
        if entity_id not in self.ca_vehicles:
            self.ca_vehicles[entity_id] = []

        if entity_type == "vehicle":
            self.ca_vehicles[entity_id].append(cert)
        else:
            self.ca_infrastructures[entity_id] = cert
        return cert
    
    def add_revocation(self, serial_number, reason, issuer):
        """
        This function will be used to add revoked certificates to the list.
        Input:
        - serial number of the certificate
        - issuer of the certificate
        - reason to blacklist
        """

        self.crl[serial_number] = {
            'issuer': issuer,
            'date': datetime.now(timezone.utc).isoformat(),
            'reason': reason
        }

class VehicleHardwareSecurityModule:
    """
    All the properties and functions related to Vehicle HSM lies here.

    Properties:
    - list of certificates of vehicle
    - list of private_keys of vehicle
    - current certificate (in use)
    - current private key (in use)
    - concerned vehicle's ID
    - current certificate and private key index number
    - message count on current certificate

    Functions:
    - Certificate rotation
    - Certificate generation request
    - Message preparation
    """
    
    def __init__(self, vehicle_id, ca):
        self.ca = ca                    # CA reference
        self.vehicle_id = vehicle_id    # concerned vehicle's ID

        # for keeping record and rotating the issued vehicle certificates
        self.index_number = 0               # index number for current certificate and private key value out of settings.NO_OF_VEH_CERTS
        self.message_count = 0              # for keeping the count of messages sent on current certificate value
        self.current_private_key = None     # current private key (in use)
        self.current_certificate = None     # current certificate (in use)

        # issued private keys and certificates list, total quantity = settings.NO_OF_VEH_CERTS
        self.private_key = []
        self.certificate = []

    def generate_vehicle_cert(self):
        """Generate a vehicle certificate and private key"""

        for _ in range(settings.NO_OF_VEH_CERTS):
            private_key = ec.generate_private_key(settings.KEY_CURVE)
            public_key = private_key.public_key()
            cert = self.ca.build_certificate(self.vehicle_id, "vehicle", public_key)
            self.private_key.append(private_key)
            self.certificate.append(cert)

        # set the first certificate and private key
        self.current_private_key = self.private_key[self.index_number]
        self.current_certificate = self.certificate[self.index_number]

    def certificate_rotation(self):
        """Certificate rotation mechanism."""

        # issue new certificates after the previous batch is exhausted
        if self.index_number == settings.NO_OF_VEH_CERTS - 1:
            # resetting all the values
            self.private_key.clear()
            self.certificate.clear()
            self.message_count = 0
            self.index_number = 0
            self.current_private_key = None
            self.current_certificate = None

            # generate new batch
            self.generate_vehicle_cert()
        
        else:
            # rotates certificates after settings.NO_OF_MSG_CERT_ROT of messages
            if self.message_count % (settings.NO_OF_MSG_CERT_ROT - 1) == 0 and self.message_count != 0:
                self.index_number = self.index_number + 1   # rotating the certificate
                self.message_count = 0                      # resetting the counter value for message_count
                # update the current private key and certificate
                self.current_private_key = self.private_key[self.index_number]
                self.current_certificate = self.certificate[self.index_number]

    def prepare_message(self, data):
        """
        Prepares data to be sent.
        Input: Entity data
        Output: Payload
        """

        self.certificate_rotation() # ensuring the certificate is rotated every prepared message

        data = dict(data)                                                   # shallow copy to avoid mutating caller's dict
        data["security_timestamp"] = datetime.now(timezone.utc).isoformat() # adding security timestamp to message
        self.message_count = self.message_count + 1                         # increment message count

        message = (json.dumps(data, sort_keys=True, separators=(',', ':'))).encode("utf-8")                                   # message preparation
        signature = base64.b64encode(self.current_private_key.sign(message, settings.SIGNATURE_ALGORITHM)).decode("ascii")    # signature generation

        # payload that is to be sent, according to ASN.1 format
        return {
            'message': message,                         # message as per SAE J2735_202409
            'signature': signature,                     # as per ECDSA and SHA256
            'certificate': self.current_certificate     # as per X.509 standard
        }

class InfrastructureHardwareSecurityModule:
    """
    All the properties and functions related to Infrastructure HSM lies here.

    Properties:
    - certificate of infrastructure
    - private_key of infrastructure
    - concerned infrastructure's ID
    - message count

    Functions:
    - Certificate generation request
    - Message preparation
    """

    def __init__(self, infra_id, ca):
        self.ca = ca                # CA reference
        self.infra_id = infra_id    # concerned infrastructure's ID
        self.private_key = None     # private_key of infrastructure
        self.certificate = None     # certificate of infrastructure
        self.message_count = 0      # message count

    def generate_infra_cert(self):
        """Generate an infrastructure certificate and private key."""

        private_key = ec.generate_private_key(settings.KEY_CURVE)
        public_key = private_key.public_key()
        cert = self.ca.build_certificate(self.infra_id, "infrastructure", public_key)
        self.private_key = private_key
        self.certificate = cert
    
    def prepare_message(self, data):
        """
        Prepares data to be sent.
        Input: Entity data
        Output: Payload
        """

        self.message_count = self.message_count + 1                                              # incrementing the message count
        data = dict(data)                                                                        # shallow copy to avoid mutating caller's dict
        data["security_timestamp"] = datetime.now(timezone.utc).isoformat()                                             # adding security timestamp to message
        message = (json.dumps(data, sort_keys=True, separators=(',', ':'))).encode("utf-8")                             # message preparation
        signature = base64.b64encode(self.private_key.sign(message, settings.SIGNATURE_ALGORITHM)).decode("ascii")      # signature generation

        # payload that is to be sent, according to ASN.1 format
        return {
            'message': message,                 # message as per SAE J2735_202409
            'signature': signature,             # as per ECDSA and SHA256
            'certificate': self.certificate     # as per X.509 standard
        }