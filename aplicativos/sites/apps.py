from django.apps import AppConfig


class SitesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "aplicativos.sites"
    verbose_name = "Sites e BioSites"

    def ready(self) -> None:
        import aplicativos.sites.elementos  # noqa: F401
