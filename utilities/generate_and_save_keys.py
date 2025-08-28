"""Generate and Save Certifying Authority Keys"""
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import os

def save_private_key(key, filename):
    """
    Save the Certifying Authority private key to the disk
    Input:
    - Filename
    - Private Key
    """
    
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        # ensuring store time encryption
        encryption_algorithm=serialization.BestAvailableEncryption(b"v2x_ca_pvt_key")
    )
    with open(f"./keys/{filename}", "wb") as f:
        f.write(pem)

def save_public_key(key, filename):
    """
    Save the Certifying Authority public key to the disk
    Input:
    - Filename
    - Private Key
    """

    pem = key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo   
    )
    with open(f"./keys/{filename}", "wb") as f:
        f.write(pem)

def generate_keys(name):
    """
    Generate the Certifying Authority key pair
    Input: name of the entity
    """
    private_key = ec.generate_private_key(ec.SECP256R1()) # private key
    public_key = private_key.public_key()                 # public key
    save_private_key(private_key, f"{name}_pvt_key.pem")
    save_public_key(public_key, f"{name}_pub_key.pem")

# Driver Code
if __name__=="__main__":
    os.makedirs("./keys", exist_ok=True) # check if the directory already exists
    generate_keys("ca")                            # calling method to generate key pair
    print("✅ Keys generated and saved in 'project/keys/'")
    print(f"ℹ️🔐 Saved CA private key as ca_pvt_key.pem")
    print(f"ℹ️🔑 Saved CA public key as ca_pub_key.pem")