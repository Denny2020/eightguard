from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All settings come from EIGHTGUARD_* environment variables."""

    model_config = SettingsConfigDict(env_prefix="EIGHTGUARD_")

    database_url: str = "postgresql+psycopg://eightguard:eightguard@localhost:5432/eightguard"
    # Public base URL of the web app (links in emails)
    public_url: str = "https://eightguard-dev.kubelab.local"
    version: str | None = None

    # OIDC (Keycloak). The issuer is the public URL in the tokens; JWKS can be fetched over the
    # cluster-internal URL so the API never depends on the public route.
    oidc_issuer: str = "https://auth.kubelab.local/realms/eightguard"
    oidc_jwks_url: str = "https://auth.kubelab.local/realms/eightguard/protocol/openid-connect/certs"
    oidc_audience: str = "eightguard-api"

    invitation_ttl_days: int = 7

    # Outgoing email (worker)
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    mail_from: str = "EightGuard <no-reply@eightguard.kubelab.local>"


settings = Settings()
