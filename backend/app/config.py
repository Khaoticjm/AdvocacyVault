from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
import json
from typing import List


class Settings(BaseSettings):
    phi_encryption_key: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    ip_hash_salt: str
    database_url: str
    db_echo_sql: bool = False

    primary_llm_model: str = "gpt-4o"
    verifier_llm_provider: str = "anthropic"
    verifier_llm_model: str = "claude-sonnet-4-6"
    verifier_llm_api_key: str = ""

    allowed_origins: List[str] = ["http://localhost:3000"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            v = v.strip()
            # Accept JSON array: '["http://a", "http://b"]'
            if v.startswith("["):
                return json.loads(v)
            # Accept comma-separated: 'http://a,http://b'
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @model_validator(mode="after")
    def verifier_differs_from_primary(self) -> "Settings":
        if self.verifier_llm_model == self.primary_llm_model:
            raise ValueError(
                "VERIFIER_LLM_MODEL must differ from PRIMARY_LLM_MODEL. "
                "The dual-LLM verification layer requires two independent models."
            )
        return self

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()  # type: ignore[call-arg]
