from .models import QualityParameter, QualityThreshold


def threshold_for(site, parameter, asset=None):
    """Most specific threshold: asset > asset type > site-wide."""
    qs = QualityThreshold.objects.filter(site=site, parameter=parameter)
    if asset is not None:
        t = qs.filter(asset=asset).first()
        if t:
            return t
        t = qs.filter(asset__isnull=True, asset_type=asset.type).first()
        if t:
            return t
    return qs.filter(asset__isnull=True, asset_type="").first()


def is_compliant(site, parameter, value, asset=None):
    """True / False, or None when no value or no threshold is configured."""
    if parameter == QualityParameter.ODOUR_COLOUR:
        # value is "OUI" (abnormal) / "NON"
        if value in (None, ""):
            return None
        return value == "NON"
    if value is None:
        return None
    t = threshold_for(site, parameter, asset)
    if t is None:
        return None
    if t.min_value is not None and value < t.min_value:
        return False
    if t.max_value is not None and value > t.max_value:
        return False
    return True
