import pytest
from cryptography.fernet import InvalidToken
from app.security import encrypt_phi, decrypt_phi, hash_ip, hash_password, verify_password, create_access_token, decode_access_token


def test_encrypt_decrypt_roundtrip():
    plaintext = "Patient reported severe chest pain was ignored by staff."
    token = encrypt_phi(plaintext)
    assert token != plaintext
    assert decrypt_phi(token) == plaintext


def test_encrypt_produces_different_tokens():
    text = "same input"
    assert encrypt_phi(text) != encrypt_phi(text)  # Fernet uses random IV


def test_decrypt_tampered_token_raises():
    token = encrypt_phi("some PHI")
    tampered = token[:-4] + "XXXX"
    with pytest.raises(Exception):
        decrypt_phi(tampered)


def test_decrypt_garbage_raises():
    with pytest.raises(Exception):
        decrypt_phi("not-a-fernet-token")


def test_hash_ip_consistent():
    ip = "192.168.1.100"
    assert hash_ip(ip) == hash_ip(ip)


def test_hash_ip_different_ips():
    assert hash_ip("10.0.0.1") != hash_ip("10.0.0.2")


def test_hash_ip_no_raw_ip_in_output():
    ip = "192.168.1.100"
    result = hash_ip(ip)
    assert ip not in result


def test_hash_ip_is_hex():
    result = hash_ip("1.2.3.4")
    int(result, 16)  # raises if not hex


def test_bcrypt_roundtrip():
    pw = "securepassword123!"
    hashed = hash_password(pw)
    assert verify_password(pw, hashed)


def test_bcrypt_wrong_password():
    hashed = hash_password("correct")
    assert not verify_password("wrong", hashed)


def test_bcrypt_hash_differs_each_time():
    pw = "same"
    assert hash_password(pw) != hash_password(pw)


def test_jwt_roundtrip():
    token = create_access_token("user-123")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"


def test_jwt_extra_claims():
    token = create_access_token("user-456", extra={"role": "adjuster"})
    payload = decode_access_token(token)
    assert payload["role"] == "adjuster"


def test_jwt_invalid_token_raises():
    with pytest.raises(ValueError):
        decode_access_token("not.a.jwt")


def test_jwt_tampered_raises():
    token = create_access_token("user-789")
    parts = token.split(".")
    parts[1] = parts[1][:-2] + "XX"
    with pytest.raises(ValueError):
        decode_access_token(".".join(parts))


def test_phi_encrypted_value_not_readable():
    narrative = "Patient has history of bipolar disorder."
    token = encrypt_phi(narrative)
    assert "bipolar" not in token
    assert "Patient" not in token


def test_phi_decrypt_preserves_unicode():
    text = "Dolor reportado: paciente describió síntomas severos. 疼痛严重。"
    assert decrypt_phi(encrypt_phi(text)) == text
