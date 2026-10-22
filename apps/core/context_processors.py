from .models import SiteBranding

def site_context(request):
    site = getattr(request, 'site', None)
    if not site:
        return {}
    from .services import network_context
    from apps.engagement.intake import INTAKES, PROGRAMME_INTAKE
    network = network_context(request)
    programme = network['current_programme']
    intake_kind = PROGRAMME_INTAKE.get(programme.code, 'learning') if programme else 'learning'
    return {
        'current_site': site,
        'branding': SiteBranding.for_site(site),
        'umbrella_initiative': getattr(site, 'organisational_initiative', None),
        'primary_intake': intake_kind,
        'primary_intake_label': INTAKES[intake_kind]['label'],
        **network,
    }
